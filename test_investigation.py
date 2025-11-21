"""
Test the full investigation flow to check App Insights integration
"""
import requests
import json

# Test the investigate endpoint
url = "http://localhost:8000/api/v1/investigate"
payload = {
    "description": "I am facing an api issue while doing division calculation",
    "severity": "high",
    "affected_services": ["calculator"],
    "time_range_hours": 720  # 30 days to match App Insights data
}

print("Sending investigation request...")
print(f"Payload: {json.dumps(payload, indent=2)}")

response = requests.post(url, json=payload)

print(f"\nStatus Code: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    print(f"\nResponse:")
    print(json.dumps(result, indent=2))
    
    # Check logs_analyzed
    print(f"\n=== LOGS ANALYZED ===")
    print(f"Logs analyzed: {result.get('logs_analyzed', 0)}")
    
    # Check suspects
    print(f"\n=== SUSPECTS ===")
    suspects = result.get('top_suspects', [])
    print(f"Number of suspects: {len(suspects)}")
    
    for i, suspect in enumerate(suspects, 1):
        print(f"\nSuspect {i}:")
        print(f"  Confidence: {suspect.get('confidence_score')}")
        print(f"  Reasoning: {suspect.get('reasoning')}")
        print(f"  Evidence: {suspect.get('evidence', {})}")
        print(f"  Related logs: {len(suspect.get('related_logs', []))}")
else:
    print(f"Error: {response.text}")
