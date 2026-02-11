
import os

def _env(name, default=None, cast=None):
    v = os.getenv(name, default)
    return cast(v) if cast and v is not None else v

# Cookie Configuration
# Defaulting to 'accounts_access_token' to match hardcoded value in auth.py
ACCESS_COOKIE_NAME = _env("ACCESS_COOKIE_NAME", "accounts_access_token")
REFRESH_COOKIE_NAME = _env("REFRESH_COOKIE_NAME", "accounts_refresh_token")

# Token Expiration
ACCESS_TOKEN_EXPIRE_MINUTES = _env("ACCESS_TOKEN_EXPIRE_MINUTES", 3600, int)
REFRESH_TOKEN_EXPIRE_DAYS = _env("REFRESH_TOKEN_EXPIRE_DAYS", 30, int)

# JWT Configuration
ALGORITHM = _env("AO_JWT_ALGORITHM", "RS256")
ISSUER = _env("AO_JWT_ISSUER", "ao")
AUDIENCE = _env("AO_JWT_AUDIENCE", "ao")

# Cookie Security
COOKIE_DOMAIN = _env("COOKIE_DOMAIN", None) # Default None (Host only)
COOKIE_SAMESITE = _env("COOKIE_SAMESITE", "Lax")
COOKIE_SECURE = _env("COOKIE_SECURE", "True") == "True" # Simple string check for Env
COOKIE_PATH = _env("COOKIE_PATH", "/")

cookie_settings = {
    "domain": COOKIE_DOMAIN,
    "secure": COOKIE_SECURE,
    "samesite": COOKIE_SAMESITE,
    "httponly": True,
    "path": COOKIE_PATH
}
