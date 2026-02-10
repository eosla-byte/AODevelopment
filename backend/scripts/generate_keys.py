import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

def generate_keys():
    # Generate private key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Serialize private key
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    )

    # Serialize public key
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )

    # Create keys directory
    os.makedirs("backend/certs", exist_ok=True)
    
    with open("backend/certs/private.pem", "wb") as f:
        f.write(private_pem)
        
    with open("backend/certs/public.pem", "wb") as f:
        f.write(public_pem)
        
    print("✅ RSA Keys generated in backend/certs/")
    
    # Print for .env
    print("\n--- .env Format (Copy these) ---")
    print(f"AO_JWT_PRIVATE_KEY_PEM=\"{private_pem.decode('utf-8').replace(chr(10), '\\n')}\"")
    print(f"AO_JWT_PUBLIC_KEY_PEM=\"{public_pem.decode('utf-8').replace(chr(10), '\\n')}\"")

if __name__ == "__main__":
    generate_keys()
