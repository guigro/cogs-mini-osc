"""Lanceur bureau de Mini-OSC.

Démarre le moteur de mini_osc.py dans un thread, puis ouvre une fenêtre native
(pywebview) sur l'interface web existante. Fermer la fenêtre quitte le logiciel.
Voir specs/001-desktop-app/contracts/launcher.md.
"""
import argparse
import html
import json
import os
import shutil
import socket
import sys
import tempfile
import threading
import time
import urllib.request

APP_NAME = "Mini-OSC"
STARTUP_TIMEOUT = 15  # secondes


def resource_dir():
    """Dossier des fichiers embarqués (index.html, vendor/, config.default.json)."""
    return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))


def default_data_dir(platform=None, environ=None):
    """Dossier utilisateur où vivent config.json et logs/ en mode bureau."""
    platform = sys.platform if platform is None else platform
    environ = os.environ if environ is None else environ
    if environ.get("MINI_OSC_DATA_DIR"):
        return environ["MINI_OSC_DATA_DIR"]
    home = os.path.expanduser("~")
    if platform == "darwin":
        return os.path.join(home, "Library", "Application Support", APP_NAME)
    if platform.startswith("win"):
        appdata = environ.get("APPDATA") or os.path.join(home, "AppData", "Roaming")
        return os.path.join(appdata, APP_NAME)
    xdg = environ.get("XDG_CONFIG_HOME") or os.path.join(home, ".config")
    return os.path.join(xdg, "mini-osc")


def window_url(flask_cfg):
    """URL affichée dans la fenêtre ; une écoute sur toutes les interfaces passe par 127.0.0.1."""
    ip = flask_cfg["ip"]
    if ip in ("0.0.0.0", "::", ""):
        ip = "127.0.0.1"
    return f"http://{ip}:{flask_cfg['port']}/"


def ensure_config(data_dir, default_path):
    """Crée config.json depuis la config par défaut s'il n'existe pas. Ne touche jamais un fichier existant."""
    config_path = os.path.join(data_dir, "config.json")
    if not os.path.exists(config_path):
        os.makedirs(data_dir, exist_ok=True)
        shutil.copyfile(default_path, config_path)
    return config_path


def redirect_console(data_dir):
    """Une app fenêtrée n'a pas de console : stdout/stderr vont dans un fichier du dossier de données."""
    if getattr(sys, "frozen", False) or sys.stdout is None:
        log = open(os.path.join(data_dir, "console.log"), "w", encoding="utf-8", buffering=1)
        sys.stdout = log
        sys.stderr = log


def start_engine(errors):
    """Lance mini_osc.start_servers() dans un thread ; toute exception est rangée dans errors."""
    import mini_osc

    def run():
        try:
            mini_osc.start_servers()
        except BaseException as e:  # noqa: BLE001 (on veut tout remonter à la fenêtre)
            errors.append(e)

    threading.Thread(target=run, daemon=True).start()


def describe_error(error, url):
    # Werkzeug fait sys.exit(1) quand le port HTTP est déjà pris
    if isinstance(error, SystemExit):
        return f"Le serveur HTTP n'a pas pu démarrer sur {url} : le port est probablement déjà utilisé par un autre programme."
    if isinstance(error, OSError):
        return f"Un serveur n'a pas pu démarrer : {error} (port déjà utilisé ?)"
    return str(error)


def wait_until_ready(url, errors, timeout=STARTUP_TIMEOUT):
    """Attend que le serveur Mini-OSC réponde sur url. Renvoie None si prêt, sinon un message d'erreur."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if errors:
            return describe_error(errors[0], url)
        try:
            with urllib.request.urlopen(url + "get_config", timeout=1) as resp:
                if "osc_server" in json.loads(resp.read().decode("utf-8")):
                    # Laisse une chance à une erreur Flask tardive (port déjà pris par un autre programme)
                    time.sleep(0.2)
                    return describe_error(errors[0], url) if errors else None
        except Exception:
            pass
        time.sleep(0.2)
    return f"Mini-OSC n'a pas répondu sur {url} en {timeout} secondes."


def error_html(message, config_path, config_problem=False):
    title = "Configuration illisible" if config_problem else "Mini-OSC n'a pas pu démarrer"
    return f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><title>{APP_NAME}</title>
<style>
  body {{ font-family: -apple-system, "Segoe UI", sans-serif; background: #1a1a2e; color: #eee; margin: 0; padding: 40px; }}
  h1 {{ color: #ff6b6b; font-size: 22px; }}
  pre {{ background: #0f0f1e; padding: 14px; border-radius: 6px; white-space: pre-wrap; word-break: break-word; }}
  button {{ margin-top: 20px; padding: 8px 18px; font-size: 14px; cursor: pointer; }}
</style></head>
<body>
  <h1>{html.escape(title)}</h1>
  <pre>{html.escape(message)}</pre>
  <p>Fichier de configuration :</p>
  <pre>{html.escape(config_path)}</pre>
  <p>Corrigez le fichier (ou libérez le port utilisé), puis relancez Mini-OSC.</p>
  <button onclick="pywebview.api.quit()">Quitter</button>
</body></html>"""


class WindowApi:
    def quit(self):
        os._exit(0)


def open_window(url=None, page=None):
    import webview

    if page is not None:
        webview.create_window(APP_NAME, html=page, width=760, height=520, js_api=WindowApi())
    else:
        webview.create_window(APP_NAME, url, width=1280, height=860, min_size=(800, 600))
    webview.start()


def free_port(kind=socket.SOCK_STREAM):
    with socket.socket(socket.AF_INET, kind) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def smoke_test():
    """Démarre les serveurs sans fenêtre dans un dossier temporaire et vérifie que l'interface est servie."""
    import mini_osc

    data_dir = tempfile.mkdtemp(prefix="mini-osc-smoke-")
    with open(os.path.join(resource_dir(), "config.default.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    cfg["osc_server"]["listen_port"] = free_port(socket.SOCK_DGRAM)
    cfg["flask_server"]["port"] = free_port()
    with open(os.path.join(data_dir, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f)
    mini_osc.set_data_dir(data_dir)

    errors = []
    start_engine(errors)
    url = window_url(cfg["flask_server"])
    problem = wait_until_ready(url, errors)
    if problem is None:
        for path in ("", "vendor/bulma.min.css", "vendor/fontawesome-all.min.js"):
            try:
                with urllib.request.urlopen(url + path, timeout=5) as resp:
                    status = resp.status
            except Exception as e:
                status = e
            if status != 200:
                problem = f"GET /{path} -> {status}"
                break
    print("SMOKE TEST OK" if problem is None else f"SMOKE TEST FAILED: {problem}", flush=True)
    shutil.rmtree(data_dir, ignore_errors=True)
    os._exit(0 if problem is None else 1)


def parse_args(argv):
    parser = argparse.ArgumentParser(prog=APP_NAME)
    parser.add_argument("--wait-lock", action="store_true", help="utilisé par le Restart : attendre la fin de l'instance précédente")
    parser.add_argument("--smoke-test", action="store_true", help="démarrer sans fenêtre, vérifier l'interface, puis quitter")
    # Le Finder peut ajouter -psn_XXX sur macOS : on ignore les arguments inconnus
    args, _unknown = parser.parse_known_args(argv)
    return args


def main(argv=None):
    args = parse_args(sys.argv[1:] if argv is None else argv)
    if args.smoke_test:
        smoke_test()

    import mini_osc

    data_dir = default_data_dir()
    mini_osc.set_data_dir(data_dir)
    redirect_console(data_dir)
    config_path = ensure_config(data_dir, os.path.join(resource_dir(), "config.default.json"))

    try:
        flask_cfg = mini_osc.load_config(config_path)["flask_server"]
    except mini_osc.ConfigError as e:
        open_window(page=error_html(str(e), config_path, config_problem=True))
        os._exit(1)

    errors = []
    start_engine(errors)
    url = window_url(flask_cfg)
    problem = wait_until_ready(url, errors)
    if problem is None:
        open_window(url=url)
    else:
        config_problem = bool(errors) and isinstance(errors[0], mini_osc.ConfigError)
        open_window(page=error_html(problem, config_path, config_problem))
    # Fenêtre fermée : on arrête tout (les threads serveurs sont daemon, les ports sont libérés)
    os._exit(0)


if __name__ == "__main__":
    main()
