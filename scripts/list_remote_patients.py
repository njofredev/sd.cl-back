import requests

API_URL = "https://hok8g44w8cggs0wkc048kogg.181.42.232.26.sslip.io"
API_KEY = "SND-b7c1f90be7d318ddbadaf8d43f1e5ec6"

def get_patients():
    # 1. Login as admin
    login_url = f"{API_URL}/api/auth/login-institucion"
    login_payload = {
        "email": "admin@sanad.cl",
        "password": "admin123",
        "rut_institucion": "9999999-9"
    }
    headers = {
        "X-ApiKey": API_KEY,
        "Content-Type": "application/json"
    }
    
    print("Logging in as admin...")
    response = requests.post(login_url, json=login_payload, headers=headers)
    if response.status_code != 200:
        print(f"Login failed: {response.text}")
        return

    token = response.json().get("access_token")
    print("Login successful.")

    # 2. Get patients
    patients_url = f"{API_URL}/api/dashboard/pacientes"
    headers["Authorization"] = f"Bearer {token}"
    
    print("Fetching patients...")
    response = requests.get(patients_url, headers=headers)
    if response.status_code != 200:
        print(f"Failed to fetch patients: {response.text}")
        return

    patients = response.json()
    print(f"Found {len(patients)} patients:")
    for p in patients:
        print(f"- RUT: {p.get('rut')}, Name: {p.get('nombre_completo')}")

if __name__ == "__main__":
    get_patients()
