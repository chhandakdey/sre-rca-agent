"""
Azure MCP Integration

This module provides integration with Azure services via Model Context Protocol (MCP):
- Azure DevOps (pipelines, deployments)
- Azure Monitor / App Insights (logs, metrics)
- Azure Resource Graph (resources)

This implementation uses MCP tools to interact with Azure services.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import httpx
import json
from azure.identity import DefaultAzureCredential

from config import settings
from models import DeploymentInfo, DeploymentStatus, LogEntry, SeverityLevel


# ============================================================================
# Azure DevOps Integration
# ============================================================================

async def check_deployments(
    project: str,
    pipeline_name: Optional[str] = None,
    commit_sha: Optional[str] = None,
    since: Optional[datetime] = None,
    max_results: int = 50
) -> List[DeploymentInfo]:
    """
    Check Azure DevOps deployment status and history using MCP.
    
    This function uses Model Context Protocol to query Azure DevOps.
    
    Args:
        project: Azure DevOps project name
        pipeline_name: Optional pipeline name to filter
        commit_sha: Optional commit SHA to find deployments for
        since: Only fetch deployments after this time
        max_results: Maximum deployments to return
        
    Returns:
        List of DeploymentInfo objects
        
    Example:
        ```python
        deployments = await check_deployments(
            project="MyProject",
            pipeline_name="payment-service-deploy",
            since=datetime.utcnow() - timedelta(hours=24)
        )
        ```
    """
    try:
        # Calculate default since time
        if since is None:
            since = datetime.utcnow() - timedelta(hours=settings.correlation_time_window_hours)
        
        # Use MCP to get builds
        builds_data = await call_azure_mcp(
            "devops.list_builds",
            {
                "organization": settings.azure_devops_org_url.split('/')[-1],
                "project": project,
                "pipeline_name": pipeline_name,
                "min_time": since.isoformat() + 'Z',
                "max_builds": max_results
            }
        )
        
        deployment_infos = []
        
        for build in builds_data:
            # Map Azure DevOps status to our DeploymentStatus
            status = DeploymentStatus.UNKNOWN
            if build.get('status') == 'completed':
                if build.get('result') == 'succeeded':
                    status = DeploymentStatus.SUCCEEDED
                elif build.get('result') == 'failed':
                    status = DeploymentStatus.FAILED
                elif build.get('result') == 'canceled':
                    status = DeploymentStatus.CANCELED
            elif build.get('status') == 'inProgress':
                status = DeploymentStatus.IN_PROGRESS
            else:
                status = DeploymentStatus.PENDING
            
            # Get commit SHA
            build_commit_sha = build.get('sourceVersion', '')
            
            # Filter by commit SHA if specified
            if commit_sha and build_commit_sha != commit_sha:
                continue
            
            # Determine environment
            pipeline = build.get('definition', {}).get('name', '')
            environment = "production"
            if "dev" in pipeline.lower():
                environment = "development"
            elif "staging" in pipeline.lower() or "stage" in pipeline.lower():
                environment = "staging"
            
            # Parse timestamps
            started_time = datetime.fromisoformat(build.get('startTime', '').replace('Z', '+00:00'))
            completed_time = build.get('finishTime')
            if completed_time:
                completed_time = datetime.fromisoformat(completed_time.replace('Z', '+00:00'))
            
            # Create DeploymentInfo
            deployment_info = DeploymentInfo(
                pipeline_id=str(build.get('definition', {}).get('id', '')),
                pipeline_name=pipeline,
                run_id=str(build.get('id', '')),
                status=status,
                started_time=started_time,
                completed_time=completed_time,
                commit_sha=build_commit_sha,
                environment=environment,
                url=build.get('_links', {}).get('web', {}).get('href', ''),
                error_message=None
            )
            
            deployment_infos.append(deployment_info)
        
        # Sort by start time (most recent first)
        deployment_infos.sort(key=lambda d: d.started_time, reverse=True)
        
        return deployment_infos[:max_results]
        
    except Exception as e:
        print(f"[Azure DevOps] Error checking deployments: {str(e)}")
        return []


def get_deployment_logs(project: str, build_id: int) -> str:
    """
    Get logs for a specific deployment/build.
    
    Args:
        project: Project name
        build_id: Build ID
        
    Returns:
        Build logs as string
    """
    try:
        credentials = BasicAuthentication('', settings.azure_devops_pat)
        connection = Connection(
            base_url=settings.azure_devops_org_url,
            creds=credentials
        )
        
        build_client = connection.clients.get_build_client()
        logs = build_client.get_build_logs(project=project, build_id=build_id)
        
        # Combine log entries
        log_text = ""
        for log in logs:
            log_content = build_client.get_build_log(
                project=project,
                build_id=build_id,
                log_id=log.id
            )
            log_text += log_content + "\n"
        
        return log_text
        
    except Exception as e:
        print(f"[Azure DevOps] Error fetching deployment logs: {str(e)}")
        return ""


# ============================================================================
# Azure Monitor / App Insights Integration
# ============================================================================

async def query_app_insights_logs(
    workspace_id: str,
    kql_query: str,
    max_results: int = 1000
) -> List[LogEntry]:
    """
    Query Azure App Insights logs using KQL via MCP.
    
    This function uses Model Context Protocol to execute KQL queries.
    
    Args:
        workspace_id: App Insights App ID
        kql_query: KQL query to execute
        max_results: Maximum log entries to return
        
    Returns:
        List of LogEntry objects
    """
    try:
        # Use MCP to query App Insights
        result = await call_azure_mcp(
            "appinsights.query",
            {
                "app_id": workspace_id,
                "query": kql_query,
                "max_results": max_results
            }
        )
        
        # Parse results into LogEntry objects
        log_entries = []
        
        tables = result.get("tables", [])
        for table in tables:
            columns = [col["name"] for col in table.get("columns", [])]
            rows = table.get("rows", [])
            
            for row in rows[:max_results]:
                try:
                    row_dict = dict(zip(columns, row))
                    
                    # Map severity level
                    severity_map = {
                        "0": SeverityLevel.INFO,
                        "1": SeverityLevel.INFO,
                        "2": SeverityLevel.LOW,
                        "3": SeverityLevel.MEDIUM,
                        "4": SeverityLevel.HIGH,
                        "5": SeverityLevel.CRITICAL,
                        0: SeverityLevel.INFO,
                        1: SeverityLevel.INFO,
                        2: SeverityLevel.LOW,
                        3: SeverityLevel.MEDIUM,
                        4: SeverityLevel.HIGH,
                        5: SeverityLevel.CRITICAL
                    }
                    
                    severity_level = row_dict.get("severityLevel", 2)
                    severity = severity_map.get(severity_level, SeverityLevel.MEDIUM)
                    
                    # Extract error code from message or result code
                    error_code = None
                    
                    # Build message from available fields
                    # For exceptions: use outerMessage or type
                    # For requests: use name or url
                    # For traces: use message
                    item_type = row_dict.get("itemType", "")
                    
                    if item_type == "exception":
                        message = row_dict.get("outerMessage") or row_dict.get("message") or row_dict.get("type") or ""
                        if row_dict.get("operation_Name"):
                            message = f"{row_dict.get('operation_Name')}: {message}"
                    elif item_type == "request":
                        message = row_dict.get("name") or row_dict.get("url") or row_dict.get("operation_Name") or ""
                    else:
                        message = row_dict.get("message") or row_dict.get("name") or row_dict.get("url") or ""
                    
                    message = str(message)
                    result_code = row_dict.get("resultCode") or row_dict.get("responseCode")
                    
                    # For requests table, include result code in message if it's an error
                    if result_code and (isinstance(result_code, int) and result_code >= 400 or isinstance(result_code, str) and result_code.isdigit() and int(result_code) >= 400):
                        error_code = f"HTTP_{result_code}"
                        if not message or message == "":
                            message = f"HTTP {result_code} error"
                        else:
                            message = f"{message} (HTTP {result_code})"
                    
                    # Extract exception type as error code
                    if item_type == "exception" and row_dict.get("type"):
                        exception_type = row_dict.get("type").split(".")[-1]  # Get last part of exception type
                        error_code = error_code or exception_type
                    
                    if "ERR_" in message:
                        import re
                        match = re.search(r'ERR_[\w_]+', message)
                        if match:
                            error_code = match.group(0)
                    
                    # Handle different timestamp field names
                    timestamp = row_dict.get("timestamp") or row_dict.get("TimeGenerated")
                    if isinstance(timestamp, str):
                        from dateutil import parser
                        timestamp = parser.parse(timestamp)
                    elif timestamp is None:
                        timestamp = datetime.utcnow()
                    
                    # Create LogEntry
                    log_entry = LogEntry(
                        timestamp=timestamp,
                        severity=severity,
                        message=message,
                        service_name=row_dict.get("cloud_RoleName"),
                        operation_id=row_dict.get("operation_Id") or row_dict.get("operation_ID"),
                        error_code=error_code,
                        stack_trace=row_dict.get("details") or row_dict.get("outerMessage"),
                        custom_dimensions=row_dict.get("customDimensions", {})
                    )
                    
                    log_entries.append(log_entry)
                    
                except Exception as e:
                    print(f"[App Insights] Error parsing row: {str(e)}")
                    continue
        
        print(f"[App Insights] Successfully parsed {len(log_entries)} log entries")
        return log_entries
        
    except Exception as e:
        print(f"[App Insights] Error querying logs: {str(e)}")
        import traceback
        traceback.print_exc()
        return []


def get_metrics(
    workspace_id: str,
    metric_names: List[str],
    resource_id: str,
    since: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    Get metrics from Azure Monitor.
    
    Args:
        workspace_id: Workspace ID
        metric_names: List of metric names to fetch
        resource_id: Azure resource ID
        since: Start time for metrics
        
    Returns:
        Dictionary of metric data
    """
    try:
        # This would use Azure Monitor Metrics API
        # Stub implementation
        return {
            "metrics": [],
            "error": "Not implemented - stub"
        }
        
    except Exception as e:
        print(f"[Azure Monitor] Error fetching metrics: {str(e)}")
        return {"metrics": [], "error": str(e)}


# ============================================================================
# MCP Server Integration (Alternative Approach)
# ============================================================================

async def call_azure_mcp(method: str, params: Dict[str, Any]) -> Any:
    """
    Call Azure MCP tools using the Model Context Protocol.
    
    This function maps MCP method names to available Azure operations
    and executes them using the MCP framework.
    
    Args:
        method: MCP method name (e.g., 'devops.list_builds', 'appinsights.query')
        params: Method parameters
        
    Returns:
        Response data from MCP
        
    Example:
        ```python
        builds = await call_azure_mcp(
            "devops.list_builds",
            {
                "organization": "myorg",
                "project": "myproject"
            }
        )
        ```
    """
    try:
        # If external MCP server is configured, use it
        if settings.azure_mcp_server_url:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{settings.azure_mcp_server_url}/rpc",
                    json={
                        "jsonrpc": "2.0",
                        "id": 1,
                        "method": f"azure.{method}",
                        "params": params
                    },
                    timeout=60.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                if "error" in result:
                    raise Exception(f"MCP Error: {result['error']}")
                
                return result.get("result", {})
        else:
            # Use Azure APIs directly via MCP-compatible interface
            return await _azure_api_call(method, params)
            
    except Exception as e:
        print(f"[Azure MCP] Error calling {method}: {str(e)}")
        raise


async def _azure_api_call(method: str, params: Dict[str, Any]) -> Any:
    """
    Direct Azure API calls wrapped in MCP-compatible interface.
    
    This is a fallback when external MCP server is not available.
    """
    if method == "devops.list_builds":
        return await _call_azure_devops_api(params)
    elif method == "appinsights.query":
        return await _call_app_insights_api(params)
    else:
        raise ValueError(f"Unsupported Azure MCP method: {method}")


async def _call_azure_devops_api(params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Call Azure DevOps REST API."""
    org = params.get('organization')
    project = params.get('project')
    base_url = f"https://dev.azure.com/{org}/{project}/_apis/build/builds"
    
    headers = {
        "Authorization": f"Basic {settings.azure_devops_pat}",
        "Content-Type": "application/json"
    }
    
    query_params = {
        "api-version": "7.0",
        "$top": params.get('max_builds', 50)
    }
    
    if params.get('min_time'):
        query_params['minTime'] = params['min_time']
    
    async with httpx.AsyncClient() as client:
        response = await client.get(base_url, headers=headers, params=query_params, timeout=30.0)
        response.raise_for_status()
        result = response.json()
        return result.get('value', [])


async def _call_app_insights_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Call Application Insights REST API."""
    app_id = params.get('app_id')
    query = params.get('query')
    
    # Get Azure credentials
    credential = DefaultAzureCredential()
    token = credential.get_token("https://api.applicationinsights.io/.default")
    
    api_url = f"https://api.applicationinsights.io/v1/apps/{app_id}/query"
    
    headers = {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json"
    }
    
    data = {"query": query}
    
    async with httpx.AsyncClient() as client:
        response = await client.post(api_url, headers=headers, json=data, timeout=60.0)
        response.raise_for_status()
        return response.json()


# ============================================================================
# Utility Functions
# ============================================================================

def format_deployment_summary(deployment: DeploymentInfo) -> str:
    """
    Format a deployment into a human-readable summary.
    
    Args:
        deployment: DeploymentInfo object
        
    Returns:
        Formatted string
    """
    duration = ""
    if deployment.completed_time:
        delta = deployment.completed_time - deployment.started_time
        minutes = int(delta.total_seconds() / 60)
        duration = f" ({minutes} min)"
    
    return (
        f"[{deployment.run_id}] {deployment.pipeline_name} → {deployment.environment}\n"
        f"  Status: {deployment.status.value}{duration}\n"
        f"  Started: {deployment.started_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"  Commit: {deployment.commit_sha[:8] if deployment.commit_sha else 'Unknown'}"
    )


def format_log_summary(log: LogEntry) -> str:
    """
    Format a log entry into a human-readable summary.
    
    Args:
        log: LogEntry object
        
    Returns:
        Formatted string
    """
    return (
        f"[{log.timestamp.strftime('%H:%M:%S')}] {log.severity.value.upper()}: {log.message[:100]}\n"
        f"  Service: {log.service_name or 'Unknown'}\n"
        f"  Operation: {log.operation_id or 'N/A'}"
    )
