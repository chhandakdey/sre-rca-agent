"""
GitHub MCP Integration

This module provides integration with GitHub via Model Context Protocol (MCP).
It uses MCP tools to interact with GitHub instead of direct API calls.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
import json
from config import settings
from models import CommitInfo


async def fetch_recent_commits(
    repository: str,
    branch: str = "main",
    since: Optional[datetime] = None,
    service_filter: Optional[str] = None,
    max_commits: int = 50
) -> List[CommitInfo]:
    """
    Fetch recent commits from GitHub repository using MCP.
    
    This function uses Model Context Protocol to interact with GitHub.
    
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
        commits = await fetch_recent_commits(
            repository="myorg/myrepo",
            branch="main",
            since=datetime.utcnow() - timedelta(hours=24),
            service_filter="payment-service"
        )
        ```
    """
    try:
        # Calculate default since time if not provided
        if since is None:
            since = datetime.utcnow() - timedelta(hours=settings.correlation_time_window_hours)
        
        # Split repository into owner and repo
        owner, repo = repository.split('/')
        
        # Use MCP to list commits
        commits_data = await call_github_mcp(
            "list_commits",
            {
                "owner": owner,
                "repo": repo,
                "sha": branch,
                "since": since.isoformat() + 'Z',
                "per_page": max_commits
            }
        )
        
        # Convert to CommitInfo objects
        commit_infos = []
        
        for commit_data in commits_data:
            # Get files changed by fetching individual commit details
            try:
                commit_detail = await call_github_mcp(
                    "get_commit",
                    {
                        "owner": owner,
                        "repo": repo,
                        "sha": commit_data.get('sha')
                    }
                )
                files_changed = [f['filename'] for f in commit_detail.get('files', [])]
                additions = sum(f.get('additions', 0) for f in commit_detail.get('files', []))
                deletions = sum(f.get('deletions', 0) for f in commit_detail.get('files', []))
            except Exception:
                files_changed = []
                additions = 0
                deletions = 0
            
            # Apply service filter if specified
            if service_filter:
                if not any(service_filter.lower() in f.lower() for f in files_changed):
                    continue
            
            # Extract commit information
            commit_obj = commit_data.get('commit', {})
            author_obj = commit_obj.get('author', {})
            
            # Create CommitInfo
            commit_info = CommitInfo(
                sha=commit_data.get('sha', ''),
                message=commit_obj.get('message', ''),
                author=author_obj.get('email', author_obj.get('name', 'Unknown')),
                timestamp=datetime.fromisoformat(author_obj.get('date', '').replace('Z', '+00:00')),
                files_changed=files_changed,
                additions=additions,
                deletions=deletions,
                branch=branch,
                url=commit_data.get('html_url', '')
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

async def call_github_mcp(method: str, params: Dict[str, Any]) -> Any:
    """
    Call GitHub MCP tools using the Model Context Protocol.
    
    This function maps MCP method names to available GitHub operations
    and executes them using the MCP framework.
    
    Args:
        method: MCP method name (e.g., 'list_commits', 'get_commit')
        params: Method parameters
        
    Returns:
        Response data from MCP
        
    Example:
        ```python
        commits = await call_github_mcp(
            "list_commits",
            {
                "owner": "myorg",
                "repo": "myrepo",
                "sha": "main",
                "since": "2025-11-21T00:00:00Z"
            }
        )
        ```
    """
    try:
        # If external MCP server is configured, use it
        if settings.github_mcp_server_url:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.github_mcp_server_url}/rpc",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": f"github.{method}",
                        "params": params
                    },
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                if "error" in result:
                    raise Exception(f"MCP Error: {result['error']}")
                
                return result.get("result", {})
        else:
            # Use GitHub REST API directly via MCP-compatible interface
            return await _github_api_call(method, params)
            
    except Exception as e:
        print(f"[GitHub MCP] Error calling {method}: {str(e)}")
        raise


async def _github_api_call(method: str, params: Dict[str, Any]) -> Any:
    """
    Direct GitHub API calls wrapped in MCP-compatible interface.
    
    This is a fallback when external MCP server is not available.
    """
    base_url = "https://api.github.com"
    headers = {
        "Authorization": f"token {settings.github_token}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    async with httpx.AsyncClient() as client:
        if method == "list_commits":
            url = f"{base_url}/repos/{params['owner']}/{params['repo']}/commits"
            query_params = {
                "sha": params.get('sha', 'main'),
                "since": params.get('since'),
                "per_page": params.get('per_page', 50)
            }
            response = await client.get(url, headers=headers, params=query_params, timeout=30.0)
            response.raise_for_status()
            return response.json()
            
        elif method == "get_commit":
            url = f"{base_url}/repos/{params['owner']}/{params['repo']}/commits/{params['sha']}"
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            return response.json()
            
        else:
            raise ValueError(f"Unsupported GitHub MCP method: {method}")


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
