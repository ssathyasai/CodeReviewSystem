"""
GitHub Integration Service
Handles webhooks from GitHub for automatic code review on push events
"""

import asyncio
import hmac
import hashlib
import tempfile
import shutil
import os
from typing import Dict, Optional
from pathlib import Path
import subprocess
import json


class GitHubIntegration:
    """
    Handles GitHub webhook events and triggers code analysis
    """
    
    def __init__(self, webhook_secret: Optional[str] = None):
        """
        Initialize GitHub integration
        
        Args:
            webhook_secret: Secret key for verifying GitHub webhooks (optional but recommended)
        """
        self.webhook_secret = webhook_secret or os.getenv("GITHUB_WEBHOOK_SECRET")
        self.temp_dir = tempfile.gettempdir()
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """
        Verify GitHub webhook signature
        
        Args:
            payload: Raw request body
            signature: X-Hub-Signature-256 header value
        
        Returns:
            True if signature is valid, False otherwise
        """
        if not self.webhook_secret:
            # Check environment dynamically
            self.webhook_secret = os.getenv("GITHUB_WEBHOOK_SECRET")
            
        if not self.webhook_secret:
            # If no secret is configured at all in env or instance, log warning
            print("⚠️ GitHub webhook secret not configured. Signature check bypassed.")
            return True
        
        if not signature:
            print("❌ Webhook request rejected: Missing X-Hub-Signature-256 header")
            return False
        
        # GitHub sends signature as "sha256=<hash>"
        expected_signature = 'sha256=' + hmac.new(
            self.webhook_secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        is_valid = hmac.compare_digest(expected_signature, signature)
        if not is_valid:
            print("❌ Webhook request rejected: Invalid HMAC signature")
        return is_valid
    
    async def handle_push_event(self, payload: Dict) -> Dict:
        """
        Handle GitHub push event
        
        Args:
            payload: GitHub webhook payload
        
        Returns:
            Analysis results
        """
        try:
            # Extract relevant information
            repo_name = payload.get('repository', {}).get('full_name')
            repo_url = payload.get('repository', {}).get('clone_url')
            branch = payload.get('ref', '').replace('refs/heads/', '')
            commits = payload.get('commits', [])
            pusher = payload.get('pusher', {}).get('name', 'unknown')
            
            if not repo_url or not branch:
                return {
                    "status": "error",
                    "message": "Invalid payload: missing repository or branch information"
                }
            
            print(f"\n{'='*60}")
            print(f"📥 GitHub Push Event Received")
            print(f"{'='*60}")
            print(f"Repository: {repo_name}")
            print(f"Branch: {branch}")
            print(f"Pusher: {pusher}")
            print(f"Commits: {len(commits)}")
            print(f"{'='*60}\n")
            
            # Clone the repository
            clone_path = await self.clone_repository(repo_url, branch)
            
            if not clone_path:
                return {
                    "status": "error",
                    "message": "Failed to clone repository"
                }
            
            try:
                # Get changed files from commits
                changed_files = self.extract_changed_files(commits)
                
                # Analyze changed files
                results = await self.analyze_repository(
                    clone_path,
                    changed_files,
                    repo_name,
                    branch
                )
                
                # Add metadata
                results['metadata'] = {
                    'repository': repo_name,
                    'branch': branch,
                    'pusher': pusher,
                    'commit_count': len(commits),
                    'changed_files': changed_files
                }
                
                return results
                
            finally:
                # Cleanup cloned repository
                self.cleanup_repository(clone_path)
        
        except Exception as e:
            print(f"❌ Error handling push event: {e}")
            import traceback
            traceback.print_exc()
            return {
                "status": "error",
                "message": str(e)
            }
    
    async def handle_pull_request_event(self, payload: Dict) -> Dict:
        """
        Handle GitHub Pull Request webhook event:
        1. Extract PR info (action, repo, PR#, branch, author)
        2. Clone PR source branch and run security analysis
        3. Format automated review comment
        4. Post review comment back to GitHub PR via API
        """
        try:
            action = payload.get('action', 'opened')
            pr_data = payload.get('pull_request', {})
            pr_number = pr_data.get('number', payload.get('number', 1))
            pr_title = pr_data.get('title', 'Pull Request Audit')
            pr_author = pr_data.get('user', {}).get('login') or payload.get('pusher', {}).get('name', 'developer')
            
            repo_data = payload.get('repository', {})
            repo_name = repo_data.get('full_name', 'ssathyasai/CodeReviewSystem')
            repo_url = repo_data.get('clone_url') or f"https://github.com/{repo_name}.git"
            
            head_branch = pr_data.get('head', {}).get('ref') or 'main'
            base_branch = pr_data.get('base', {}).get('ref') or 'main'
            
            print(f"\n{'='*60}")
            print(f"🔀 GitHub Pull Request Webhook Event Received")
            print(f"{'='*60}")
            print(f"Action: {action}")
            print(f"Repository: {repo_name}")
            print(f"PR #{pr_number}: {pr_title}")
            print(f"Author: {pr_author}")
            print(f"Head Branch: {head_branch} -> Base Branch: {base_branch}")
            print(f"{'='*60}\n")
            
            clone_path = await self.clone_repository(repo_url, head_branch)
            if not clone_path:
                return {
                    "status": "error",
                    "message": f"Failed to clone PR branch '{head_branch}'"
                }
            
            try:
                results = await self.analyze_repository(
                    clone_path,
                    changed_files=[],
                    repo_name=repo_name,
                    branch=head_branch
                )
                
                results['scan_type'] = 'github_pr'
                results['event_type'] = 'pull_request'
                results['pr_number'] = pr_number
                results['pr_title'] = pr_title
                results['pr_author'] = pr_author
                results['pr_action'] = action
                results['metadata'] = {
                    'repository': repo_name,
                    'branch': head_branch,
                    'base_branch': base_branch,
                    'pusher': pr_author,
                    'pr_number': pr_number,
                    'pr_title': pr_title,
                    'commit_count': 1,
                    'changed_files': [f['path'] for f in results.get('files', [])]
                }
                
                comment_text = self.format_pr_comment_markdown(results)
                results['pr_comment_markdown'] = comment_text
                
                post_status = await self.post_pr_comment(repo_name, pr_number, comment_text)
                results['github_comment_posted'] = post_status.get('success', False)
                results['github_comment_response'] = post_status.get('message', '')
                
                return results
            finally:
                self.cleanup_repository(clone_path)
                
        except Exception as e:
            print(f"❌ Error handling pull request event: {e}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}

    def format_pr_comment_markdown(self, results: Dict) -> str:
        """Format an automated code review comment for GitHub Pull Request"""
        verdict = results.get('status', 'success').upper()
        msg = results.get('message', 'Review complete')
        summary = results.get('summary', {})
        files = results.get('files', [])
        
        icon = "✅" if verdict in ['SUCCESS', 'INFO'] else "⚠️" if verdict == 'WARNING' else "🚨"
        
        md = f"### {icon} CodeIntelligence Automated PR Review\n\n"
        md += f"**Verdict**: `{verdict}` — {msg}\n\n"
        md += f"| Metric | Count |\n| --- | --- |\n"
        md += f"| 🚨 Critical | {summary.get('critical_issues', 0)} |\n"
        md += f"| ⚠️ High | {summary.get('high_issues', 0)} |\n"
        md += f"| ⚡ Medium | {summary.get('medium_issues', 0)} |\n"
        md += f"| ℹ️ Total Issues | {summary.get('total_issues', 0)} |\n\n"
        
        if files:
            md += "#### 📁 Audited Code Files\n"
            for f in files:
                md += f"- `{f.get('path')}` ({f.get('findings_count', 0)} issue(s))\n"
                
        md += "\n---\n*Automated review by CodeIntelligence Agent • OWASP & SAST Enforced*"
        return md

    async def post_pr_comment(self, repo_name: str, pr_number: int, review_body: str) -> Dict:
        """Post review comment to GitHub Pull Request via GitHub REST API"""
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            print("[GitHub Notice] GITHUB_TOKEN not configured in .env. Skipping live API comment posting.")
            return {"success": False, "message": "GITHUB_TOKEN missing in server environment"}
            
        try:
            import urllib.request
            url = f"https://api.github.com/repos/{repo_name}/issues/{pr_number}/comments"
            data = json.dumps({"body": review_body}).encode('utf-8')
            req = urllib.request.Request(
                url,
                data=data,
                headers={
                    "Authorization": f"token {token}",
                    "Accept": "application/vnd.github.v3+json",
                    "User-Agent": "CodeReviewAgent/2.0",
                    "Content-Type": "application/json"
                },
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                if resp.status in [200, 201]:
                    print(f"✅ Successfully posted automated comment to GitHub PR #{pr_number}")
                    return {"success": True, "message": f"Posted review comment to PR #{pr_number}"}
                return {"success": False, "message": f"HTTP {resp.status}"}
        except Exception as e:
            print(f"❌ Failed to post PR comment to GitHub API: {e}")
            return {"success": False, "message": str(e)}
    
    async def clone_repository(self, repo_url: str, branch: str = "main") -> Optional[str]:
        """
        Clone or download GitHub repository to temporary directory.
        Tries git clone first, falls back to downloading repository ZIP if git is missing.
        """
        clone_dir = os.path.join(
            self.temp_dir,
            f"github_review_{os.urandom(8).hex()}"
        )
        
        print(f"[GitHub] Fetching repository: {repo_url} (branch: {branch})")
        
        # 1. Try git clone
        try:
            result = subprocess.run(
                ['git', 'clone', '--depth', '1', '--branch', branch, repo_url, clone_dir],
                capture_output=True,
                text=True,
                timeout=60
            )
            if result.returncode == 0 and os.path.exists(clone_dir):
                print(f"[GitHub] Repository cloned successfully via Git")
                return clone_dir
        except (FileNotFoundError, Exception) as e:
            print(f"[GitHub Warning] Git CLI not available or failed: {e}. Falling back to ZIP download...")

        # 2. Native Python HTTP ZIP download fallback (No Git binary required!)
        try:
            import urllib.request
            import zipfile
            import io
            
            clean_url = repo_url.rstrip('/').replace('.git', '')
            if 'github.com/' in clean_url:
                parts = clean_url.split('github.com/')[-1].split('/')
                if len(parts) >= 2:
                    owner, repo = parts[0], parts[1]
                    zip_urls = [
                        f"https://github.com/{owner}/{repo}/archive/refs/heads/{branch}.zip",
                        f"https://github.com/{owner}/{repo}/archive/refs/heads/main.zip",
                        f"https://github.com/{owner}/{repo}/archive/refs/heads/master.zip",
                        f"https://api.github.com/repos/{owner}/{repo}/zipball/{branch}"
                    ]
                    
                    for z_url in zip_urls:
                        try:
                            req = urllib.request.Request(z_url, headers={"User-Agent": "CodeReviewAgent/2.0"})
                            with urllib.request.urlopen(req, timeout=30) as resp:
                                zip_bytes = resp.read()
                                if zip_bytes and len(zip_bytes) > 100:
                                    os.makedirs(clone_dir, exist_ok=True)
                                    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
                                        z.extractall(clone_dir)
                                    print(f"[GitHub] Repository downloaded successfully via GitHub ZIP Archive!")
                                    return clone_dir
                        except Exception as ze:
                            print(f"  Attempted {z_url}: {ze}")
        except Exception as fallback_err:
            print(f"[GitHub Error] ZIP download fallback error: {fallback_err}")

        return None
    
    def extract_changed_files(self, commits: list) -> list:
        """
        Extract list of changed Python files from commits
        
        Args:
            commits: List of commit objects from GitHub payload
        
        Returns:
            List of changed Python file paths
        """
        changed_files = set()
        
        for commit in commits:
            # Get added, modified, and removed files
            for file in commit.get('added', []):
                if file.endswith('.py'):
                    changed_files.add(file)
            
            for file in commit.get('modified', []):
                if file.endswith('.py'):
                    changed_files.add(file)
        
        return list(changed_files)
    
    async def analyze_repository(
        self,
        repo_path: str,
        changed_files: list,
        repo_name: str,
        branch: str
    ) -> Dict:
        """
        Analyze repository using the code intelligence engines
        
        Args:
            repo_path: Path to cloned repository
            changed_files: List of files to analyze
            repo_name: Repository name
            branch: Branch name
        
        Returns:
            Analysis results
        """
        from engines.sast_engine import run_semgrep_analysis
        from engines.governance_engine_api import run_governance_check
        from engines.dast_engine import run_runtime_analysis
        
        print(f"\n{'='*60}")
        print(f"[Analysis] Starting Code Analysis")
        print(f"{'='*60}")
        
        # If no specific files changed, analyze all Python files
        if not changed_files:
            print("No specific files in commits, analyzing all Python files...")
            changed_files = []
            for root, dirs, files in os.walk(repo_path):
                # Skip .git and common ignore patterns
                dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', 'venv', '.venv']]
                for file in files:
                    if file.endswith('.py'):
                        rel_path = os.path.relpath(os.path.join(root, file), repo_path)
                        changed_files.append(rel_path)
        
        print(f"Analyzing {len(changed_files)} Python files")
        
        results = {
            "repository": repo_name,
            "branch": branch,
            "files_analyzed": len(changed_files),
            "files": [],
            "summary": {
                "total_issues": 0,
                "critical_issues": 0,
                "high_issues": 0,
                "medium_issues": 0,
                "low_issues": 0
            }
        }
        
        # Analyze each file
        for file_rel_path in changed_files:
            file_path = os.path.join(repo_path, file_rel_path)
            
            if not os.path.exists(file_path):
                print(f"[Warning] File not found (may have been deleted): {file_rel_path}")
                continue
            
            print(f"\n[Analyzing] File: {file_rel_path}")
            
            try:
                # Run all three engines in parallel
                sast_task = asyncio.create_task(run_semgrep_analysis(file_path))
                governance_task = asyncio.create_task(run_governance_check(file_path))
                dast_task = asyncio.create_task(run_runtime_analysis(file_path))
                
                sast_results, governance_results, dast_results = await asyncio.gather(
                    sast_task, governance_task, dast_task
                )
                
                # Collect all findings
                all_findings = []
                all_findings.extend(sast_results.get('findings', []))
                all_findings.extend(governance_results.get('findings', []))
                all_findings.extend(dast_results.get('findings', []))
                
                # Count issues by severity
                file_summary = {
                    "critical": 0,
                    "high": 0,
                    "medium": 0,
                    "low": 0
                }
                
                for finding in all_findings:
                    severity = finding.get('severity', 'LOW').upper()
                    if severity == 'CRITICAL':
                        file_summary['critical'] += 1
                        results['summary']['critical_issues'] += 1
                    elif severity == 'HIGH':
                        file_summary['high'] += 1
                        results['summary']['high_issues'] += 1
                    elif severity == 'MEDIUM':
                        file_summary['medium'] += 1
                        results['summary']['medium_issues'] += 1
                    else:
                        file_summary['low'] += 1
                        results['summary']['low_issues'] += 1
                    
                    results['summary']['total_issues'] += 1
                
                results['files'].append({
                    "path": file_rel_path,
                    "status": "analyzed",
                    "findings_count": len(all_findings),
                    "summary": file_summary,
                    "engines": {
                        "sast": sast_results,
                        "governance": governance_results,
                        "dast": dast_results
                    }
                })
                
                # Print summary for this file
                if len(all_findings) > 0:
                    print(f"   [Notice] Found {len(all_findings)} issue(s)")
                    print(f"   Critical: {file_summary['critical']}, High: {file_summary['high']}, Medium: {file_summary['medium']}, Low: {file_summary['low']}")
                else:
                    print(f"   [OK] No issues found")
                
            except Exception as e:
                print(f"   [Error] Analysis failed: {e}")
                results['files'].append({
                    "path": file_rel_path,
                    "status": "error",
                    "error": str(e)
                })
        
        # Calculate overall status
        if results['summary']['critical_issues'] > 0:
            results['status'] = 'critical'
            results['can_deploy'] = False
            results['message'] = f"Found {results['summary']['critical_issues']} critical issue(s). Deployment blocked."
        elif results['summary']['high_issues'] > 0:
            results['status'] = 'warning'
            results['can_deploy'] = False
            results['message'] = f"Found {results['summary']['high_issues']} high severity issue(s). Review recommended."
        elif results['summary']['total_issues'] > 0:
            results['status'] = 'info'
            results['can_deploy'] = True
            results['message'] = f"Found {results['summary']['total_issues']} minor issue(s). Safe to deploy."
        else:
            results['status'] = 'success'
            results['can_deploy'] = True
            results['message'] = "All checks passed. Safe to deploy!"
        
        print(f"\n{'='*60}")
        print(f"Analysis Complete: {results['message']}")
        print(f"{'='*60}\n")
        
        return results
    
    def cleanup_repository(self, repo_path: str):
        """
        Remove cloned repository
        
        Args:
            repo_path: Path to repository to remove
        """
        try:
            if os.path.exists(repo_path):
                print(f"[Cleanup] Removing temporary folder: {repo_path}")
                shutil.rmtree(repo_path, ignore_errors=True)
                print("[Cleanup] Cleanup complete")
        except Exception as e:
            print(f"[Cleanup Warning] {e}")


# Global instance
github_integration = GitHubIntegration()