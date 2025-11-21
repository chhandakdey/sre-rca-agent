"""
Data Models for SRE RCA Agent

This module defines all Pydantic models used across the application.
These models ensure type safety and data validation.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


# ============================================================================
# Enums and Type Definitions
# ============================================================================

class SeverityLevel(str, Enum):
    """Severity levels for errors and incidents"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DeploymentStatus(str, Enum):
    """Status of Azure DevOps deployments"""
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    IN_PROGRESS = "in_progress"
    PENDING = "pending"
    CANCELED = "canceled"
    UNKNOWN = "unknown"


class ConfidenceLevel(str, Enum):
    """Confidence level for correlation results"""
    VERY_HIGH = "very_high"  # 90-100%
    HIGH = "high"             # 70-89%
    MEDIUM = "medium"         # 40-69%
    LOW = "low"               # 0-39%


# ============================================================================
# Input Models
# ============================================================================

class UserContext(BaseModel):
    """
    User-provided context for RCA investigation.
    
    This is the initial input from the Teams chatbot user.
    """
    raw_text: str = Field(..., description="Free-form text describing the issue")
    user_id: Optional[str] = Field(None, description="ID of the user reporting the issue")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow, 
                                         description="When the issue was reported")
    
    class Config:
        json_schema_extra = {
            "example": {
                "raw_text": "Users are experiencing 500 errors in the payment service around 2PM today. Error code: ERR_PAYMENT_GATEWAY_TIMEOUT",
                "user_id": "user@company.com",
                "timestamp": "2025-11-21T14:30:00Z"
            }
        }


# ============================================================================
# Parsed Context Models
# ============================================================================

class ParsedContext(BaseModel):
    """
    Structured context extracted by the Context Parser Agent.
    
    The GPT-4.1 Nano model parses free text into structured entities.
    """
    service_name: Optional[str] = Field(None, description="Identified service or module name")
    error_codes: List[str] = Field(default_factory=list, 
                                   description="Extracted error codes")
    timestamp: Optional[datetime] = Field(None, 
                                         description="Incident timestamp")
    severity: SeverityLevel = Field(default=SeverityLevel.MEDIUM,
                                   description="Estimated severity")
    keywords: List[str] = Field(default_factory=list,
                               description="Key terms for search")
    summary: str = Field(..., description="Concise summary of the issue")
    
    class Config:
        json_schema_extra = {
            "example": {
                "service_name": "payment-service",
                "error_codes": ["ERR_PAYMENT_GATEWAY_TIMEOUT", "500"],
                "timestamp": "2025-11-21T14:00:00Z",
                "severity": "high",
                "keywords": ["timeout", "payment", "gateway"],
                "summary": "Payment service experiencing gateway timeouts"
            }
        }


# ============================================================================
# GitHub Models
# ============================================================================

class CommitInfo(BaseModel):
    """
    Information about a GitHub commit.
    
    Retrieved by the GitHub Commit Fetcher Agent.
    """
    sha: str = Field(..., description="Commit SHA")
    message: str = Field(..., description="Commit message")
    author: str = Field(..., description="Commit author")
    timestamp: datetime = Field(..., description="Commit timestamp")
    files_changed: List[str] = Field(default_factory=list,
                                    description="List of modified files")
    additions: int = Field(0, description="Lines added")
    deletions: int = Field(0, description="Lines deleted")
    branch: Optional[str] = Field(None, description="Branch name")
    url: str = Field(..., description="GitHub URL to the commit")
    
    class Config:
        json_schema_extra = {
            "example": {
                "sha": "abc123def456",
                "message": "Fix timeout handling in payment gateway",
                "author": "developer@company.com",
                "timestamp": "2025-11-21T13:45:00Z",
                "files_changed": ["src/payment/gateway.py", "src/payment/config.py"],
                "additions": 15,
                "deletions": 3,
                "branch": "main",
                "url": "https://github.com/org/repo/commit/abc123"
            }
        }


class GitHubFetchResult(BaseModel):
    """Result from GitHub Commit Fetcher Agent"""
    commits: List[CommitInfo] = Field(default_factory=list)
    repository: str = Field(..., description="Repository name")
    branch: str = Field(..., description="Branch queried")
    time_range: str = Field(..., description="Time range of search")


# ============================================================================
# Azure DevOps Models
# ============================================================================

class DeploymentInfo(BaseModel):
    """
    Azure DevOps deployment information.
    
    Retrieved by the Azure DevOps Deployment Checker Agent.
    """
    pipeline_id: str = Field(..., description="Pipeline ID")
    pipeline_name: str = Field(..., description="Pipeline name")
    run_id: str = Field(..., description="Run/build ID")
    status: DeploymentStatus = Field(..., description="Deployment status")
    started_time: datetime = Field(..., description="When deployment started")
    completed_time: Optional[datetime] = Field(None, description="When deployment completed")
    commit_sha: Optional[str] = Field(None, description="Deployed commit SHA")
    environment: str = Field(..., description="Target environment (dev/staging/prod)")
    url: str = Field(..., description="Azure DevOps URL")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    class Config:
        json_schema_extra = {
            "example": {
                "pipeline_id": "123",
                "pipeline_name": "payment-service-deploy",
                "run_id": "456",
                "status": "succeeded",
                "started_time": "2025-11-21T13:50:00Z",
                "completed_time": "2025-11-21T14:05:00Z",
                "commit_sha": "abc123def456",
                "environment": "production",
                "url": "https://dev.azure.com/org/project/_build/results?buildId=456"
            }
        }


class DeploymentCheckResult(BaseModel):
    """Result from Azure DevOps Deployment Checker Agent"""
    deployments: List[DeploymentInfo] = Field(default_factory=list)
    recent_failures: int = Field(0, description="Number of recent failures")
    last_successful_deployment: Optional[DeploymentInfo] = None


# ============================================================================
# App Insights Models
# ============================================================================

class LogEntry(BaseModel):
    """
    A single log entry from Azure App Insights.
    
    Retrieved by the App Insights Log Retriever Agent using KQL.
    """
    timestamp: datetime = Field(..., description="Log timestamp")
    severity: SeverityLevel = Field(..., description="Log severity level")
    message: str = Field(..., description="Log message")
    service_name: Optional[str] = Field(None, description="Service that generated the log")
    operation_id: Optional[str] = Field(None, description="Operation/trace ID")
    error_code: Optional[str] = Field(None, description="Error code if present")
    stack_trace: Optional[str] = Field(None, description="Stack trace if available")
    custom_properties: Dict[str, Any] = Field(default_factory=dict,
                                             description="Additional properties")
    
    class Config:
        json_schema_extra = {
            "example": {
                "timestamp": "2025-11-21T14:02:35Z",
                "severity": "critical",
                "message": "Payment gateway timeout after 30s",
                "service_name": "payment-service",
                "operation_id": "abc-123-def",
                "error_code": "ERR_PAYMENT_GATEWAY_TIMEOUT",
                "custom_properties": {"endpoint": "/api/payment/process"}
            }
        }


class AppInsightsQueryResult(BaseModel):
    """Result from App Insights Log Retriever Agent"""
    logs: List[LogEntry] = Field(default_factory=list)
    total_count: int = Field(0, description="Total number of matching logs")
    error_count: int = Field(0, description="Number of error-level logs")
    time_range: str = Field(..., description="Time range queried")
    kql_query: str = Field(..., description="KQL query executed")


# ============================================================================
# Correlation Models
# ============================================================================

class CorrelationMatch(BaseModel):
    """
    A single correlation match between logs, commits, and deployments.
    
    Generated by the Correlation Engine Agent.
    """
    cause_description: str = Field(..., description="Description of the suspected cause")
    confidence_score: float = Field(..., ge=0.0, le=1.0, 
                                   description="Confidence score (0-1)")
    confidence_level: ConfidenceLevel = Field(..., description="Confidence level")
    
    # Related entities
    related_commits: List[CommitInfo] = Field(default_factory=list)
    related_deployments: List[DeploymentInfo] = Field(default_factory=list)
    related_logs: List[LogEntry] = Field(default_factory=list)
    
    # Evidence and reasoning
    evidence: List[str] = Field(default_factory=list,
                               description="Evidence supporting this correlation")
    reasoning: str = Field(..., description="Why this is a suspected cause")
    
    # Metadata
    correlation_factors: Dict[str, float] = Field(default_factory=dict,
                                                 description="Individual factor scores")
    timestamp_proximity: Optional[float] = Field(None, 
                                                description="Time proximity score")
    
    class Config:
        json_schema_extra = {
            "example": {
                "cause_description": "Recent deployment introduced timeout in payment gateway",
                "confidence_score": 0.87,
                "confidence_level": "high",
                "evidence": [
                    "Deployment completed 5 minutes before first error",
                    "Commit modified gateway timeout configuration",
                    "95% of errors occurred after deployment"
                ],
                "reasoning": "Strong temporal correlation and code changes to affected component",
                "correlation_factors": {
                    "time_proximity": 0.95,
                    "service_match": 1.0,
                    "error_pattern": 0.78
                }
            }
        }


class CorrelationResult(BaseModel):
    """Complete result from Correlation Engine Agent"""
    matches: List[CorrelationMatch] = Field(default_factory=list)
    total_matches: int = Field(0, description="Total number of matches found")
    analysis_timestamp: datetime = Field(default_factory=datetime.utcnow)
    time_window_analyzed: str = Field(..., description="Time window analyzed")
    anomalies_detected: List[str] = Field(default_factory=list,
                                         description="ML-detected anomalies")


# ============================================================================
# Final Response Models
# ============================================================================

class RCAResponse(BaseModel):
    """
    Final response generated by the Response Generator Agent.
    
    This is what gets sent back to the Teams chatbot.
    """
    summary: str = Field(..., description="Executive summary of findings")
    top_suspects: List[CorrelationMatch] = Field(default_factory=list,
                                                description="Top suspected causes")
    timeline: List[Dict[str, Any]] = Field(default_factory=list,
                                          description="Timeline of events")
    recommendations: List[str] = Field(default_factory=list,
                                      description="Recommended actions")
    
    # Additional context
    investigation_metadata: Dict[str, Any] = Field(default_factory=dict,
                                                  description="Metadata about the investigation")
    
    # For Teams Adaptive Cards
    adaptive_card: Optional[Dict[str, Any]] = Field(None,
                                                   description="Teams Adaptive Card JSON")
    
    class Config:
        json_schema_extra = {
            "example": {
                "summary": "Investigation identified a recent deployment as the likely cause of payment service timeouts.",
                "top_suspects": [],  # Would contain CorrelationMatch objects
                "recommendations": [
                    "Review commit abc123 which modified gateway configuration",
                    "Consider rolling back deployment 456",
                    "Increase timeout threshold in payment gateway"
                ],
                "investigation_metadata": {
                    "duration_seconds": 12.5,
                    "agents_invoked": 6,
                    "confidence": "high"
                }
            }
        }


# ============================================================================
# Agent Execution Models
# ============================================================================

class AgentExecutionContext(BaseModel):
    """
    Context passed between agents during orchestration.
    
    Used by the Controller Agent to manage workflow.
    """
    request_id: str = Field(..., description="Unique request ID")
    user_context: UserContext = Field(..., description="Original user input")
    parsed_context: Optional[ParsedContext] = None
    github_result: Optional[GitHubFetchResult] = None
    deployment_result: Optional[DeploymentCheckResult] = None
    appinsights_result: Optional[AppInsightsQueryResult] = None
    correlation_result: Optional[CorrelationResult] = None
    final_response: Optional[RCAResponse] = None
    
    # Execution metadata
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    errors: List[str] = Field(default_factory=list)


class AgentResult(BaseModel):
    """
    Generic result wrapper for agent execution.
    
    Each agent returns this to indicate success/failure.
    """
    agent_name: str = Field(..., description="Name of the agent")
    success: bool = Field(..., description="Whether execution succeeded")
    data: Optional[Any] = Field(None, description="Result data")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time: float = Field(..., description="Execution time in seconds")
    metadata: Dict[str, Any] = Field(default_factory=dict)
