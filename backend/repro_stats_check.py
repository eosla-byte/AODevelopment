
import threading
import time
import uvicorn
import sys
import os
import urllib.request
import urllib.error
from database import get_root_path

sys.path.append(os.getcwd())
from main import app

def run_server():
    try:
        uvicorn.run(app, host="127.0.0.1", port=8005, log_level="error")
    except: pass

def test_stats():
    # Start server in thread
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    
    print("Waiting for server...")
    time.sleep(4)
    
    # Request /api/projects/stats
    print("Requesting /api/projects/stats ...")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8005/api/projects/stats") as response:
            print(f"Status: {response.getcode()}")
            content = response.read().decode('utf-8')
            print(f"Content: {content}")
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} {e.reason}")
        print("Error Body:")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_stats()
