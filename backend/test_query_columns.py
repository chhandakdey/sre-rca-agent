"""
Test to see what columns are returned by App Insights query
"""
import sys
sys.path.insert(0, '.')

from config import settings
from azure.identity import DefaultAzureCredential
import requests

app_id = settings.app_insights_app_id

kql_query = """
requests
| where timestamp > ago(24h)
| where success == false or toint(resultCode) >= 400
| union (traces | where timestamp > ago(24h) and severityLevel >= 2)
| union (exceptions | where timestamp > ago(24h))
| order by timestamp desc
| limit 5
"""

print("Getting token...")
credential = DefaultAzureCredential()
token = credential.get_token("https://api.applicationinsights.io/.default")

api_url = f"https://api.applicationinsights.io/v1/apps/{app_id}/query"

headers = {
    "Authorization": f"Bearer {token.token}",
    "Content-Type": "application/json"
}

data = {"query": kql_query}

print(f"Querying: {api_url}")
response = requests.post(api_url, headers=headers, json=data, timeout=60)

if response.status_code == 200:
    result = response.json()
    tables = result.get("tables", [])
    
    for table in tables:
        columns = [col["name"] for col in table.get("columns", [])]
        rows = table.get("rows", [])
        
        print(f"\n=== Columns ({len(columns)}) ===")
        print(columns)
        
        print(f"\n=== First Row ===")
        if rows:
            row_dict = dict(zip(columns, rows[0]))
            for key, value in row_dict.items():
                print(f"{key}: {value}")
else:
    print(f"Error {response.status_code}: {response.text}")
