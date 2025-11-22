"""
Test GitHub Deployments Fetching

This script tests fetching deployment information from GitHub Actions workflows.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from integrations.github_mcp import fetch_recent_deployments

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_fetch_deployments():
    """Test fetching deployments from GitHub Actions."""
    try:
        logger.info("=" * 60)
        logger.info("Testing GitHub Deployments Fetch")
        logger.info("=" * 60)
        
        # Test parameters
        repository = "chhandakdey/SimpleSRETestApp"
        since = datetime.now(timezone.utc) - timedelta(days=30)
        
        logger.info(f"\nFetching deployments from: {repository}")
        logger.info(f"Since: {since.isoformat()}")
        
        # Fetch deployments
        deployments = await fetch_recent_deployments(
            repository=repository,
            since=since,
            max_results=10
        )
        
        logger.info(f"\n✓ Found {len(deployments)} deployment(s)")
        
        if deployments:
            logger.info("\nDeployment Details:")
            for i, deployment in enumerate(deployments, 1):
                logger.info(f"\n{i}. {deployment.pipeline_name}")
                logger.info(f"   Run ID: {deployment.run_id}")
                logger.info(f"   Status: {deployment.status.value}")
                logger.info(f"   Environment: {deployment.environment}")
                logger.info(f"   Started: {deployment.started_time}")
                logger.info(f"   Completed: {deployment.completed_time}")
                logger.info(f"   Commit: {deployment.commit_sha[:8] if deployment.commit_sha else 'N/A'}")
                logger.info(f"   URL: {deployment.url}")
                if deployment.error_message:
                    logger.info(f"   Error: {deployment.error_message}")
        else:
            logger.info("\n⚠ No deployments found. This might mean:")
            logger.info("  - The repository has no GitHub Actions workflows")
            logger.info("  - No workflows have run in the specified time period")
            logger.info("  - The repository might not exist or is not accessible")
        
        # Test with environment filter
        logger.info("\n" + "-" * 60)
        logger.info("Testing with environment filter (production)...")
        
        prod_deployments = await fetch_recent_deployments(
            repository=repository,
            environment="production",
            since=since,
            max_results=5
        )
        
        logger.info(f"✓ Found {len(prod_deployments)} production deployment(s)")
        
        logger.info("\n" + "=" * 60)
        logger.info("GitHub Deployments Test Complete")
        logger.info("=" * 60)
        
    except Exception as e:
        logger.error(f"❌ Error testing deployments: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_fetch_deployments())
