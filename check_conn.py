import requests
try:
    print("Intentando conectar a crearpslglobal.com...")
    r = requests.get('https://crearpslglobal.com/admin/datosparticipante.php', timeout=15, verify=False)
    print(f"Status Code: {r.status_code}")
    print(f"URL: {r.url}")
except Exception as e:
    print(f"Error: {e}")
