import requests

url = "http://127.0.0.1:8000/hr"
try:
    resp = requests.get(url)
    print(f"Status: {resp.status_code}")
except Exception as e:
    print(e)
