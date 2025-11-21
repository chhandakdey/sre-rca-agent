"""
Test script to debug App Insights integration
"""
import sys
import traceback
from datetime import datetime, timedelta

def test_appinsights():
    try:
        print("Testing App Insights Integration...")
        print("-" * 60)
        
        # Test imports
        print("\n1. Testing imports...")
        from azure.identity import DefaultAzureCredential
        from azure.monitor.query import LogsQueryClient, LogsQueryStatus
        print("   ✓ Azure imports successful")
        
        # Test configuration
        print("\n2. Testing configuration...")
        from config import settings
        workspace_id = settings.app_insights_workspace_id
        print(f"   Workspace ID: {workspace_id[:20]}...")
        
        # Test credential
        print("\n3. Testing Azure credentials...")
        try:
            credential = DefaultAzureCredential()
            print("   ✓ DefaultAzureCredential initialized")
        except Exception as e:
            print(f"   ✗ Credential error: {e}")
            print("\n   Note: DefaultAzureCredential requires one of:")
            print("   - Azure CLI login (az login)")
            print("   - Environment variables (AZURE_CLIENT_ID, AZURE_TENANT_ID, AZURE_CLIENT_SECRET)")
            print("   - Managed identity (when running in Azure)")
            return
        
        # Test query
        print("\n4. Testing available tables...")
        client = LogsQueryClient(credential)
        
        # First, try to list available tables
        schema_query = """
        search *
        | summarize count() by $table
        | order by count_ desc
        """
        
        print(f"   Checking what tables exist in the workspace...")
        try:
            response = client.query_workspace(
                workspace_id=workspace_id,
                query=schema_query,
                timespan=timedelta(days=30)
            )
            
            if response.status == LogsQueryStatus.SUCCESS:
                print(f"   ✓ Available tables in workspace:")
                for table in response.tables:
                    for row in table.rows:
                        row_dict = dict(zip([col.name for col in table.columns], row))
                        table_name = row_dict.get('$table') or row_dict.get('Column1')
                        count = row_dict.get('count_') or row_dict.get('Column2')
                        print(f"     - {table_name}: {count} rows")
            else:
                print(f"   Schema query status: {response.status}")
        except Exception as e:
            print(f"   Could not list tables: {e}")
        
        # Try AppTraces and AppExceptions (new schema)
        print("\n5. Testing App Insights query with new schema...")
        kql_query = """
        AppTraces
        | union AppExceptions  
        | where TimeGenerated > ago(30d)
        | order by TimeGenerated desc
        | limit 10
        """
        
        print(f"   Executing KQL query...")
        response = client.query_workspace(
            workspace_id=workspace_id,
            query=kql_query,
            timespan=timedelta(days=30)
        )
        
        print(f"   Query status: {response.status}")
        
        if response.status == LogsQueryStatus.SUCCESS:
            total_rows = sum(len(table.rows) for table in response.tables)
            print(f"   ✓ Query successful! Found {total_rows} log entries")
            
            if total_rows > 0:
                print("\n5. Sample log entries:")
                for table in response.tables:
                    print(f"   Table columns: {[col.name for col in table.columns]}")
                    for i, row in enumerate(table.rows[:3], 1):
                        row_dict = dict(zip([col.name for col in table.columns], row))
                        print(f"   Row {i}: timestamp={row_dict.get('timestamp')}, message={str(row_dict.get('message', ''))[:50]}...")
            else:
                print("\n   ⚠ No log entries found in the last 7 days")
                print("   This could mean:")
                print("   - No application logs have been sent to App Insights")
                print("   - The workspace ID is incorrect")
                print("   - The application is not configured to send logs")
        else:
            print(f"   ✗ Query failed with status: {response.status}")
            if hasattr(response, 'partial_error'):
                print(f"   Error: {response.partial_error}")
        
    except Exception as e:
        print(f"\n✗ Error occurred: {type(e).__name__}: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_appinsights()
