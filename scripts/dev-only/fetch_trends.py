import requests, json, os

url = 'http://127.0.0.1:8000/api/trends'
resp = requests.get(url, timeout=10)
data = resp.json()
out_path = os.path.abspath('trends_output.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2)
print(f'Wrote {len(data)} items to {out_path}')
