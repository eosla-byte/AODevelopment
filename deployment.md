# Deployment Guide: Authentication (RSA)

The authentication system now uses RS256 asymmetry.

## Environment Variables

### Accounts Service (Signer)
- `AO_JWT_PRIVATE_KEY_PEM`: The RSA Private Key (PEM format).
- `AO_JWT_PUBLIC_KEY_PEM`: The RSA Public Key (PEM format).
- `AO_JWT_KEY_ID`: Optional Key ID (default: "ao-k1").
- `AO_JWT_SECRET`: **DEPRECATED**. Remove from production env.

### Other Services (Verifier: Finance, Plugin, Daily, etc.)
- `AO_JWT_PUBLIC_KEY_PEM`: The RSA Public Key (PEM format).
- `AO_JWT_KEY_ID`: Optional Key ID (must match signer).

## Key Generation
Use `openssl` to generate keys:
```bash
# Generate Private Key
openssl genrsa -out private.pem 2048

# Extract Public Key
openssl rsa -in private.pem -pubout -out public.pem
```

## Docker / Railway
Ensure multiline PEM keys are correctly set in environment variables. Use `\n` for newlines if the platform requires single-line values, or paste the full block if supported. The code handles `\n` replacement automatically.
