"""
GitHub MCP Integration

This module provides integration with GitHub via Model Context Protocol (MCP).
It uses MCP tools to interact with GitHub instead of direct API calls.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
import json
import logging
import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from config import settings
from models import CommitInfo, DeploymentInfo, DeploymentStatus

# Setup logging
logger = logging.getLogger(__name__)

# Global MCP session (will be initialized on first use)
_mcp_session: Optional[ClientSession] = None
_mcp_session_lock = asyncio.Lock()
_available_tools: List[Dict[str, Any]] = []
_stdio_context = None
_session_context = None


# ============================================================================
# MCP Session Management
# ============================================================================

async def initialize_github_mcp() -> ClientSession:
    """
    Initialize GitHub MCP client session using stdio transport.
    
    Returns:
        Initialized ClientSession
    """
    global _mcp_session, _available_tools, _stdio_context, _session_context
    
    async with _mcp_session_lock:
        if _mcp_session is not None:
            return _mcp_session
        
        try:
            logger.info("Initializing GitHub MCP client session...")
            
            # MCP server configuration
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@modelcontextprotocol/server-github"],
                env={
                    "GITHUB_PERSONAL_ACCESS_TOKEN": settings.github_token
                }
            )
            
            # Create stdio client connection - enter the context and keep it alive
            _stdio_context = stdio_client(server_params)
            read, write = await _stdio_context.__aenter__()
            
            # Create and initialize session - enter session context
            _session_context = ClientSession(read, write)
            await _session_context.__aenter__()
            await _session_context.initialize()
            
            # List and cache available tools
            tools_response = await _session_context.list_tools()
            _available_tools = [{
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema
                }
            } for tool in tools_response.tools]
            
            logger.info(f"GitHub MCP initialized with {len(_available_tools)} tools")
            for tool in tools_response.tools:
                logger.debug(f"  - {tool.name}")
            
            # Try to list resources if supported
            try:
                resources = await _session_context.list_resources()
                logger.info(f"GitHub MCP has {len(resources.resources)} resources available")
            except Exception as e:
                logger.debug(f"Resources not supported by GitHub MCP server ({type(e).__name__})")
            
            _mcp_session = _session_context
            return _session_context
            
        except Exception as e:
            logger.error(f"Failed to initialize GitHub MCP: {e}")
            import traceback
            traceback.print_exc()
            raise


async def get_github_mcp_session() -> ClientSession:
    """
    Get or create GitHub MCP session.
    
    Returns:
        Active ClientSession
    """
    global _mcp_session
    
    if _mcp_session is None:
        await initialize_github_mcp()
    
    return _mcp_session


async def call_github_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Call a GitHub MCP tool with the given arguments.
    
    Args:
        tool_name: Name of the MCP tool to call
        arguments: Tool arguments
        
    Returns:
        Tool response content
        
    Example:
        ```python
        result = await call_github_mcp_tool(
            "get_file_contents",
            {
                "owner": "chhandakdey",
                "repo": "SimpleSRETestApp",
                "path": "README.md"
            }
        )
        ```
    """
    try:
        session = await get_github_mcp_session()
        
        logger.debug(f"Calling GitHub MCP tool: {tool_name}")
        logger.debug(f"Arguments: {json.dumps(arguments, indent=2)}")
        
        # Call the tool
        result = await session.call_tool(tool_name, arguments)
        
        # Extract text content from result
        if isinstance(result.content, list):
            content_text = "\n".join([
                item.text if hasattr(item, 'text') else str(item) 
                for item in result.content
            ])
        elif hasattr(result.content, 'text'):
            content_text = result.content.text
        else:
            content_text = str(result.content)
        
        logger.debug(f"Tool response: {content_text[:500]}...")
        
        # Try to parse as JSON if possible
        try:
            return json.loads(content_text)
        except json.JSONDecodeError:
            return content_text
            
    except Exception as e:
        logger.error(f"Error calling GitHub MCP tool {tool_name}: {e}")
        raise


async def close_github_mcp():
    """
    Close GitHub MCP session.
    """
    global _mcp_session, _stdio_context, _session_context
    
    async with _mcp_session_lock:
        if _mcp_session is not None:
            try:
                # Close session context
                if _session_context is not None:
                    await _session_context.__aexit__(None, None, None)
                    _session_context = None
                
                # Close stdio context
                if _stdio_context is not None:
                    await _stdio_context.__aexit__(None, None, None)
                    _stdio_context = None
                
                _mcp_session = None
                logger.info("GitHub MCP session closed")
            except Exception as e:
                logger.error(f"Error closing GitHub MCP session: {e}")


# ============================================================================
# GitHub Operations
# ============================================================================

async def fetch_recent_deployments(
    repository: str,
    workflow_name: Optional[str] = None,
    environment: Optional[str] = None,
    since: Optional[datetime] = None,
    incident_time: Optional[datetime] = None,
    max_results: int = 20
) -> List[DeploymentInfo]:
    """
    Fetch recent GitHub Actions workflow runs (deployments) from a repository.
    
    This function queries GitHub Actions workflow runs to track deployments.
    Since GitHub MCP doesn't have workflow tools, we use the REST API fallback.
    
    Args:
        repository: Repository name in format "org/repo"
        workflow_name: Optional workflow name to filter (e.g., "deploy.yml", "ci-cd")
        environment: Optional environment filter (dev/staging/production)
        since: Only fetch runs after this timestamp (overrides incident_time)
        incident_time: If provided and 'since' is not, calculates lookback window using DEPLOYMENT_CORRELATION_HOURS
        max_results: Maximum number of results to return
        
    Returns:
        List of DeploymentInfo objects representing workflow runs
        
    Example:
        ```python
        # Using explicit since time
        deployments = await fetch_recent_deployments(
            repository="myorg/myrepo",
            workflow_name="deploy",
            environment="production",
            since=datetime.utcnow() - timedelta(hours=24)
        )
        
        # Using incident_time with env variable DEPLOYMENT_CORRELATION_HOURS (default: 2 hours)
        deployments = await fetch_recent_deployments(
            repository="myorg/myrepo",
            incident_time=incident_datetime,
            environment="production"
        )
        ```
    """
    try:
        # Calculate default since time if not provided
        if since is None:
            if incident_time is not None:
                # Use deployment-specific correlation window
                correlation_hours = settings.deployment_correlation_hours
                since = incident_time - timedelta(hours=correlation_hours)
                logger.info(f"[GitHub MCP] Using deployment correlation window of {correlation_hours} hours from incident time")
            else:
                # Use general correlation window as fallback
                since = datetime.utcnow() - timedelta(hours=settings.correlation_time_window_hours)
        
        # Validate repository format
        if '/' not in repository:
            raise ValueError(f"Invalid repository format '{repository}'. Expected 'owner/repo'.")
        
        owner, repo = repository.split('/', 1)
        
        logger.info(f"[GitHub MCP] Fetching workflow runs (deployments) from {owner}/{repo}")
        
        # Use GitHub REST API to fetch workflow runs
        # GitHub MCP doesn't have workflow tools, so we use the fallback API
        base_url = "https://api.github.com"
        headers = {
            "Authorization": f"token {settings.github_token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "SRE-RCA-Agent"
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get workflow runs
            url = f"{base_url}/repos/{owner}/{repo}/actions/runs"
            params = {
                "per_page": max_results,
                "status": "completed"  # Can be: completed, success, failure, cancelled
            }
            
            # Add created filter if since is provided
            if since:
                params["created"] = f">={since.isoformat()}"
            
            response = await client.get(url, headers=headers, params=params)
            response.raise_for_status()
            runs_data = response.json()
            
            workflow_runs = runs_data.get('workflow_runs', [])
            logger.info(f"[GitHub MCP] Retrieved {len(workflow_runs)} workflow runs")
            
            # Convert to DeploymentInfo objects
            deployment_infos = []
            
            for run in workflow_runs:
                # Filter by workflow name if specified
                if workflow_name and workflow_name.lower() not in run.get('name', '').lower():
                    continue
                
                # Map GitHub Actions conclusion to DeploymentStatus
                conclusion = run.get('conclusion', 'unknown')
                status_map = {
                    'success': DeploymentStatus.SUCCEEDED,
                    'failure': DeploymentStatus.FAILED,
                    'cancelled': DeploymentStatus.CANCELED,
                    'skipped': DeploymentStatus.CANCELED,
                    'timed_out': DeploymentStatus.FAILED,
                    'action_required': DeploymentStatus.PENDING,
                    'neutral': DeploymentStatus.UNKNOWN,
                }
                
                # Check if run is still in progress
                if run.get('status') == 'in_progress':
                    status = DeploymentStatus.IN_PROGRESS
                elif run.get('status') == 'queued':
                    status = DeploymentStatus.PENDING
                else:
                    status = status_map.get(conclusion, DeploymentStatus.UNKNOWN)
                
                # Determine environment from workflow name or event
                detected_env = "unknown"
                workflow_name_lower = run.get('name', '').lower()
                event = run.get('event', '')
                
                # Try to detect environment from workflow name
                if 'prod' in workflow_name_lower or 'production' in workflow_name_lower:
                    detected_env = "production"
                elif 'staging' in workflow_name_lower or 'stage' in workflow_name_lower:
                    detected_env = "staging"
                elif 'dev' in workflow_name_lower or 'development' in workflow_name_lower:
                    detected_env = "development"
                elif event == 'release':
                    detected_env = "production"
                elif event == 'push':
                    # Check branch name
                    branch = run.get('head_branch', '')
                    if branch == 'main' or branch == 'master':
                        detected_env = "production"
                    elif 'staging' in branch or 'stage' in branch:
                        detected_env = "staging"
                    else:
                        detected_env = "development"
                
                # Filter by environment if specified
                if environment and environment.lower() != detected_env.lower():
                    continue
                
                # Parse timestamps
                started_time = datetime.fromisoformat(run.get('created_at', '').replace('Z', '+00:00'))
                completed_time = None
                if run.get('updated_at'):
                    completed_time = datetime.fromisoformat(run.get('updated_at', '').replace('Z', '+00:00'))
                
                # Create DeploymentInfo
                deployment_info = DeploymentInfo(
                    pipeline_id=str(run.get('workflow_id', '')),
                    pipeline_name=run.get('name', 'Unknown Workflow'),
                    run_id=str(run.get('id', '')),
                    status=status,
                    started_time=started_time,
                    completed_time=completed_time,
                    commit_sha=run.get('head_sha', ''),
                    environment=detected_env,
                    url=run.get('html_url', ''),
                    error_message=f"Conclusion: {conclusion}" if status == DeploymentStatus.FAILED else None
                )
                
                deployment_infos.append(deployment_info)
            
            logger.info(f"[GitHub MCP] Successfully processed {len(deployment_infos)} deployments")
            return deployment_infos[:max_results]
            
    except httpx.HTTPStatusError as e:
        logger.error(f"[GitHub MCP] GitHub API error fetching workflow runs: {e.response.status_code}")
        return []
    except Exception as e:
        logger.error(f"[GitHub MCP] Error fetching workflow runs from {repository}: {str(e)}")
        import traceback
        logger.error(f"[GitHub MCP] Traceback: {traceback.format_exc()}")
        return []


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
        
        # Validate repository format
        if '/' not in repository:
            raise ValueError(f"Invalid repository format '{repository}'. Expected 'owner/repo'.")
        
        # Split repository into owner and repo
        owner, repo = repository.split('/', 1)
        
        logger.info(f"[GitHub MCP] Fetching commits from {owner}/{repo} on branch '{branch}'")
        
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
        
        if not commits_data:
            logger.info(f"[GitHub MCP] No commits found for {owner}/{repo}")
            return []
        
        logger.info(f"[GitHub MCP] Retrieved {len(commits_data)} commits")
        
        # Convert to CommitInfo objects
        commit_infos = []
        
        for commit_data in commits_data:
            # Extract files changed from commit data if available
            # Note: list_commits may not include full file details, 
            # so we'll work with what we have
            try:
                files_changed = []
                additions = 0
                deletions = 0
                
                # Check if files are included in the commit data
                if 'files' in commit_data:
                    files_changed = [f.get('filename', f.get('path', '')) for f in commit_data.get('files', [])]
                    additions = sum(f.get('additions', 0) for f in commit_data.get('files', []))
                    deletions = sum(f.get('deletions', 0) for f in commit_data.get('files', []))
                
                # If no files info, check stats
                elif 'stats' in commit_data:
                    stats = commit_data.get('stats', {})
                    additions = stats.get('additions', 0)
                    deletions = stats.get('deletions', 0)
                
            except Exception as detail_error:
                logger.warning(f"[GitHub MCP] Warning: Could not extract details for commit {commit_data.get('sha', 'unknown')}: {str(detail_error)}")
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
        
        logger.info(f"[GitHub MCP] Successfully processed {len(commit_infos)} commits")
        return commit_infos
        
    except ValueError as ve:
        # Configuration or input validation errors
        logger.error(f"[GitHub MCP] Configuration error: {str(ve)}")
        return []
    except Exception as e:
        # Log detailed error and return empty list
        logger.error(f"[GitHub MCP] Error fetching commits from {repository}: {str(e)}")
        import traceback
        logger.error(f"[GitHub MCP] Traceback: {traceback.format_exc()}")
        return []


async def get_commit_details(repository: str, commit_sha: str) -> Optional[CommitInfo]:
    """
    Get detailed information about a specific commit.
    
    Args:
        repository: Repository name in format "org/repo"
        commit_sha: Commit SHA to fetch
        
    Returns:
        CommitInfo object or None if not found
    """
    try:
        # Validate repository format
        if '/' not in repository:
            raise ValueError(f"Invalid repository format '{repository}'. Expected 'owner/repo'.")
        
        owner, repo = repository.split('/', 1)
        
        # Use fallback API call directly since get_commit tool doesn't exist in GitHub MCP
        commit_data = await _github_api_call(
            "get_commit",
            {
                "owner": owner,
                "repo": repo,
                "sha": commit_sha
            }
        )
        
        files_changed = [f['filename'] for f in commit_data.get('files', [])]
        additions = sum(f.get('additions', 0) for f in commit_data.get('files', []))
        deletions = sum(f.get('deletions', 0) for f in commit_data.get('files', []))
        
        commit_obj = commit_data.get('commit', {})
        author_obj = commit_obj.get('author', {})
        
        return CommitInfo(
            sha=commit_data.get('sha', ''),
            message=commit_obj.get('message', ''),
            author=author_obj.get('email', author_obj.get('name', 'Unknown')),
            timestamp=datetime.fromisoformat(author_obj.get('date', '').replace('Z', '+00:00')),
            files_changed=files_changed,
            additions=additions,
            deletions=deletions,
            branch="unknown",  # Branch info not available in single commit query
            url=commit_data.get('html_url', '')
        )
        
    except Exception as e:
        logger.error(f"[GitHub MCP] Error fetching commit {commit_sha}: {str(e)}")
        return None


async def search_commits_by_keyword(
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
        all_commits = await fetch_recent_commits(
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
        logger.error(f"[GitHub MCP] Error searching commits: {str(e)}")
        return []


# ============================================================================
# MCP Server Integration
# ============================================================================

async def call_github_mcp(method: str, params: Dict[str, Any]) -> Any:
    """
    Call GitHub MCP tools using the Model Context Protocol.
    
    This function maps method names to GitHub MCP tool names and executes them.
    
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
        # Map method names to actual MCP tool names
        tool_mapping = {
            "list_commits": "list_commits",
            "get_file_contents": "get_file_contents",
            "create_or_update_file": "create_or_update_file",
            "push_files": "push_files",
            "search_repositories": "search_repositories",
            "create_repository": "create_repository",
            "get_file": "get_file_contents",
            "search_code": "search_code",
            "create_issue": "create_issue",
            "create_pull_request": "create_pull_request",
            "fork_repository": "fork_repository",
            "create_branch": "create_branch",
            "list_issues": "list_issues",
            "get_issue": "get_issue",
            "update_issue": "update_issue",
            "add_issue_comment": "add_issue_comment",
            "list_pull_requests": "list_pull_requests",
            "get_pull_request": "get_pull_request",
            "merge_pull_request": "merge_pull_request",
        }
        
        # Get the actual tool name or use the method as-is
        tool_name = tool_mapping.get(method, method)
        
        # For methods not available in MCP, use fallback directly
        if method == "get_commit":
            logger.debug(f"[GitHub MCP] Using fallback API for {method}")
            return await _github_api_call(method, params)
        
        # Call the MCP tool using our session
        result = await call_github_mcp_tool(tool_name, params)
        
        return result
            
    except Exception as e:
        logger.error(f"[GitHub MCP] Error calling {method}: {str(e)}")
        # Fallback to direct API calls if MCP fails
        return await _github_api_call(method, params)


async def _github_api_call(method: str, params: Dict[str, Any]) -> Any:
    """
    Direct GitHub API calls wrapped in MCP-compatible interface.
    
    This is a fallback when external MCP server is not available.
    """
    base_url = "https://api.github.com"
    
    # Check if GitHub token is configured
    if not settings.github_token or settings.github_token == "your-github-token":
        raise ValueError("GitHub token not configured. Please set GITHUB_TOKEN in .env file.")
    
    headers = {
        "Authorization": f"token {settings.github_token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "SRE-RCA-Agent"
    }
    
    try:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            if method == "list_commits":
                url = f"{base_url}/repos/{params['owner']}/{params['repo']}/commits"
                query_params = {
                    "sha": params.get('sha', 'main'),
                    "per_page": params.get('per_page', 50)
                }
                # Only include 'since' if it's provided
                if params.get('since'):
                    query_params["since"] = params['since']
                    
                response = await client.get(url, headers=headers, params=query_params)
                response.raise_for_status()
                return response.json()
                
            elif method == "get_commit":
                url = f"{base_url}/repos/{params['owner']}/{params['repo']}/commits/{params['sha']}"
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                return response.json()
                
            else:
                raise ValueError(f"Unsupported GitHub MCP method: {method}")
                
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            raise Exception(f"GitHub authentication failed. Please check your GITHUB_TOKEN.")
        elif e.response.status_code == 404:
            raise Exception(f"GitHub repository not found: {params.get('owner')}/{params.get('repo')}")
        elif e.response.status_code == 403:
            raise Exception(f"GitHub API rate limit exceeded or access forbidden.")
        else:
            raise Exception(f"GitHub API error ({e.response.status_code}): {e.response.text}")
    except httpx.ConnectError as e:
        raise Exception(f"Failed to connect to GitHub API. Please check your internet connection: {str(e)}")
    except httpx.TimeoutException:
        raise Exception(f"GitHub API request timed out. Please try again.")
    except Exception as e:
        raise Exception(f"GitHub API call failed: {str(e)}")


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
