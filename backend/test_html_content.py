import requests

url = "http://127.0.0.1:8000/hr"
try:
    resp = requests.get(url)
    print(f"Status: {resp.status_code}")
    if "juan perez" in resp.text.lower():
        print("FOUND: juan perez")
    else:
        print("NOT FOUND: 'juan perez' in HTML")
        
    if "debug user" in resp.text.lower():
        print("FOUND: debug user")
    else:
        print("NOT FOUND: 'debug user' in HTML")
except Exception as e:
    print(e)
