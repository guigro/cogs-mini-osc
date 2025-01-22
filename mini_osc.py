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

    # Validation minimale
    if "osc_server" not in cfg:
        print("Invalid configuration : 'osc_server' is missing.")
        sys.exit(1)
    if "flask_server" not in cfg:
        print("Invalid configuration : 'flask_server' is missing.")
        sys.exit(1)
    if "targets" not in cfg or not isinstance(cfg["targets"], list):
        print("Invalid configuration : 'targets' must be a list.")
        sys.exit(1)
    if "routes" not in cfg or not isinstance(cfg["routes"], list):
        print("Invalid configuration : 'routes' must be a list.")
        sys.exit(1)

    return cfg

def init_targets_and_routes(cfg):
    for t in cfg["targets"]:
        name = t["name"]
        targets_dict[name] = t
    global routes
    routes = cfg["routes"]


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

@app.route('/update_tcp_server', methods=['POST'])
def update_tcp_server():
    data = request.json
    config = load_config(CONFIG_FILE)
    for route in config['routes'] :
        if route['from']['protocol'] == "tcp":
            route['from']['ip'] = data['ip']
            route['from']['port'] = int(data['port'])
    save_config(config)
    return jsonify({"status": "success"})

@app.route('/add_target', methods=['POST'])
def add_target():
    data = request.json
    new_target = {
        "name": data['name'],
        "type": data['type'],
        "ip": data.get('address', ''),
        "port": int(data.get('port', 0)),
        "url": data.get('url', '')
    }
    config = load_config(CONFIG_FILE)
    config['targets'].append(new_target)
    save_config(config)
    return jsonify({"status": "success"})

@app.route('/remove_target', methods=['POST'])
def remove_target():
    data = request.json
    index = int(data['index'])
    config = load_config(CONFIG_FILE)
    if 0 <= index < len(config['targets']):
        del config['targets'][index]
        save_config(config)
        return jsonify({"status": "success"})
    return jsonify({"status": "error", "message": "Invalid index"}), 400

@app.route('/add_route', methods=['POST'])
def add_route():
    data = request.json
    new_route = {
        "from": data['from'],
        "to": data['to']
    }
    config = load_config(CONFIG_FILE)
    config['routes'].append(new_route)
    save_config(config)
    return jsonify({"status": "success"})

@app.route('/remove_route', methods=['POST'])
def remove_route():
    data = request.json
    index = int(data['index'])
    config = load_config(CONFIG_FILE)
    if 0 <= index < len(config['routes']):
        del config['routes'][index]
        save_config(config)
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

# API to update Cogs target
@app.route('/update_cogs_target', methods=['POST'])
def update_cogs_target():
    data = request.json
    
    # Charger la configuration
    config = load_config(CONFIG_FILE)
    
    for target in config.get('targets', []):
        if target.get('name') == 'cogs':
            target['ip'] = str(data['ip'])  # Assurez-vous que l'IP est une chaîne
            target['port'] = int(data['port'])  # Le port doit être un entier
            
            print(f"IP de 'cogs' mise à jour à : {data['ip']}:{data['port']}")
            break
    else:
        return jsonify({"status": "error", "message": "Target 'cogs' not found"}), 404

    # Sauvegarder les modifications
    save_config(config)
    print(f"Updated Cogs Target to {data['ip']}:{data['port']}")
    return jsonify({"status": "success", "ip": data['ip'], "port": data['port']})



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
    # print("[DEBUG] (send_to_tcp) args reçu =", args)
    # add_log(f"[DEBUG] (send_to_tcp) args reçu = {args}")

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


    # print("[DEBUG] send_to_tcp payload =", payload)
    # add_log(f"[DEBUG] send_to_tcp payload = {payload}")
    
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
    # print(f"[DEBUG] handle_osc_in_message called with address={address}, args={args}")
    # add_log(f"[DEBUG] handle_osc_in_message called with address={address}, args={args}")

    # On parcourt les routes pour voir si on a une route OSC->X
    for route in routes:
        if route["from"]["protocol"] == "osc":
            # print(f"[DEBUG] Checking route with address_pattern={route['from']['address_pattern']}")
            # add_log(f"[DEBUG] Checking route with address_pattern={route['from']['address_pattern']}")
            
            if route["from"]["address_pattern"] == address:
                # print(f"[DEBUG] This route is matched => {route}")
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
                from_cfg = route["from"]  # On se raccourcit l'écriture
                if "values" in from_cfg:
                    # print(f"[DEBUG] 'values' found => {route['from']['values']}")
                    # On a un tableau de keys, comme ["GameID", "Level1", "Level2", "Level3"]
                    # On construit un dictionnaire : { "GameID": args[0], "Level1": args[1], ... }
                    mapped_args = {}
                    for i, key_name in enumerate(from_cfg["values"]):
                        # Pour éviter les erreurs si le message n'a pas assez d'arguments
                        # on vérifie si i < len(args)
                        if i < len(args):
                            mapped_args[key_name] = args[i]
                        else:
                            mapped_args[key_name] = None
                    # C'est ce dictionnaire qu'on enverra
                    final_args = mapped_args
                else:
                    # print("[DEBUG] No 'values' in this route")
                    # Pas de 'values' => on garde la liste d'arguments comme avant
                    final_args = args
                # ----------------------------------------------------------------


                ttype = target["type"]
                if ttype == "http":
                    send_to_http(target, address, final_args)
                    add_log("Send request to HTTP")
                elif ttype == "tcp":
                    # print("[DEBUG] (handle_osc_in_message) final_args avant send_to_tcp =", final_args)
                    # add_log(f"[DEBUG] (handle_osc_in_message) final_args avant send_to_tcp = {final_args}")
                    send_to_tcp(target, address, final_args)
                elif ttype == "udp":
                    send_to_udp(target, address, final_args)
                else:
                    print(f"Type de cible inconnu: {ttype}")
                # Pour l'instant, on s’arrête après la première route matchée
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
                # On récupère le target OSC (main_osc_out)
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
    init_targets_and_routes(config)

    print("Config loaded with success.")
    logs.append("Server is running and ready to receive requests.")
    # print(json.dumps(config, indent=2))
    
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
    # Si tu veux changer le port HTTP, fais-le ici
    app.run(host=config["flask_server"]["ip"], port=config["flask_server"]["port"], debug=False)
