
# Auth Constants
# Single source of truth for cookie names and configuration

ACCESS_COOKIE_NAME = "accounts_access_token"
REFRESH_COOKIE_NAME = "accounts_refresh_token"

# Shared Session Config (for Daily/BIM/Accounts)
COOKIE_DOMAIN = ".somosao.com"
COOKIE_SAMESITE = "none" # Required for cross-site/iframe
COOKIE_SECURE = True

ACCESS_TOKEN_EXPIRE_MINUTES = 40320 # 4 weeks (standardized)
REFRESH_TOKEN_EXPIRE_DAYS = 30
ALGORITHM = "HS256"

cookie_settings = {
    "domain": COOKIE_DOMAIN,
    "secure": COOKIE_SECURE,
    "samesite": COOKIE_SAMESITE,
    "httponly": True
}
