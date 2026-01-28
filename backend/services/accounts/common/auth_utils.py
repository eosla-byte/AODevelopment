
import bcrypt
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt

# Configuration
SECRET_KEY = "AO_RESOURCES_SUPER_SECRET_KEY_CHANGE_THIS_IN_PROD"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 # 24 Hours

def verify_password(plain_password, hashed_password):
    if not hashed_password: return False
    if isinstance(hashed_password, str):
        hashed_password = hashed_password.encode('utf-8')
    if isinstance(plain_password, str):
        plain_password = plain_password.encode('utf-8')
    return bcrypt.checkpw(plain_password, hashed_password)

def get_password_hash(password):
    if isinstance(password, str):
        password = password.encode('utf-8')
    return bcrypt.hashpw(password, bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def decode_access_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer

# auto_error=False allows us to check for cookies if header is missing
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token", auto_error=False) 

def verify_token_dep(token: str = Depends(oauth2_scheme)):
    # This function seems unused or legacy, but we'll leave it simple
    if not token: 
         raise HTTPException(status_code=401, detail="No token provided")
    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token

async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme)
):
    # 1. Try Token from Header (OAuth2PasswordBearer)
    # 2. If missing, Try Cookie
    if not token:
        cookie_token = request.cookies.get("accounts_access_token")
        if cookie_token:
            # Handle "Bearer <token>" or just "<token>"
            if cookie_token.startswith("Bearer "):
                token = cookie_token.split(" ")[1]
            else:
                token = cookie_token
    
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated (No Header or Cookie)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload # Returns the dict (sub, role, etc)
