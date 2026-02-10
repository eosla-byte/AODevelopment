import os
import sys

# Mock Env Var
dummy_key = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAv/1+
...
-----END PUBLIC KEY-----"""

# Real key for test (generated)
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
pub = key.public_key()
pem = pub.public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo
)
os.environ["AO_JWT_PUBLIC_KEY_PEM"] = pem.decode("utf-8")

# Setup Path
sys.path.insert(0, os.path.abspath("backend"))

try:
    from backend.services.accounts.main import jwks_endpoint
    print("Testing JWKS Endpoint...")
    result = jwks_endpoint()
    print("Result:", result)
    
    if len(result["keys"]) == 1 and result["keys"][0]["kty"] == "RSA":
        print("✅ JWKS Logic Verified")
    else:
        print("❌ JWKS Logic Failed")
except Exception as e:
    print(f"❌ Error: {e}")
