"""
GitHub MCP Integration

This module provides integration with GitHub via GitHub MCP.
It wraps GitHub API calls and provides a clean interface for fetching commits.

NOTE: This is a stub implementation. In production, you would:
1. Use the actual GitHub MCP client/SDK
2. Or use PyGithub directly
3. Or call external MCP server via HTTP
"""

from typing import List, Optional
from datetime import datetime, timedelta
from github import Github
from config import settings
from models import CommitInfo


def fetch_recent_commits(
    repository: str,
    branch: str = "main",
    since: Optional[datetime] = None,
    service_filter: Optional[str] = None,
    max_commits: int = 50
) -> List[CommitInfo]:
    """
    Fetch recent commits from GitHub repository.
    
    This function integrates with GitHub (via PyGithub) to retrieve
    commit history. In production, this would use GitHub MCP.
    
    Args:
        repository: Repository name in format "org/repo"
        branch: Branch name to query
        since: Only fetch commits after this timestamp
        service_filter: Filter commits by service/module (looks in file paths)
        max_commits: Maximum number of commits to return
        
    Returns:
        List of CommitInfo objects
        
    Example:
        ```python
        commits = fetch_recent_commits(
            repository="myorg/myrepo",
            branch="main",
            since=datetime.utcnow() - timedelta(hours=24),
            service_filter="payment-service"
        )
        ```
    """
    try:
        # Initialize GitHub client
        # In production, this would use GitHub MCP client
        github_client = Github(settings.github_token)
        
        # Get repository
        repo = github_client.get_repo(repository)
        
        # Calculate default since time if not provided
        if since is None:
            since = datetime.utcnow() - timedelta(hours=settings.correlation_time_window_hours)
        
        # Fetch commits
        commits = repo.get_commits(sha=branch, since=since)
        
        # Convert to CommitInfo objects
        commit_infos = []
        
        for commit in commits[:max_commits]:
            # Get files changed
            files_changed = [f.filename for f in commit.files] if commit.files else []
            
            # Apply service filter if specified
            if service_filter:
                # Check if any file path contains the service name
                if not any(service_filter.lower() in f.lower() for f in files_changed):
                    continue
            
            # Get commit stats
            additions = sum(f.additions for f in commit.files) if commit.files else 0
            deletions = sum(f.deletions for f in commit.files) if commit.files else 0
            
            # Create CommitInfo
            commit_info = CommitInfo(
                sha=commit.sha,
                message=commit.commit.message,
                author=commit.commit.author.email if commit.commit.author else "Unknown",
                timestamp=commit.commit.author.date,
                files_changed=files_changed,
                additions=additions,
                deletions=deletions,
                branch=branch,
                url=commit.html_url
            )
            
            commit_infos.append(commit_info)
        
        return commit_infos
        
    except Exception as e:
        # Log error and return empty list
        print(f"[GitHub MCP] Error fetching commits: {str(e)}")
        return []


def get_commit_details(repository: str, commit_sha: str) -> Optional[CommitInfo]:
    """
    Get detailed information about a specific commit.
    
    Args:
        repository: Repository name in format "org/repo"
        commit_sha: Commit SHA to fetch
        
    Returns:
        CommitInfo object or None if not found
    """
    try:
        github_client = Github(settings.github_token)
        repo = github_client.get_repo(repository)
        commit = repo.get_commit(commit_sha)
        
        files_changed = [f.filename for f in commit.files] if commit.files else []
        additions = sum(f.additions for f in commit.files) if commit.files else 0
        deletions = sum(f.deletions for f in commit.files) if commit.files else 0
        
        return CommitInfo(
            sha=commit.sha,
            message=commit.commit.message,
            author=commit.commit.author.email if commit.commit.author else "Unknown",
            timestamp=commit.commit.author.date,
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
            branch="unknown",  # Branch info not available in single commit query
            url=commit.html_url
        )
        
    except Exception as e:
        print(f"[GitHub MCP] Error fetching commit {commit_sha}: {str(e)}")
        return None


def search_commits_by_keyword(
    repository: str,
    keyword: str,
    branch: str = "main",
    since: Optional[datetime] = None,
    max_results: int = 20
) -> List[CommitInfo]:
    """
    Search commits by keyword in commit message.
    
    Args:
        repository: Repository name
        keyword: Keyword to search for
        branch: Branch to search in
        since: Only search commits after this time
        max_results: Maximum results to return
        
    Returns:
        List of matching commits
    """
    try:
        # Fetch all recent commits
        all_commits = fetch_recent_commits(
            repository=repository,
            branch=branch,
            since=since,
            max_commits=max_results * 2  # Fetch more to filter
        )
        
        # Filter by keyword
        matching_commits = [
            c for c in all_commits
            if keyword.lower() in c.message.lower()
        ]
        
        return matching_commits[:max_results]
        
    except Exception as e:
        print(f"[GitHub MCP] Error searching commits: {str(e)}")
        return []


# ============================================================================
# MCP Server Integration (Alternative Approach)
# ============================================================================

def call_github_mcp_server(method: str, params: dict) -> dict:
    """
    Call external GitHub MCP server via HTTP.
    
    This is an alternative approach if you're using an external MCP server.
    
    Args:
        method: MCP method to call
        params: Method parameters
        
    Returns:
        Response data
        
    Example:
        ```python
        result = call_github_mcp_server(
            method="github.fetchCommits",
            params={
                "repository": "org/repo",
                "branch": "main",
                "since": "2025-11-21T00:00:00Z"
            }
        )
        ```
    """
    import httpx
    
    if not settings.github_mcp_server_url:
        raise ValueError("GitHub MCP server URL not configured")
    
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{settings.github_mcp_server_url}/rpc",
                json={
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": method,
                    "params": params
                },
                timeout=30.0
            )
            
            response.raise_for_status()
            result = response.json()
            
            if "error" in result:
                raise Exception(f"MCP Error: {result['error']}")
            
            return result.get("result", {})
            
    except Exception as e:
        print(f"[GitHub MCP Server] Error calling {method}: {str(e)}")
        raise


# ============================================================================
# Utility Functions
# ============================================================================

def format_commit_summary(commit: CommitInfo) -> str:
    """
    Format a commit into a human-readable summary.
    
    Args:
        commit: CommitInfo object
        
    Returns:
        Formatted string
    """
    return (
        f"[{commit.sha[:8]}] {commit.message.split('\n')[0][:80]}\n"
        f"  Author: {commit.author}\n"
        f"  Time: {commit.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"  Files: {len(commit.files_changed)} (+{commit.additions}/-{commit.deletions})"
    )
