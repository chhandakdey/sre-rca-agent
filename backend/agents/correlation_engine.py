"""  
Correlation Engine Agent

This agent correlates logs, commits, and deployments to identify
suspected root causes. It uses both rule-based and ML-based approaches.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta
import numpy as np
from sklearn.ensemble import IsolationForest
from collections import defaultdict

from models import (
    ParsedContext, GitHubFetchResult, DeploymentCheckResult,
    AppInsightsQueryResult, CorrelationMatch, CorrelationResult,
    ConfidenceLevel, AgentResult, CommitInfo, DeploymentInfo, LogEntry
)
from config import settings
class CorrelationEngineAgent:
    """
    Agent responsible for correlating data and identifying root causes.
    
    This agent combines rule-based correlation (time proximity, service matching)
    with ML-based anomaly detection to rank suspected causes.
    """
    
    def __init__(self):
        """Initialize the Correlation Engine Agent"""
        
        # ML model for anomaly detection
        self.anomaly_detector = None
        if settings.enable_ml_correlation:
            self.anomaly_detector = IsolationForest(
                contamination=0.1,  # Expect 10% anomalies
                random_state=42
            )
    
    async def correlate(
        self,
        parsed_context: ParsedContext,
        github_result: GitHubFetchResult,
        deployment_result: DeploymentCheckResult,
        appinsights_result: AppInsightsQueryResult
    ) -> AgentResult:
        """
        Correlate all data to identify root causes.
        
        Args:
            parsed_context: Parsed incident context
            github_result: GitHub commits
            deployment_result: Deployment information
            appinsights_result: Log entries
            
        Returns:
            AgentResult with CorrelationResult data
        """
        start_time = datetime.utcnow()
        
        try:
            # Step 1: Rule-based correlation
            rule_based_matches = self._rule_based_correlation(
                parsed_context,
                github_result,
                deployment_result,
                appinsights_result
            )
            
            print(f"[Correlation] Rule-based matches: {len(rule_based_matches)}")
            
            # Step 2: ML-based anomaly detection
            anomalies = []
            if settings.enable_ml_correlation and len(appinsights_result.logs) > 10:
                anomalies = self._ml_anomaly_detection(appinsights_result.logs)
            
            # Step 3: LLM-based reasoning for complex correlations
            llm_enhanced_matches = await self._llm_reasoning(
                parsed_context,
                rule_based_matches,
                github_result,
                deployment_result
            )
            
            print(f"[Correlation] LLM enhanced matches: {len(llm_enhanced_matches)}")
            
            # Step 4: Rank and filter matches
            final_matches = self._rank_matches(llm_enhanced_matches)
            
            print(f"[Correlation] Final ranked matches: {len(final_matches)}")
            
            # Limit to top N results
            final_matches = final_matches[:settings.correlation_max_results]
            
            # Build result
            correlation_result = CorrelationResult(
                matches=final_matches,
                total_matches=len(final_matches),
                analysis_timestamp=datetime.utcnow(),
                time_window_analyzed=f"{settings.correlation_time_window_hours} hours",
                anomalies_detected=anomalies
            )
            
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            return AgentResult(
                agent_name="correlation_engine",
                success=True,
                data=correlation_result,
                error=None,
                execution_time=execution_time,
                metadata={
                    "rule_based_matches": len(rule_based_matches),
                    "anomalies_detected": len(anomalies),
                    "ml_enabled": settings.enable_ml_correlation
                }
            )
            
        except Exception as e:
            execution_time = (datetime.utcnow() - start_time).total_seconds()
            
            # Return empty result on error
            empty_result = CorrelationResult(
                matches=[],
                total_matches=0,
                analysis_timestamp=datetime.utcnow(),
                time_window_analyzed=f"{settings.correlation_time_window_hours} hours",
                anomalies_detected=[]
            )
            
            return AgentResult(
                agent_name="correlation_engine",
                success=False,
                data=empty_result,
                error=str(e),
                execution_time=execution_time,
                metadata={}
            )
    
    def _rule_based_correlation(
        self,
        parsed_context: ParsedContext,
        github_result: GitHubFetchResult,
        deployment_result: DeploymentCheckResult,
        appinsights_result: AppInsightsQueryResult
    ) -> List[CorrelationMatch]:
        """
        Perform rule-based correlation.
        
        Correlates based on:
        - Time proximity
        - Service name matching
        - Error code matching
        - File/component matching
        
        Returns:
            List of correlation matches
        """
        matches = []
        incident_time = parsed_context.timestamp
        
        print(f"[Correlation] Starting correlation...")
        print(f"[Correlation] Incident time: {incident_time}")
        print(f"[Correlation] Service name: {parsed_context.service_name}")
        print(f"[Correlation] Deployments: {len(deployment_result.deployments)}")
        print(f"[Correlation] Commits: {len(github_result.commits)}")
        print(f"[Correlation] Logs: {len(appinsights_result.logs)}")
        
        # Correlate deployments with commits and logs
        for deployment in deployment_result.deployments:
            # Calculate time proximity score
            deployment_time = deployment.completed_time or deployment.started_time
            # Ensure both timestamps are timezone-naive for comparison
            if deployment_time.tzinfo is not None:
                deployment_time = deployment_time.replace(tzinfo=None)
            if incident_time.tzinfo is not None:
                incident_time_naive = incident_time.replace(tzinfo=None)
            else:
                incident_time_naive = incident_time
            time_diff = abs((deployment_time - incident_time_naive).total_seconds())
            time_score = self._calculate_time_proximity_score(time_diff)
            
            if time_score < 0.3:  # Skip if too far in time
                continue
            
            # Find related commits
            related_commits = [
                c for c in github_result.commits
                if c.sha == deployment.commit_sha
            ]
            
            # Find related logs (within 1 hour of deployment)
            deployment_time = deployment.completed_time or deployment.started_time
            related_logs = [
                log for log in appinsights_result.logs
                if abs((log.timestamp - deployment_time).total_seconds()) < 3600
            ]
            
            # Service name matching
            service_score = 1.0 if (
                parsed_context.service_name and
                parsed_context.service_name.lower() in deployment.pipeline_name.lower()
            ) else 0.5
            
            # Calculate overall confidence
            confidence_score = (time_score * 0.4 + service_score * 0.3 + 
                              (0.3 if related_logs else 0))
            
            # Build evidence list
            evidence = []
            if time_diff < 3600:  # Within 1 hour
                evidence.append(f"Deployment completed {int(time_diff/60)} minutes before incident")
            evidence.append(f"Deployment status: {deployment.status.value}")
            if related_commits:
                evidence.append(f"Deployment included {len(related_commits)} commit(s)")
            if related_logs:
                evidence.append(f"{len(related_logs)} log entries around deployment time")
            
            # Create correlation match
            match = CorrelationMatch(
                cause_description=f"Deployment '{deployment.pipeline_name}' to {deployment.environment}",
                confidence_score=confidence_score,
                confidence_level=self._score_to_confidence_level(confidence_score),
                related_commits=related_commits,
                related_deployments=[deployment],
                related_logs=related_logs[:5],  # Limit to 5 logs
                evidence=evidence,
                reasoning=f"Deployment occurred close to incident time with {deployment.status.value} status",
                correlation_factors={
                    "time_proximity": time_score,
                    "service_match": service_score
                },
                timestamp_proximity=time_score
            )
            
            matches.append(match)
        
        # Correlate commits without deployments
        undeployed_commits = [
            c for c in github_result.commits
            if not any(c.sha == d.commit_sha for d in deployment_result.deployments)
        ]
        
        for commit in undeployed_commits[:5]:  # Limit to 5 commits
            # Ensure both timestamps are timezone-naive for comparison
            commit_time = commit.timestamp.replace(tzinfo=None) if commit.timestamp.tzinfo is not None else commit.timestamp
            incident_time_naive = incident_time.replace(tzinfo=None) if incident_time.tzinfo is not None else incident_time
            time_diff = abs((commit_time - incident_time_naive).total_seconds())
            time_score = self._calculate_time_proximity_score(time_diff)
            
            if time_score < 0.1:  # Lower threshold
                continue
            
            # Check if commit is to main/master branch (likely auto-deployed via GitHub Actions)
            is_main_branch = commit.branch.lower() in ['main', 'master', 'production', 'prod']
            
            # Check if commit touches relevant files
            file_relevance = self._calculate_file_relevance(
                commit.files_changed,
                parsed_context.service_name,
                parsed_context.keywords
            )
            
            # Find related logs within timeframe
            related_logs = []
            for log in appinsights_result.logs[:20]:
                log_time = log.timestamp.replace(tzinfo=None) if log.timestamp.tzinfo else log.timestamp
                log_commit_diff = abs((log_time - commit_time).total_seconds())
                if log_commit_diff < 7200:  # Within 2 hours of commit
                    related_logs.append(log)
            
            # Higher confidence for main branch commits with nearby errors
            confidence_score = (time_score * 0.4 + file_relevance * 0.3 + 
                              (0.2 if is_main_branch else 0.1) +
                              (0.1 if related_logs else 0))
            
            evidence = [
                f"Commit made {int(time_diff/60)} minutes before incident",
                f"Modified {len(commit.files_changed)} file(s)",
                f"Commit message: {commit.message[:100]}"
            ]
            
            if is_main_branch:
                evidence.append("⚠️ Commit to main branch (likely auto-deployed via GitHub Actions)")
            
            if related_logs:
                evidence.append(f"🔍 {len(related_logs)} error logs appeared after this commit")
            
            match = CorrelationMatch(
                cause_description=f"Recent commit{' (auto-deployed)' if is_main_branch else ''}: {commit.message[:60]}",
                confidence_score=confidence_score,
                confidence_level=self._score_to_confidence_level(confidence_score),
                related_commits=[commit],
                related_deployments=[],
                related_logs=[],
                evidence=evidence,
                reasoning="Recent commit that may not have been deployed yet",
                correlation_factors={
                    "time_proximity": time_score,
                    "file_relevance": file_relevance
                }
            )
            
            matches.append(match)
        
        # Correlate logs with error patterns even without deployments
        # Group logs by error code or message pattern
        print(f"[Correlation] Checking error log patterns...")
        print(f"[Correlation] Sample log messages:")
        for log in appinsights_result.logs[:3]:
            print(f"  - Message: '{log.message}' | Error code: {log.error_code} | Severity: {log.severity}")
        
        error_log_groups = defaultdict(list)
        for log in appinsights_result.logs[:50]:  # Check first 50 logs
            if log.error_code:
                print(f"[Correlation] Found log with error code: {log.error_code}")
                error_log_groups[log.error_code].append(log)
            elif "error" in log.message.lower() or "exception" in log.message.lower():
                # Group by first 50 chars of message
                key = log.message[:50]
                print(f"[Correlation] Found log with error/exception: {key}")
                error_log_groups[key].append(log)
        
        print(f"[Correlation] Error log groups: {len(error_log_groups)}")
        
        # Create matches for significant error patterns
        for error_key, logs in error_log_groups.items():
            print(f"[Correlation] Processing error key '{error_key}' with {len(logs)} logs")
            if len(logs) < 1:  # Skip if no logs (should never happen)
                print(f"[Correlation] Skipping - only {len(logs)} occurrence(s)")
                continue
            
            # Find related commits (within time window)
            related_commits = []
            for commit in github_result.commits[:10]:
                commit_time = commit.timestamp.replace(tzinfo=None) if commit.timestamp.tzinfo else commit.timestamp
                log_time = logs[0].timestamp.replace(tzinfo=None) if logs[0].timestamp.tzinfo else logs[0].timestamp
                time_diff = abs((commit_time - log_time).total_seconds())
                
                if time_diff < 86400:  # Within 24 hours
                    related_commits.append(commit)
            
            # Calculate confidence based on frequency and recency
            log_count = len(logs)
            newest_log = max(logs, key=lambda x: x.timestamp)
            log_time = newest_log.timestamp.replace(tzinfo=None) if newest_log.timestamp.tzinfo else newest_log.timestamp
            incident_time_naive = incident_time.replace(tzinfo=None) if incident_time.tzinfo else incident_time
            time_diff = abs((log_time - incident_time_naive).total_seconds())
            time_score = self._calculate_time_proximity_score(time_diff)
            
            # Higher score for more frequent errors
            frequency_score = min(log_count / 10.0, 1.0)
            confidence_score = (time_score * 0.5 + frequency_score * 0.5)
            
            # Extract API endpoints from logs
            api_endpoints = set()
            sample_errors = []
            for log in logs[:5]:
                if log.service_name:
                    api_endpoints.add(log.service_name)
                # Collect sample error messages
                if log.message and len(sample_errors) < 3:
                    sample_errors.append(log.message[:100])
            
            evidence = [
                f"Found {log_count} occurrences of this error pattern",
                f"Most recent occurrence: {newest_log.timestamp}",
                f"Service: {newest_log.service_name or 'Unknown'}"
            ]
            
            if api_endpoints:
                evidence.append(f"🔴 Affected API endpoint(s): {', '.join(list(api_endpoints)[:3])}")
            
            if sample_errors:
                evidence.append(f"📋 Sample errors: {sample_errors[0][:80]}...")
            
            if related_commits:
                evidence.append(f"{len(related_commits)} commits in timeframe")
            
            match = CorrelationMatch(
                cause_description=f"Error pattern: {error_key}",
                confidence_score=confidence_score,
                confidence_level=self._score_to_confidence_level(confidence_score),
                related_commits=related_commits[:3],
                related_deployments=[],
                related_logs=logs[:5],
                evidence=evidence,
                reasoning=f"Recurring error pattern with {log_count} occurrences near incident time",
                correlation_factors={
                    "time_proximity": time_score,
                    "frequency": frequency_score,
                    "has_commits": 1.0 if related_commits else 0.0
                },
                timestamp_proximity=time_score
            )
            
            matches.append(match)
        
        print(f"[Correlation] Total matches created: {len(matches)}")
        return matches
    
    def _calculate_time_proximity_score(self, time_diff_seconds: float) -> float:
        """
        Calculate time proximity score (0-1).
        
        Closer in time = higher score
        Uses exponential decay: score = e^(-time_diff / decay_constant)
        
        Args:
            time_diff_seconds: Time difference in seconds
            
        Returns:
            Score between 0 and 1
        """
        # Decay constant: 1 hour = 3600 seconds
        # After 1 hour, score = ~0.37
        # After 4 hours, score = ~0.02
        decay_constant = 3600
        score = np.exp(-abs(time_diff_seconds) / decay_constant)
        return float(score)
    
    def _calculate_file_relevance(
        self,
        files: List[str],
        service_name: str,
        keywords: List[str]
    ) -> float:
        """
        Calculate file relevance score based on service name and keywords.
        
        Args:
            files: List of file paths
            service_name: Service name to match
            keywords: Keywords to match
            
        Returns:
            Score between 0 and 1
        """
        if not files:
            return 0.0
        
        relevance_scores = []
        
        for file_path in files:
            file_lower = file_path.lower()
            score = 0.0
            
            # Check service name match
            if service_name and service_name.lower() in file_lower:
                score += 0.5
            
            # Check keyword matches
            keyword_matches = sum(1 for kw in keywords if kw.lower() in file_lower)
            if keyword_matches > 0:
                score += min(0.5, keyword_matches * 0.1)
            
            relevance_scores.append(min(1.0, score))
        
        # Return average relevance
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    
    def _ml_anomaly_detection(self, logs: List[LogEntry]) -> List[str]:
        """
        Perform ML-based anomaly detection on logs.
        
        Uses Isolation Forest to detect unusual patterns.
        
        Args:
            logs: Log entries
            
        Returns:
            List of detected anomaly descriptions
        """
        if not logs or len(logs) < 10:
            return []
        
        try:
            # Extract features from logs
            # Features: hour of day, severity level, message length
            features = []
            for log in logs:
                hour = log.timestamp.hour
                severity_map = {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}
                severity_val = severity_map.get(log.severity.value, 0)
                msg_length = len(log.message)
                
                features.append([hour, severity_val, msg_length])
            
            X = np.array(features)
            
            # Fit and predict
            predictions = self.anomaly_detector.fit_predict(X)
            
            # Find anomalies
            anomaly_indices = np.where(predictions == -1)[0]
            
            anomalies = []
            for idx in anomaly_indices[:5]:  # Limit to 5 anomalies
                log = logs[idx]
                anomalies.append(
                    f"Unusual log at {log.timestamp.strftime('%H:%M:%S')}: "
                    f"{log.severity.value} - {log.message[:100]}"
                )
            
            return anomalies
            
        except Exception:
            return []
    
    async def _llm_reasoning(
        self,
        parsed_context: ParsedContext,
        rule_matches: List[CorrelationMatch],
        github_result: GitHubFetchResult,
        deployment_result: DeploymentCheckResult
    ) -> List[CorrelationMatch]:
        """
        Skip LLM reasoning and return rule-based matches as-is.
        
        Args:
            parsed_context: Parsed context
            rule_matches: Rule-based correlation matches
            github_result: GitHub data
            deployment_result: Deployment data
            
        Returns:
            Original correlation matches (without LLM enhancement)
        """
        # Simply return the rule-based matches without LLM enhancement
        return rule_matches
    
    def _rank_matches(self, matches: List[CorrelationMatch]) -> List[CorrelationMatch]:
        """
        Rank correlation matches by confidence score.
        
        Args:
            matches: List of correlation matches
            
        Returns:
            Sorted list of matches (highest confidence first)
        """
        return sorted(matches, key=lambda m: m.confidence_score, reverse=True)
    
    def _score_to_confidence_level(self, score: float) -> ConfidenceLevel:
        """
        Convert numeric score to confidence level enum.
        
        Args:
            score: Confidence score (0-1)
            
        Returns:
            ConfidenceLevel enum
        """
        if score >= 0.9:
            return ConfidenceLevel.VERY_HIGH
        elif score >= 0.7:
            return ConfidenceLevel.HIGH
        elif score >= 0.4:
            return ConfidenceLevel.MEDIUM
        else:
            return ConfidenceLevel.LOW


# Convenience function
async def correlate_data(
    parsed_context: ParsedContext,
    github_result: GitHubFetchResult,
    deployment_result: DeploymentCheckResult,
    appinsights_result: AppInsightsQueryResult
) -> CorrelationResult:
    """
    Standalone function to correlate data.
    
    Returns:
        Correlation result
    """
    agent = CorrelationEngineAgent()
    result = await agent.correlate(
        parsed_context,
        github_result,
        deployment_result,
        appinsights_result
    )
    return result.data
