import requests
import os
from dotenv import load_dotenv

load_dotenv()

API_URL = "https://hok8g44w8cggs0wkc048kogg.181.42.232.26.sslip.io"
API_KEY = "SND-b7c1f90be7d318ddbadaf8d43f1e5ec6"

def test_login(rut):
    url = f"{API_URL}/api/auth/login-paciente"
    headers = {
        "X-ApiKey": API_KEY,
        "Content-Type": "application/json"
    }
    payload = {"rut": rut}
    
    print(f"Testing login for RUT: {rut}")
    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"Status Code: {response.status_code}")
        print(f"Response Body: {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Test with Camille's RUT from init_db.py
    test_login("18765432-1")
    # Test with dots
    test_login("18.765.432-1")
    # Test without dash (likely to fail based on current logic)
    test_login("187654321")
