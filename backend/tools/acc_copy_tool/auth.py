import requests
import time
import base64
from .config import APS_CLIENT_ID, APS_CLIENT_SECRET, APS_SCOPES

_TOKEN_CACHE = {
    "access_token": None,
    "expires_at": 0
}

def get_access_token():
    """
    Returns a valid access token (2-legged).
    Refreshes if expired.
    """
    global _TOKEN_CACHE
    
    if _TOKEN_CACHE["access_token"] and time.time() < _TOKEN_CACHE["expires_at"]:
        return _TOKEN_CACHE["access_token"]
        
    url = "https://developer.api.autodesk.com/authentication/v2/token"
    
    # Needs Basic Auth header
    auth_str = f"{APS_CLIENT_ID}:{APS_CLIENT_SECRET}"
    b64_auth = base64.b64encode(auth_str.encode()).decode()
    
    headers = {
        "Authorization": f"Basic {b64_auth}",
        "Content-Type": "application/x-www-form-urlencoded"
    }
    
    data = {
        "grant_type": "client_credentials",
        "scope": " ".join(APS_SCOPES)
    }
    
    res = requests.post(url, headers=headers, data=data)
    
    if res.status_code != 200:
        raise Exception(f"Failed to authenticate: {res.text}")
        
    json_data = res.json()
    _TOKEN_CACHE["access_token"] = json_data["access_token"]
    # Buffer of 60 seconds
    _TOKEN_CACHE["expires_at"] = time.time() + json_data["expires_in"] - 60
    
    return _TOKEN_CACHE["access_token"]
