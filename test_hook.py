import requests
token = "YOUR_GITHUB_TOKEN_HERE"
repo = "mitul-bhatia/Aegis"
res = requests.post(f"https://api.github.com/repos/{repo}/hooks", json={
    "name": "web", "active": True, "events": ["push"], "config": {"url": "http://localhost:8000/webhook/github", "content_type": "json"}
}, headers={"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json"})
print(res.status_code, res.json())
