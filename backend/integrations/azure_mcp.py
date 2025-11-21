"""
Azure MCP Integration

This module provides integration with Azure services via Azure MCP:
- Azure DevOps (pipelines, deployments)
- Azure Monitor / App Insights (logs, metrics)
- Azure Resource Graph (resources)

NOTE: This is a stub implementation. In production, you would:
1. Use the actual Azure MCP client/SDK
2. Or use Azure SDKs directly (azure-devops, azure-monitor-query)
3. Or call external MCP server via HTTP
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from azure.devops.connection import Connection
from azure.identity import DefaultAzureCredential
from msrest.authentication import BasicAuthentication
import requests

from config import settings
from models import DeploymentInfo, DeploymentStatus, LogEntry, SeverityLevel


# ============================================================================
# Azure DevOps Integration
# ============================================================================

def check_deployments(
    project: str,
    pipeline_name: Optional[str] = None,
    commit_sha: Optional[str] = None,
    since: Optional[datetime] = None,
    max_results: int = 50
) -> List[DeploymentInfo]:
    """
    Check Azure DevOps deployment status and history.
    
    This function queries Azure DevOps for pipeline runs and deployments.
    In production, this would use Azure MCP.
    
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
        deployments = check_deployments(
            project="MyProject",
            pipeline_name="payment-service-deploy",
            since=datetime.utcnow() - timedelta(hours=24)
        )
        ```
    """
    try:
        # Initialize Azure DevOps connection
        # In production, this would use Azure MCP client
        credentials = BasicAuthentication('', settings.azure_devops_pat)
        connection = Connection(
            base_url=settings.azure_devops_org_url,
            creds=credentials
        )
        
        # Get build client
        build_client = connection.clients.get_build_client()
        
        # Calculate default since time
        if since is None:
            since = datetime.utcnow() - timedelta(hours=settings.correlation_time_window_hours)
        
        # Get all pipelines in the project
        pipelines = build_client.get_definitions(project=project)
        
        # Filter by pipeline name if specified
        if pipeline_name:
            pipelines = [p for p in pipelines if pipeline_name.lower() in p.name.lower()]
        
        deployment_infos = []
        
        # For each pipeline, get recent builds
        for pipeline in pipelines[:10]:  # Limit pipelines to check
            try:
                builds = build_client.get_builds(
                    project=project,
                    definitions=[pipeline.id],
                    min_time=since,
                    max_builds_per_definition=max_results
                )
                
                for build in builds:
                    # Map Azure DevOps status to our DeploymentStatus
                    status_map = {
                        "completed": DeploymentStatus.SUCCEEDED if build.result == "succeeded" else DeploymentStatus.FAILED,
                        "inProgress": DeploymentStatus.IN_PROGRESS,
                        "cancelling": DeploymentStatus.CANCELED,
                        "postponed": DeploymentStatus.PENDING,
                        "notStarted": DeploymentStatus.PENDING
                    }
                    
                    status = status_map.get(build.status, DeploymentStatus.UNKNOWN)
                    if build.result == "succeeded":
                        status = DeploymentStatus.SUCCEEDED
                    elif build.result == "failed":
                        status = DeploymentStatus.FAILED
                    elif build.result == "canceled":
                        status = DeploymentStatus.CANCELED
                    
                    # Get commit SHA from source version
                    build_commit_sha = build.source_version if build.source_version else None
                    
                    # Filter by commit SHA if specified
                    if commit_sha and build_commit_sha != commit_sha:
                        continue
                    
                    # Determine environment (heuristic based on pipeline name)
                    environment = "production"
                    if "dev" in pipeline.name.lower():
                        environment = "development"
                    elif "staging" in pipeline.name.lower() or "stage" in pipeline.name.lower():
                        environment = "staging"
                    
                    # Create DeploymentInfo
                    deployment_info = DeploymentInfo(
                        pipeline_id=str(pipeline.id),
                        pipeline_name=pipeline.name,
                        run_id=str(build.id),
                        status=status,
                        started_time=build.start_time or datetime.utcnow(),
                        completed_time=build.finish_time,
                        commit_sha=build_commit_sha,
                        environment=environment,
                        url=f"{settings.azure_devops_org_url}/{project}/_build/results?buildId={build.id}",
                        error_message=None  # Could extract from build logs if needed
                    )
                    
                    deployment_infos.append(deployment_info)
                    
            except Exception as e:
                print(f"[Azure DevOps] Error fetching builds for pipeline {pipeline.name}: {str(e)}")
                continue
        
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

def query_app_insights_logs(
    workspace_id: str,
    kql_query: str,
    max_results: int = 1000
) -> List[LogEntry]:
    """
    Query Azure App Insights logs using KQL.
    
    This function executes a KQL query against App Insights using the Application Insights API.
    
    Args:
        workspace_id: App Insights App ID (not Log Analytics workspace ID)
        kql_query: KQL query to execute
        max_results: Maximum log entries to return
        
    Returns:
        List of LogEntry objects
    """
    try:
        # Try using Application Insights API directly (for classic or workspace-based App Insights)
        # Use App ID from config if available
        app_id = settings.app_insights_app_id or workspace_id
        
        print(f"[App Insights] Starting query...")
        print(f"[App Insights] App ID from settings: {settings.app_insights_app_id}")
        print(f"[App Insights] Workspace ID parameter: {workspace_id}")
        print(f"[App Insights] Using App ID: {app_id}")
        print(f"[App Insights] KQL Query: {kql_query}")
        
        # Get Azure credentials
        print(f"[App Insights] Getting Azure credentials...")
        credential = DefaultAzureCredential()
        print(f"[App Insights] Getting token...")
        token = credential.get_token("https://api.applicationinsights.io/.default")
        print(f"[App Insights] Token acquired successfully")
        
        # Query App Insights API
        import requests
        api_url = f"https://api.applicationinsights.io/v1/apps/{app_id}/query"
        
        print(f"[App Insights] API URL: {api_url}")
        
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        data = {"query": kql_query}
        
        print(f"[App Insights] Sending POST request...")
        response = requests.post(api_url, headers=headers, json=data, timeout=60)
        
        print(f"[App Insights] Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"[App Insights] Query failed: {response.status_code} - {response.text[:500]}")
            return []
        
        result = response.json()
        tables = result.get("tables", [])
        
        print(f"[App Insights] Number of tables in response: {len(tables)}")
        
        if not tables:
            print(f"[App Insights] No tables in response")
            return []
        
        # Parse results into LogEntry objects
        log_entries = []
        
        for table in tables:
            columns = [col["name"] for col in table.get("columns", [])]
            rows = table.get("rows", [])
            
            print(f"[App Insights] Found {len(rows)} rows")
            print(f"[App Insights] Columns available: {columns}")
            
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

def call_azure_mcp_server(method: str, params: dict) -> dict:
    """
    Call external Azure MCP server via HTTP.
    
    This is an alternative approach if you're using an external MCP server.
    
    Args:
        method: MCP method to call
        params: Method parameters
        
    Returns:
        Response data
        
    Example:
        ```python
        result = call_azure_mcp_server(
            method="azure.devops.listBuilds",
            params={
                "project": "MyProject",
                "pipelineId": "123"
            }
        )
        ```
    """
    import httpx
    
    if not settings.azure_mcp_server_url:
        raise ValueError("Azure MCP server URL not configured")
    
    try:
        with httpx.Client() as client:
            response = client.post(
                f"{settings.azure_mcp_server_url}/rpc",
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
        print(f"[Azure MCP Server] Error calling {method}: {str(e)}")
        raise


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
