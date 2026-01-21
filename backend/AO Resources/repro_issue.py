
import os
import sys
sys.path.append(os.getcwd())

from fastapi.testclient import TestClient
from main import app

# Create client
client = TestClient(app)

print("Requesting root / ...")
try:
    response = client.get("/")
    print(f"Status: {response.status_code}")
    if response.status_code != 200:
        print("Response body:")
        print(response.text)
except Exception as e:
    print(f"EXCEPTION causing crash: {e}")
    import traceback
    traceback.print_exc()

print("\nRequesting /projects ...")
try:
    response = client.get("/projects")
    print(f"Status: {response.status_code}")
except Exception as e:
    print(f"EXCEPTION: {e}")
    import traceback
    traceback.print_exc()
