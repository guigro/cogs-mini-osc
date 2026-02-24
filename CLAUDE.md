# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Mini-OSC for Cogs is a protocol bridge application that converts and routes messages between OSC (Open Sound Control), HTTP, TCP, and UDP protocols. It's designed to help the Cogs application communicate with various network devices and services.

## Commands

```bash
# Setup
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt

# Run the application
python mini_osc.py
```

The web interface is accessible at `http://<flask_ip>:<flask_port>` (default: http://127.0.0.1:5000).

## Architecture

### Single-File Application (`mini_osc.py`)

The application runs multiple concurrent servers:
- **OSC Server**: Listens for incoming OSC messages (using `pythonosc`)
- **Flask HTTP Server**: Serves the web UI and handles HTTP API requests
- **TCP/UDP Servers**: Started dynamically based on connection configuration

### Configuration (`config.json`)

JSON configuration with three main sections:
- `osc_server`: IP and port for OSC listener
- `flask_server`: IP and port for HTTP server
- `connections`: List of unified connection definitions (from + to)

Each connection is self-descriptive with a `from` (source) and `to` (destination):
```json
{
  "name": "HTTP to Cogs",
  "from": { "protocol": "http", "endpoint": "/send_osc" },
  "to": { "protocol": "osc", "ip": "192.168.50.248", "port": 12097 }
}
```

**Auto-migration**: Old config files using `targets` + `routes` are automatically converted to the `connections` format on first load.

### Internal Adapter

At startup, `expand_connections()` converts the `connections[]` array into internal `targets_dict` + `routes[]` structures. The routing engine (`handle_osc_in_message`, `handle_incoming_non_osc`, `send_to_tcp`, etc.) operates on these internal structures unchanged.

### Message Routing Flow

1. **Incoming OSC** → `osc_message_handler()` → `handle_osc_in_message()` → routes to HTTP/TCP/UDP targets
2. **Incoming HTTP** (`/send_osc`) → `http_endpoint()` → `handle_incoming_non_osc()` → routes to OSC targets
3. **Incoming TCP/UDP** → `tcp_server()`/`udp_server()` → `handle_incoming_non_osc()` → routes to OSC targets

### Value Mapping

Connections from OSC can include a `values` array to map positional OSC arguments to named dictionary keys:
```json
{
  "name": "Quiz1",
  "from": { "protocol": "osc", "address_pattern": "/quiz1", "values": ["GameID", "Level"] },
  "to": { "protocol": "tcp", "ip": "192.168.50.232", "port": 5000 }
}
```
OSC args `[42, 5]` become `{"GameID": 42, "Level": 5}`.

### Web Interface (`index.html`)

Single-page Bulma CSS application with three tabs:
- **Servers**: Configure OSC and Flask server settings
- **Connections**: Manage unified connection definitions (source + destination)
- **Logs**: View real-time application logs (auto-refresh every 2 seconds)

### Key Flask API Endpoints

- `GET /get_config` - Retrieve full configuration
- `POST /send_osc` - Send OSC message (supports JSON and form-urlencoded)
- `POST /add_connection` - Add a new connection
- `POST /remove_connection` - Remove a connection by index
- `POST /update_osc_server`, `/update_flask_server` - Update server settings
- `GET /get_logs`, `POST /clear_logs` - Log management
