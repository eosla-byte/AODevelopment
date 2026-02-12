import jwt
import os
import sys

# Add current directory to path
sys.path.append(os.getcwd())

# 1. Load Keys from generated file
KEYS_FILE = "backend/generated_keys_v3.txt"
if not os.path.exists(KEYS_FILE):
    print(f"❌ Key file not found: {KEYS_FILE}")
    sys.exit(1)

print(f"✅ Loading keys from {KEYS_FILE}...")
with open(KEYS_FILE, "r") as f:
    content = f.read()

# Extract Private Key
priv_match = content.split("-----BEGIN PRIVATE KEY-----")[1].split("-----END PRIVATE KEY-----")[0]
priv_key = "-----BEGIN PRIVATE KEY-----" + priv_match + "-----END PRIVATE KEY-----"

# Extract Public Key
pub_match = content.split("-----BEGIN PUBLIC KEY-----")[1].split("-----END PUBLIC KEY-----")[0]
pub_key = "-----BEGIN PUBLIC KEY-----" + pub_match + "-----END PUBLIC KEY-----"

print("✅ Extracted Keys.")

# 2. Simulate Accounts Signing
print("\n--- SIMULATING ACCOUNTS SIGNING ---")
payload = {
    "sub": "test_user",
    "iss": "accounts.somosao.com",
    "aud": ["somosao", "ao-platform"],
    "exp": 1999999999
}

try:
    token = jwt.encode(
        payload,
        priv_key,
        algorithm="RS256",
        headers={"kid": "ao-k1"}
    )
    print(f"✅ Token Signed: {token[:20]}...{token[-20:]}")
except Exception as e:
    print(f"❌ Signing Failed: {e}")
    sys.exit(1)

# 3. Simulate Finance Verification (Standard PyJWT)
print("\n--- SIMULATING FINANCE VERIFICATION (Standard) ---")
try:
    decoded = jwt.decode(
        token,
        pub_key,
        algorithms=["RS256"],
        options={"verify_aud": False}
    )
    print(f"✅ Standard PyJWT Verification Success: {decoded['sub']}")
except Exception as e:
    print(f"❌ Standard PyJWT Verification Failed: {e}")

# 4. Simulate Finance Verification (Cryptography Explicit)
print("\n--- SIMULATING FINANCE VERIFICATION (Cryptography) ---")
try:
    from cryptography.hazmat.primitives import serialization
    from cryptography.hazmat.backends import default_backend
    
    pub_obj = serialization.load_pem_public_key(
        pub_key.encode('utf-8'),
        backend=default_backend()
    )
    print("✅ Cryptography Key Load Success")
    
    decoded_c = jwt.decode(
        token,
        pub_obj,
        algorithms=["RS256"],
        options={"verify_aud": False}
    )
    print(f"✅ Cryptography explicit Verification Success: {decoded_c['sub']}")
except Exception as e:
    print(f"❌ Cryptography explicit verification Failed: {e}")
