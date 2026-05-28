import requests

r = requests.get('http://localhost:5000/api/ban/active')
bans = r.json()
count = 0
for b in bans:
    if b['ipAddress'] == '127.0.0.1':
        requests.delete(f"http://localhost:5000/api/ban/{b['id']}")
        count += 1
print(f"Lifted {count} bans on 127.0.0.1")
