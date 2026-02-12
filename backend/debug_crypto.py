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

# Robust extraction using regex or markers
import re
try:
    # Find PRIVATE KEY block
    priv_blocks = re.findall(r'(-+BEGIN PRIVATE KEY-+[\s\S]*?-+END PRIVATE KEY-+)', content)
    if not priv_blocks:
        # Try finding the prompt value
        # The file has "VALUE:\n<env_var_style>\n\n" usually
        pass 
        
    # Actually, the file V3 format is:
    # SERVICE: ACCOUNTS
    # VARIABLE: AO_JWT_PRIVATE_KEY_PEM
    # VALUE:
    # <one line with \n>
    
    # Wait, my generator script writes the ENV VAR value (escaped newlines)?
    # Let's check the generator script again.
    
    # Ah, generate_rsa_keys.py writes:
    # f.write(priv_env + "\n\n")  <-- priv_env has \\n
    
    # Check if the file contains the escaped version or the multiline version?
    # The script output says:
    # f.write("VALUE:\n")
    # f.write(priv_env + "\n\n")
    
    # So the file contains ONE LONG LINE with literals "\n".
    # I need to parse that line and convert \\n back to \n.
    
    # Naive parse: look for the line starting with "-----BEGIN"
    lines = content.splitlines()
    priv_key_str = None
    pub_key_str = None
    
    for line in lines:
        line = line.strip()
        if "-----BEGIN PRIVATE KEY-----" in line:
            priv_key_str = line.replace("\\n", "\n")
        elif "-----BEGIN PUBLIC KEY-----" in line:
            pub_key_str = line.replace("\\n", "\n")
            
    if not priv_key_str:
        print("❌ Could not find Private Key (escaped) in file")
        sys.exit(1)
    if not pub_key_str:
        print("❌ Could not find Public Key (escaped) in file")
        sys.exit(1)

    priv_key = priv_key_str.encode('utf-8')
    pub_key = pub_key_str.encode('utf-8')

except Exception as e:
    print(f"❌ Error parsing file: {e}")
    sys.exit(1)

print("✅ Extracted Keys (PEM format).")

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
