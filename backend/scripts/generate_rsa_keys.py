import rsa
import base64

def generate_keys():
    print("Generating RSA 2048 Key Pair...")
    (pubkey, privkey) = rsa.newkeys(2048)
    
    # Export to PEM format
    priv_pem = privkey.save_pkcs1().decode('utf-8')
    pub_pem = pubkey.save_pkcs1().decode('utf-8')
    
    # Escape newlines for .env / Railway variables
    priv_env = priv_pem.replace('\n', '\\n')
    pub_env = pub_pem.replace('\n', '\\n')
    
    print("\n" + "="*60)
    print("🔑  NEW RSA KEYS GENERATED  🔑")
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
        f.write("RSA KEYS FOR RAILWAY (COPY VALUES BETWEEN QUOTES)\n")
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
        
    import os
    print(f"✅ Keys also saved to: {os.path.abspath('generated_keys.txt')}")

if __name__ == "__main__":
    try:
        generate_keys()
    except ImportError:
        print("Installing 'rsa' library...")
        import subprocess
        subprocess.check_call(["pip", "install", "rsa"])
        import rsa
        generate_keys()
