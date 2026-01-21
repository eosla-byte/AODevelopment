
import threading
import time
import uvicorn
import sys
import os
import urllib.request
import urllib.error
from database import get_users, get_root_path
from auth_utils import create_access_token

sys.path.append(os.getcwd())
from main import app

def run_server():
    try:
        uvicorn.run(app, host="127.0.0.1", port=8003, log_level="error")
    except: pass

def test_authenticated():
    # Start server in thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    
    print("Waiting for server...")
    time.sleep(4)
    
    # 1. Create Token
    root_path = get_root_path()
    if not root_path:
        root_path = os.getcwd() # Fallback

    users = get_users(root_path)
    if not users:
        print("No users found to impersonate.")
        # Try to login even without users? No, will redirect to login.
        # Let's request /login
        print("Requesting /login ...")
        try:
             with urllib.request.urlopen("http://127.0.0.1:8003/login") as response:
                print(f"Login Status: {response.getcode()}")
        except Exception as e:
            print(f"Login Error: {e}")
        return

    user = users[0]
    token = create_access_token(data={"sub": user.email, "role": user.role, "name": user.name})
    print(f"Impersonating {user.email}")
    
    # 2. Request /
    req = urllib.request.Request("http://127.0.0.1:8003/")
    req.add_header("Cookie", f"access_token={token}")
    
    print("Requesting authenticated / (Dashboard) ...")
    try:
        with urllib.request.urlopen(req) as response:
            print(f"Status: {response.getcode()}")
            content = response.read().decode('utf-8')
            print(f"Content Length: {len(content)}")
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} {e.reason}")
        print("Error Body:")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_authenticated()
