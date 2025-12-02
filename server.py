import math
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import threading


BUS_POSITIONS = {}   # { idBus: {empresa, ruta, lat, lon, vel, timestamp} }

# In-memory routes database
RUTAS_DATABASE = {
    "TransPubenza": {
        1: [
            {"nombre": "Parque Caldas (Centro)", "lat": 2.4448, "lon": -76.6147, "orden": 1},
            {"nombre": "Calle 5", "lat": 2.4455, "lon": -76.6135, "orden": 2},
            {"nombre": "Barrio Bolivar", "lat": 2.4470, "lon": -76.6120, "orden": 3},
            {"nombre": "Av. Las Américas", "lat": 2.4485, "lon": -76.6105, "orden": 4},
            {"nombre": "Entrada Universidad", "lat": 2.4505, "lon": -76.6090, "orden": 5},
            {"nombre": "Universidad del Cauca", "lat": 2.4520, "lon": -76.6075, "orden": 6}
        ],
        5: [
            {"nombre": "Parque Caldas (Centro)", "lat": 2.4448, "lon": -76.6147, "orden": 1},
            {"nombre": "Calle 3", "lat": 2.4430, "lon": -76.6155, "orden": 2},
            {"nombre": "La Esmeralda", "lat": 2.4410, "lon": -76.6170, "orden": 3},
            {"nombre": "Av. Sur", "lat": 2.4385, "lon": -76.6190, "orden": 4},
            {"nombre": "Barrio San Camilo", "lat": 2.4360, "lon": -76.6210, "orden": 5},
            {"nombre": "Bello Horizonte", "lat": 2.4335, "lon": -76.6230, "orden": 6}
        ]
    },
    "TransLibertad": {
        3: [
            {"nombre": "Parque Caldas (Centro)", "lat": 2.4448, "lon": -76.6147, "orden": 1},
            {"nombre": "Calle 6", "lat": 2.4465, "lon": -76.6155, "orden": 2},
            {"nombre": "Alfonso López", "lat": 2.4490, "lon": -76.6175, "orden": 3},
            {"nombre": "Av. Panamericana", "lat": 2.4520, "lon": -76.6200, "orden": 4},
            {"nombre": "Barrio Modelo", "lat": 2.4550, "lon": -76.6225, "orden": 5},
            {"nombre": "Terminal El Modelo", "lat": 2.4580, "lon": -76.6245, "orden": 6}
        ]
    },
    "TransTambo": {
        7: [
            {"nombre": "Parque Caldas (Centro)", "lat": 2.4448, "lon": -76.6147, "orden": 1},
            {"nombre": "Salida Occidental", "lat": 2.4460, "lon": -76.6165, "orden": 2},
            {"nombre": "San Rafael", "lat": 2.4475, "lon": -76.6195, "orden": 3},
            {"nombre": "Puente del Humilladero", "lat": 2.4495, "lon": -76.6235, "orden": 4},
            {"nombre": "Vía al Tambo", "lat": 2.4520, "lon": -76.6280, "orden": 5},
            {"nombre": "Julumito", "lat": 2.4545, "lon": -76.6330, "orden": 6}
        ]
    },
    "Sotracauca": {
        10: [
            {"nombre": "Norte - Terra Plaza", "lat": 2.4785, "lon": -76.5740, "orden": 1},
            {"nombre": "Campanario CC", "lat": 2.4582, "lon": -76.5975, "orden": 2},
            {"nombre": "Terminal de Transportes", "lat": 2.4545, "lon": -76.6015, "orden": 3},
            {"nombre": "Estadio Ciro Lopez", "lat": 2.4490, "lon": -76.6080, "orden": 4},
            {"nombre": "Centro - Parque Caldas", "lat": 2.4448, "lon": -76.6147, "orden": 5},
            {"nombre": "Sur - La Esmeralda", "lat": 2.4350, "lon": -76.6180, "orden": 6}
        ]
    }
}

TARIFAS = {
    "TransPubenza": 2500,
    "TransLibertad": 2800,
    "TransTambo": 3000
}

# Helper functions
def distancia_haversine(lat1, lon1, lat2, lon2):
    """
    Calcula distancia entre dos puntos GPS en km
    """
    R = 6371  # Radio de la Tierra en km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat/2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon/2)**2
    c = 2 * math.asin(math.sqrt(a))
    return R * c


def encontrar_parada_mas_cercana(punto_lat, punto_lon, ruta_paradas):
    mejores = []
    for parada in ruta_paradas:
        d = distancia_haversine(punto_lat, punto_lon, parada['lat'], parada['lon'])
        mejores.append((d, parada))
    mejores.sort(key=lambda x: x[0])
    return mejores[0]  # distancia, parada


def validar_coordenadas(lat, lon):
    if not isinstance(lat, (int, float)) or not isinstance(lon, (int, float)):
        return False
    if lat < 2.3 or lat > 2.5:
        return False
    if lon < -76.7 or lon > -76.5:
        return False
    return True


def calcular_ruta_osrm(origen_lat, origen_lon, destino_lat, destino_lon):
    """
    Calcula ruta real usando OSRM API pública
    Retorna: dict con distancia_km, tiempo_minutos, y geometría de la ruta
             None si hay error
    """
    try:
        # OSRM espera lon,lat (no lat,lon)
        url = f"http://router.project-osrm.org/route/v1/driving/{origen_lon},{origen_lat};{destino_lon},{destino_lat}"
        params = {
            "overview": "full",
            "geometries": "geojson",
            "steps": "false"
        }
        
        response = requests.get(url, params=params, timeout=10)
        
        if response.status_code != 200:
            return None
            
        data = response.json()
        
        if data.get('code') != 'Ok' or not data.get('routes'):
            return None
        
        route = data['routes'][0]
        distancia_metros = route['distance']
        tiempo_segundos = route['duration']
        
        return {
            'distancia_km': round(distancia_metros / 1000, 2),
            'tiempo_minutos': int(tiempo_segundos / 60),
            'geometria': route.get('geometry', None)
        }
    except Exception as e:
        _safe_print(f"⚠️ Error al consultar OSRM: {str(e)}")
        return None


# Flask app
app = Flask(__name__)
# Development CORS (allow all origins for local testing from Android). In production restrict to client domains.
CORS(app, resources={r"/api/*": {"origins": "*"}})


def _safe_print(*args, **kwargs):
    """Print helper that avoids crashing on consoles with limited encodings (Windows cp1252)."""
    try:
        print(*args, **kwargs)
    except UnicodeEncodeError:
        # Fallback: remove non-ascii characters so printing never raises
        safe = ' '.join(str(a).encode('ascii', errors='ignore').decode('ascii') for a in args)
        print(safe, **kwargs)


@app.route('/api/health', methods=['GET'])
def health():
    try:
        empresas = list(RUTAS_DATABASE.keys())
        return jsonify({
            "status": "online",
            "message": "Servidor funcionando correctamente",
            "empresas_disponibles": empresas
        }), 200
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# Root endpoint -> quick instructions
@app.route('/', methods=['GET'])
def index():
    return jsonify({
        "service": "Estimación de Rutas - Popayán",
        "message": "Use POST /api/estimate-route with JSON payload. See /api/health and /api/rutas for info"
    }), 200


# Global error handlers to always return JSON with required structure
@app.errorhandler(400)
def handle_bad_request(e):
    # e may be an HTTPException or validation message
    msg = getattr(e, 'description', str(e)) if e is not None else 'Bad Request'
    return respuesta_error(400, f"Bad Request: {msg}")


@app.errorhandler(404)
def handle_not_found(e):
    msg = getattr(e, 'description', 'Not Found')
    return respuesta_error(404, f"Not Found: {msg}")


@app.errorhandler(405)
def handle_method_not_allowed(e):
    msg = getattr(e, 'description', 'Method Not Allowed')
    # Provide helpful guidance if the path points to estimate-route
    path = getattr(request, 'path', '')
    if '/api/estimate-route' in path:
        return respuesta_error(405, "Method Not Allowed: this endpoint only supports POST")
    return respuesta_error(405, f"Method Not Allowed: {msg}"), 405


@app.errorhandler(500)
def handle_internal_error(e):
    # Keep internal messages generic for security
    return respuesta_error(500, "Internal Server Error")


@app.route('/api/rutas', methods=['GET'])
def listar_rutas():
    try:
        rutas = []
        for empresa, rutas_dict in RUTAS_DATABASE.items():
            for num, paradas in rutas_dict.items():
                rutas.append({
                    "empresa": empresa,
                    "numeroRuta": num,
                    "numParadas": len(paradas),
                    "origen": paradas[0]['nombre'],
                    "destino": paradas[-1]['nombre']
                })
        return jsonify({"total_rutas": len(rutas), "rutas": rutas}), 200
    except Exception as e:
        return jsonify({"success": False, "mensaje": str(e)}), 500


@app.route('/api/routing-info', methods=['GET'])
def routing_info():
    """Informa sobre los métodos de ruteo disponibles"""
    # Probar si OSRM está disponible
    osrm_disponible = False
    try:
        test_url = "http://router.project-osrm.org/route/v1/driving/-76.6147,2.4448;-76.6075,2.4520"
        resp = requests.get(test_url, timeout=5)
        osrm_disponible = (resp.status_code == 200)
    except:
        pass
    
    return jsonify({
        "metodos_disponibles": {
            "osrm": osrm_disponible,
            "estatico": True
        },
        "metodo_preferido": "osrm" if osrm_disponible else "estatico",
        "mensaje": "OSRM calcula rutas reales. Estático usa rutas predefinidas."
    }), 200


@app.route('/api/estimate-route', methods=['POST'])
def estimate_route():
    try:
        payload = request.get_json(force=True)
        # Validate required numeric fields
        required = ['origenLat', 'origenLon', 'destinoLat', 'destinoLon']
        for k in required:
            if k not in payload:
                return respuesta_error(400, "Faltan campos obligatorios: %s" % k)
            if not isinstance(payload[k], (int, float)):
                return respuesta_error(400, "El campo %s debe ser numérico" % k)

        origenLat = payload['origenLat']
        origenLon = payload['origenLon']
        destinoLat = payload['destinoLat']
        destinoLon = payload['destinoLon']
        empresa = payload.get('empresa', '')
        numeroRuta = payload.get('numeroRuta', 0)

        # Optional fields type validation
        if 'empresa' in payload and payload.get('empresa') is not None and not isinstance(payload.get('empresa'), str):
            return respuesta_error(400, "El campo 'empresa' debe ser una cadena")

        if 'numeroRuta' in payload and payload.get('numeroRuta') is not None:
            if not isinstance(payload.get('numeroRuta'), int):
                # accept float that are integers (e.g., 1.0)
                if isinstance(payload.get('numeroRuta'), float) and payload.get('numeroRuta').is_integer():
                    numeroRuta = int(payload.get('numeroRuta'))
                else:
                    return respuesta_error(400, "El campo 'numeroRuta' debe ser un entero")

        # Validate ranges
        if not validar_coordenadas(origenLat, origenLon) or not validar_coordenadas(destinoLat, destinoLon):
            return respuesta_error(400, "Coordenadas fuera del rango válido para Popayán")

        metodo_usado = "estatico"  # Default
        
        # Default behavior if empresa/numeroRuta not provided: try OSRM first
        if empresa == '' or numeroRuta == 0:
            # Intentar calcular ruta dinámica con OSRM
            ruta_osrm = calcular_ruta_osrm(origenLat, origenLon, destinoLat, destinoLon)
            
            if ruta_osrm is not None:
                # OSRM exitoso - usar ruta dinámica
                metodo_usado = "osrm"
                distancia_km = ruta_osrm['distancia_km']
                tiempo_total = ruta_osrm['tiempo_minutos']
                
                # Encontrar la empresa/ruta más cercana para determinar tarifa
                mejor_empresa = None
                mejor_dist = float('inf')
                for emp, rutas_dict in RUTAS_DATABASE.items():
                    for num, paradas in rutas_dict.items():
                        dist_o, _ = encontrar_parada_mas_cercana(origenLat, origenLon, paradas)
                        dist_d, _ = encontrar_parada_mas_cercana(destinoLat, destinoLon, paradas)
                        dist_total = dist_o + dist_d
                        if dist_total < mejor_dist:
                            mejor_dist = dist_total
                            mejor_empresa = (emp, num)
                
                if mejor_empresa:
                    empresa = mejor_empresa[0]
                    numeroRuta = mejor_empresa[1]
                else:
                    # Usar primera empresa por defecto
                    empresa = list(RUTAS_DATABASE.keys())[0]
                    numeroRuta = list(RUTAS_DATABASE[empresa].keys())[0]
                
                # Crear paradas virtuales para compatibilidad con respuesta
                paradaOrigen = {
                    "nombre": f"Origen ({origenLat:.4f}, {origenLon:.4f})",
                    "lat": origenLat,
                    "lon": origenLon,
                    "orden": 1
                }
                paradaDestino = {
                    "nombre": f"Destino ({destinoLat:.4f}, {destinoLon:.4f})",
                    "lat": destinoLat,
                    "lon": destinoLon,
                    "orden": 2
                }
            else:
                # OSRM falló - usar método estático
                _safe_print("⚠️ OSRM no disponible, usando rutas estáticas")
                mejor_comb = None
                for emp, rutas_dict in RUTAS_DATABASE.items():
                    for num, paradas in rutas_dict.items():
                        dist_o, parada_o = encontrar_parada_mas_cercana(origenLat, origenLon, paradas)
                        dist_d, parada_d = encontrar_parada_mas_cercana(destinoLat, destinoLon, paradas)
                        if dist_o <= 1.0 and dist_d <= 1.0 and parada_o['orden'] <= parada_d['orden']:
                            # compute total distance along route
                            total_km = calcular_distancia_entre_paradas(paradas, parada_o['orden'], parada_d['orden'])
                            if mejor_comb is None or total_km < mejor_comb[0]:
                                mejor_comb = (total_km, emp, num, parada_o, parada_d)
                if mejor_comb is None:
                    return respuesta_error(404, "No se encontró una ruta válida cerca de los puntos seleccionados")
                distancia_km = mejor_comb[0]
                empresa = mejor_comb[1]
                numeroRuta = mejor_comb[2]
                paradaOrigen = mejor_comb[3]
                paradaDestino = mejor_comb[4]
                
                # Calcular tiempo para método estático
                tiempo_viaje_minutos = (distancia_km / 20.0) * 60.0
                numero_paradas = abs(paradaDestino['orden'] - paradaOrigen['orden'])
                tiempo_paradas_minutos = numero_paradas * 2
                tiempo_total = int(round(tiempo_viaje_minutos + tiempo_paradas_minutos))
        else:
            # Validate empresa
            if empresa not in RUTAS_DATABASE:
                return respuesta_error(404, "Empresa %s no encontrada" % empresa)
            if numeroRuta not in RUTAS_DATABASE[empresa]:
                return respuesta_error(404, "La ruta %d no existe para la empresa %s" % (numeroRuta, empresa))

            paradas = RUTAS_DATABASE[empresa][numeroRuta]
            dist_o, paradaOrigen = encontrar_parada_mas_cercana(origenLat, origenLon, paradas)
            dist_d, paradaDestino = encontrar_parada_mas_cercana(destinoLat, destinoLon, paradas)

            if dist_o > 1.0 or dist_d > 1.0:
                return respuesta_error(400, "Los puntos están muy lejos de la ruta")

            if paradaOrigen['orden'] > paradaDestino['orden']:
                return respuesta_error(400, "El orden de paradas sugiere que el destino está antes que el origen en la ruta")

            distancia_km = calcular_distancia_entre_paradas(paradas, paradaOrigen['orden'], paradaDestino['orden'])
            
            # Calcular tiempo para método estático
            tiempo_viaje_minutos = (distancia_km / 20.0) * 60.0
            numero_paradas = abs(paradaDestino['orden'] - paradaOrigen['orden'])
            tiempo_paradas_minutos = numero_paradas * 2
            tiempo_total = int(round(tiempo_viaje_minutos + tiempo_paradas_minutos))


        costo = TARIFAS.get(empresa, 0)
        distancia_km_rounded = round(distancia_km, 2)

        # Build canonical success response with controlled types and fields
        respuesta = {
            "success": True,
            "metodo": metodo_usado,
            "empresa": str(empresa),
            "numeroRuta": int(numeroRuta),
            "paradaOrigen": {
                "nombre": str(paradaOrigen.get('nombre', '')),
                "lat": float(paradaOrigen.get('lat', 0.0)),
                "lon": float(paradaOrigen.get('lon', 0.0)),
                "orden": int(paradaOrigen.get('orden', 0))
            },
            "paradaDestino": {
                "nombre": str(paradaDestino.get('nombre', '')),
                "lat": float(paradaDestino.get('lat', 0.0)),
                "lon": float(paradaDestino.get('lon', 0.0)),
                "orden": int(paradaDestino.get('orden', 0))
            },
            "tiempoEstimadoMinutos": int(tiempo_total),
            "distanciaKm": float(distancia_km_rounded),
            "costo": int(costo),
            "mensaje": f"Ruta calculada exitosamente con {metodo_usado.upper()}"
        }

        # -------------------------------------------
        # NUEVO BLOQUE PARA ENVIAR GEOMETRÍA A ANDROID
        # -------------------------------------------
        if metodo_usado == "osrm" and ruta_osrm is not None and "geometria" in ruta_osrm:
            respuesta["geometria"] = ruta_osrm["geometria"]   # GeoJSON válido
        else:
            respuesta["geometria"] = None


        # Log to console (safe printing for environments without emoji support)
        _safe_print(f"✅ Estimación calculada ({metodo_usado.upper()}): {empresa} Ruta {numeroRuta}")
        _safe_print(f"   Desde: {paradaOrigen['nombre']} -> Hasta: {paradaDestino['nombre']}")
        _safe_print(f"   Tiempo: {tiempo_total} min | Distancia: {distancia_km_rounded} km | Costo: ${costo}")

        return jsonify(respuesta), 200

    except Exception as e:
        _safe_print("❌ Error interno:", str(e))
        return respuesta_error(500, "Error interno del servidor: %s" % str(e))


# Additional helpers

def calcular_distancia_entre_paradas(paradas, orden_origen, orden_destino):
    if orden_destino < orden_origen:
        return 0.0
    total = 0.0
    for ord_act in range(orden_origen, orden_destino):
        p1 = paradas[ord_act - 1]
        p2 = paradas[ord_act]
        total += distancia_haversine(p1['lat'], p1['lon'], p2['lat'], p2['lon'])
    return total


def respuesta_error(codigo_http, mensaje):
    err = {
        "success": False,
        "empresa": "",
        "numeroRuta": 0,
        "paradaOrigen": {"nombre": "", "lat": 0.0, "lon": 0.0, "orden": 0},
        "paradaDestino": {"nombre": "", "lat": 0.0, "lon": 0.0, "orden": 0},
        "tiempoEstimadoMinutos": 0,
        "distanciaKm": 0.0,
        "costo": 0,
        "mensaje": mensaje
    }
    return jsonify(err), codigo_http

# ==========================================================
# === BLOQUE AÑADIDO PARA ETA Y SIMULACIÓN AUTOMÁTICA  =====
# ==========================================================

# ==========================================================
# 1. Endpoint: Usuarios reportan la ubicación del bus
# ==========================================================
@app.route('/api/update-bus-gps', methods=['POST'])
def update_bus_gps():
    """
    Usuario dentro del bus envía su GPS.
    Esto hace que el bus exista en el mapa.
    """
    data = request.get_json(force=True)

    required = ["idBus", "empresa", "ruta", "lat", "lon"]
    for r in required:
        if r not in data:
            return jsonify({"success": False, "mensaje": f"Falta campo {r}"}), 400

    idBus = str(data["idBus"])
    empresa = data["empresa"]
    ruta = int(data["ruta"])
    lat = float(data["lat"])
    lon = float(data["lon"])
    vel = float(data.get("velocidad", 20))  # km/h por defecto 

    if empresa not in RUTAS_DATABASE or ruta not in RUTAS_DATABASE[empresa]:
        return jsonify({"success": False, "mensaje": "Empresa o ruta inválida"}), 400

    if not validar_coordenadas(lat, lon):
        return jsonify({"success": False, "mensaje": "Coordenadas inválidas"}), 400

    BUS_POSITIONS[idBus] = {
        "empresa": empresa,
        "ruta": ruta,
        "lat": lat,
        "lon": lon,
        "vel": vel,
        "timestamp": time.time()
    }

    return jsonify({
        "success": True,
        "mensaje": f"Bus {idBus} actualizado",
        "bus": BUS_POSITIONS[idBus]
    }), 200


@app.route('/api/buses', methods=['GET'])
def get_buses():
    """
    Retorna la lista de todos los buses activos.
    Filtra buses que no se han actualizado en los últimos 5 minutos.
    """
    ahora = time.time()
    buses_activos = []
    
    # Copia para evitar errores de modificación durante iteración
    for bid, datos in list(BUS_POSITIONS.items()):
        # Si la última actualización fue hace menos de 5 minutos (300 segundos)
        if ahora - datos['timestamp'] < 300:
            bus_info = datos.copy()
            bus_info['id'] = bid
            buses_activos.append(bus_info)
            
    return jsonify(buses_activos), 200

# ==========================================================
# 2. Helper: Bus más cercano que pase por una ruta específica
# ==========================================================
def obtener_buses_en_ruta(empresa, ruta):
    buses = []
    for bid, datos in BUS_POSITIONS.items():
        if datos["empresa"] == empresa and datos["ruta"] == ruta:
            buses.append((bid, datos))
    return buses

# ==========================================================
# 3. ETA real desde la posición del bus hacia un paradero
# ==========================================================
def eta_bus_a_paradero(bus, parada):
    dist_km = distancia_haversine(bus["lat"], bus["lon"], parada["lat"], parada["lon"])
    vel_ms = max(bus["vel"] * 1000 / 3600, 0.1)
    eta_min = (dist_km * 1000) / vel_ms / 60
    return round(eta_min, 1)



# ==========================================================
# 4. Endpoint ETA por coordenada libre
# ==========================================================
@app.route('/api/eta', methods=['POST'])
def eta_usuario():
    """
    Usuario envía su GPS -> Se le recomienda un paradero + ruta + ETA
    """
    data = request.get_json(force=True)
    required = ["userLat", "userLon"]
    for r in required:
        if r not in data:
            return jsonify({"success": False, "mensaje": f"Falta campo {r}"}), 400

    userLat = float(data["userLat"])
    userLon = float(data["userLon"])

    if not validar_coordenadas(userLat, userLon):
        return jsonify({"success": False, "mensaje": "Coordenadas fuera de Popayán"}), 400

    mejor = None

    # Buscar la mejor combinación: empresa+ruta+paradero más cercano
    for empresa, rutasVar in RUTAS_DATABASE.items():
        for rutaNum, paradas in rutasVar.items():
            dist, parada = encontrar_parada_mas_cercana(userLat, userLon, paradas)

            if dist < 0.8:  # Debe estar cerca del recorrido
                if mejor is None or dist < mejor["distancia"]:
                    mejor = {
                        "empresa": empresa,
                        "numeroRuta": rutaNum,
                        "parada": parada,
                        "distancia": dist
                    }

    if mejor is None:
        return jsonify({"success": False, "mensaje": "No hay rutas cerca de ti"}), 404

    empresa = mejor["empresa"]
    ruta = mejor["numeroRuta"]
    parada = mejor["parada"]
    idx_parada = parada.get("orden", 0) - 1

    # Buses disponibles en esa ruta
    buses = obtener_buses_en_ruta(empresa, ruta)
    if not buses:
        return jsonify({
            "success": True,
            "empresa": empresa,
            "numeroRuta": ruta,
            "paradaOrigen": None,
            "paradaDestino": parada,  # debe existir
            "tiempoEstimadoMinutos": None,
            "tiempoEntreParadasMinutos": None,
            "distanciaKm": round(mejor["distancia"], 3),  # obligatorio
            "costo": 2500,  # obligatorio
            "mensaje": "No hay buses reportados en esta ruta aún",
            "estado": "NO_HAY_BUSES"
        }), 200

    # Buscar el bus con ETA más corta
    mejorETA = None
    mejorBusID = None
    estado = "EN_CAMINO"

    for bid, bus in buses:
        # Determinar si el bus ya pasó
        idx_bus = bus.get("ultima_parada_index", -1)
        
        # Si el bus va en una dirección y el usuario espera en una parada anterior, ya pasó.
        if idx_bus >= idx_parada:
            estado = "YA_PASO"
            continue

        eta = eta_bus_a_paradero(bus, parada)
        if mejorETA is None or eta < mejorETA:
            mejorETA = eta
            mejorBusID = bid
            estado = "EN_CAMINO"

    if mejorETA is None:
        
        return jsonify({
            "success": True,
            "empresa": empresa,
            "numeroRuta": ruta,
            "paradaOrigen": None,
            "paradaDestino": parada,
            "tiempoEstimadoMinutos": None,
            "tiempoEntreParadasMinutos": None,
            "distanciaKm": round(mejor["distancia"], 3),
            "costo": 2500,
            "mensaje": "El bus acaba de pasar o no hay buses cercanos",
            "estado": estado
        }), 200


    return jsonify({
    "success": True,
    "empresa": empresa,
    "numeroRuta": ruta,
    "paradaOrigen": parada,
    "paradaDestino": parada,
    "tiempoEstimadoMinutos": mejorETA,
    "tiempoEntreParadasMinutos": None,
    "distanciaKm": round(mejor["distancia"], 3),
    "costo": 2500,
    "mensaje": f"El bus {mejorBusID} llegará en {mejorETA} min",
    "estado": estado
}), 200

# ==========================================================
# 5. Simulador automático de buses
# ==========================================================
@app.route('/api/simular-bus', methods=['POST'])
def simular_bus():
    """
    Simula un bus recorriendo toda la ruta automáticamente con logs detallados.
    Usa geometría OSRM para seguir la carretera exacta.
    """
    data = request.get_json(force=True)

    idBus = str(data.get("idBus", "SIM01"))
    empresa = data.get("empresa")
    ruta = int(data.get("ruta"))
    velocidad_base = float(data.get("velocidad", 25))  # km/h

    if empresa not in RUTAS_DATABASE or ruta not in RUTAS_DATABASE[empresa]:
        return jsonify({"success": False, "mensaje": "Ruta inválida"}), 400

    paradas = RUTAS_DATABASE[empresa][ruta]

    _safe_print(f"🔵 Iniciando simulación SUAVE del bus {idBus} - {empresa} Ruta {ruta}")
    _safe_print(f"   Velocidad Base: {velocidad_base} km/h")

    def hilo_simulacion():
        global BUS_POSITIONS
        import random

        # Copiar paradas para poder modificarlas
        paradas_actuales = list(paradas)

        # Posicionar en inicio
        BUS_POSITIONS[idBus] = {
            "empresa": empresa,
            "ruta": ruta,
            "lat": paradas_actuales[0]["lat"],
            "lon": paradas_actuales[0]["lon"],
            "vel": 0,
            "timestamp": time.time(),
            "estado": "EN_PARADA",
            "proxima_parada": paradas_actuales[0]["nombre"]
        }

        _safe_print(f"🟢 Bus {idBus} en salida: {paradas_actuales[0]['nombre']}")
        time.sleep(2)

        while True:
            # Bucle de recorrido (Ida)
            recorrer_tramo(idBus, empresa, ruta, paradas_actuales, velocidad_base)
            
            # Llegada al final
            _safe_print(f"🏁 Bus {idBus} terminó recorrido. Esperando retorno...")
            time.sleep(10)
            
            # Invertir ruta para el retorno
            paradas_actuales = paradas_actuales[::-1]
            _safe_print(f"🔄 Bus {idBus} inicia retorno: {paradas_actuales[0]['nombre']} -> {paradas_actuales[-1]['nombre']}")

    t = threading.Thread(target=hilo_simulacion, daemon=True)
    t.start()

    return jsonify({
        "success": True,
        "mensaje": f"Simulación SUAVE con RETORNO iniciada para bus {idBus}",
        "empresa": empresa,
        "ruta": ruta
    }), 200

def recorrer_tramo(idBus, empresa, ruta, paradas, velocidad_base):
    global BUS_POSITIONS
    import random
    
    for i in range(len(paradas) - 1):
        inicio = paradas[i]
        fin = paradas[i + 1]
        
        # Obtener geometría real de la calle usando OSRM
        ruta_osrm = calcular_ruta_osrm(inicio['lat'], inicio['lon'], fin['lat'], fin['lon'])
        
        puntos_ruta = []
        if ruta_osrm and 'geometria' in ruta_osrm and ruta_osrm['geometria']:
            coords = ruta_osrm['geometria']['coordinates']
            puntos_ruta = [[c[1], c[0]] for c in coords] # [lat, lon]
        else:
            puntos_ruta = [[inicio['lat'], inicio['lon']], [fin['lat'], fin['lon']]]

        # Recorrer los puntos de la geometría con interpolación
        for idx in range(len(puntos_ruta) - 1):
            p1 = puntos_ruta[idx]
            p2 = puntos_ruta[idx+1]
            
            # Calcular distancia del micro-segmento
            dist_km = distancia_haversine(p1[0], p1[1], p2[0], p2[1])
            
            # Determinar velocidad para este tramo
            factor_velocidad = random.uniform(0.8, 1.1)
            velocidad_actual = velocidad_base * factor_velocidad
            
            # Reducir velocidad cerca de paradas (último tramo del segmento principal)
            if i == len(paradas) - 2 and idx > len(puntos_ruta) * 0.9:
                    velocidad_actual *= 0.5
            
            # Calcular tiempo necesario para recorrer este micro-segmento
            if velocidad_actual < 1: velocidad_actual = 1
            tiempo_segmento_horas = dist_km / velocidad_actual
            tiempo_segmento_segundos = tiempo_segmento_horas * 3600
            
            paso_tiempo = 0.2
            num_pasos = int(max(1, tiempo_segmento_segundos / paso_tiempo))
            
            for paso in range(num_pasos):
                avance = (paso + 1) / num_pasos
                lat_interp = p1[0] + (p2[0] - p1[0]) * avance
                lon_interp = p1[1] + (p2[1] - p1[1]) * avance
                
                BUS_POSITIONS[idBus] = {
                    "empresa": empresa,
                    "ruta": ruta,
                    "lat": lat_interp,
                    "lon": lon_interp,
                    "vel": round(velocidad_actual, 1),
                    "timestamp": time.time(),
                    "ultima_parada_index": i,
                    "estado": "EN_TRANSITO",
                    "proxima_parada": fin["nombre"]
                }
                time.sleep(paso_tiempo)

        # LLEGADA A PARADA
        _safe_print(f"🛑 Bus {idBus} PARADO en: {fin['nombre']}")
        BUS_POSITIONS[idBus]["vel"] = 0
        BUS_POSITIONS[idBus]["estado"] = "EN_PARADA"
        BUS_POSITIONS[idBus]["lat"] = fin["lat"]
        BUS_POSITIONS[idBus]["lon"] = fin["lon"]
        
        tiempo_parada = random.randint(5, 8)
        time.sleep(tiempo_parada)

if __name__ == '__main__':
    # Set timeout behavior if needed (for production should use gunicorn with timeout)
    app.run(host='0.0.0.0', port=3002, debug=True)
