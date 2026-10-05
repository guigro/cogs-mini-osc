# Mini-OSC for Cogs

A protocol bridge that converts and routes messages between **OSC**, **HTTP**, **TCP**, **UDP**, and **raw JSON**. Designed to help [Cogs](https://cogs.show) communicate with network devices and external services.

## Desktop app (recommended)

Mini-OSC is available as a standalone app with its own window. No Python needed. Download the file for your system from the [latest release](https://github.com/guigro/cogs-mini-osc/releases/latest):

| System | File |
|---|---|
| macOS, Apple Silicon (M1 and later) | `Mini-OSC-<version>-macos-arm64.dmg` |
| macOS, Intel | `Mini-OSC-<version>-macos-intel.dmg` |
| Windows 10/11 (64-bit) | `Mini-OSC-<version>-windows-x64.exe` |
| Linux PC (x86_64) | `Mini-OSC-<version>-linux-x86_64.AppImage` |

Launch it: the servers start and the usual interface opens in a window. **Closing the window quits Mini-OSC.** Only one instance runs at a time: launching it again brings the existing window back.

### First launch

The app is not signed, so each system asks for confirmation once:

- **macOS**: open the `.dmg` and drag Mini-OSC into Applications. At first launch macOS blocks it: go to *System Settings > Privacy & Security* and click *Open Anyway*. Alternative, in a terminal: `xattr -dr com.apple.quarantine /Applications/Mini-OSC.app`.
- **Windows**: SmartScreen shows "Windows protected your PC": click *More info* then *Run anyway*.
- **Linux**: make the file executable (`chmod +x Mini-OSC-*.AppImage`) and run it. It needs WebKitGTK, present on most desktops (Ubuntu 22.04+, Debian 12+); otherwise: `sudo apt install libwebkit2gtk-4.1-0 gir1.2-webkit2-4.1`.
- **Firewall**: macOS and Windows ask to allow incoming connections, since Mini-OSC listens on the network. Allow it.

### Where are my settings?

The desktop app keeps `config.json` and the `logs/` folder in your user folder, so they survive app updates:

| System | Folder |
|---|---|
| macOS | `~/Library/Application Support/Mini-OSC/` |
| Windows | `%APPDATA%\Mini-OSC\` |
| Linux | `~/.config/mini-osc/` |

On first launch a default config is created (HTTP interface on port 5009, OSC on 53000, no connections). The exact paths are shown in the app (Servers tab for the config, Logs tab for the logs), each with an **Open folder** button. If Mini-OSC cannot start (for example a config from another machine, listening on an IP this computer does not have, or a port already in use), the window lists each server with its IP and port so you can fix them and restart, replace missing IPs with `127.0.0.1` in one click, open the folder, or go back to the default config. The previous file is always kept in `backups/`. If the config file is unreadable, it is left untouched.

**Import / Export**: in the Servers tab, *Export* saves the current configuration to a JSON file, *Import* loads one (old `targets` + `routes` configs are converted automatically). An imported file is checked first; the previous config is kept in the `backups/` folder, then Mini-OSC restarts.

To update, download the new version and replace the old one. Settings are kept.

## Run from source

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

In this mode, `config.json` and `logs/` stay next to `mini_osc.py` (even if you launch it from another folder).

To run the desktop window from source: `pip install -r requirements-desktop.txt` then `python desktop.py`. To build the apps yourself: `packaging/build_macos.sh`, `packaging/build_linux.sh`, or `pyinstaller packaging/mini_osc.spec` on Windows. Pushing a `v*` tag builds all four files on GitHub Actions and publishes a release.

## How It Works

Mini-OSC acts as a bridge between protocols. You define **connections** that describe a **source** (from) and a **destination** (to). When a message arrives on the source, it gets converted and forwarded to the destination.

```
Cogs  --OSC-->  Mini-OSC  --HTTP/TCP/UDP-->  Device / API
Cogs  <--OSC--  Mini-OSC  <--HTTP/TCP/UDP--  Device / API
```

## Configuration

All settings are in `config.json` (see [Where are my settings?](#where-are-my-settings) for the desktop app). The web interface lets you edit everything visually.

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

#### OSC to JSON (raw)

Send an arbitrary JSON body to any HTTP endpoint. The **first OSC argument** is sent as-is as the request body with `Content-Type: application/json` — no wrapper, no transformation.

Useful for devices/APIs that expect a specific JSON schema (WLED, Home Assistant, Hue, custom REST endpoints, etc.).

```json
{
    "name": "OSC to WLED",
    "from": {
        "protocol": "osc",
        "address_pattern": "/wled/state",
        "values": ["body"]
    },
    "to": { "protocol": "json", "url": "http://192.168.1.63/json/state" }
}
```

Then send an OSC message with the full JSON as the first argument:

```bash
oscsend 192.168.50.226 53000 /wled/state s '{"seg":[{"id":1,"on":true,"col":[[255,255,255]],"bri":255}]}'
```

Mini-OSC will perform the equivalent of:

```bash
curl -X POST "http://192.168.1.63/json/state" \
  -H "Content-Type: application/json" \
  -d '{"seg":[{"id":1,"on":true,"col":[[255,255,255]],"bri":255}]}'
```

#### OSC to OSC (device-prefix routing)

Forward OSC messages to another OSC device. The `address_pattern` acts as a **device prefix**: any incoming address starting with the pattern is forwarded to the destination with the prefix stripped. OSC arguments are passed through unchanged.

```json
{
    "name": "OSC to WLED device",
    "from": { "protocol": "osc", "address_pattern": "/wled" },
    "to": { "protocol": "osc", "ip": "192.168.1.63", "port": 9000 }
}
```

With this connection, an incoming `/wled/state/on` with args `[1]` is forwarded to `192.168.1.63:9000` as `/state/on` with args `[1]`:

```bash
oscsend 192.168.50.226 53000 /wled/state/on i 1
# → forwards OSC /state/on 1 to 192.168.1.63:9000
```

Notes:
- If the incoming address matches the pattern **exactly** (no sub-address), the optional `to.address` field is used as a fallback forwarding address; if it is not set, the message is dropped and a warning is logged.
- The `values` mapping does not apply to OSC destinations — arguments stay a positional list.
- Connection order matters: the first matching connection wins.

## Web Interface

Three tabs accessible at `http://<ip>:<port>`:

| Tab | Description |
|---|---|
| **Servers** | Configure OSC and Flask server IP/port |
| **Connections** | Add, edit, delete connections (visual form) |
| **Logs** | Real-time logs (auto-refresh every 2s) |

## Sending & Receiving Messages

In the examples below, replace `192.168.50.226` and ports with your actual values (shown in the **Servers** tab).

### Send to Mini-OSC (incoming)

#### HTTP

```bash
# POST with JSON body
curl -X POST http://192.168.50.226:5000/send_osc \
  -H "Content-Type: application/json" \
  -d '{"address": "/my_address", "args": [42, "hello"]}'

# GET with query parameters
curl "http://192.168.50.226:5000/send_osc?address=/my_address&arg1=42&arg2=hello"
```

#### OSC

Send a standard OSC message to `192.168.50.226:53000`. Any OSC client works (Cogs, TouchOSC, QLab, custom scripts...).

#### TCP

```bash
echo '{"address": "/my_address", "args": [1, 2, 3]}' | nc 192.168.50.226 57676
```

#### UDP

```bash
echo '{"address": "/my_address", "args": [1, 2, 3]}' | nc -u 192.168.50.226 57677
```

> For TCP and UDP, the payload is a JSON string with an `address` field (required) and optional extra fields. All non-address fields are flattened into OSC arguments.

### Sent by Mini-OSC (outgoing)

#### OSC (to Cogs)

Standard OSC message on the configured address pattern. Args are sent as positional OSC arguments.

#### HTTP

- **POST** (default): `{"address": "/pattern", "args": [1, 2, 3]}`
- **GET**: query params built from values mapping, e.g. `?command=scotland-yard-opened`

#### TCP

JSON payload over a raw TCP socket:
- With `values` mapping: `{"GameID": 42, "Level": 5}` (flat dict, no address wrapper)
- Without mapping: `{"address": "/pattern", "args": [1, 2, 3]}`

#### UDP

JSON payload over a UDP datagram: `{"address": "/pattern", "args": [1, 2, 3]}`

#### JSON (raw)

The first OSC argument is sent as the raw POST body with `Content-Type: application/json`. No `{"address": ..., "args": ...}` wrapper is added — useful when the target device expects its own schema.

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `GET/POST` | `/send_osc` | Send an OSC message (main entry point for HTTP) |
| `GET` | `/get_config` | Get full configuration |
| `GET` | `/get_local_ip` | Get detected LAN IP address |
| `POST` | `/add_connection` | Add a new connection |
| `POST` | `/update_connection` | Update an existing connection |
| `POST` | `/remove_connection` | Remove a connection by index |
| `POST` | `/update_osc_server` | Update OSC server settings |
| `POST` | `/update_flask_server` | Update Flask server settings |
| `GET` | `/get_logs` | Get application logs |
| `POST` | `/clear_logs` | Clear all logs |

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
