import requests
import time

MACRODROID_ID = "7c051b6b-4231-4c86-8b98-2d9ccc88ccf7"
EVENT_NAME = "enviar_sms"

def test_gateway():
    print(f"--- DIAGNOSTICO DE GATEWAY SMS (MacroDroid) ---")
    print(f"ID del Dispositivo: {MACRODROID_ID}")
    
    # Intentar un ping al Webhook
    url = f"https://trigger.macrodroid.com/{MACRODROID_ID}/{EVENT_NAME}"
    params = {
        "numero": "TEST",
        "mensaje": "TEST_DIAGNOSTICO_ANTIGRAVITY"
    }
    
    print(f"Enviando señal de prueba a: {url}...")
    try:
        start_time = time.time()
        response = requests.get(url, params=params, timeout=10)
        duration = time.time() - start_time
        
        if response.status_code == 200:
            print(f"RESULTADO: EXITOSO (200 OK)")
            print(f"Tiempo de respuesta: {duration:.2f}s")
            print("LA SEÑAL SALIO DE LA PC CORRECTAMENTE.")
            print("Si el SMS no llega al telefono, el problema esta EN EL TELEFONO:")
            print("1. MacroDroid debe estar abierto.")
            print("2. La macro 'enviar_sms' debe estar activa.")
            print("3. El telefono debe tener internet y señal de red movil.")
        else:
            print(f"RESULTADO: FALLIDO (Status {response.status_code})")
            print(f"Respuesta: {response.text}")
    except Exception as e:
        print(f"RESULTADO: ERROR DE CONEXION")
        print(f"Detalle: {e}")
        print("POSIBLE CAUSA: Sin internet en la PC o URL de MacroDroid bloqueada.")

if __name__ == "__main__":
    test_gateway()
