import requests
import os
from dotenv import load_dotenv

load_dotenv()

# The internal URL should be used if the remote one is not accessible
API_URL = "http://localhost:8000"
# Based on main.py, it uses SANAD_API_KEY from .env
API_KEY = os.getenv("SANAD_API_KEY")

def test_endpoint(name, url, headers=None, expected_status=200):
    print(f"Testing {name}...")
    try:
        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        if response.status_code == expected_status:
            print("✅ Success")
        else:
            print(f"❌ Failed (Expected {expected_status})")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error: {e}")
    print("-" * 20)

if __name__ == "__main__":
    print(f"Using API Key: {API_KEY}")
    
    # Wait a bit for server to be ready
    import time
    time.sleep(1)

    # 1. Test unprotected endpoint without auth
    test_endpoint("Root (No Auth)", f"{API_URL}/")
    
    # 2. Test health check (wait for DB)
    test_endpoint("Health Check", f"{API_URL}/health")

    # 3. Test protected endpoint with API Key
    headers = {"X-ApiKey": API_KEY}
    test_endpoint("Profesionales (API Key)", f"{API_URL}/api/v1/profesionales", headers=headers)
    
    # 4. Test protected endpoint without auth (should fail)
    test_endpoint("Profesionales (No Auth)", f"{API_URL}/api/v1/profesionales", expected_status=401)
    
    # 5. Test protected endpoint with invalid API Key
    headers_invalid = {"X-ApiKey": "wrong-key"}
    test_endpoint("Profesionales (Invalid API Key)", f"{API_URL}/api/v1/profesionales", headers=headers_invalid, expected_status=401)
