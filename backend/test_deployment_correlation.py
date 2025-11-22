"""
Test Deployment Correlation with GitHub Actions

This script demonstrates how GitHub deployments can be correlated with
Azure incidents using the existing correlation engine.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from integrations.github_mcp import fetch_recent_deployments
from models import DeploymentStatus
from config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_deployment_correlation():
    """Test correlating deployments with potential incidents."""
    try:
        logger.info("=" * 60)
        logger.info("Testing GitHub Deployment Correlation")
        logger.info("=" * 60)
        
        # Simulate an incident time window
        incident_time = datetime(2025, 11, 21, 10, 30, 0, tzinfo=timezone.utc)  # Example incident time
        
        repository = "chhandakdey/SimpleSRETestApp"
        
        logger.info(f"\n📅 Incident Time: {incident_time}")
        logger.info(f"📦 Repository: {repository}")
        logger.info(f"⏱️ Correlation Window: {settings.deployment_correlation_hours} hours (from DEPLOYMENT_CORRELATION_HOURS)")
        
        # Fetch deployments using incident_time parameter
        # This will automatically use the DEPLOYMENT_CORRELATION_HOURS env variable
        deployments = await fetch_recent_deployments(
            repository=repository,
            incident_time=incident_time,
            max_results=20
        )
        
        logger.info(f"\n✓ Found {len(deployments)} total deployment(s)")
        
        # Correlate deployments near incident time
        lookback_window = timedelta(hours=settings.deployment_correlation_hours)
        correlated = []
        for deployment in deployments:
            time_diff = abs((deployment.completed_time - incident_time).total_seconds())
            if time_diff <= lookback_window.total_seconds():
                correlated.append((deployment, time_diff))
        
        logger.info(f"🎯 Found {len(correlated)} deployment(s) within correlation window")
        
        if correlated:
            # Sort by proximity to incident
            correlated.sort(key=lambda x: x[1])
            
            logger.info("\n📊 Correlated Deployments (ordered by proximity):")
            for i, (deployment, time_diff) in enumerate(correlated, 1):
                minutes_before = (incident_time - deployment.completed_time).total_seconds() / 60
                
                logger.info(f"\n{i}. {deployment.pipeline_name}")
                logger.info(f"   Status: {deployment.status.value}")
                logger.info(f"   Completed: {deployment.completed_time}")
                logger.info(f"   Time before incident: {minutes_before:.1f} minutes")
                logger.info(f"   Commit: {deployment.commit_sha[:8] if deployment.commit_sha else 'N/A'}")
                logger.info(f"   Environment: {deployment.environment}")
                
                # Highlight suspicious patterns
                if deployment.status == DeploymentStatus.FAILED:
                    logger.warning(f"   ⚠️ DEPLOYMENT FAILED - Likely root cause!")
                elif minutes_before < 30:
                    logger.info(f"   🔍 Recent deployment - Potential correlation")
                
                logger.info(f"   URL: {deployment.url}")
        
        # Test with multiple environments
        logger.info("\n" + "-" * 60)
        logger.info("Testing Environment-Specific Deployments...")
        
        for env in ["production", "staging", "development"]:
            env_deployments = await fetch_recent_deployments(
                repository=repository,
                environment=env,
                incident_time=incident_time,
                max_results=5
            )
            logger.info(f"  {env}: {len(env_deployments)} deployment(s)")
        
        logger.info("\n" + "=" * 60)
        logger.info("✓ Deployment Correlation Test Complete")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error in correlation test: {e}")
        import traceback
        traceback.print_exc()


async def demonstrate_integration():
    """Demonstrate how this integrates with the existing system."""
    logger.info("\n" + "=" * 60)
    logger.info("Integration Pattern Demonstration")
    logger.info("=" * 60)
    
    logger.info("""
    📝 Integration Flow:
    
    1. User reports incident at specific time
    2. System fetches GitHub deployments using fetch_recent_deployments()
    3. Correlation engine matches deployments to incident window
    4. System identifies potential root cause deployments
    5. GitHub MCP fetches commit details and file changes
    6. Context parser analyzes deployment changes
    7. Response generator creates RCA with deployment context
    
    📦 Key Benefits:
    
    ✓ Unified deployment tracking (GitHub + Azure DevOps)
    ✓ Commit SHA correlation across both platforms
    ✓ Environment-aware filtering
    ✓ Workflow status mapping to standard DeploymentStatus
    ✓ Direct links to GitHub Actions runs for investigation
    
    🔧 Usage in Correlation Engine:
    
    from integrations.github_mcp import fetch_recent_deployments
    from config import settings
    
    # In correlation_engine.py - Using incident_time parameter (recommended)
    github_deployments = await fetch_recent_deployments(
        repository="org/repo",
        incident_time=incident_time,  # Automatically uses DEPLOYMENT_CORRELATION_HOURS
        environment="production"
    )
    
    # Alternative: Using explicit since parameter
    github_deployments = await fetch_recent_deployments(
        repository="org/repo",
        since=incident_time - timedelta(hours=2),
        environment="production"
    )
    
    # Merge with Azure DevOps deployments
    all_deployments = azure_deployments + github_deployments
    
    # Existing correlation logic works seamlessly!
    correlated = correlate_with_time_window(
        all_deployments,
        incident_time
    )
    
    🔧 Environment Variable Configuration:
    
    # In .env file:
    DEPLOYMENT_CORRELATION_HOURS=2  # Default: 2 hours
    
    # To change the correlation window:
    DEPLOYMENT_CORRELATION_HOURS=4  # Look back 4 hours for deployments
    """)
if __name__ == "__main__":
    asyncio.run(test_deployment_correlation())
    asyncio.run(demonstrate_integration())
