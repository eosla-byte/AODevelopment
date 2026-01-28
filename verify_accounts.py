import requests
import sys

BASE_URL = "http://localhost:8005"
session = requests.Session()

try:
    # 1. Setup Admin
    print("1. Setting up admin...")
    r = session.get(f"{BASE_URL}/setup_initial_admin")
    print(f"Setup Response: {r.status_code} - {r.text}")

    # 2. Login
    print("\n2. Logging in...")
    r = session.post(f"{BASE_URL}/auth/login", data={"email": "admin@somosao.com", "password": "admin123"})
    print(f"Login Status: {r.status_code}")
    if r.status_code != 200:
        print("Login Failed")
        sys.exit(1)

    # 3. Create User
    print("\n3. Creating User...")
    data = {
        "full_name": "Verification User",
        "email": "verify@example.com",
        "password": "password123",
        "access_aodev": "true",
        "access_projects": "true" 
    }
    r = session.post(f"{BASE_URL}/api/users", data=data)
    print(f"Create User Status: {r.status_code}")
    print(f"Create User Response: {r.text}")

    # 4. Check Dashboard
    print("\n4. Checking Dashboard HTML...")
    r = session.get(f"{BASE_URL}/dashboard")
    if "Verification User" in r.text:
        print("SUCCESS: Verification User found in dashboard HTML.")
    else:
        print("FAILURE: Verification User NOT found in dashboard.")

except Exception as e:
    print(f"Exception: {e}")
