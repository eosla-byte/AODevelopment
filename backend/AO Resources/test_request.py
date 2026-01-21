import requests

url = "http://127.0.0.1:8000/hr/create"
data = {
    "name": "Debug User",
    "role": "Bim Manager",
    "salary": "5000",
    "birthday": "1990-01-01",
    "start_date": "2023-01-01"
}

try:
    resp = requests.post(url, data=data)
    print(f"Status: {resp.status_code}")
    print(resp.url)
except Exception as e:
    print(e)
