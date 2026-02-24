import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import threading
import time
import sys
import requests
import socket
from pythonosc import dispatcher, osc_server, udp_client


current_dir = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, static_folder=current_dir, static_url_path='')
CORS(app)  # Permet les requêtes CORS

CONFIG_FILE = "config.json"
config = None
targets_dict = {}
routes = []
logs = []

########################################
# Chargement et validation de la config
########################################

def migrate_config(cfg):
    """Migrate old targets+routes format to new connections format."""
    if "connections" in cfg:
        return cfg  # Already in new format

    if "targets" not in cfg or "routes" not in cfg:
        return cfg

    targets_by_name = {}
    for t in cfg["targets"]:
        targets_by_name[t["name"]] = t

    connections = []
    for route in cfg["routes"]:
        fr = route["from"]
        to = route["to"]
        target_name = to.get("target_name", "")
        target = targets_by_name.get(target_name, {})

        # Auto-generate a descriptive name
        conn_name = f"{fr['protocol'].upper()} to {target_name}"
        conn = {"name": conn_name}

        # Build "from" section
        conn_from = {"protocol": fr["protocol"]}
        if fr["protocol"] == "osc":
            conn_from["address_pattern"] = fr.get("address_pattern", "")
            if "values" in fr:
                conn_from["values"] = fr["values"]
        elif fr["protocol"] == "http":
            conn_from["endpoint"] = fr.get("endpoint", "")
        elif fr["protocol"] in ["tcp", "udp"]:
            conn_from["listen_ip"] = fr.get("ip", "")
            conn_from["listen_port"] = fr.get("port", 0)

        conn["from"] = conn_from

        # Build "to" section
        target_type = target.get("type", "")
        conn_to = {"protocol": target_type}
        if target_type == "osc":
            conn_to["ip"] = target.get("ip", "")
            conn_to["port"] = target.get("port", 0)
            if "address" in to:
                conn_to["address"] = to["address"]
        elif target_type in ["tcp", "udp"]:
            conn_to["ip"] = target.get("ip", "")
            conn_to["port"] = target.get("port", 0)
        elif target_type == "http":
            conn_to["url"] = target.get("url", "")

        conn["to"] = conn_to
        connections.append(conn)

    new_cfg = {
        "osc_server": cfg["osc_server"],
        "flask_server": cfg["flask_server"],
        "connections": connections
    }
    return new_cfg


def expand_connections(cfg):
    """Convert connections[] to internal targets_dict + routes[] for the routing engine."""
    global targets_dict, routes
    targets_dict = {}
    routes = []

    for i, conn in enumerate(cfg.get("connections", [])):
        fr = conn["from"]
        to = conn["to"]
        # Generate a unique internal target name
        target_name = f"_conn_{i}_{conn.get('name', '')}"

        # Build internal target
        target = {"name": target_name, "type": to["protocol"]}
        if to["protocol"] in ["osc", "tcp", "udp"]:
            target["ip"] = to.get("ip", "")
            target["port"] = to.get("port", 0)
        if to["protocol"] == "http":
            target["url"] = to.get("url", "")
        targets_dict[target_name] = target

        # Build internal route
        route_from = {"protocol": fr["protocol"]}
        if fr["protocol"] == "osc":
            route_from["address_pattern"] = fr.get("address_pattern", "")
            if "values" in fr:
                route_from["values"] = fr["values"]
        elif fr["protocol"] == "http":
            route_from["endpoint"] = fr.get("endpoint", "")
        elif fr["protocol"] in ["tcp", "udp"]:
            route_from["ip"] = fr.get("listen_ip", "")
            route_from["port"] = fr.get("listen_port", 0)

        route_to = {"target_name": target_name}
        if to["protocol"] == "osc" and "address" in to:
            route_to["address"] = to["address"]

        routes.append({"from": route_from, "to": route_to})


def load_config(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            cfg = json.load(f)
    except FileNotFoundError:
        print(f"File {filename} can't be found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON in {filename} : {e}")
        sys.exit(1)

    # Auto-migrate old format
    cfg = migrate_config(cfg)

    # Validation
    if "osc_server" not in cfg:
        print("Invalid configuration : 'osc_server' is missing.")
        sys.exit(1)
    if "flask_server" not in cfg:
        print("Invalid configuration : 'flask_server' is missing.")
        sys.exit(1)
    if "connections" not in cfg or not isinstance(cfg["connections"], list):
        print("Invalid configuration : 'connections' must be a list.")
        sys.exit(1)

    return cfg


def save_config(data):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(data, f, indent=4)

########################################
# Routes Flask
########################################
@app.route('/')
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/get_config', methods=['GET'])
def get_config():
    config = load_config(CONFIG_FILE)
    return jsonify(config)

@app.route('/update_osc_server', methods=['POST'])
def update_osc_server():
    data = request.json
    config = load_config(CONFIG_FILE)
    config['osc_server']['listen_ip'] = data['ip']
    config['osc_server']['listen_port'] = int(data['port'])
    save_config(config)
    return jsonify({"status": "success"})

@app.route('/update_flask_server', methods=['POST'])
def update_flask_server():
    data = request.json
    config = load_config(CONFIG_FILE)
    config['flask_server']['ip'] = data['ip']
    config['flask_server']['port'] = int(data['port'])
    save_config(config)
    return jsonify({"status": "success"})

@app.route('/add_connection', methods=['POST'])
def add_connection():
    data = request.json
    new_conn = {
        "name": data.get("name", ""),
        "from": data["from"],
        "to": data["to"]
    }
    config = load_config(CONFIG_FILE)
    config['connections'].append(new_conn)
    save_config(config)
    expand_connections(config)
    return jsonify({"status": "success"})

@app.route('/update_connection', methods=['POST'])
def update_connection():
    data = request.json
    index = int(data['index'])
    config = load_config(CONFIG_FILE)
    if 0 <= index < len(config['connections']):
        config['connections'][index] = {
            "name": data.get("name", ""),
            "from": data["from"],
            "to": data["to"]
        }
        save_config(config)
        expand_connections(config)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid index"}), 400

@app.route('/remove_connection', methods=['POST'])
def remove_connection():
    data = request.json
    index = int(data['index'])
    config = load_config(CONFIG_FILE)
    if 0 <= index < len(config['connections']):
        del config['connections'][index]
        save_config(config)
        expand_connections(config)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid index"}), 400

@app.route('/get_logs', methods=['GET'])
def get_logs():
    return jsonify(logs)

@app.route('/clear_logs', methods=['POST'])
def clear_logs():
    global logs
    logs = []
    return jsonify({"status": "success"})

# API to get local IP
@app.route('/get_local_ip', methods=['GET'])
def get_local_ip():
    local_ip = socket.gethostbyname(socket.gethostname())
    return jsonify({"local_ip": local_ip})


@app.route('/send_osc', methods=['GET', 'POST'])
def http_endpoint():
    # Déterminer les paramètres et l'adresse OSC selon GET ou POST
    if request.method == 'GET':
        osc_address = request.args.get('address')
        if not osc_address:
            return jsonify({"error": "Missing OSC address"}), 400

        osc_args = {key: request.args.get(key) for key in request.args if key != 'address'}
        osc_args_list = list(osc_args.values())
    elif request.method == 'POST':
        data = request.json
        osc_address = data.get('address')
        if not osc_address:
            return jsonify({"error": "Missing OSC address"}), 400

        osc_args_list = data.get('args', [])
        osc_args = data.get('args')

    # Créer les données pour handle_incoming_non_osc
    data = {
        "args": osc_args_list,  # Liste des arguments OSC
        "address": osc_address  # Adresse OSC depuis la requête
    }

    # Appeler handle_incoming_non_osc
    try:
        handle_incoming_non_osc("http", data, {"endpoint": "/send_osc"})
        return jsonify({"status": "Message routed", "address": osc_address, "args": osc_args_list}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


########################################
# Fonctions d'envoi vers les cibles
########################################

def send_to_http(target, address, args):
    url = target["url"]
    payload = {
        "address": address,
        "args": args
    }
    try:
        r = requests.post(url, json=payload, timeout=2)
        print(f"[HTTP] Send to {url}, statut={r.status_code}")
        add_log(f"[HTTP] Send to {url}, statut={r.status_code}")
    except Exception as e:
        print(f"[HTTP] Error sending to {url}: {e}")
        add_log(f"[HTTP] Error sending to {url}: {e}")

def send_to_tcp(target, address, args):
    ip = target["ip"]
    port = target["port"]

    # S'il s'agit d'un dict (issu de "values"), on l'envoie tel quel.
    # Sinon, on garde le comportement existant (wrapper).
    if isinstance(args, dict):
        # On envoie le dictionnaire brut, SANS "address" ni "args"
        payload = args
    else:
        # Ancien fonctionnement (liste ou autre)
        payload = {
            "address": address,
            "args": args
        }

    data = json.dumps(payload).encode("utf-8")

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((ip, port))
            s.sendall(data)
        print(f"[TCP] Send to {ip}:{port} OK with : {payload}")
        add_log(f"[TCP] Send to {ip}:{port} OK with : {payload}")
    except Exception as e:
        print(f"[TCP] Error sending to {ip}:{port}: {e}")
        add_log(f"[TCP] Error sending to {ip}:{port}: {e}")

def send_to_udp(target, address, args):
    ip = target["ip"]
    port = target["port"]
    payload = {
        "address": address,
        "args": args
    }
    data = json.dumps(payload).encode("utf-8")

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.sendto(data, (ip, port))
        print(f"[UDP] Send to {ip}:{port} OK")
        add_log(f"[UDP] Send to {ip}:{port} OK")
    except Exception as e:
        print(f"[UDP] Error sending {ip}:{port}: {e}")
        add_log(f"[UDP] Error sending to {ip}:{port}: {e}")


def send_osc_message(ip, port, address, args):
    client = udp_client.SimpleUDPClient(ip, port)
    client.send_message(address, args)
    print(f"[OSC] Sent args {args} on {address} to {ip}:{port}")
    add_log(f"[OSC] Sent args {args} on {address} to {ip}:{port}")

def handle_osc_out(target_name, address, args):
    # target_name est le nom de la cible OSC
    if target_name not in targets_dict:
        print(f"Target {target_name} can't be found.")
        add_log(f"Target {target_name} can't be found.")
        return
    target = targets_dict[target_name]
    if target["type"] != "osc":
        print(f"Target {target_name} is not OSC.")
        add_log(f"Target {target_name} is not OSC.")
        return

    ip = target["ip"]
    port = target["port"]
    print(f"Sending OSC : {ip}:{port} adress {address} args {args}")

    send_osc_message(ip, port, address, args)

########################################
# Gestion des messages entrants
########################################

def handle_osc_in_message(address, args):
    # On parcourt les routes pour voir si on a une route OSC->X
    for route in routes:
        if route["from"]["protocol"] == "osc":
            if route["from"]["address_pattern"] == address:
                target_name = route["to"]["target_name"]
                # Type de target ?
                target = targets_dict.get(target_name)
                if not target:
                    print(f"Target {target_name} can't be found")
                    add_log(f"Target {target_name} can't be found")
                    return

                # ----------------------------------------------------------------
                # Étape : gestion du mapping args -> dictionnaire selon 'values'
                # ----------------------------------------------------------------
                from_cfg = route["from"]
                if "values" in from_cfg:
                    mapped_args = {}
                    for i, key_name in enumerate(from_cfg["values"]):
                        if i < len(args):
                            mapped_args[key_name] = args[i]
                        else:
                            mapped_args[key_name] = None
                    final_args = mapped_args
                else:
                    final_args = args
                # ----------------------------------------------------------------

                ttype = target["type"]
                if ttype == "http":
                    send_to_http(target, address, final_args)
                    add_log("Send request to HTTP")
                elif ttype == "tcp":
                    send_to_tcp(target, address, final_args)
                elif ttype == "udp":
                    send_to_udp(target, address, final_args)
                else:
                    print(f"Type de cible inconnu: {ttype}")
                # Pour l'instant, on s'arrête après la première route matchée
                return

def handle_incoming_non_osc(protocol, data, route_filter):
    # Data est un dict: {"args": [...]}
    # route_filter contient l'info pour matcher la route (endpoint, ip, port)

    for route in routes:
        if route["from"]["protocol"] == protocol:
            match = False
            if protocol == "http":
                # Compare l'endpoint
                if route["from"]["endpoint"] == route_filter["endpoint"]:
                    match = True
            elif protocol in ["tcp", "udp"]:
                # Compare IP/port
                if route["from"]["ip"] == route_filter["ip"] and route["from"]["port"] == route_filter["port"]:
                    match = True

            if match:
                # On a trouvé une route non-OSC->OSC
                target_name = route["to"]["target_name"]

                # Priorise l'adresse depuis les données de la requête HTTP
                address = data.get("address") or route["to"].get("address") or data.get("osc_address")
                if not address:
                    print("Error: No OSC address provided")
                    return

                if protocol == "http":
                    args = data.get("args", [])
                elif protocol in ["tcp", "udp"]:
                    args = []
                    for key, value in data.items():
                        if key not in ["osc_address", "address"]:
                            if isinstance(value, list):
                                args.extend(value)  # Ajoute les éléments de la sous-liste
                            else:
                                args.append(value)

                handle_osc_out(target_name, address, args)
                return

########################################
# Serveurs TCP et UDP entrant
########################################

def tcp_server(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((ip, port))
    s.listen(1)
    print(f"TCP server listening on {ip}:{port}")
    add_log(f"TCP server listening on {ip}:{port}")
    while True:
        conn, addr = s.accept()
        data = conn.recv(4096)
        if data:
            try:
                payload = json.loads(data.decode("utf-8"))
                handle_incoming_non_osc("tcp", payload, {"ip":ip, "port":port})
            except Exception as e:
                print("[TCP] Error:", e)
        conn.close()

def start_tcp_server(ip, port):
    t = threading.Thread(target=tcp_server, args=(ip, port), daemon=True)
    t.start()

def udp_server(ip, port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((ip, port))
    print(f"Serveur UDP écoute sur {ip}:{port}")
    add_log(f"Serveur UDP écoute sur {ip}:{port}")
    while True:
        data, addr = s.recvfrom(4096)
        if data:
            try:
                payload = json.loads(data.decode("utf-8"))
                handle_incoming_non_osc("udp", payload, {"ip":ip, "port":port})
            except Exception as e:
                print("[UDP] Erreur:", e)

def start_udp_server(ip, port):
    t = threading.Thread(target=udp_server, args=(ip, port), daemon=True)
    t.start()

########################################
# Gestion des logs
########################################

def add_log(message):
    """Ajoute un message dans les logs et limite leur taille."""
    global logs
    logs.append(message)
    if len(logs) > 100:  # Limite à 100 entrées pour éviter un débordement
        logs.pop(0)

########################################
# Serveur OSC principal
########################################

def osc_message_handler(address, *args):
    print(f"OSC received: address={address}, args={args}")
    add_log(f"OSC received: address={address}, args={args}")
    handle_osc_in_message(address, args)

if __name__ == "__main__":
    config = load_config(CONFIG_FILE)

    # Save migrated config if it was in old format
    save_config(config)

    # Expand connections to internal targets_dict + routes
    expand_connections(config)

    print("Config loaded with success.")
    logs.append("Server is running and ready to receive requests.")

    # Lancer le serveur OSC entrant
    osc_ip = config["osc_server"]["listen_ip"]
    osc_port = config["osc_server"]["listen_port"]
    disp = dispatcher.Dispatcher()
    disp.map("/*", osc_message_handler)
    osc_srv = osc_server.ThreadingOSCUDPServer((osc_ip, osc_port), disp)
    print(f"OSC server listening on {osc_ip}:{osc_port}")
    add_log(f"OSC server listening on {osc_ip}:{osc_port}")
    osc_thread = threading.Thread(target=osc_srv.serve_forever, daemon=True)
    osc_thread.start()

    # Lancer les serveurs TCP/UDP définis dans les routes
    for r in routes:
        fr = r["from"]
        if fr["protocol"] == "tcp":
            start_tcp_server(fr["ip"], fr["port"])
        elif fr["protocol"] == "udp":
            start_udp_server(fr["ip"], fr["port"])

    # Lancer le serveur HTTP Flask
    app.run(host=config["flask_server"]["ip"], port=config["flask_server"]["port"], debug=False)
