
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
        uvicorn.run(app, host="127.0.0.1", port=8002, log_level="error")
    except: pass

def test_authenticated():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    
    print("Waiting for server...")
    time.sleep(4)
    
    # 1. Create Token
    root_path = get_root_path()
    users = get_users(root_path)
    if not users:
        print("No users found to impersonate.")
        return

    user = users[0]
    token = create_access_token(data={"sub": user.email, "role": user.role, "name": user.name})
    print(f"Impersonating {user.email}")
    
    # 2. Request /
    req = urllib.request.Request("http://127.0.0.1:8002/")
    req.add_header("Cookie", f"access_token={token}")
    
    print("Requesting authenticated / ...")
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
