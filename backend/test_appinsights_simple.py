"""
Simple test to verify Application Insights API connectivity
"""
import asyncio
import sys
sys.path.insert(0, '.')

from integrations.azure_mcp import query_app_insights_logs
from config import settings

async def test_simple_query():
    """Test with a very simple KQL query"""
    
    print("=" * 80)
    print("Testing Application Insights API")
    print("=" * 80)
    print(f"\nApp ID: {settings.app_insights_app_id}")
    print(f"Workspace ID: {settings.app_insights_workspace_id}")
    
    # Test 1: Simple query - just count requests
    print("\n" + "-" * 80)
    print("Test 1: Simple requests count")
    print("-" * 80)
    
    simple_query = """
requests
| where timestamp > ago(24h)
| take 10
"""
    
    print(f"Query:\n{simple_query}")
    
    try:
        logs = await query_app_insights_logs(
            workspace_id=settings.app_insights_app_id or settings.app_insights_workspace_id,
            kql_query=simple_query
        )
        print(f"\n✓ SUCCESS: Retrieved {len(logs)} log entries")
        
        if logs:
            print("\nFirst log entry:")
            log = logs[0]
            print(f"  Timestamp: {log.timestamp}")
            print(f"  Severity: {log.severity}")
            print(f"  Message: {log.message[:100]}...")
            
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    # Test 2: Query with filters (like the actual tool uses)
    print("\n" + "-" * 80)
    print("Test 2: Query with error filters")
    print("-" * 80)
    
    filtered_query = """
requests
| where timestamp > ago(24h)
| where success == false or toint(resultCode) >= 400
| union (traces | where timestamp > ago(24h) | where severityLevel >= 2)
| union (exceptions | where timestamp > ago(24h))
| order by timestamp desc
| limit 100
"""
    
    print(f"Query:\n{filtered_query}")
    
    try:
        logs = await query_app_insights_logs(
            workspace_id=settings.app_insights_app_id or settings.app_insights_workspace_id,
            kql_query=filtered_query
        )
        print(f"\n✓ SUCCESS: Retrieved {len(logs)} log entries")
        
        if logs:
            print(f"\nFirst 3 entries:")
            for i, log in enumerate(logs[:3], 1):
                print(f"\n{i}. {log.timestamp} | {log.severity.value}")
                print(f"   {log.message[:100]}...")
                if log.error_code:
                    print(f"   Error: {log.error_code}")
                    
    except Exception as e:
        print(f"\n✗ FAILED: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_simple_query())
