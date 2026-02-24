# Mini-OSC for Cogs

A protocol bridge that converts and routes messages between **OSC**, **HTTP**, **TCP**, and **UDP**. Designed to help [Cogs](https://cogs.show) communicate with network devices and external services.

## Quick Start

### Automatic installation

```bash
# Clone the repo
git clone https://github.com/guigro/cogs-mini-osc.git
cd cogs-mini-osc

# Run the installer (creates venv, installs dependencies)
chmod +x install.sh
./install.sh

# Start the app
source venv/bin/activate
python mini_osc.py
```

### Manual installation

```bash
python3 -m venv venv
source venv/bin/activate        # Linux/Mac
# venv\Scripts\activate          # Windows
pip install -r requirements.txt
python mini_osc.py
```

### macOS shortcut

Double-click `Start_OSC_Webapp.command` to launch everything automatically (venv activation + dependencies + browser).

Once running, open **http://127.0.0.1:5000** (or your configured IP/port) in a browser.

## How It Works

Mini-OSC acts as a bridge between protocols. You define **connections** that describe a **source** (from) and a **destination** (to). When a message arrives on the source, it gets converted and forwarded to the destination.

```
Cogs  --OSC-->  Mini-OSC  --HTTP/TCP/UDP-->  Device / API
Cogs  <--OSC--  Mini-OSC  <--HTTP/TCP/UDP--  Device / API
```

## Configuration

All settings are in `config.json`. The web interface lets you edit everything visually.

### Servers

```json
{
    "osc_server": {
        "listen_ip": "127.0.0.1",
        "listen_port": 53000
    },
    "flask_server": {
        "ip": "127.0.0.1",
        "port": 5000
    }
}
```

> **Tip:** Use your machine's local IP (e.g. `192.168.x.x`) instead of `127.0.0.1` if you need to receive messages from other devices on the network.

### Connections

Each connection has a `from` (source) and a `to` (destination). Here are all supported types:

#### HTTP to OSC (receive HTTP, send to Cogs)

```json
{
    "name": "HTTP to Cogs",
    "from": { "protocol": "http", "endpoint": "/send_osc" },
    "to": { "protocol": "osc", "ip": "127.0.0.1", "port": 12097 }
}
```

#### TCP to OSC

```json
{
    "name": "TCP to Cogs",
    "from": { "protocol": "tcp", "listen_ip": "127.0.0.1", "listen_port": 57676 },
    "to": { "protocol": "osc", "ip": "127.0.0.1", "port": 12097 }
}
```

#### UDP to OSC

```json
{
    "name": "UDP to Cogs",
    "from": { "protocol": "udp", "listen_ip": "127.0.0.1", "listen_port": 57677 },
    "to": { "protocol": "osc", "ip": "127.0.0.1", "port": 12097 }
}
```

#### OSC to TCP (with value mapping)

Map OSC arguments to named keys. OSC args `[42, 5]` become `{"GameID": 42, "Level": 5}`.

```json
{
    "name": "OSC to Game",
    "from": {
        "protocol": "osc",
        "address_pattern": "/game",
        "values": ["GameID", "Level"]
    },
    "to": { "protocol": "tcp", "ip": "127.0.0.1", "port": 5001 }
}
```

#### OSC to HTTP (with response forwarding)

Send an OSC message to an HTTP API and **forward the response back as OSC** to Cogs. Each field of the JSON response becomes a separate OSC argument.

```json
{
    "name": "OSC to API",
    "from": { "protocol": "osc", "address_pattern": "/api_call" },
    "to": { "protocol": "http", "url": "https://httpbin.org/post" },
    "response_to_osc": {
        "enabled": true,
        "ip": "127.0.0.1",
        "port": 12097,
        "address": "/api_response"
    }
}
```

When `response_to_osc` is enabled, the HTTP response JSON is split into individual OSC arguments:
- Simple values (string, number) are sent as-is
- Complex values (objects, arrays) are JSON-serialized as strings

Example: if the API returns `{"status": "ok", "score": 42, "data": [1,2,3]}`, Cogs receives:
- `arguments[0]` = `"ok"`
- `arguments[1]` = `42`
- `arguments[2]` = `"[1, 2, 3]"`

## Web Interface

Three tabs accessible at `http://<ip>:<port>`:

| Tab | Description |
|---|---|
| **Servers** | Configure OSC and Flask server IP/port |
| **Connections** | Add, edit, delete connections (visual form) |
| **Logs** | Real-time logs (auto-refresh every 2s) |

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET/POST` | `/send_osc` | Send an OSC message (main entry point for HTTP) |
| `GET` | `/get_config` | Get full configuration |
| `POST` | `/add_connection` | Add a new connection |
| `POST` | `/update_connection` | Update an existing connection |
| `POST` | `/remove_connection` | Remove a connection by index |
| `POST` | `/update_osc_server` | Update OSC server settings |
| `POST` | `/update_flask_server` | Update Flask server settings |
| `GET` | `/get_logs` | Get application logs |
| `POST` | `/clear_logs` | Clear all logs |

### Sending OSC via HTTP

```bash
# POST with JSON
curl -X POST http://127.0.0.1:5000/send_osc \
  -H "Content-Type: application/json" \
  -d '{"address": "/my_address", "args": [42, "hello"]}'

# GET with query params
curl "http://127.0.0.1:5000/send_osc?address=/my_address&arg1=42&arg2=hello"
```

## Usage with Cogs

### Receive data from a device in Cogs

1. Create a connection: **HTTP** (or TCP/UDP) **to OSC**
2. Point the source to your device and the destination to Cogs' OSC port (default: 12097)
3. In Cogs, use `osc.message?.arguments[0]` to read the first argument, `[1]` for the second, etc.

### Send data from Cogs to a device

1. Create a connection: **OSC to HTTP** (or TCP/UDP)
2. Set the OSC address pattern to match what Cogs sends
3. Use `values` mapping if you want named keys instead of a raw args list

### Call an API and get the response back in Cogs

1. Create a connection: **OSC to HTTP** with `response_to_osc` enabled
2. Cogs sends an OSC message, Mini-OSC calls the API, and forwards the response back as a new OSC message
3. Read each field with `osc.message?.arguments[0]`, `[1]`, etc.

## License

GPL-3.0 - See [LICENSE](LICENSE) for details.
