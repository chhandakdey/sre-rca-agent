"""
Query App Insights using the Application Insights API (not Log Analytics)
"""
import requests
from azure.identity import DefaultAzureCredential
from datetime import datetime, timedelta

def query_appinsights_direct():
    try:
        print("Querying App Insights directly...")
        print("-" * 60)
        
        # App Insights details from connection string
        app_id = "6d72b15e-fd53-497a-8b31-1576e777d3f6"
        
        print(f"\nApplication ID: {app_id}")
        
        # Get Azure credentials
        print("\n1. Getting Azure credentials...")
        credential = DefaultAzureCredential()
        token = credential.get_token("https://api.applicationinsights.io/.default")
        print(f"   ✓ Got access token")
        
        # Query API endpoint
        api_url = f"https://api.applicationinsights.io/v1/apps/{app_id}/query"
        
        # KQL query
        query = """
        requests
        | where timestamp > ago(30d)
        | order by timestamp desc
        | take 10
        """
        
        print(f"\n2. Executing query via App Insights API...")
        print(f"   Endpoint: {api_url}")
        print(f"   Query: requests (last 30 days)")
        
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json"
        }
        
        data = {
            "query": query
        }
        
        response = requests.post(api_url, headers=headers, json=data, timeout=30)
        
        print(f"   Status Code: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            tables = result.get("tables", [])
            
            if tables:
                table = tables[0]
                columns = table.get("columns", [])
                rows = table.get("rows", [])
                
                print(f"   ✓ Query successful! Found {len(rows)} requests")
                
                if rows:
                    print(f"\n3. Sample request entries:")
                    col_names = [col["name"] for col in columns]
                    print(f"   Columns: {col_names}")
                    
                    for i, row in enumerate(rows[:5], 1):
                        row_dict = dict(zip(col_names, row))
                        print(f"\n   Request {i}:")
                        print(f"      Name: {row_dict.get('name', 'N/A')}")
                        print(f"      URL: {str(row_dict.get('url', 'N/A'))[:60]}...")
                        print(f"      Result Code: {row_dict.get('resultCode', 'N/A')}")
                        print(f"      Duration: {row_dict.get('duration', 'N/A')} ms")
                        print(f"      Timestamp: {row_dict.get('timestamp', 'N/A')}")
                else:
                    print(f"\n   ⚠ No requests found in the last 30 days")
            else:
                print(f"   ⚠ No tables in response")
                
        else:
            print(f"   ✗ Query failed")
            print(f"   Response: {response.text[:500]}")
            
        # Try traces and exceptions
        print(f"\n4. Checking for traces/exceptions...")
        for table_name in ['traces', 'exceptions', 'customEvents']:
            query = f"""
            {table_name}
            | where timestamp > ago(30d)
            | take 5
            """
            
            data = {"query": query}
            response = requests.post(api_url, headers=headers, json=data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                tables = result.get("tables", [])
                if tables:
                    rows = tables[0].get("rows", [])
                    print(f"   {table_name}: {len(rows)} entries found")
            else:
                print(f"   {table_name}: Query failed ({response.status_code})")
        
        print("\n" + "="*60)
        print("Test completed!")
        
    except Exception as e:
        print(f"\n✗ Error: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    query_appinsights_direct()
