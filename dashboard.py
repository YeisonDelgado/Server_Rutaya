from flask import Flask, render_template_string, jsonify, request
import requests
import time

app = Flask(__name__)

# Configuración
BACKEND_URL = "http://192.168.1.7:3002"
PORT = 5001

@app.route("/")
def index():
    return render_template_string(
        """
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8" />
    <title>Monitor de Buses - Popayán</title>
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    <style>
        body { margin: 0; padding: 0; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
        #map { height: 100vh; width: 100%; }
        #panel {
            position: absolute; top: 10px; right: 10px; width: 350px;
            background: white; padding: 15px; border-radius: 8px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2); z-index: 1000;
            max-height: 90vh; overflow-y: auto;
        }
        .tab-buttons { display: flex; border-bottom: 1px solid #ddd; margin-bottom: 15px; }
        .tab-btn { flex: 1; padding: 10px; border: none; background: none; cursor: pointer; font-weight: bold; color: #7f8c8d; }
        .tab-btn.active { color: #2c3e50; border-bottom: 2px solid #3498db; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        
        .bus-card {
            border-left: 5px solid #333; background: #f9f9f9;
            margin-bottom: 10px; padding: 10px; border-radius: 4px;
            cursor: pointer; transition: background 0.2s;
        }
        .bus-card:hover { background: #ecf0f1; }
        .bus-info { display: flex; justify-content: space-between; font-size: 0.9em; color: #555; }
        .bus-badge { padding: 2px 6px; border-radius: 4px; color: white; font-size: 0.8em; }
        h3 { margin: 0 0 5px 0; font-size: 1.1em; }
        
        /* Form styles */
        .form-group { margin-bottom: 10px; }
        label { display: block; margin-bottom: 5px; font-size: 0.9em; font-weight: bold; }
        input, select { width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 4px; box-sizing: border-box; }
        button.action-btn { width: 100%; padding: 10px; background: #3498db; color: white; border: none; border-radius: 4px; cursor: pointer; font-weight: bold; margin-top: 5px; }
        button.action-btn:hover { background: #2980b9; }
        .result-box { margin-top: 10px; padding: 10px; background: #e8f6f3; border-radius: 4px; font-size: 0.9em; display: none; }
        
        /* Marker colors */
        .marker-icon {
            width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 4px rgba(0,0,0,0.3);
        }
        
        /* Smooth movement for markers */
        .leaflet-marker-icon {
            transition: all 1s linear;
        }
    </style>
</head>
<body>

<div id="panel">
    <div class="tab-buttons">
        <button class="tab-btn active" onclick="switchTab('monitor')">Monitor</button>
        <button class="tab-btn" onclick="switchTab('admin')">Administración</button>
    </div>

    <!-- Pestaña Monitor -->
    <div id="monitor" class="tab-content active">
        <h2>🚍 Monitor de Buses</h2>
        <div id="status" style="margin-bottom:10px; font-size:0.8em; color:#7f8c8d">Conectando...</div>
        <div id="busList"></div>
    </div>

    <!-- Pestaña Administración -->
    <div id="admin" class="tab-content">
        <h2>🛠️ Control de Simulación</h2>
        
        <div class="form-group">
            <label>Simular Nuevo Bus</label>
            <input type="text" id="simId" placeholder="ID Bus (ej. BUS-99)">
            <select id="simEmpresa" style="margin-top:5px" onchange="cargarRutas()">
                <option value="">Selecciona Empresa</option>
                <option value="Sotracauca">Sotracauca</option>
                <option value="TransPubenza">TransPubenza</option>
                <option value="TransLibertad">TransLibertad</option>
                <option value="TransTambo">TransTambo</option>
            </select>
            <select id="simRuta" style="margin-top:5px" disabled>
                <option value="">Primero selecciona empresa</option>
            </select>
            <input type="number" id="simVel" placeholder="Velocidad (km/h)" value="30" style="margin-top:5px">
            <button class="action-btn" onclick="simularBus()">Lanzar Bus</button>
        </div>
        
        <hr>
        
        <div class="form-group">
            <label>Consultar ETA (Simular Usuario)</label>
            <small style="color:#7f8c8d">Haz clic en el mapa para llenar coords</small>
            <div style="display:flex; gap:5px; margin-top:5px">
                <input type="text" id="userLat" placeholder="Latitud">
                <input type="text" id="userLon" placeholder="Longitud">
            </div>
            <button class="action-btn" style="background:#27ae60" onclick="consultarETA()">Consultar Rutas</button>
            <div id="etaResult" class="result-box"></div>
        </div>
    </div>
</div>

<div id="map"></div>

<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<script>
    const map = L.map('map').setView([2.4448, -76.6147], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '© OpenStreetMap contributors'
    }).addTo(map);

    const markers = {};
    let routePolyline = null;
    let userMarker = null;
    let stopMarkers = [];
    let rutasData = {};

    function getMarkerColor(empresa) {
        const colors = {
            "TransPubenza": "#e74c3c", // Rojo
            "TransLibertad": "#2ecc71", // Verde
            "TransTambo": "#f1c40f",    // Amarillo
            "Sotracauca": "#9b59b6"     // Morado
        };
        return colors[empresa] || "#3498db";
    }

    // Cargar rutas disponibles al inicio
    async function cargarRutasData() {
        try {
            const res = await fetch('/api/proxy/rutas');
            rutasData = await res.json();
            console.log("Rutas cargadas:", rutasData);
        } catch(e) {
            console.error("Error cargando rutas:", e);
        }
    }

    // Actualizar dropdown de rutas según empresa seleccionada
    function cargarRutas() {
        const empresa = document.getElementById('simEmpresa').value;
        const rutaSelect = document.getElementById('simRuta');
        
        console.log("Empresa seleccionada:", empresa);
        console.log("Datos de rutas disponibles:", rutasData);
        
        rutaSelect.innerHTML = '';
        rutaSelect.disabled = !empresa;
        
        if (!empresa) {
            rutaSelect.innerHTML = '<option value="">Primero selecciona empresa</option>';
            return;
        }
        
        if (!rutasData || Object.keys(rutasData).length === 0) {
            rutaSelect.innerHTML = '<option value="">Cargando rutas...</option>';
            // Intentar cargar de nuevo
            cargarRutasData().then(() => cargarRutas());
            return;
        }
        
        // El API devuelve {rutas: {empresa: {ruta: [...]}}}
        const rutasDB = rutasData.rutas || rutasData;
        
        if (rutasDB[empresa]) {
            const rutas = Object.keys(rutasDB[empresa]);
            console.log("Rutas para", empresa, ":", rutas);
            
            if (rutas.length === 0) {
                rutaSelect.innerHTML = '<option value="">No hay rutas disponibles</option>';
            } else {
                rutaSelect.innerHTML = '<option value="">Selecciona ruta</option>';
                rutas.forEach(ruta => {
                    const option = document.createElement('option');
                    option.value = ruta;
                    option.textContent = `Ruta ${ruta}`;
                    rutaSelect.appendChild(option);
                });
                rutaSelect.disabled = false;
            }
        } else {
            rutaSelect.innerHTML = '<option value="">No hay rutas para esta empresa</option>';
        }
    }

    function switchTab(tabId) {
        document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
        document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
        document.getElementById(tabId).classList.add('active');
        event.target.classList.add('active');
    }

    // Click en mapa para llenar coordenadas de usuario
    map.on('click', function(e) {
        document.getElementById('userLat').value = e.latlng.lat.toFixed(5);
        document.getElementById('userLon').value = e.latlng.lng.toFixed(5);
        
        if (userMarker) map.removeLayer(userMarker);
        userMarker = L.marker(e.latlng, {draggable: true}).addTo(map).bindPopup("Usuario").openPopup();
    });

    async function simularBus() {
        const empresa = document.getElementById('simEmpresa').value;
        const ruta = document.getElementById('simRuta').value;
        
        if (!empresa || !ruta) {
            alert("Por favor selecciona empresa y ruta");
            return;
        }
        
        const data = {
            idBus: document.getElementById('simId').value || `BUS-${Math.floor(Math.random()*1000)}`,
            empresa: empresa,
            ruta: parseInt(ruta),
            velocidad: parseFloat(document.getElementById('simVel').value)
        };
        
        try {
            const res = await fetch('/api/proxy/simular-bus', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const json = await res.json();
            alert(json.mensaje || "Comando enviado");
            
            // Actualizar paradas con el color de la empresa
            actualizarParadas(empresa, parseInt(ruta));
        } catch(e) { alert("Error: " + e); }
    }

    async function consultarETA() {
        const data = {
            userLat: document.getElementById('userLat').value,
            userLon: document.getElementById('userLon').value
        };
        
        try {
            const res = await fetch('/api/proxy/eta', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            });
            const json = await res.json();
            const box = document.getElementById('etaResult');
            box.style.display = 'block';
            
            if(json.success) {
                if (json.estado === "YA_PASO") {
                     box.innerHTML = `<b>⚠️ ${json.mensaje}</b>`;
                     box.style.background = "#fcf3cf";
                } else {
                    box.innerHTML = `
                        <b>🚍 Bus Recomendado:</b><br>
                        Ruta: ${json.ruta} (${json.empresa})<br>
                        Parada: ${json.paraderoRecomendado.nombre}<br>
                        <b>ETA: ${json.etaMin} min</b>
                    `;
                    box.style.background = "#e8f6f3";
                }
            } else {
                box.innerHTML = `❌ ${json.mensaje}`;
                box.style.background = "#fadbd8";
            }
        } catch(e) { alert("Error: " + e); }
    }

    function actualizarParadas(empresa, ruta) {
        // Limpiar paradas anteriores
        stopMarkers.forEach(marker => map.removeLayer(marker));
        stopMarkers = [];
        
        // El API devuelve {rutas: {empresa: {ruta: [...]}}}
        const rutasDB = rutasData.rutas || rutasData;
        
        if (rutasDB[empresa] && rutasDB[empresa][ruta]) {
            const paradas = rutasDB[empresa][ruta];
            const color = getMarkerColor(empresa);
            
            paradas.forEach(stop => {
                const marker = L.circleMarker([stop.lat, stop.lon], {
                    radius: 6,
                    fillColor: color,
                    color: "#fff",
                    weight: 2,
                    opacity: 1,
                    fillOpacity: 0.8
                }).addTo(map).bindPopup(`<b>${empresa} - Ruta ${ruta}</b><br>${stop.nombre}`);
                
                stopMarkers.push(marker);
            });
        }
    }

    function updateMap(buses) {
        const currentIds = new Set(buses.map(b => b.id));
        
        // Remove old markers
        Object.keys(markers).forEach(id => {
            if (!currentIds.has(id)) {
                map.removeLayer(markers[id]);
                delete markers[id];
            }
        });
        
        // Update/Add markers
        buses.forEach(b => {
            const color = getMarkerColor(b.empresa);
            
            // Status indicator (moving vs stopped)
            const isStopped = b.estado === "EN_PARADA";
            const statusColor = isStopped ? "#e74c3c" : "#2ecc71"; 
            
            const icon = L.divIcon({
                className: 'custom-marker',
                html: `
                    <div style="
                        background-color: ${color}; 
                        width: 20px; height: 20px; 
                        border-radius: 50%; 
                        border: 3px solid white; 
                        box-shadow: 0 0 4px rgba(0,0,0,0.3);
                        position: relative;
                    ">
                        <div style="
                            position: absolute; bottom: -5px; right: -5px;
                            width: 10px; height: 10px;
                            background-color: ${statusColor};
                            border-radius: 50%;
                            border: 1px solid white;
                        "></div>
                    </div>`,
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            });

            const popupContent = `
                <div style="min-width: 150px">
                    <h3 style="margin:0 0 5px; color:${color}">${b.empresa}</h3>
                    <b>Ruta ${b.ruta}</b><br>
                    <div style="margin-top:5px; padding-top:5px; border-top:1px solid #eee">
                        Vel: <b>${b.vel} km/h</b><br>
                        Estado: <b>${b.estado || 'En ruta'}</b><br>
                        ${b.proxima_parada ? `Próxima: ${b.proxima_parada}` : ''}
                    </div>
                </div>
            `;

            if (!markers[b.id]) {
                markers[b.id] = L.marker([b.lat, b.lon], {icon: icon})
                    .bindPopup(popupContent)
                    .addTo(map);
            } else {
                markers[b.id].setLatLng([b.lat, b.lon]);
                markers[b.id].setIcon(icon);
                markers[b.id].setPopupContent(popupContent);
            }
        });
    }

    function updatePanel(buses) {
        const list = document.getElementById("busList");
        const status = document.getElementById("status");
        
        if (buses.length === 0) {
            list.innerHTML = '<div class="empty-state">No hay buses activos.<br><small>Ve a "Administración" para crear uno.</small></div>';
            status.innerText = "Conectado - Sin buses";
            return;
        }
        
        let html = "";
        buses.forEach(b => {
            const color = getMarkerColor(b.empresa);
            const isStopped = b.estado === "EN_PARADA";
            
            html += `
                <div class='bus-card' style="border-left-color: ${color}" onclick="focusBus(${b.lat}, ${b.lon})">
                    <div class="bus-info">
                        <span class="bus-badge" style="background-color: ${color}">${b.empresa}</span>
                        <span>#${b.id}</span>
                    </div>
                    <h3>Ruta ${b.ruta}</h3>
                    <div class="bus-info">
                        <span>Vel: ${b.vel.toFixed(1)} km/h</span>
                        <span>${isStopped ? '🛑 PARADO' : '▶️ EN RUTA'}</span>
                    </div>
                    ${b.proxima_parada ? `<div style="margin-top:5px; font-size:12px; color:#95a5a6">🔜 ${b.proxima_parada}</div>` : ''}
                </div>
            `;
        });
        
        list.innerHTML = html;
        status.innerText = `Actualizado: ${new Date().toLocaleTimeString()} - ${buses.length} buses`;
    }
    
    function focusBus(lat, lon) {
        map.setView([lat, lon], 16);
    }

    async function fetchData() {
        try {
            const res = await fetch("/api/proxy/buses");
            if (!res.ok) throw new Error("Error fetching data");
            
            const data = await res.json();
            updateMap(data);
            updatePanel(data);
        } catch (error) {
            console.error("Error:", error);
            document.getElementById("status").innerText = "Error de conexión con el backend";
        }
    }

    // Update every 1 second for smoother animation
    setInterval(fetchData, 1000);
    fetchData();
    cargarRutasData(); // Cargar rutas disponibles al inicio

</script>
</body>
</html>
        """
    )

@app.route("/api/proxy/buses")
def proxy_buses():
    try:
        response = requests.get(f"{BACKEND_URL}/api/buses", timeout=2)
        return jsonify(response.json()) if response.status_code == 200 else jsonify([])
    except: return jsonify([])

@app.route("/api/proxy/rutas")
def proxy_rutas():
    try:
        response = requests.get(f"{BACKEND_URL}/api/rutas", timeout=2)
        return jsonify(response.json()) if response.status_code == 200 else jsonify({})
    except: return jsonify({})

@app.route("/api/proxy/simular-bus", methods=['POST'])
def proxy_simular():
    try:
        response = requests.post(f"{BACKEND_URL}/api/simular-bus", json=request.json, timeout=2)
        return jsonify(response.json())
    except Exception as e: return jsonify({"success":False, "mensaje": str(e)})

@app.route("/api/proxy/eta", methods=['POST'])
def proxy_eta():
    try:
        response = requests.post(f"{BACKEND_URL}/api/eta", json=request.json, timeout=2)
        return jsonify(response.json())
    except Exception as e: return jsonify({"success":False, "mensaje": str(e)})

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=PORT, debug=True)
