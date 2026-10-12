import io
import logging
import os
import re
import shutil
import subprocess
import zipfile
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import urlparse

import httpx

from backend.app.config import settings

logger = logging.getLogger("codereview.github")


class GitHubSecurityError(Exception):
    pass


class GitHubService:
    ALLOWED_HOSTS = ["github.com", "www.github.com", "api.github.com"]

    @classmethod
    def find_git_binary(cls) -> Optional[str]:
        """Locates the git executable on the system, checking standard PATH and common installation paths."""
        git_path = shutil.which("git")
        if git_path and os.path.exists(git_path):
            return git_path

        candidates = [
            r"C:\Program Files\Git\cmd\git.exe",
            r"C:\Program Files\Git\bin\git.exe",
            r"C:\Program Files (x86)\Git\cmd\git.exe",
            r"C:\Program Files (x86)\Git\bin\git.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\cmd\git.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Git\bin\git.exe"),
            os.path.expandvars(r"%PROGRAMFILES%\Git\cmd\git.exe"),
            "/usr/bin/git",
            "/usr/local/bin/git",
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return None

    @classmethod
    def validate_repo_url(cls, repo_url: str) -> Tuple[bool, str]:
        """
        Validates the GitHub repository URL to ensure:
        - Must be https protocol
        - Must be from an allowed host (github.com)
        - Matches standard repository format (owner/repo)
        - Blocks command injection or shell escapes
        """
        if not repo_url or not isinstance(repo_url, str):
            return False, "Repository URL cannot be empty."

        repo_url = repo_url.strip()
        # Auto-prefix https if user entered without scheme
        if repo_url.startswith("github.com/") or repo_url.startswith("www.github.com/"):
            repo_url = f"https://{repo_url}"

        try:
            parsed = urlparse(repo_url)
        except Exception:
            return False, "Malformed URL."

        if parsed.scheme != "https":
            return False, "Only secure HTTPS URLs are allowed (https://github.com/owner/repo)."

        if parsed.netloc.lower() not in cls.ALLOWED_HOSTS:
            return False, f"Domain '{parsed.netloc}' is not allowed. Only official github.com repositories are accepted."

        # Path must be /owner/repo or /owner/repo.git
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        if len(path_parts) < 2:
            return False, "Invalid GitHub repository path. Format must be https://github.com/owner/repo"

        owner, repo = path_parts[0], path_parts[1]
        repo_clean = repo.removesuffix(".git")

        # Sanitize name format
        valid_name_regex = r"^[a-zA-Z0-9_\-\.]+$"
        if not re.match(valid_name_regex, owner) or not re.match(valid_name_regex, repo_clean):
            return False, "Repository owner or name contains invalid characters."

        clean_url = f"https://github.com/{owner}/{repo_clean}.git"
        return True, clean_url

    @classmethod
    def _download_repository_archive(
        cls,
        clean_url: str,
        target_dir: Path,
        branch: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout_seconds: int = 60,
    ) -> Dict[str, Any]:
        """
        Fallback downloader when Git CLI is unavailable or fails.
        Downloads repository zip archive directly via HTTPS and extracts into target_dir.
        """
        parsed = urlparse(clean_url)
        path_parts = [p for p in parsed.path.strip("/").split("/") if p]
        owner, repo = path_parts[0], path_parts[1].removesuffix(".git")

        token = auth_token or settings.GITHUB_TOKEN
        headers = {
            "User-Agent": "CodeReviewSystem-Scanner",
            "Accept": "application/vnd.github.v3+json",
        }
        if token:
            headers["Authorization"] = f"token {token}"

        target_branch = branch or "main"
        urls_to_try = [
            f"https://github.com/{owner}/{repo}/archive/refs/heads/{target_branch}.zip",
        ]
        if not branch or branch == "main":
            urls_to_try.append(f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip")
        urls_to_try.append(f"https://api.github.com/repos/{owner}/{repo}/zipball")

        last_error = None
        extracted = False

        for url in urls_to_try:
            try:
                with httpx.Client(timeout=timeout_seconds, follow_redirects=True) as client:
                    resp = client.get(url, headers=headers)
                    if resp.status_code == 200 and len(resp.content) > 0:
                        with zipfile.ZipFile(io.BytesIO(resp.content)) as zf:
                            members = zf.infolist()
                            if not members:
                                continue

                            # GitHub zipballs prefix all contents with repo-branch/
                            root_prefix = members[0].filename.split("/")[0] + "/"

                            for member in members:
                                rel_path = member.filename
                                if rel_path.startswith(root_prefix):
                                    rel_path = rel_path[len(root_prefix):]
                                if not rel_path:
                                    continue

                                dest_path = target_dir / rel_path
                                if member.is_dir():
                                    dest_path.mkdir(parents=True, exist_ok=True)
                                else:
                                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                                    with zf.open(member) as src, open(dest_path, "wb") as dst:
                                        dst.write(src.read())

                            extracted = True
                            break
                    else:
                        last_error = f"HTTP {resp.status_code}"
            except Exception as e:
                last_error = str(e)

        if not extracted or not any(target_dir.iterdir()):
            raise GitHubSecurityError(
                f"Could not clone repository with Git and HTTP fallback failed ({last_error}). "
                "Please verify the repository is public or supply a valid GitHub token."
            )

        return {
            "status": "SUCCESS",
            "repo_url": clean_url,
            "commit_sha": "archive-head",
            "branch": branch or target_branch,
            "target_dir": str(target_dir),
        }

    @classmethod
    def clone_repository(
        cls,
        repo_url: str,
        target_dir: Path,
        branch: Optional[str] = None,
        commit: Optional[str] = None,
        auth_token: Optional[str] = None,
        timeout_seconds: int = 60,
    ) -> Dict[str, Any]:
        """
        Performs a secure shallow git clone into the isolated target_dir.
        Enforces:
        - Strict parameter passing to git (no shell interpolation)
        - Shallow depth 1 for speed and resource limits
        - Fallback to HTTP zip archive if Git CLI is missing or clone fails
        - Commit hash extraction
        """
        valid, clean_url_or_err = cls.validate_repo_url(repo_url)
        if not valid:
            raise GitHubSecurityError(clean_url_or_err)

        target_dir.mkdir(parents=True, exist_ok=True)
        # Clear any stale contents in target_dir
        for item in target_dir.iterdir():
            if item.is_dir():
                shutil.rmtree(item, ignore_errors=True)
            else:
                try:
                    item.unlink(missing_ok=True)
                except Exception:
                    pass

        token = auth_token or settings.GITHUB_TOKEN
        clone_url = clean_url_or_err
        if token:
            parsed = urlparse(clean_url_or_err)
            clone_url = f"https://x-access-token:{token}@{parsed.netloc}{parsed.path}"

        clean_branch = None
        if branch and branch.strip().lower() not in ["", "default", "head", "none"]:
            clean_branch = branch.strip()

        git_bin = cls.find_git_binary()
        if not git_bin:
            logger.info("Git binary not found on system PATH. Using direct HTTPS archive download.")
            return cls._download_repository_archive(
                clean_url_or_err, target_dir, branch=clean_branch, auth_token=token, timeout_seconds=timeout_seconds
            )

        # Build git clone command with explicit binary
        git_cmd = [git_bin, "clone", "--depth", "1"]
        if clean_branch and not commit:
            if re.match(r"^[a-zA-Z0-9_\-\./]+$", clean_branch):
                git_cmd.extend(["--branch", clean_branch])

        git_cmd.extend([clone_url, str(target_dir.resolve())])

        env = os.environ.copy()
        git_dir = str(Path(git_bin).parent)
        if git_dir not in env.get("PATH", ""):
            env["PATH"] = f"{git_dir};" + env.get("PATH", "")

        clone_succeeded = False
        try:
            result = subprocess.run(
                git_cmd,
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                env=env,
            )
            if result.returncode == 0:
                clone_succeeded = True
            elif clean_branch and ("Remote branch" in (result.stderr or "") or "not found" in (result.stderr or "")):
                # If specified branch failed, retry with default branch
                logger.warning(f"Branch '{clean_branch}' not found. Retrying shallow clone on default branch...")
                for item in target_dir.iterdir():
                    if item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                    else:
                        item.unlink(missing_ok=True)
                fallback_cmd = [git_bin, "clone", "--depth", "1", clone_url, str(target_dir.resolve())]
                fallback_res = subprocess.run(
                    fallback_cmd, capture_output=True, text=True, timeout=timeout_seconds, env=env
                )
                if fallback_res.returncode == 0:
                    clone_succeeded = True
        except Exception as e:
            logger.warning(f"Git execution error: {e}")

        # If Git clone failed, seamlessly fall back to HTTP archive
        if not clone_succeeded:
            logger.info("Git clone command failed. Switching to direct HTTPS archive fallback...")
            return cls._download_repository_archive(
                clean_url_or_err, target_dir, branch=clean_branch, auth_token=token, timeout_seconds=timeout_seconds
            )

        # If specific commit requested and commit is valid hex
        if commit and re.match(r"^[a-fA-F0-9]{7,40}$", commit):
            try:
                subprocess.run(
                    [git_bin, "fetch", "--depth", "1", "origin", commit],
                    cwd=str(target_dir),
                    capture_output=True,
                    timeout=30,
                    env=env,
                )
                subprocess.run(
                    [git_bin, "checkout", commit],
                    cwd=str(target_dir),
                    capture_output=True,
                    timeout=15,
                    env=env,
                )
            except Exception as e:
                logger.warning(f"Could not checkout specific commit {commit}: {e}")

        # Extract commit SHA
        commit_sha = "unknown"
        try:
            rev_res = subprocess.run(
                [git_bin, "rev-parse", "HEAD"],
                cwd=str(target_dir),
                capture_output=True,
                text=True,
                timeout=10,
                env=env,
            )
            if rev_res.returncode == 0:
                commit_sha = rev_res.stdout.strip()
        except Exception:
            pass

        return {
            "status": "SUCCESS",
            "repo_url": clean_url_or_err,
            "commit_sha": commit_sha,
            "branch": clean_branch or "default",
            "target_dir": str(target_dir),
        }
