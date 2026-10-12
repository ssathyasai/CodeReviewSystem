import pytest
from backend.app.services.github_service import GitHubService, GitHubSecurityError

def test_valid_github_urls():
    valid_urls = [
        "https://github.com/torvalds/linux",
        "https://github.com/fastapi/fastapi.git",
        "https://www.github.com/facebook/react"
    ]
    for url in valid_urls:
        valid, clean = GitHubService.validate_repo_url(url)
        assert valid is True
        assert "github.com" in clean


def test_invalid_github_urls():
    invalid_urls = [
        "http://github.com/owner/repo",            # insecure HTTP
        "https://evil-site.com/malicious/repo",    # unapproved host
        "https://github.com/owner/repo; rm -rf /", # command injection attempt
        "ftp://github.com/owner/repo",             # non-https scheme
        "not-a-url"                                # malformed
    ]
    for url in invalid_urls:
        valid, err = GitHubService.validate_repo_url(url)
        assert valid is False
