"""
GitHub Commit Fetcher Agent

This agent retrieves recent commits from GitHub repositories using GitHub MCP.
It filters commits based on time range and service/module names.
"""

from typing import Optional
from datetime import datetime, timedelta

from models import CommitInfo, GitHubFetchResult, ParsedContext, AgentResult
from config import settings


class GitHubFetcherAgent:
    """
    Agent responsible for fetching relevant commits from GitHub.
    
    This agent uses GitHub MCP to retrieve commit history and filters
    commits based on the parsed incident context.
    """
    
    def __init__(self):
        """Initialize the GitHub Fetcher Agent"""
        # Simple initialization - no AI agent needed for direct GitHub queries
        pass
    
    async def fetch_commits(
        self, 
        parsed_context: ParsedContext,
        time_window_hours: int = None
    ) -> AgentResult:
        """
        Fetch relevant commits from GitHub.
        
        Args:
            parsed_context: Parsed incident context
            time_window_hours: Hours to look back (defaults to config value)
            
        Returns:
            AgentResult with GitHubFetchResult data
        """
        start_time = datetime.utcnow()
        
        try:
            # Import the GitHub MCP integration
            from integrations.github_mcp import fetch_recent_commits
            
            # Determine time window
            if time_window_hours is None:
                time_window_hours = settings.correlation_time_window_hours
            
            # Calculate since timestamp
            since_dt = parsed_context.timestamp - timedelta(hours=time_window_hours)
            
            # Determine repository (from config or context)
            repository = f"{settings.github_org}/{settings.github_repo}"
            branch = "main"
            
            # Determine service filter - only use if it's not the same as repo name
            # (to avoid filtering out all commits when service name = repo name)
            service_filter = None
            if parsed_context.service_name:
                # Only use service filter if it's different from repo name
                if parsed_context.service_name.lower() not in repository.lower():
                    service_filter = parsed_context.service_name
            
            # Fetch commits directly from GitHub MCP
            print(f"[GitHub Fetcher] Fetching commits from {repository}...")
            print(f"[GitHub Fetcher] Time window: {time_window_hours} hours (since {since_dt.isoformat()})")
            if service_filter:
                print(f"[GitHub Fetcher] Service filter: {service_filter}")
            else:
                print(f"[GitHub Fetcher] No service filter (showing all commits)")
            
            commits = fetch_recent_commits(
                repository=repository,
                branch=branch,
                since=since_dt,
                service_filter=service_filter
            )
            
            # Build result
            commits_data = GitHubFetchResult(
                commits=commits,
                repository=repository,
                branch=branch,
                time_range=f"Last {time_window_hours} hours"
            )
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            print(f"[GitHub Fetcher] ✓ Found {len(commits)} commits in {execution_time:.2f}s")
            
            return AgentResult(
                agent_name="github_fetcher",
                success=True,
                data=commits_data,
                error=None,
                execution_time=execution_time,
                metadata={
                    "repository": repository,
                    "time_window_hours": time_window_hours,
                    "commits_found": len(commits_data.commits)
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            print(f"[GitHub Fetcher] ✗ Error: {str(e)}")
            
            # Return empty result on error
            empty_result = GitHubFetchResult(
                commits=[],
                repository=f"{settings.github_org}/{settings.github_repo}",
                branch="main",
                time_range=f"Last {time_window_hours or 24} hours"
            )
            
            return AgentResult(
                agent_name="github_fetcher",
                success=False,
                data=empty_result,
                error=str(e),
                execution_time=execution_time,
                metadata={}
            )


# Convenience function for standalone usage
async def fetch_github_commits(
    parsed_context: ParsedContext,
    time_window_hours: int = None
) -> GitHubFetchResult:
    """
    Standalone function to fetch GitHub commits.
    
    Args:
        parsed_context: Parsed incident context
        time_window_hours: Hours to look back
        
    Returns:
        GitHub fetch result
    """
    agent = GitHubFetcherAgent()
    result = await agent.fetch_commits(parsed_context, time_window_hours)
    return result.data
