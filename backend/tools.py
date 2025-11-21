"""
LangChain Tools and Utilities for Agent System

This module defines custom LangChain tools that agents can use to interact
with external services (GitHub, Azure MCP, App Insights, etc.).
"""

from langchain.tools import BaseTool
from typing import Optional, Type, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import json

# Import our models and integrations
from models import (
    CommitInfo, GitHubFetchResult, DeploymentInfo, 
    DeploymentCheckResult, LogEntry, AppInsightsQueryResult
)


# ============================================================================
# Tool Input Schemas
# ============================================================================

class GitHubFetchInput(BaseModel):
    """Input schema for GitHub commit fetching"""
    repository: str = Field(..., description="Repository name (org/repo)")
    branch: str = Field(default="main", description="Branch to query")
    since: Optional[str] = Field(None, description="ISO timestamp to fetch commits since")
    service_filter: Optional[str] = Field(None, description="Filter by service/module name")


class DeploymentCheckInput(BaseModel):
    """Input schema for Azure DevOps deployment checking"""
    project: str = Field(..., description="Azure DevOps project name")
    pipeline_name: Optional[str] = Field(None, description="Pipeline name to filter")
    commit_sha: Optional[str] = Field(None, description="Commit SHA to find deployment for")
    since: Optional[str] = Field(None, description="ISO timestamp to check deployments since")


class AppInsightsQueryInput(BaseModel):
    """Input schema for App Insights log querying"""
    workspace_id: str = Field(..., description="App Insights workspace ID")
    time_range_hours: int = Field(default=24, description="Hours to look back")
    service_name: Optional[str] = Field(None, description="Service to filter by")
    error_code: Optional[str] = Field(None, description="Error code to search for")
    keywords: Optional[List[str]] = Field(None, description="Keywords to search in logs")
    severity_filter: Optional[str] = Field(None, description="Minimum severity level")


# ============================================================================
# GitHub Commit Fetcher Tool
# ============================================================================

class GitHubCommitFetcherTool(BaseTool):
    """
    Tool for fetching recent commits from GitHub.
    
    This tool integrates with GitHub MCP to retrieve commit history
    based on time range and optional service filters.
    """
    
    name = "github_commit_fetcher"
    description = (
        "Fetches recent commits from GitHub repository. "
        "Useful for finding code changes related to an incident. "
        "Input should include repository, branch, and time range."
    )
    args_schema: Type[BaseModel] = GitHubFetchInput
    
    def _run(
        self, 
        repository: str,
        branch: str = "main",
        since: Optional[str] = None,
        service_filter: Optional[str] = None
    ) -> str:
        """
        Execute the tool to fetch commits.
        
        Args:
            repository: GitHub repository in format "org/repo"
            branch: Branch name to query
            since: ISO timestamp to fetch commits since
            service_filter: Optional filter by service/module name
            
        Returns:
            JSON string with commit information
        """
        try:
            # Import the GitHub MCP integration
            from integrations.github_mcp import fetch_recent_commits
            
            # Parse the since timestamp
            since_dt = None
            if since:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            
            # Fetch commits using GitHub MCP
            commits = fetch_recent_commits(
                repository=repository,
                branch=branch,
                since=since_dt,
                service_filter=service_filter
            )
            
            # Build result
            result = GitHubFetchResult(
                commits=commits,
                repository=repository,
                branch=branch,
                time_range=f"Since {since}" if since else "All recent commits"
            )
            
            return result.model_dump_json()
            
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "commits": []
            })
    
    async def _arun(self, *args, **kwargs) -> str:
        """Async version (delegates to sync for now)"""
        return self._run(*args, **kwargs)


# ============================================================================
# Azure DevOps Deployment Checker Tool
# ============================================================================

class AzureDevOpsDeploymentTool(BaseTool):
    """
    Tool for checking Azure DevOps pipeline deployments.
    
    This tool integrates with Azure MCP to retrieve deployment status
    and history for specified pipelines.
    """
    
    name = "azure_devops_deployment_checker"
    description = (
        "Checks Azure DevOps deployment status and history. "
        "Useful for correlating deployments with incidents. "
        "Can filter by pipeline name or commit SHA."
    )
    args_schema: Type[BaseModel] = DeploymentCheckInput
    
    def _run(
        self,
        project: str,
        pipeline_name: Optional[str] = None,
        commit_sha: Optional[str] = None,
        since: Optional[str] = None
    ) -> str:
        """
        Execute the tool to check deployments.
        
        Args:
            project: Azure DevOps project name
            pipeline_name: Optional pipeline name to filter
            commit_sha: Optional commit SHA to find deployment for
            since: ISO timestamp to check deployments since
            
        Returns:
            JSON string with deployment information
        """
        try:
            # Import the Azure MCP integration
            from integrations.azure_mcp import check_deployments
            
            # Parse the since timestamp
            since_dt = None
            if since:
                since_dt = datetime.fromisoformat(since.replace('Z', '+00:00'))
            
            # Check deployments using Azure MCP
            deployments = check_deployments(
                project=project,
                pipeline_name=pipeline_name,
                commit_sha=commit_sha,
                since=since_dt
            )
            
            # Count recent failures
            recent_failures = sum(
                1 for d in deployments 
                if d.status.value == "failed"
            )
            
            # Find last successful deployment
            successful = [d for d in deployments if d.status.value == "succeeded"]
            last_successful = successful[0] if successful else None
            
            # Build result
            result = DeploymentCheckResult(
                deployments=deployments,
                recent_failures=recent_failures,
                last_successful_deployment=last_successful
            )
            
            return result.model_dump_json()
            
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "deployments": []
            })
    
    async def _arun(self, *args, **kwargs) -> str:
        """Async version (delegates to sync for now)"""
        return self._run(*args, **kwargs)


# ============================================================================
# App Insights Log Retriever Tool
# ============================================================================

class AppInsightsLogTool(BaseTool):
    """
    Tool for querying Azure App Insights logs using KQL.
    
    This tool integrates with Azure MCP to execute KQL queries
    and retrieve relevant log entries.
    """
    
    name = "app_insights_log_retriever"
    description = (
        "Queries Azure App Insights logs using KQL. "
        "Useful for finding error logs and traces related to an incident. "
        "Can filter by time range, service name, error codes, and keywords."
    )
    args_schema: Type[BaseModel] = AppInsightsQueryInput
    
    def _run(
        self,
        workspace_id: str,
        time_range_hours: int = 24,
        service_name: Optional[str] = None,
        error_code: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        severity_filter: Optional[str] = None
    ) -> str:
        """
        Execute the tool to query logs.
        
        Args:
            workspace_id: App Insights workspace ID
            time_range_hours: Hours to look back
            service_name: Optional service to filter by
            error_code: Optional error code to search for
            keywords: Optional keywords to search in logs
            severity_filter: Optional minimum severity level
            
        Returns:
            JSON string with log entries
        """
        try:
            # Import the Azure MCP integration
            from integrations.azure_mcp import query_app_insights_logs
            
            # Build KQL query
            kql_query = self._build_kql_query(
                time_range_hours=time_range_hours,
                service_name=service_name,
                error_code=error_code,
                keywords=keywords,
                severity_filter=severity_filter
            )
            
            # Query logs using Azure MCP
            logs = query_app_insights_logs(
                workspace_id=workspace_id,
                kql_query=kql_query
            )
            
            # Count errors
            error_count = sum(
                1 for log in logs 
                if log.severity.value in ["critical", "high"]
            )
            
            # Build result
            result = AppInsightsQueryResult(
                logs=logs,
                total_count=len(logs),
                error_count=error_count,
                time_range=f"Last {time_range_hours} hours",
                kql_query=kql_query
            )
            
            return result.model_dump_json()
            
        except Exception as e:
            return json.dumps({
                "error": str(e),
                "logs": []
            })
    
    def _build_kql_query(
        self,
        time_range_hours: int,
        service_name: Optional[str] = None,
        error_code: Optional[str] = None,
        keywords: Optional[List[str]] = None,
        severity_filter: Optional[str] = None
    ) -> str:
        """
        Build a KQL query based on input parameters.
        
        Returns:
            KQL query string
        """
        # Build individual queries for each table type
        request_filters = [
            f"timestamp > ago({time_range_hours}h)",
            f"success == false or toint(resultCode) >= 400"
        ]
        
        trace_filters = [
            f"timestamp > ago({time_range_hours}h)",
            f"severityLevel >= 2"
        ]
        
        exception_filters = [
            f"timestamp > ago({time_range_hours}h)"
        ]
        
        # Add service name filter if provided
        if service_name:
            service_filter = f"cloud_RoleName == '{service_name}'"
            request_filters.append(service_filter)
            trace_filters.append(service_filter)
            exception_filters.append(service_filter)
        
        # Add error code filter if provided
        if error_code:
            error_filter = f"(message contains '{error_code}' or customDimensions contains '{error_code}')"
            request_filters.append(error_filter)
            trace_filters.append(error_filter)
            exception_filters.append(error_filter)
        
        # Add keyword filter if provided
        if keywords:
            keyword_conditions = " or ".join([f"message contains '{kw}'" for kw in keywords])
            keyword_filter = f"({keyword_conditions})"
            request_filters.append(keyword_filter)
            trace_filters.append(keyword_filter)
            exception_filters.append(keyword_filter)
        
        # Add severity filter only for traces (not applicable to requests)
        if severity_filter:
            severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1}
            severity_level = severity_map.get(severity_filter.lower(), 2)
            trace_filters.append(f"severityLevel >= {severity_level}")
        
        # Build the complete query
        query_parts = [
            f"requests",
            f"| where {' and '.join(request_filters)}",
            f"| union (traces | where {' and '.join(trace_filters)})",
            f"| union (exceptions | where {' and '.join(exception_filters)})",
            f"| order by timestamp desc",
            f"| limit 1000"
        ]
        
        return "\n".join(query_parts)
    
    async def _arun(self, *args, **kwargs) -> str:
        """Async version (delegates to sync for now)"""
        return self._run(*args, **kwargs)


# ============================================================================
# Tool Factory and Registry
# ============================================================================

class ToolRegistry:
    """
    Registry for all available tools.
    
    Provides easy access to tool instances for agent initialization.
    """
    
    @staticmethod
    def get_all_tools() -> List[BaseTool]:
        """
        Get all available tools for agents.
        
        Returns:
            List of instantiated tools
        """
        return [
            GitHubCommitFetcherTool(),
            AzureDevOpsDeploymentTool(),
            AppInsightsLogTool()
        ]
    
    @staticmethod
    def get_tool_by_name(name: str) -> Optional[BaseTool]:
        """
        Get a specific tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        tools = {
            "github_commit_fetcher": GitHubCommitFetcherTool(),
            "azure_devops_deployment_checker": AzureDevOpsDeploymentTool(),
            "app_insights_log_retriever": AppInsightsLogTool()
        }
        return tools.get(name)


# ============================================================================
# Utility Functions
# ============================================================================

def format_time_range(hours: int) -> str:
    """
    Format a time range for queries.
    
    Args:
        hours: Number of hours
        
    Returns:
        Formatted time range string
    """
    now = datetime.utcnow()
    since = now - timedelta(hours=hours)
    return f"{since.isoformat()}Z"


def parse_tool_output(output: str) -> Dict[str, Any]:
    """
    Parse tool output JSON safely.
    
    Args:
        output: JSON string from tool
        
    Returns:
        Parsed dictionary
    """
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return {"error": "Failed to parse tool output", "raw_output": output}
