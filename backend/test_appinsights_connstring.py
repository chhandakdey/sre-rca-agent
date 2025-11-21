"""
Test App Insights with connection string
"""
import sys
import traceback
from datetime import datetime, timedelta

def test_with_connection_string():
    try:
        print("Testing App Insights with Connection String...")
        print("-" * 60)
        
        # Parse connection string
        connection_string = "InstrumentationKey=c1eb727b-4792-4be6-85d1-31426081f808;IngestionEndpoint=https://centralindia-0.in.applicationinsights.azure.com/;LiveEndpoint=https://centralindia.livediagnostics.monitor.azure.com/;ApplicationId=6d72b15e-fd53-497a-8b31-1576e777d3f6"
        
        # Extract ApplicationId (this is what we need for queries)
        app_id = None
        for part in connection_string.split(';'):
            if part.startswith('ApplicationId='):
                app_id = part.split('=')[1]
                break
        
        print(f"\n1. Connection string parsed:")
        print(f"   Application ID: {app_id}")
        
        # Test imports
        print("\n2. Testing imports...")
        from azure.identity import DefaultAzureCredential
        from azure.monitor.query import LogsQueryClient, LogsQueryStatus
        print("   ✓ Azure imports successful")
        
        # Test credential
        print("\n3. Testing Azure credentials...")
        credential = DefaultAzureCredential()
        print("   ✓ DefaultAzureCredential initialized")
        
        # Create client
        print("\n4. Creating LogsQueryClient...")
        client = LogsQueryClient(credential)
        print("   ✓ Client created")
        
        # Try querying with Application ID
        print(f"\n5. Testing query with Application ID...")
        
        # Query using app ID (note: different from workspace ID)
        kql_query = """
        requests
        | where timestamp > ago(30d)
        | order by timestamp desc
        | limit 10
        """
        
        print(f"   Executing query on app ID: {app_id}")
        print(f"   Query: requests table (last 30 days)")
        
        try:
            response = client.query_workspace(
                workspace_id=app_id,
                query=kql_query,
                timespan=timedelta(days=30)
            )
            
            print(f"   Query status: {response.status}")
            
            if response.status == LogsQueryStatus.SUCCESS:
                total_rows = sum(len(table.rows) for table in response.tables)
                print(f"   ✓ Found {total_rows} request entries")
                
                if total_rows > 0:
                    print("\n6. Sample request entries:")
                    for table in response.tables:
                        print(f"   Columns: {[col.name for col in table.columns]}")
                        for i, row in enumerate(table.rows[:3], 1):
                            row_dict = dict(zip([col.name for col in table.columns], row))
                            print(f"   Request {i}:")
                            print(f"      Name: {row_dict.get('name', 'N/A')}")
                            print(f"      URL: {row_dict.get('url', 'N/A')[:60]}...")
                            print(f"      Result: {row_dict.get('resultCode', 'N/A')}")
                            print(f"      Duration: {row_dict.get('duration', 'N/A')}ms")
            else:
                print(f"   Query failed with status: {response.status}")
                
        except Exception as e:
            print(f"   ✗ Query with Application ID failed: {e}")
            print("\n   Trying alternative queries...")
            
            # Try different table names
            for table_name in ['AppRequests', 'AppTraces', 'AppExceptions', 'traces', 'exceptions']:
                try:
                    print(f"\n   Trying table: {table_name}")
                    alt_query = f"""
                    {table_name}
                    | limit 5
                    """
                    response = client.query_workspace(
                        workspace_id=app_id,
                        query=alt_query,
                        timespan=timedelta(days=30)
                    )
                    
                    if response.status == LogsQueryStatus.SUCCESS:
                        total_rows = sum(len(table.rows) for table in response.tables)
                        print(f"      ✓ {table_name}: {total_rows} rows found")
                        if total_rows > 0:
                            print(f"      Columns: {[col.name for col in response.tables[0].columns]}")
                    
                except Exception as te:
                    print(f"      ✗ {table_name}: {str(te)[:80]}")
        
        print("\n" + "="*60)
        print("Test completed!")
        
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {str(e)}")
        print("\nFull traceback:")
        traceback.print_exc()

if __name__ == "__main__":
    test_with_connection_string()
