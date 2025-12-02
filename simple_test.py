import requests
import json

print("Testing OSRM Integration...")

# Test OSRM dynamic routing
payload = {
    "origenLat": 2.4448,
    "origenLon": -76.6147,
    "destinoLat": 2.4520,
    "destinoLon": -76.6075
}

response = requests.post('http://localhost:3002/api/estimate-route', json=payload, timeout=30)
result = response.json()

print(f"Success: {result['success']}")
print(f"Metodo: {result.get('metodo', 'N/A')}")
print(f"Empresa: {result['empresa']}")
print(f"Distancia: {result['distanciaKm']} km")
print(f"Tiempo: {result['tiempoEstimadoMinutos']} min")
print(f"Costo: ${result['costo']}")
print(f"Mensaje: {result['mensaje']}")
