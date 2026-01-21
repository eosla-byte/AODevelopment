
import threading
import time
import uvicorn
import sys
import os
import urllib.request
import urllib.error

# Ensure current dir is in path
sys.path.append(os.getcwd())

from main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8001, log_level="error")

def test_server():
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    
    print("Waiting for server start...")
    time.sleep(5)
    
    print("Requesting http://127.0.0.1:8001/")
    try:
        with urllib.request.urlopen("http://127.0.0.1:8001/") as response:
            print(f"Status: {response.getcode()}")
            print(response.read().decode('utf-8')[:500])
    except urllib.error.HTTPError as e:
        print(f"HTTPError: {e.code} {e.reason}")
        print("Error Body:")
        print(e.read().decode('utf-8'))
    except Exception as e:
        print(f"Connection Error: {e}")

if __name__ == "__main__":
    test_server()
