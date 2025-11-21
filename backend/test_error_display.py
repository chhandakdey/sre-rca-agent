import requests
import json

print("Sending request to API...")
response = requests.post(
    "http://localhost:8000/api/v1/investigate",
    json={
        "raw_text": "System.ArgumentException errors affecting the calculator divide endpoint. JSON serialization errors with infinity values.",
        "timestamp": "2025-11-21T14:17:00Z"
    }
)

print(f"\nStatus: {response.status_code}")

if response.status_code == 200:
    data = response.json()
    
    print("\n=== SUMMARY ===")
    print(data['summary'])
    
    if data['top_suspects']:
        print("\n=== TOP SUSPECT DETAILS ===")
        suspect = data['top_suspects'][0]
        
        print(f"\nCause: {suspect['cause_description']}")
        print(f"Confidence: {suspect['confidence_score']:.2f}")
        
        print("\n📋 EVIDENCE:")
        for ev in suspect['evidence']:
            print(f"  • {ev}")
        
        print("\n🔴 ERROR LOGS:")
        for i, log in enumerate(suspect['related_logs'][:3], 1):
            print(f"\n  Log #{i}:")
            print(f"    Time: {log['timestamp']}")
            print(f"    Severity: {log['severity']}")
            print(f"    API Endpoint: {log.get('service_name', 'N/A')}")
            print(f"    Error Code: {log.get('error_code', 'N/A')}")
            print(f"    Message: {log['message'][:150]}...")
            if log.get('stack_trace'):
                print(f"    Stack Trace Available: Yes ({len(log['stack_trace'])} chars)")
        
        print("\n📊 TIMELINE (First 5 events):")
        for i, event in enumerate(data['timeline'][:5], 1):
            print(f"\n  Event #{i}:")
            print(f"    Time: {event['time']}")
            print(f"    Type: {event['type']}")
            print(f"    Description: {event['description'][:100]}...")
            if event.get('api_endpoint'):
                print(f"    API Endpoint: {event['api_endpoint']}")
            if event.get('error_code'):
                print(f"    Error Code: {event['error_code']}")
else:
    print(f"Error: {response.text}")
