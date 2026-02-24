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
- **TCP/UDP Servers**: Started dynamically based on route configuration

### Configuration (`config.json`)

JSON configuration with four main sections:
- `osc_server`: IP and port for OSC listener
- `flask_server`: IP and port for HTTP server
- `targets`: List of destination endpoints (OSC, HTTP, TCP, UDP)
- `routes`: Message routing rules from source to target

### Message Routing Flow

1. **Incoming OSC** → `osc_message_handler()` → `handle_osc_in_message()` → routes to HTTP/TCP/UDP targets
2. **Incoming HTTP** (`/send_osc`) → `http_endpoint()` → `handle_incoming_non_osc()` → routes to OSC targets
3. **Incoming TCP/UDP** → `tcp_server()`/`udp_server()` → `handle_incoming_non_osc()` → routes to OSC targets

### Route Value Mapping

Routes can include a `values` array to map positional OSC arguments to named dictionary keys:
```json
{
  "from": { "protocol": "osc", "address_pattern": "/example", "values": ["GameID", "Level"] },
  "to": { "target_name": "MyTarget" }
}
```
OSC args `[42, 5]` become `{"GameID": 42, "Level": 5}`.

### Web Interface (`index.html`)

Single-page Bulma CSS application with four tabs:
- **Servers**: Configure OSC, TCP, Flask server settings and Cogs target
- **Targets**: Manage destination endpoints
- **Routes**: Configure message routing rules
- **Logs**: View real-time application logs (auto-refresh every 2 seconds)

### Key Flask API Endpoints

- `GET /get_config` - Retrieve full configuration
- `POST /send_osc` - Send OSC message (supports JSON and form-urlencoded)
- `POST /add_target`, `/remove_target` - Manage targets
- `POST /add_route`, `/remove_route` - Manage routes
- `GET /get_logs`, `POST /clear_logs` - Log management
