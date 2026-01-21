import requests

collab_id = "1768336697" # Adjust if necessary
url = f"http://127.0.0.1:8000/hr/{collab_id}/update"

data = {
    "role": "Bim Coordinator",
    "base_salary": "7500",
    "bonus_incentive": "500",
    "birthday": "1990-01-01",
    "start_date": "2023-01-01"
}

print(f"Sending update to {url} with data: {data}")
try:
    resp = requests.post(url, data=data, allow_redirects=False)
    print(f"Status: {resp.status_code}")
    print(f"Location: {resp.headers.get('Location')}")
except Exception as e:
    print(e)
