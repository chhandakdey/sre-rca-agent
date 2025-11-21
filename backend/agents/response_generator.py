"""  
Response Generator Agent

This agent generates the final response for the Teams chatbot,
formatting correlation results into a user-friendly summary with
recommendations and optional Adaptive Card format.
"""

from typing import Dict, Any, List
from datetime import datetime

from models import (
    CorrelationResult, RCAResponse, CorrelationMatch,
    ParsedContext, AgentResult
)
from config import settings
class ResponseGeneratorAgent:
    """
    Agent responsible for generating the final RCA response.
    
    This agent formats correlation results into a comprehensive,
    actionable response for Teams chatbot users.
    """
    
    def __init__(self):
        """Initialize the Response Generator Agent"""
        # Simple response generation without LLM
        pass
    
    async def generate_response(
        self,
        parsed_context: ParsedContext,
        correlation_result: CorrelationResult,
        execution_metadata: Dict[str, Any] = None
    ) -> AgentResult:
        """
        Generate final RCA response.
        
        Args:
            parsed_context: Parsed incident context
            correlation_result: Correlation analysis results
            execution_metadata: Metadata about the investigation
            
        Returns:
            AgentResult with RCAResponse data
        """
        start_time = datetime.utcnow()
        
        try:
            # Generate executive summary using LLM
            summary = await self._generate_summary(parsed_context, correlation_result)
            
            # Get top suspects (already ranked)
            top_suspects = correlation_result.matches[:5]
            
            # Build timeline
            timeline = self._build_timeline(correlation_result)
            
            # Generate recommendations
            recommendations = self._generate_recommendations(
                parsed_context,
                correlation_result
            )
            
            # Build investigation metadata
            metadata = execution_metadata or {}
            metadata.update({
                "total_matches": correlation_result.total_matches,
                "anomalies_detected": len(correlation_result.anomalies_detected),
                "analysis_time": correlation_result.analysis_timestamp.isoformat(),
                "top_confidence": top_suspects[0].confidence_level.value if top_suspects else "none"
            })
            
            # Generate Teams Adaptive Card (optional)
            adaptive_card = self._generate_adaptive_card(
                summary,
                top_suspects,
                recommendations
            )
            
            # Build final response
            rca_response = RCAResponse(
                summary=summary,
                top_suspects=top_suspects,
                timeline=timeline,
                recommendations=recommendations,
                investigation_metadata=metadata,
                adaptive_card=adaptive_card
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return AgentResult(
                agent_name="response_generator",
                success=True,
                data=rca_response,
                error=None,
                execution_time=execution_time,
                metadata={"response_length": len(summary)}
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Generate fallback response
            fallback_response = self._generate_fallback_response(parsed_context)
            
            return AgentResult(
                agent_name="response_generator",
                success=False,
                data=fallback_response,
                error=str(e),
                execution_time=execution_time,
                metadata={"fallback": True}
            )
    
    async def _generate_summary(
        self,
        parsed_context: ParsedContext,
        correlation_result: CorrelationResult
    ) -> str:
        """
        Generate executive summary using rule-based template.
        
        Args:
            parsed_context: Parsed context
            correlation_result: Correlation results
            
        Returns:
            Summary string
        """
        # Simple rule-based summary generation
        if correlation_result.matches:
            top_match = correlation_result.matches[0]
            
            # Extract API endpoint info from logs
            api_info = ""
            if top_match.related_logs:
                apis = set()
                for log in top_match.related_logs[:5]:
                    if log.service_name:
                        apis.add(log.service_name)
                if apis:
                    api_info = f" affecting API endpoint(s): {', '.join(list(apis)[:3])}"
            
            error_count = len(top_match.related_logs)
            return (f"Investigation of {parsed_context.summary} identified "
                   f"{top_match.cause_description} as the most likely cause "
                   f"({top_match.confidence_level.value} confidence) with "
                   f"{error_count} error occurrence(s){api_info}.")
        else:
            return (f"Investigation of {parsed_context.summary} did not "
                   f"identify a clear root cause. Manual review recommended.")
    
    def _build_timeline(self, correlation_result: CorrelationResult) -> List[Dict[str, Any]]:
        """
        Build timeline of events.
        
        Args:
            correlation_result: Correlation results
            
        Returns:
            List of timeline events
        """
        timeline = []
        
        # Collect all events with timestamps
        events = []
        
        for match in correlation_result.matches[:5]:
            # Add deployment events
            for deployment in match.related_deployments:
                events.append({
                    "timestamp": deployment.started_time,
                    "type": "deployment",
                    "description": f"Deployment started: {deployment.pipeline_name}",
                    "status": deployment.status.value
                })
                
                if deployment.completed_time:
                    events.append({
                        "timestamp": deployment.completed_time,
                        "type": "deployment",
                        "description": f"Deployment completed: {deployment.pipeline_name}",
                        "status": deployment.status.value
                    })
            
            # Add commit events
            for commit in match.related_commits:
                events.append({
                    "timestamp": commit.timestamp,
                    "type": "commit",
                    "description": f"Commit: {commit.message[:80]}",
                    "author": commit.author
                })
            
            # Add log events with API endpoints
            for log in match.related_logs[:5]:  # Increased from 2 to 5
                # Extract API endpoint from service_name or message
                api_endpoint = log.service_name or "N/A"
                error_details = log.message[:150]
                
                events.append({
                    "timestamp": log.timestamp,
                    "type": "log",
                    "description": f"{log.severity.value.upper()}: {error_details}",
                    "severity": log.severity.value,
                    "api_endpoint": api_endpoint,
                    "error_code": log.error_code or "N/A",
                    "stack_trace": log.stack_trace[:200] if log.stack_trace else None
                })
        
        # Sort by timestamp
        events.sort(key=lambda e: e["timestamp"])
        
        # Format for output
        for event in events[:15]:  # Increased to 15 events to show more logs
            timeline_item = {
                "time": event["timestamp"].isoformat(),
                "type": event["type"],
                "description": event["description"],
                "metadata": {k: v for k, v in event.items() 
                            if k not in ["timestamp", "type", "description"]}
            }
            
            # Add detailed error info for log events
            if event["type"] == "log":
                timeline_item["api_endpoint"] = event.get("api_endpoint", "N/A")
                timeline_item["error_code"] = event.get("error_code", "N/A")
                if event.get("stack_trace"):
                    timeline_item["stack_trace_preview"] = event["stack_trace"]
            
            timeline.append(timeline_item)
        
        return timeline
    
    def _generate_recommendations(
        self,
        parsed_context: ParsedContext,
        correlation_result: CorrelationResult
    ) -> List[str]:
        """
        Generate actionable recommendations.
        
        Args:
            parsed_context: Parsed context
            correlation_result: Correlation results
            
        Returns:
            List of recommendations
        """
        recommendations = []
        
        if not correlation_result.matches:
            recommendations.extend([
                "No clear correlations found - conduct manual investigation",
                "Review service logs for additional context",
                f"Check {parsed_context.service_name or 'affected service'} configuration"
            ])
            return recommendations
        
        top_match = correlation_result.matches[0]
        
        # Deployment-related recommendations
        if top_match.related_deployments:
            deployment = top_match.related_deployments[0]
            
            if deployment.status.value == "succeeded":
                recommendations.append(
                    f"Review and consider rolling back deployment '{deployment.pipeline_name}' "
                    f"(Run ID: {deployment.run_id})"
                )
            
            if top_match.related_commits:
                commit = top_match.related_commits[0]
                recommendations.append(
                    f"Examine commit {commit.sha[:8]} by {commit.author}: '{commit.message[:60]}...'"
                )
                
                if commit.files_changed:
                    recommendations.append(
                        f"Focus on modified files: {', '.join(commit.files_changed[:3])}"
                    )
        
        # Error-specific recommendations
        if parsed_context.error_codes:
            error_code = parsed_context.error_codes[0]
            recommendations.append(
                f"Search documentation and known issues for error code: {error_code}"
            )
        
        # Monitoring recommendations
        if parsed_context.service_name:
            recommendations.append(
                f"Increase monitoring and alerting for {parsed_context.service_name}"
            )
        
        # Anomaly recommendations
        if correlation_result.anomalies_detected:
            recommendations.append(
                f"Investigate {len(correlation_result.anomalies_detected)} detected anomalies "
                "in log patterns"
            )
        
        # Generic recommendation
        if len(recommendations) == 0:
            recommendations.append("Continue monitoring for additional symptoms")
        
        return recommendations[:5]  # Limit to 5 recommendations
    
    def _generate_adaptive_card(
        self,
        summary: str,
        top_suspects: List[CorrelationMatch],
        recommendations: List[str]
    ) -> Dict[str, Any]:
        """
        Generate Teams Adaptive Card JSON.
        
        Args:
            summary: Executive summary
            top_suspects: Top correlation matches
            recommendations: Recommendations
            
        Returns:
            Adaptive Card JSON
        """
        # Build Adaptive Card structure
        card = {
            "type": "AdaptiveCard",
            "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
            "version": "1.4",
            "body": [
                {
                    "type": "TextBlock",
                    "text": "🔍 RCA Investigation Results",
                    "weight": "bolder",
                    "size": "large",
                    "color": "accent"
                },
                {
                    "type": "TextBlock",
                    "text": summary,
                    "wrap": True,
                    "spacing": "medium"
                },
                {
                    "type": "TextBlock",
                    "text": "Top Suspected Causes",
                    "weight": "bolder",
                    "size": "medium",
                    "spacing": "large"
                }
            ]
        }
        
        # Add top suspects
        for i, suspect in enumerate(top_suspects[:3], 1):
            # Confidence color
            confidence_color = {
                "very_high": "good",
                "high": "good",
                "medium": "warning",
                "low": "attention"
            }.get(suspect.confidence_level.value, "default")
            
            suspect_block = {
                "type": "Container",
                "spacing": "small",
                "separator": True,
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"**{i}. {suspect.cause_description}**",
                        "wrap": True
                    },
                    {
                        "type": "TextBlock",
                        "text": f"Confidence: {suspect.confidence_level.value.replace('_', ' ').title()}",
                        "color": confidence_color,
                        "size": "small"
                    },
                    {
                        "type": "TextBlock",
                        "text": f"💡 {suspect.reasoning}",
                        "wrap": True,
                        "size": "small",
                        "spacing": "small"
                    }
                ]
            }
            
            card["body"].append(suspect_block)
        
        # Add recommendations
        if recommendations:
            card["body"].append({
                "type": "TextBlock",
                "text": "📋 Recommended Actions",
                "weight": "bolder",
                "size": "medium",
                "spacing": "large"
            })
            
            for rec in recommendations[:3]:
                card["body"].append({
                    "type": "TextBlock",
                    "text": f"• {rec}",
                    "wrap": True,
                    "spacing": "small"
                })
        
        return card
    
    def _generate_fallback_response(self, parsed_context: ParsedContext) -> RCAResponse:
        """
        Generate fallback response on error.
        
        Args:
            parsed_context: Parsed context
            
        Returns:
            Basic RCA response
        """
        return RCAResponse(
            summary=f"Unable to complete full analysis of: {parsed_context.summary}",
            top_suspects=[],
            timeline=[],
            recommendations=[
                "Manual investigation required",
                "Check service logs and metrics",
                "Contact on-call engineer"
            ],
            investigation_metadata={
                "status": "incomplete",
                "error": "Analysis failed"
            }
        )


# Convenience function
async def generate_rca_response(
    parsed_context: ParsedContext,
    correlation_result: CorrelationResult,
    execution_metadata: Dict[str, Any] = None
) -> RCAResponse:
    """
    Standalone function to generate RCA response.
    
    Returns:
        RCA response
    """
    agent = ResponseGeneratorAgent()
    result = await agent.generate_response(
        parsed_context,
        correlation_result,
        execution_metadata
    )
    return result.data
