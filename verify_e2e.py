import os
import sys
import time
from fastapi.testclient import TestClient
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

# 1. SETUP ENV & KEYS
print("🔑 Generating Ephemeral RSA Keys...")
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
private_pem = key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
).decode("utf-8")
public_pem = key.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
).decode("utf-8")

os.environ["AO_JWT_PRIVATE_KEY_PEM"] = private_pem
os.environ["AO_JWT_PUBLIC_KEY_PEM"] = public_pem
os.environ["AO_JWT_SECRET"] = "legacy_secret_just_in_case"

# Setup Paths
BASE_DIR = os.path.abspath("backend")
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)
SERVICES_DIR = os.path.abspath("backend/services")
if SERVICES_DIR not in sys.path:
    sys.path.insert(0, SERVICES_DIR)

print("🚀 Importing Services...")
try:
    from backend.services.accounts.main import app as accounts_app
    from backend.services.finance.main import app as finance_app
    from backend.services.plugin.main import app as plugin_app
    print("✅ Services Imported")
except Exception as e:
    print(f"❌ Import Failed: {e}")
    sys.exit(1)

# 2. TEST FLOW (Using Context Managers for Startup Events)
def run_tests():
    with TestClient(accounts_app) as client_acc:
        print("\n[Startup Info] Accounts App Started")
        
        # Try Creating Admin First (Just in case)
        res_setup = client_acc.get("/setup_initial_admin") 
        print(f"[Startup] Setup Admin Status: {res_setup.status_code}") 
        
        print("\n--- TEST: LOGIN (Accounts) ---")
        login_payload = {"email": "admin@somosao.com", "password": "admin123"}
        res_login = client_acc.post("/auth/login", data=login_payload)
        print(f"Login Status: {res_login.status_code}")
        
        if res_login.status_code != 200:
            print(f"❌ Login Failed: {res_login.text}")
            sys.exit(1)
            
        # Manual extraction from headers (TestClient strictness workaround)
        import re
        acc_token = None
        ref_token = None
        
        # TestClient/Starlette/Requests merging behavior varies.
        # We try to get 'set-cookie' content. 
        # Note: requests 'headers' is CaseInsensitiveDict. it might merge multiple set-cookie into one string separated by comma?
        # But Set-Cookie values contain commas (in dates)!
        # So we look at raw headers if possible, or try to parse what we get.
        
        set_cookie_raw = res_login.headers.get("set-cookie")
        print(f"🍪 Raw Set-Cookie Header: {set_cookie_raw}")
        
        if set_cookie_raw:
            # Simple regex search
            m_acc = re.search(r'accounts_access_token=([^;]+)', set_cookie_raw)
            if m_acc: acc_token = m_acc.group(1)
            
            m_ref = re.search(r'accounts_refresh_token=([^;]+)', set_cookie_raw)
            if m_ref: ref_token = m_ref.group(1)

        cookies_dict = {
            "accounts_access_token": acc_token,
            "accounts_refresh_token": ref_token
        }
        print(f"🍪 Extracted Dict: {cookies_dict}")
        
        print(f"✅ Login Success.")
        
        # FINANCE
        with TestClient(finance_app) as client_fin:
            print("\n--- TEST: FINANCE ACCESS ---")
            res_fin = client_fin.get("/api/quotes/", cookies=cookies_dict)
            print(f"Finance /api/quotes/ Status: {res_fin.status_code}")
            if res_fin.status_code != 200:
                print(f"Finance Error: {res_fin.text}")
            
        # PLUGIN (Protected Cloud Endpoint)
        with TestClient(plugin_app) as client_plug:
            print("\n--- TEST: PLUGIN ACCESS ---")
            # /api/plugin/cloud/calculate/quantities
            payload = {
                "project_id": "test",
                "element_type": "Wall",
                "vertices": [],
                "metadata": {}
            }
            res_plug = client_plug.post("/api/plugin/cloud/calculate/quantities", json=payload, cookies=cookies_dict)
            print(f"Plugin /api/plugin/cloud/calculate/quantities Status: {res_plug.status_code}")
            
        # REFRESH (Back to Accounts)
        print("\n--- TEST: REFRESH FLOW ---")
        res_refresh = client_acc.post("/auth/refresh", cookies=cookies_dict)
        print(f"Refresh Status: {res_refresh.status_code}")
        
        if res_refresh.status_code == 200:
            print("✅ Refresh Success")
        else:
            print(f"❌ Refresh Failed: {res_refresh.text}")
            
        # LOGOUT
        print("\n--- TEST: LOGOUT ---")
        res_logout = client_acc.post("/auth/logout", cookies=cookies_dict)
        print(f"Logout Status: {res_logout.status_code}")
        print("\n🏁 E2E Verification Complete")

if __name__ == "__main__":
    run_tests()
