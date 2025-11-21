"""
Direct test of App Insights query function
"""
import sys
sys.path.insert(0, '.')

from integrations.azure_mcp import query_app_insights_logs
from config import settings

# Build a simple KQL query
kql_query = """
requests
| where timestamp > ago(720h)
| where success == false or toint(resultCode) >= 400
| union (traces | where timestamp > ago(720h) | where severityLevel >= 2)
| union (exceptions | where timestamp > ago(720h))
| order by timestamp desc
| limit 100
"""

print("=" * 80)
print("Testing App Insights Query")
print("=" * 80)
print(f"\nApp Insights Workspace ID: {settings.app_insights_workspace_id}")
print(f"App Insights App ID: {settings.app_insights_app_id}")
print(f"\nKQL Query:")
print(kql_query)
print("\n" + "=" * 80)

# Query logs
logs = query_app_insights_logs(
    workspace_id=settings.app_insights_workspace_id,
    kql_query=kql_query
)

print(f"\nResults: {len(logs)} log entries found")

if logs:
    print("\nFirst 3 log entries:")
    for i, log in enumerate(logs[:3], 1):
        print(f"\n{i}. Timestamp: {log.timestamp}")
        print(f"   Severity: {log.severity}")
        print(f"   Message: {log.message[:100]}...")
        print(f"   Service: {log.service_name}")
        print(f"   Error Code: {log.error_code}")
else:
    print("\nNo logs found!")
