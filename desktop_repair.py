"""Page d'erreur de démarrage de Mini-OSC bureau, avec réparation de la configuration.

Quand les serveurs ne démarrent pas (IP absente de la machine, port occupé...), la fenêtre affiche
chaque serveur avec son IP et son port, modifiables, puis enregistre et redémarre. Si la config est
illisible, elle propose d'ouvrir le dossier ou de revenir à la config par défaut.
"""
import html
import ipaddress
import json
import os
import shutil
import socket
from datetime import datetime

ALL_INTERFACES = ("0.0.0.0", "::", "")


def listeners_from_config(cfg):
    """Tout ce qui écoute sur une IP et un port : serveur OSC, serveur HTTP, sources TCP/UDP des connexions."""
    listeners = [
        {"key": "osc_server", "index": -1, "label": "OSC server",
         "ip": cfg["osc_server"].get("listen_ip", ""), "port": cfg["osc_server"].get("listen_port", "")},
        {"key": "flask_server", "index": -1, "label": "HTTP server (web interface)",
         "ip": cfg["flask_server"].get("ip", ""), "port": cfg["flask_server"].get("port", "")},
    ]
    for i, conn in enumerate(cfg.get("connections", [])):
        fr = conn.get("from", {})
        if fr.get("protocol") in ("tcp", "udp"):
            name = conn.get("name") or f"Connection {i + 1}"
            listeners.append({"key": "connection", "index": i, "label": f"{name} ({fr['protocol'].upper()} listener)",
                              "ip": fr.get("listen_ip", ""), "port": fr.get("listen_port", "")})
    return listeners


def apply_listener_edits(cfg, edits):
    """Applique les IP/ports saisis. Lève ValueError avec un message lisible si une valeur est invalide."""
    for edit in edits:
        ip = str(edit.get("ip", "")).strip()
        port_text = str(edit.get("port", "")).strip()
        label = edit.get("label") or edit.get("key")
        if ip not in ALL_INTERFACES:
            try:
                ipaddress.ip_address(ip)
            except ValueError:
                raise ValueError(f"{label}: \"{ip}\" is not a valid IP address.")
        if not port_text.isdigit() or not 1 <= int(port_text) <= 65535:
            raise ValueError(f"{label}: the port must be a number between 1 and 65535.")
        port = int(port_text)

        key = edit.get("key")
        if key == "osc_server":
            cfg["osc_server"]["listen_ip"], cfg["osc_server"]["listen_port"] = ip, port
        elif key == "flask_server":
            cfg["flask_server"]["ip"], cfg["flask_server"]["port"] = ip, port
        elif key == "connection":
            fr = cfg["connections"][int(edit["index"])]["from"]
            fr["listen_ip"], fr["listen_port"] = ip, port
    return cfg


def ip_available(ip):
    """Vrai si cette machine peut écouter sur cette IP (elle existe sur une de ses interfaces)."""
    if ip in ALL_INTERFACES:
        return True
    try:
        family = socket.AF_INET6 if ipaddress.ip_address(ip).version == 6 else socket.AF_INET
        with socket.socket(family, socket.SOCK_DGRAM) as s:
            s.bind((ip, 0))
        return True
    except (ValueError, OSError):
        return False


def local_ip_suggestions():
    """IP proposées dans les champs : boucle locale, IP réseau principale, toutes les interfaces."""
    ips = ["127.0.0.1"]
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))  # aucun paquet envoyé : sert seulement à choisir l'interface
            lan = s.getsockname()[0]
        if lan not in ips:
            ips.append(lan)
    except OSError:
        pass
    ips.append("0.0.0.0")
    return ips


def backup_config(config_path):
    """Copie config.json dans backups/ (même illisible). Renvoie le chemin de la copie, ou None."""
    if not os.path.exists(config_path):
        return None
    backup_dir = os.path.join(os.path.dirname(config_path), "backups")
    os.makedirs(backup_dir, exist_ok=True)
    backup = os.path.join(backup_dir, f"config-{datetime.now().strftime('%Y%m%d-%H%M%S')}.json")
    shutil.copyfile(config_path, backup)
    return backup


class RepairApi:
    """Actions de la page d'erreur, appelées depuis le JavaScript via pywebview.api."""

    def __init__(self, config_path, default_path, relaunch, open_folder):
        self.config_path = config_path
        self.default_path = default_path
        self._relaunch = relaunch
        self._open_folder = open_folder

    def save(self, edits, force=False):
        import mini_osc
        try:
            cfg = mini_osc.load_config(self.config_path)
            apply_listener_edits(cfg, edits)
        except (ValueError, mini_osc.ConfigError) as e:
            return {"error": str(e)}
        missing = sorted({str(e.get("ip", "")).strip() for e in edits if not ip_available(str(e.get("ip", "")).strip())})
        if missing and not force:
            return {"warning": f"These IP addresses do not exist on this computer: {', '.join(missing)}. "
                               "Mini-OSC will not be able to start here. Save anyway (for example for another computer)?"}
        backup_config(self.config_path)
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=4, ensure_ascii=False)
        self._relaunch()

    def restore_default(self):
        backup_config(self.config_path)
        shutil.copyfile(self.default_path, self.config_path)
        self._relaunch()

    def open_folder(self):
        self._open_folder(os.path.dirname(self.config_path))

    def quit(self):
        os._exit(0)


def repair_html(message, config_path, cfg=None, config_problem=False):
    """Page d'erreur. cfg est la config lisible (champs modifiables) ou None si elle est illisible."""
    title = "Unreadable configuration" if config_problem else "Mini-OSC could not start"
    suggestions = "".join(f'<option value="{html.escape(ip)}">' for ip in local_ip_suggestions())

    if cfg is not None:
        rows = []
        for item in listeners_from_config(cfg):
            ok = ip_available(str(item["ip"]))
            rows.append(f"""
      <tr class="listener" data-key="{item['key']}" data-index="{item['index']}" data-label="{html.escape(item['label'])}">
        <td>{html.escape(item['label'])}</td>
        <td><input class="ip{'' if ok else ' bad'}" list="ips" value="{html.escape(str(item['ip']))}" data-ok="{'1' if ok else '0'}">
            {'' if ok else '<div class="hint">This IP does not exist on this computer</div>'}</td>
        <td><input class="port" type="number" min="1" max="65535" value="{html.escape(str(item['port']))}"></td>
      </tr>""")
        editor = f"""
  <h2>Servers</h2>
  <table>
    <tr><th></th><th>IP</th><th>Port</th></tr>{''.join(rows)}
  </table>
  <datalist id="ips">{suggestions}</datalist>
  <div class="actions">
    <button class="secondary" onclick="useLoopback()">Replace missing IPs with 127.0.0.1</button>
    <button class="primary" onclick="save()">Save and restart</button>
  </div>"""
    else:
        editor = ""

    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Mini-OSC</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", sans-serif; background: #1a1a2e; color: #eee; margin: 0; padding: 32px 40px; }}
  h1 {{ color: #ff6b6b; font-size: 22px; margin-top: 0; }}
  h2 {{ font-size: 16px; margin: 28px 0 8px; }}
  pre {{ background: #0f0f1e; padding: 12px 14px; border-radius: 6px; white-space: pre-wrap; word-break: break-word; margin: 6px 0; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; font-weight: 500; color: #aab; font-size: 13px; padding: 4px 8px; }}
  td {{ padding: 6px 8px; vertical-align: top; }}
  td:first-child {{ padding-top: 12px; }}
  input {{ background: #0f0f1e; color: #eee; border: 1px solid #3a3a5a; border-radius: 6px; padding: 7px 9px; font-size: 14px; width: 100%; box-sizing: border-box; }}
  input.port {{ width: 100px; }}
  input.bad {{ border-color: #ff6b6b; }}
  .hint {{ color: #ff6b6b; font-size: 12px; margin-top: 4px; }}
  .actions {{ display: flex; flex-wrap: wrap; gap: 10px; margin-top: 18px; }}
  button {{ padding: 9px 16px; font-size: 14px; border-radius: 6px; border: 0; cursor: pointer; background: #3a3a5a; color: #eee; }}
  button.primary {{ background: #6c5ce7; }}
  #msg {{ color: #ff6b6b; margin-top: 12px; min-height: 1em; }}
</style></head>
<body>
  <h1>{html.escape(title)}</h1>
  <pre>{html.escape(message)}</pre>
  <p style="margin-bottom:0">Configuration file:</p>
  <pre>{html.escape(config_path)}</pre>
  {editor}
  <div id="msg"></div>
  <h2>Other actions</h2>
  <div class="actions">
    <button onclick="pywebview.api.open_folder()">Open folder</button>
    <button onclick="restoreDefault()">Restore default configuration</button>
    <button onclick="pywebview.api.quit()">Quit</button>
  </div>
<script>
  function useLoopback() {{
    document.querySelectorAll('input.ip[data-ok="0"]').forEach(i => {{
      i.value = '127.0.0.1';
      i.classList.remove('bad');
      const hint = i.parentElement.querySelector('.hint');
      if (hint) hint.remove();
    }});
  }}
  async function save() {{
    const edits = [...document.querySelectorAll('tr.listener')].map(r => ({{
      key: r.dataset.key, index: parseInt(r.dataset.index), label: r.dataset.label,
      ip: r.querySelector('input.ip').value, port: r.querySelector('input.port').value
    }}));
    document.getElementById('msg').textContent = '';
    let res = await pywebview.api.save(edits, false);
    if (res && res.warning && confirm(res.warning)) res = await pywebview.api.save(edits, true);
    if (res && res.error) document.getElementById('msg').textContent = res.error;
  }}
  function restoreDefault() {{
    if (confirm("Replace the configuration with the default one? The current file will be kept in the backups/ folder.")) {{
      pywebview.api.restore_default();
    }}
  }}
</script>
</body></html>"""
