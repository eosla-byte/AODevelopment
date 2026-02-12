import os
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend

def generate_keys():
    print("Generating RSA 2048 Key Pair (PKCS#8 Standard)...")
    
    # Generate Private Key
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
        backend=default_backend()
    )
    
    # Generate Public Key
    public_key = private_key.public_key()
    
    # Serialize Private Key (PKCS#8)
    priv_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    # Serialize Public Key (PKCS#8 - BEGIN PUBLIC KEY)
    pub_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    # Escape newlines for .env / Railway variables
    priv_env = priv_pem.replace('\n', '\\n')
    pub_env = pub_pem.replace('\n', '\\n')
    
    print("\n" + "="*60)
    print("🔑  NEW RSA KEYS GENERATED (PKCS#8)  🔑")
    print("="*60)
    
    print("\nInstructions:")
    print("1. Copy the values below exactly as shown.")
    print("2. Update the Environment Variables in Railway.")
    print("3. RESTART both services (Accounts & Finance).")
    
    print("\n" + "-"*20 + " For ACCOUNTS Service " + "-"*20)
    print(f"Variable: AO_JWT_PRIVATE_KEY_PEM")
    print(f"Value:    {priv_env}")
    
    print("\n" + "-"*20 + " For FINANCE Service " + "-"*20)
    print(f"Variable: AO_JWT_PUBLIC_KEY_PEM")
    print(f"Value:    {pub_env}")
    
    print("\n" + "="*60 + "\n")
    
    # Save to file
    with open("generated_keys.txt", "w", encoding="utf-8") as f:
        f.write("="*60 + "\n")
        f.write("RSA KEYS (PKCS#8) FOR RAILWAY\n")
        f.write("="*60 + "\n\n")
        f.write("SERVICE: ACCOUNTS\n")
        f.write("VARIABLE: AO_JWT_PRIVATE_KEY_PEM\n")
        f.write("VALUE:\n")
        f.write(priv_env + "\n\n")
        f.write("-" * 40 + "\n\n")
        f.write("SERVICE: FINANCE\n")
        f.write("VARIABLE: AO_JWT_PUBLIC_KEY_PEM\n")
        f.write("VALUE:\n")
        f.write(pub_env + "\n")
        
    print(f"✅ Keys also saved to: {os.path.abspath('generated_keys.txt')}")

if __name__ == "__main__":
    generate_keys()
