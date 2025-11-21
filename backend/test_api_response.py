"""
Test API response directly
"""
import requests
import json

url = "http://localhost:8000/api/v1/investigate"
payload = {
    "raw_text": "I am facing an api issue while doing division calculation",
    "user_id": "test-user",
    "timestamp": "2025-11-21T14:16:23Z"
}

print("Sending request to API...")
response = requests.post(url, json=payload)

print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    
    print(f"\n=== Response Keys ===")
    print(result.keys())
    
    print(f"\n=== Top Suspects ===")
    suspects = result.get('top_suspects', [])
    print(f"Number of suspects: {len(suspects)}")
    
    if suspects:
        print(f"\nFirst suspect structure:")
        print(json.dumps(suspects[0], indent=2, default=str))
    else:
        print("No suspects in response!")
        print(f"\nFull response:")
        print(json.dumps(result, indent=2, default=str))
else:
    print(f"Error: {response.text}")
