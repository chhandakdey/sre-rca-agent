"""
Orchestrator - Controller Agent

This is the main orchestrator that coordinates all agents in the RCA workflow.
It manages the execution flow and aggregates results from individual agents.
"""

from typing import Optional
from datetime import datetime
import uuid
import asyncio

from models import (
    UserContext, ParsedContext, AgentExecutionContext, 
    RCAResponse, AgentResult
)
from config import settings

# Import agents
from agents.context_parser import ContextParserAgent
from agents.github_fetcher import GitHubFetcherAgent
from agents.correlation_engine import CorrelationEngineAgent
from agents.response_generator import ResponseGeneratorAgent

# Import tool agents (these use tools directly)
from tools import (
    AzureDevOpsDeploymentTool,
    AppInsightsLogTool,
    parse_tool_output
)


class OrchestratorAgent:
    """
    Controller Agent that orchestrates the entire RCA workflow.
    
    This agent:
    1. Initializes all sub-agents
    2. Manages execution context
    3. Coordinates agent invocations in the correct order
    4. Handles errors and fallbacks
    5. Aggregates results into final response
    """
    
    def __init__(self):
        """Initialize the orchestrator with all agents"""
        
        # Initialize all agents
        self.context_parser = ContextParserAgent()
        self.github_fetcher = GitHubFetcherAgent()
        self.correlation_engine = CorrelationEngineAgent()
        self.response_generator = ResponseGeneratorAgent()
        
        # Initialize tools for direct use
        self.devops_tool = AzureDevOpsDeploymentTool()
        self.appinsights_tool = AppInsightsLogTool()
    
    async def investigate(self, user_context: UserContext) -> RCAResponse:
        """
        Main orchestration method - runs the full RCA investigation.
        
        This method coordinates all agents in the proper sequence:
        1. Parse user context
        2. Fetch GitHub commits (parallel with deployments and logs)
        3. Check Azure DevOps deployments (parallel)
        4. Query App Insights logs (parallel)
        5. Correlate all data
        6. Generate final response
        
        Args:
            user_context: User-provided incident context
            
        Returns:
            Complete RCA response
        """
        # Create execution context
        execution_ctx = AgentExecutionContext(
            request_id=str(uuid.uuid4()),
            user_context=user_context
        )
        
        try:
            # ================================================================
            # STEP 1: Parse User Context
            # ================================================================
            print(f"[Orchestrator] Step 1/6: Parsing user context...")
            parse_result = await self.context_parser.parse_context(user_context)
            
            if not parse_result.success:
                execution_ctx.errors.append(f"Context parsing failed: {parse_result.error}")
            
            execution_ctx.parsed_context = parse_result.data
            print(f"[Orchestrator] ✓ Context parsed: {execution_ctx.parsed_context.summary}")
            
            # ================================================================
            # STEP 2-4: Fetch Data in Parallel
            # ================================================================
            print(f"[Orchestrator] Step 2-4/6: Fetching data from multiple sources...")
            
            # Run GitHub, DevOps, and AppInsights queries in parallel
            github_task = self._fetch_github_data(execution_ctx)
            devops_task = self._fetch_devops_data(execution_ctx)
            appinsights_task = self._fetch_appinsights_data(execution_ctx)
            
            # Wait for all to complete
            github_result, devops_result, appinsights_result = await asyncio.gather(
                github_task,
                devops_task,
                appinsights_task,
                return_exceptions=True
            )
            
            # Handle results
            if isinstance(github_result, AgentResult):
                execution_ctx.github_result = github_result.data
                print(f"[Orchestrator] ✓ GitHub: {len(github_result.data.commits)} commits found")
            else:
                execution_ctx.errors.append(f"GitHub fetch failed: {str(github_result)}")
            
            if isinstance(devops_result, AgentResult):
                execution_ctx.deployment_result = devops_result.data
                print(f"[Orchestrator] ✓ DevOps: {len(devops_result.data.deployments)} deployments found")
            else:
                execution_ctx.errors.append(f"DevOps fetch failed: {str(devops_result)}")
            
            if isinstance(appinsights_result, AgentResult):
                execution_ctx.appinsights_result = appinsights_result.data
                print(f"[Orchestrator] ✓ AppInsights: {appinsights_result.data.total_count} logs found")
            else:
                execution_ctx.errors.append(f"AppInsights fetch failed: {str(appinsights_result)}")
            
            # ================================================================
            # STEP 5: Correlate Data
            # ================================================================
            print(f"[Orchestrator] Step 5/6: Correlating data...")
            
            correlation_result = await self.correlation_engine.correlate(
                execution_ctx.parsed_context,
                execution_ctx.github_result,
                execution_ctx.deployment_result,
                execution_ctx.appinsights_result
            )
            
            if not correlation_result.success:
                execution_ctx.errors.append(f"Correlation failed: {correlation_result.error}")
            
            execution_ctx.correlation_result = correlation_result.data
            print(f"[Orchestrator] ✓ Found {len(correlation_result.data.matches)} correlations")
            
            # ================================================================
            # STEP 6: Generate Response
            # ================================================================
            print(f"[Orchestrator] Step 6/6: Generating response...")
            
            # Prepare execution metadata
            execution_ctx.completed_at = datetime.utcnow()
            duration = (execution_ctx.completed_at - execution_ctx.started_at).total_seconds()
            
            metadata = {
                "request_id": execution_ctx.request_id,
                "duration_seconds": duration,
                "agents_invoked": 6,
                "errors": execution_ctx.errors,
                "github_commits": len(execution_ctx.github_result.commits) if execution_ctx.github_result else 0,
                "deployments": len(execution_ctx.deployment_result.deployments) if execution_ctx.deployment_result else 0,
                "logs_analyzed": execution_ctx.appinsights_result.total_count if execution_ctx.appinsights_result else 0
            }
            
            response_result = await self.response_generator.generate_response(
                execution_ctx.parsed_context,
                execution_ctx.correlation_result,
                metadata
            )
            
            execution_ctx.final_response = response_result.data
            print(f"[Orchestrator] ✓ Investigation complete in {duration:.2f}s")
            
            return execution_ctx.final_response
            
        except Exception as e:
            # Handle catastrophic failure
            print(f"[Orchestrator] ✗ Investigation failed: {str(e)}")
            execution_ctx.errors.append(f"Orchestration failed: {str(e)}")
            execution_ctx.completed_at = datetime.utcnow()
            
            # Return minimal response
            from models import RCAResponse
            return RCAResponse(
                summary=f"Investigation failed due to system error: {str(e)}",
                top_suspects=[],
                timeline=[],
                recommendations=[
                    "System error occurred during investigation",
                    "Contact system administrator",
                    "Conduct manual investigation"
                ],
                investigation_metadata={
                    "request_id": execution_ctx.request_id,
                    "errors": execution_ctx.errors,
                    "status": "failed"
                }
            )
    
    async def _fetch_github_data(self, execution_ctx: AgentExecutionContext) -> AgentResult:
        """
        Fetch GitHub commits data.
        
        Args:
            execution_ctx: Execution context
            
        Returns:
            AgentResult with GitHub data
        """
        return await self.github_fetcher.fetch_commits(
            execution_ctx.parsed_context,
            settings.correlation_time_window_hours
        )
    
    async def _fetch_devops_data(self, execution_ctx: AgentExecutionContext) -> AgentResult:
        """
        Fetch deployment data from GitHub Actions.
        
        Args:
            execution_ctx: Execution context
            
        Returns:
            AgentResult with deployment data
        """
        start_time = datetime.utcnow()
        
        try:
            # Use GitHub Actions for deployments
            from integrations.github_mcp import fetch_recent_deployments
            from datetime import timedelta
            from models import DeploymentCheckResult
            
            # Get repository from settings
            repository = f"{settings.github_org}/{settings.github_repo}"
            
            # Fetch deployments using incident time and correlation window
            deployments = await fetch_recent_deployments(
                repository=repository,
                incident_time=execution_ctx.parsed_context.timestamp,
                max_results=50
            )
            
            # Count recent failures
            recent_failures = sum(
                1 for dep in deployments 
                if dep.status.value in ["failed", "cancelled"]
            )
            
            # Find last successful deployment
            last_successful = None
            for dep in sorted(deployments, key=lambda d: d.completed_time, reverse=True):
                if dep.status.value == "succeeded":
                    last_successful = dep
                    break
            
            deployment_result = DeploymentCheckResult(
                deployments=deployments,
                recent_failures=recent_failures,
                last_successful_deployment=last_successful
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return AgentResult(
                agent_name="github_deployments",
                success=True,
                data=deployment_result,
                error=None,
                execution_time=execution_time,
                metadata={
                    "source": "github_actions",
                    "repository": repository
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            from models import DeploymentCheckResult
            return AgentResult(
                agent_name="azure_devops_deployment",
                success=False,
                data=DeploymentCheckResult(deployments=[], recent_failures=0),
                error=str(e),
                execution_time=execution_time,
                metadata={}
            )
    
    async def _fetch_appinsights_data(self, execution_ctx: AgentExecutionContext) -> AgentResult:
        """
        Fetch App Insights logs data.
        
        Args:
            execution_ctx: Execution context
            
        Returns:
            AgentResult with log data
        """
        start_time = datetime.utcnow()
        
        try:
            # Invoke App Insights tool
            result_json = self.appinsights_tool._run(
                workspace_id=settings.app_insights_workspace_id,
                time_range_hours=settings.correlation_time_window_hours,
                service_name=execution_ctx.parsed_context.service_name,
                error_code=execution_ctx.parsed_context.error_codes[0] if execution_ctx.parsed_context.error_codes else None,
                keywords=execution_ctx.parsed_context.keywords,
                severity_filter=execution_ctx.parsed_context.severity.value
            )
            
            # Parse result
            result_data = parse_tool_output(result_json)
            
            # Convert to model
            from models import AppInsightsQueryResult, LogEntry
            
            logs = []
            for log_data in result_data.get("logs", []):
                try:
                    log = LogEntry(**log_data)
                    logs.append(log)
                except Exception:
                    continue
            
            appinsights_result = AppInsightsQueryResult(
                logs=logs,
                total_count=result_data.get("total_count", len(logs)),
                error_count=result_data.get("error_count", 0),
                time_range=result_data.get("time_range", ""),
                kql_query=result_data.get("kql_query", "")
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return AgentResult(
                agent_name="app_insights_log_retriever",
                success=True,
                data=appinsights_result,
                error=None,
                execution_time=execution_time,
                metadata={}
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            from models import AppInsightsQueryResult
            return AgentResult(
                agent_name="app_insights_log_retriever",
                success=False,
                data=AppInsightsQueryResult(
                    logs=[],
                    total_count=0,
                    error_count=0,
                    time_range="",
                    kql_query=""
                ),
                error=str(e),
                execution_time=execution_time,
                metadata={}
            )


# Convenience function for standalone usage
async def run_investigation(user_context: UserContext) -> RCAResponse:
    """
    Run a complete RCA investigation.
    
    Args:
        user_context: User-provided context
        
    Returns:
        Complete RCA response
    """
    orchestrator = OrchestratorAgent()
    return await orchestrator.investigate(user_context)
