"""
Example Usage of SRE RCA Agent

This file demonstrates how to use the RCA system programmatically
and via API calls.
"""

import asyncio
import json
from datetime import datetime

# ============================================================================
# Example 1: Using the Orchestrator Directly
# ============================================================================

async def example_direct_usage():
    """
    Use the orchestrator directly in Python code.
    """
    from models import UserContext
    from orchestrator import OrchestratorAgent
    
    # Create user context
    user_context = UserContext(
        raw_text="""
        Users are reporting 500 errors in the payment service since 2PM today.
        The error message shows: ERR_PAYMENT_GATEWAY_TIMEOUT
        Checkout flow is completely broken.
        """,
        user_id="sre.engineer@company.com",
        timestamp=datetime.fromisoformat("2025-11-21T14:00:00")
    )
    
    # Run investigation
    orchestrator = OrchestratorAgent()
    result = await orchestrator.investigate(user_context)
    
    # Print results
    print("=" * 60)
    print("RCA INVESTIGATION RESULTS")
    print("=" * 60)
    print(f"\nSummary: {result.summary}")
    print(f"\nTop Suspects ({len(result.top_suspects)}):")
    
    for i, suspect in enumerate(result.top_suspects, 1):
        print(f"\n{i}. {suspect.cause_description}")
        print(f"   Confidence: {suspect.confidence_level.value} ({suspect.confidence_score:.2f})")
        print(f"   Reasoning: {suspect.reasoning}")
        print(f"   Evidence:")
        for evidence in suspect.evidence[:3]:
            print(f"   - {evidence}")
    
    print(f"\nRecommendations:")
    for i, rec in enumerate(result.recommendations, 1):
        print(f"{i}. {rec}")
    
    print(f"\nTimeline ({len(result.timeline)} events):")
    for event in result.timeline[:5]:
        print(f"  [{event['time']}] {event['type']}: {event['description']}")


# ============================================================================
# Example 2: Using Individual Agents
# ============================================================================

async def example_individual_agents():
    """
    Use individual agents separately for testing.
    """
    from models import UserContext, ParsedContext
    from agents.context_parser import ContextParserAgent
    from agents.github_fetcher import GitHubFetcherAgent
    
    # Step 1: Parse context
    print("Step 1: Parsing context...")
    user_context = UserContext(
        raw_text="Database connection timeout in auth-service at 3PM. Error: DB_CONN_TIMEOUT",
        user_id="test@example.com"
    )
    
    parser = ContextParserAgent()
    parse_result = await parser.parse_context(user_context)
    
    if parse_result.success:
        parsed = parse_result.data
        print(f"  Service: {parsed.service_name}")
        print(f"  Error Codes: {parsed.error_codes}")
        print(f"  Severity: {parsed.severity.value}")
        print(f"  Keywords: {parsed.keywords}")
    
    # Step 2: Fetch commits
    print("\nStep 2: Fetching GitHub commits...")
    fetcher = GitHubFetcherAgent()
    fetch_result = await fetcher.fetch_commits(parse_result.data)
    
    if fetch_result.success:
        commits = fetch_result.data.commits
        print(f"  Found {len(commits)} commits")
        for commit in commits[:3]:
            print(f"  - [{commit.sha[:8]}] {commit.message[:60]}...")


# ============================================================================
# Example 3: Using the REST API
# ============================================================================

def example_api_usage():
    """
    Use the REST API with requests library.
    """
    import requests
    
    # API endpoint
    api_url = "http://localhost:8000/api/v1/investigate"
    
    # Request payload
    payload = {
        "raw_text": """
        Mobile app users are experiencing crashes during login.
        Error appears in logs: AUTH_TOKEN_INVALID
        Started happening around 10AM this morning.
        Affects iOS app version 2.5.0
        """,
        "user_id": "mobile.support@company.com",
        "timestamp": "2025-11-21T10:00:00Z"
    }
    
    print("Sending request to API...")
    response = requests.post(api_url, json=payload, timeout=60)
    
    if response.status_code == 200:
        result = response.json()
        
        print("\nAPI Response:")
        print(f"Summary: {result['summary']}")
        print(f"\nTop Suspect:")
        if result['top_suspects']:
            suspect = result['top_suspects'][0]
            print(f"  {suspect['cause_description']}")
            print(f"  Confidence: {suspect['confidence_level']}")
        
        print(f"\nRecommendations:")
        for rec in result['recommendations']:
            print(f"  - {rec}")
    else:
        print(f"Error: {response.status_code}")
        print(response.text)


# ============================================================================
# Example 4: Testing Context Parser Only
# ============================================================================

def example_test_context_parser():
    """
    Test just the context parsing endpoint.
    """
    import requests
    
    api_url = "http://localhost:8000/api/v1/parse-context"
    
    payload = {
        "raw_text": "API gateway returning 502 errors for checkout endpoint. High latency observed.",
        "user_id": "test@example.com"
    }
    
    response = requests.post(api_url, json=payload)
    
    if response.status_code == 200:
        parsed = response.json()
        print("Parsed Context:")
        print(json.dumps(parsed, indent=2))
    else:
        print(f"Error: {response.text}")


# ============================================================================
# Example 5: Batch Processing Multiple Incidents
# ============================================================================

async def example_batch_processing():
    """
    Process multiple incidents in batch.
    """
    from models import UserContext
    from orchestrator import OrchestratorAgent
    
    incidents = [
        {
            "raw_text": "Redis cache timeout in user-service",
            "user_id": "sre1@company.com"
        },
        {
            "raw_text": "Payment processing failed with 500 errors",
            "user_id": "sre2@company.com"
        },
        {
            "raw_text": "Database replication lag detected",
            "user_id": "sre3@company.com"
        }
    ]
    
    orchestrator = OrchestratorAgent()
    
    print(f"Processing {len(incidents)} incidents...\n")
    
    for i, incident_data in enumerate(incidents, 1):
        print(f"Incident {i}: {incident_data['raw_text']}")
        
        user_context = UserContext(**incident_data)
        result = await orchestrator.investigate(user_context)
        
        print(f"  → {result.summary[:100]}...")
        if result.top_suspects:
            print(f"  → Top cause: {result.top_suspects[0].cause_description}")
        print()


# ============================================================================
# Example 6: Custom Correlation Workflow
# ============================================================================

async def example_custom_correlation():
    """
    Use correlation engine directly with custom data.
    """
    from models import (
        ParsedContext, GitHubFetchResult, DeploymentCheckResult,
        AppInsightsQueryResult, SeverityLevel
    )
    from agents.correlation_engine import CorrelationEngineAgent
    
    # Create mock data
    parsed_context = ParsedContext(
        service_name="payment-service",
        error_codes=["ERR_TIMEOUT"],
        timestamp=datetime.utcnow(),
        severity=SeverityLevel.HIGH,
        keywords=["timeout", "payment"],
        summary="Payment timeout errors"
    )
    
    github_result = GitHubFetchResult(
        commits=[],
        repository="org/repo",
        branch="main",
        time_range="24h"
    )
    
    deployment_result = DeploymentCheckResult(
        deployments=[],
        recent_failures=0
    )
    
    appinsights_result = AppInsightsQueryResult(
        logs=[],
        total_count=0,
        error_count=0,
        time_range="24h",
        kql_query=""
    )
    
    # Run correlation
    engine = CorrelationEngineAgent()
    result = await engine.correlate(
        parsed_context,
        github_result,
        deployment_result,
        appinsights_result
    )
    
    print(f"Correlation found {len(result.data.matches)} matches")


# ============================================================================
# Example 7: Teams Adaptive Card Preview
# ============================================================================

def example_adaptive_card():
    """
    Generate and display an Adaptive Card.
    """
    from models import CorrelationMatch, CorrelationResult, ConfidenceLevel, ParsedContext, SeverityLevel
    from agents.response_generator import ResponseGeneratorAgent
    
    # This would typically come from a full investigation
    # Here we create mock data for demonstration
    
    async def generate():
        parsed_context = ParsedContext(
            service_name="payment-service",
            error_codes=["500"],
            timestamp=datetime.utcnow(),
            severity=SeverityLevel.CRITICAL,
            keywords=["timeout"],
            summary="Payment service errors"
        )
        
        correlation_result = CorrelationResult(
            matches=[
                CorrelationMatch(
                    cause_description="Recent deployment",
                    confidence_score=0.9,
                    confidence_level=ConfidenceLevel.VERY_HIGH,
                    evidence=["Deployment at 2PM", "Errors started at 2:05PM"],
                    reasoning="Strong temporal correlation",
                    correlation_factors={"time": 0.95}
                )
            ],
            total_matches=1,
            analysis_timestamp=datetime.utcnow(),
            time_window_analyzed="24h",
            anomalies_detected=[]
        )
        
        generator = ResponseGeneratorAgent()
        result = await generator.generate_response(parsed_context, correlation_result)
        
        if result.data.adaptive_card:
            print("Adaptive Card JSON:")
            print(json.dumps(result.data.adaptive_card, indent=2))
    
    asyncio.run(generate())


# ============================================================================
# Main Runner
# ============================================================================

def main():
    """
    Run examples.
    """
    print("SRE RCA Agent - Usage Examples\n")
    print("Choose an example to run:")
    print("1. Direct orchestrator usage")
    print("2. Individual agents")
    print("3. REST API usage")
    print("4. Context parser only")
    print("5. Batch processing")
    print("6. Custom correlation")
    print("7. Adaptive Card preview")
    
    choice = input("\nEnter choice (1-7): ").strip()
    
    examples = {
        "1": example_direct_usage,
        "2": example_individual_agents,
        "3": example_api_usage,
        "4": example_test_context_parser,
        "5": example_batch_processing,
        "6": example_custom_correlation,
        "7": example_adaptive_card
    }
    
    example_func = examples.get(choice)
    
    if example_func:
        if asyncio.iscoroutinefunction(example_func):
            asyncio.run(example_func())
        else:
            example_func()
    else:
        print("Invalid choice")


if __name__ == "__main__":
    main()
