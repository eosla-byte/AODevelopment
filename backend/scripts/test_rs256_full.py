
import sys
import os
import time

# Add backend to sys.path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

def test_rs256_flow():
    print("🚀 Starting RS256 Verification...")
    
    # 1. Load Keys
    try:
        with open("backend/certs/private.pem", "r") as f:
            private_key = f.read()
            
        with open("backend/certs/public.pem", "r") as f:
            public_key = f.read()
            
        # Set Env Vars (Simulate Env)
        os.environ["AO_JWT_PRIVATE_KEY_PEM"] = private_key
        os.environ["AO_JWT_PUBLIC_KEY_PEM"] = public_key
        os.environ["AO_JWT_KEY_ID"] = "test-kid-1"
        
        print("✅ Keys Loaded into Environment")
    except FileNotFoundError:
        print("❌ Keys not found. Run generate_keys.py first.")
        return

    # 2. Reload Auth Module (to pick up env vars)
    import importlib
    import common.auth as auth
    importlib.reload(auth)
    
    print(f"ℹ️ Auth Config: Alg={auth.ALGORITHM}, Kid={auth.AO_JWT_KEY_ID}")
    
    # 3. Sign Token (Accounts Service Role)
    print("\n--- 🔐 Signing (Accounts Service) ---")
    payload = {
        "sub": "user-123",
        "email": "test@somosao.com",
        "role": "Admin",
        "org_id": "org-ABC",
        "services": ["daily", "bim"]
    }
    
    token = auth.create_access_token(payload)
    print(f"✅ Token Generated: {token[:20]}...{token[-20:]}")
    
    # Check Header
    import jwt
    header = jwt.get_unverified_header(token)
    print(f"ℹ️ Token Header: {header}")
    
    if header.get("alg") != "RS256":
        print("❌ ALGORITHM ERROR: Expected RS256")
        return
    if header.get("kid") != "test-kid-1":
        print("❌ KEY ID ERROR: Expected test-kid-1")
        return
        
    # 4. Verify Token (Daily Service Role)
    print("\n--- 🛡️ Verifying (Daily Service) ---")
    # Simulate Daily Service only having Public Key
    # We can't easily unset private key from module since it loaded it, 
    # but verify doesn't use it.
    
    decoded = auth.decode_token(token)
    
    if not decoded:
        print("❌ Verification Failed!")
        return
        
    print(f"✅ Token Verified! Payload: {decoded}")
    
    if decoded["sub"] == "user-123" and decoded["org_id"] == "org-ABC":
        print("✅ Claims match.")
    else:
        print("❌ Claims mismatch.")
        
    print("\n🚀 RS256 Migration Verification COMPLETE.")

if __name__ == "__main__":
    test_rs256_flow()
