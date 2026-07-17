import urllib.request
import json

try:
    url = "http://127.0.0.1:5000/api/dashboard-stats"
    response = urllib.request.urlopen(url, timeout=5)
    data = json.loads(response.read().decode('utf-8'))
    print("Dashboard total:", data.get('kpis', {}).get('total_participantes'))
except Exception as e:
    print("Error querying stats:", e)
