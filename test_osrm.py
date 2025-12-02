import requests
import json

# Test 1: OSRM dynamic routing (without empresa/numeroRuta)
print("=" * 60)
print("TEST 1: OSRM Dynamic Routing")
print("=" * 60)
payload1 = {
    "origenLat": 2.4448,
    "origenLon": -76.6147,
    "destinoLat": 2.4520,
    "destinoLon": -76.6075
}

try:
    response1 = requests.post('http://localhost:3002/api/estimate-route', json=payload1, timeout=30)
    print(f"Status Code: {response1.status_code}")
    result1 = response1.json()
    print(json.dumps(result1, indent=2, ensure_ascii=False))
    print(f"\n✅ Método usado: {result1.get('metodo', 'N/A')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 2: Static routing (with empresa/numeroRuta)
print("\n" + "=" * 60)
print("TEST 2: Static Routing (with empresa/numeroRuta)")
print("=" * 60)
payload2 = {
    "origenLat": 2.4448,
    "origenLon": -76.6147,
    "destinoLat": 2.4520,
    "destinoLon": -76.6075,
    "empresa": "TransPubenza",
    "numeroRuta": 1
}

try:
    response2 = requests.post('http://localhost:3002/api/estimate-route', json=payload2, timeout=30)
    print(f"Status Code: {response2.status_code}")
    result2 = response2.json()
    print(json.dumps(result2, indent=2, ensure_ascii=False))
    print(f"\n✅ Método usado: {result2.get('metodo', 'N/A')}")
except Exception as e:
    print(f"❌ Error: {e}")

# Test 3: Routing info endpoint
print("\n" + "=" * 60)
print("TEST 3: Routing Info Endpoint")
print("=" * 60)
try:
    response3 = requests.get('http://localhost:3002/api/routing-info', timeout=10)
    print(f"Status Code: {response3.status_code}")
    result3 = response3.json()
    print(json.dumps(result3, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"❌ Error: {e}")

print("\n" + "=" * 60)
print("TESTS COMPLETED")
print("=" * 60)
