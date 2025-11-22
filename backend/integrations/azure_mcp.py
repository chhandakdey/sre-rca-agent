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
import logging
import asyncio
from azure.identity import DefaultAzureCredential, ClientSecretCredential, get_bearer_token_provider
from mcp import ClientSession, StdioServerParameters, types
from mcp.client.stdio import stdio_client

from config import settings
from models import DeploymentInfo, DeploymentStatus, LogEntry, SeverityLevel

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

async def initialize_azure_mcp() -> ClientSession:
    """
    Initialize Azure MCP client session using stdio transport.
    
    Returns:
        Initialized ClientSession
    """
    global _mcp_session, _available_tools, _stdio_context, _session_context
    
    async with _mcp_session_lock:
        if _mcp_session is not None:
            return _mcp_session
        
        try:
            logger.info("Initializing Azure MCP client session...")
            
            # MCP server configuration
            server_params = StdioServerParameters(
                command="npx",
                args=["-y", "@azure/mcp@latest", "server", "start"],
                env=None
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
            
            logger.info(f"Azure MCP initialized with {len(_available_tools)} tools")
            for tool in tools_response.tools:
                logger.debug(f"  - {tool.name}")
            
            _mcp_session = _session_context
            return _session_context
            
        except Exception as e:
            logger.error(f"Failed to initialize Azure MCP: {e}")
            import traceback
            traceback.print_exc()
            raise


async def get_azure_mcp_session() -> ClientSession:
    """
    Get or create Azure MCP session.
    
    Returns:
        Active ClientSession
    """
    global _mcp_session
    
    if _mcp_session is None:
        await initialize_azure_mcp()
    
    return _mcp_session


async def call_azure_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> Any:
    """
    Call an Azure MCP tool with the given arguments.
    
    Args:
        tool_name: Name of the MCP tool to call
        arguments: Tool arguments
        
    Returns:
        Tool response content
        
    Example:
        ```python
        result = await call_azure_mcp_tool(
            "subscription_list",
            {}
        )
        ```
    """
    try:
        session = await get_azure_mcp_session()
        
        logger.debug(f"Calling Azure MCP tool: {tool_name}")
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
        logger.error(f"Error calling Azure MCP tool {tool_name}: {e}")
        raise


async def close_azure_mcp():
    """
    Close Azure MCP session.
    """
    global _mcp_session, _stdio_context, _session_context
    
    async with _mcp_session_lock:
        if _mcp_session is not None:
            try:
                # Set session to None first to prevent new calls
                session_to_close = _session_context
                stdio_to_close = _stdio_context
                
                _mcp_session = None
                _session_context = None
                _stdio_context = None
                
                # Close session context if it exists
                if session_to_close is not None:
                    try:
                        await session_to_close.__aexit__(None, None, None)
                    except Exception as e:
                        logger.warning(f"Error closing session context (non-critical): {e}")
                
                # Close stdio context if it exists
                if stdio_to_close is not None:
                    try:
                        await stdio_to_close.__aexit__(None, None, None)
                    except Exception as e:
                        logger.warning(f"Error closing stdio context (non-critical): {e}")
                
                logger.info("Azure MCP session closed")
            except Exception as e:
                logger.error(f"Error closing Azure MCP session: {e}")




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
        logger.error(f"[Azure DevOps] Error checking deployments: {str(e)}")
        return []


async def get_deployment_logs(project: str, build_id: int) -> str:
    """
    Get logs for a specific deployment/build.
    
    Args:
        project: Project name
        build_id: Build ID
        
    Returns:
        Build logs as string
    """
    try:
        # Use MCP to get build logs
        result = await call_azure_mcp(
            "devops.get_build_logs",
            {
                "project": project,
                "build_id": build_id
            }
        )
        
        if isinstance(result, str):
            return result
        elif isinstance(result, dict):
            return json.dumps(result, indent=2)
        else:
            return str(result)
        
    except Exception as e:
        logger.error(f"[Azure DevOps] Error fetching deployment logs: {str(e)}")
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
    Query Azure App Insights logs using KQL via REST API.
    
    This function queries Application Insights directly using the REST API.
    
    Args:
        workspace_id: App Insights App ID (not workspace ID). 
                     This is a GUID found in the App Insights portal under API Access.
                     Example: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee'
        kql_query: KQL query to execute
        max_results: Maximum log entries to return
        
    Returns:
        List of LogEntry objects
        
    Note:
        The workspace_id parameter should be the Application Insights App ID,
        which is different from the Log Analytics Workspace ID.
        You can find the App ID in Azure Portal > Application Insights > API Access.
    """
    try:
        # Use direct REST API for App Insights queries
        logger.info(f"Querying App Insights with App ID: {workspace_id}")
        logger.debug(f"KQL Query: {kql_query}")
        
        # Check if we have the app_id configured
        from config import settings
        app_id = settings.app_insights_app_id or workspace_id
        
        if not app_id or app_id == workspace_id and len(workspace_id) != 36:
            logger.warning(f"App ID might be invalid. Expected format: xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx")
            logger.warning(f"Received: {workspace_id}")
            logger.info(f"Trying to use workspace_id from settings: {settings.app_insights_workspace_id}")
        
        # Get credentials
        credential = DefaultAzureCredential()
        
        # Get access token for Application Insights
        token = credential.get_token("https://api.applicationinsights.io/.default")
        
        # Make direct API call - use app_id (not workspace_id)
        api_url = f"https://api.applicationinsights.io/v1/apps/{app_id}/query"
        
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "query": kql_query
        }
        
        logger.debug(f"Making request to: {api_url}")
        
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(api_url, json=payload, headers=headers)
            
            if response.status_code == 404:
                logger.error(f"[App Insights] 404 Not Found - App ID '{app_id}' is invalid or doesn't exist")
                logger.error(f"Please check:")
                logger.error(f"  1. APP_INSIGHTS_APP_ID is set correctly in .env")
                logger.error(f"  2. The App ID (not Workspace ID) from Azure Portal > Application Insights > API Access")
                logger.error(f"  3. Your credentials have access to this Application Insights resource")
                raise ValueError(f"Invalid Application Insights App ID: {app_id}")
            
            if response.status_code == 400:
                logger.error(f"[App Insights] 400 Bad Request - Invalid query or request format")
                logger.error(f"Response body: {response.text}")
                logger.error(f"KQL Query sent: {kql_query}")
                try:
                    error_details = response.json()
                    logger.error(f"Error details: {json.dumps(error_details, indent=2)}")
                except:
                    pass
                raise ValueError(f"Invalid Application Insights query: {response.text}")
            
            response.raise_for_status()
            result = response.json()
        
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
                    logger.error(f"[App Insights] Error parsing row: {str(e)}")
                    continue
        
        logger.info(f"[App Insights] Successfully parsed {len(log_entries)} log entries")
        return log_entries
        
    except Exception as e:
        logger.error(f"[App Insights] Error querying logs: {str(e)}")
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
        logger.error(f"[Azure Monitor] Error fetching metrics: {str(e)}")
        return {"metrics": [], "error": str(e)}


# ============================================================================
# MCP Server Integration
# ============================================================================

async def call_azure_mcp(method: str, params: Dict[str, Any]) -> Any:
    """
    Call Azure MCP tools using the Model Context Protocol.
    
    This function maps method names to Azure MCP tool names and executes them.
    
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
        # Map method names to actual MCP tool names
        tool_mapping = {
            "devops.list_builds": "azd",  # Azure Developer CLI
            "appinsights.query": "monitor",  # Azure Monitor for querying logs
            "monitor.query": "monitor",
        }
        
        # Get the actual tool name or use the method as-is
        tool_name = tool_mapping.get(method, method)
        
        # Call the MCP tool using our session
        result = await call_azure_mcp_tool(tool_name, params)
        
        return result
            
    except Exception as e:
        logger.error(f"[Azure MCP] Error calling {method}: {str(e)}")
        # Fallback to direct API calls if MCP fails
        return await _azure_api_call(method, params)


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
