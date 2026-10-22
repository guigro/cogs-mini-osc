"""Destination Multiball : pilote un mur Multiball (LYMB.iO) via son API cloud.

COGS envoie <préfixe>/<action> en OSC (start, switch, play, stop, status). Chaque action tourne
dans son propre thread pour ne jamais bloquer le serveur OSC. Le jeton n'est jamais journalisé.

Ce module ne dépend pas de mini_osc : la fonction de log et l'envoi OSC lui sont injectés.
"""
import copy
import json
import threading

import requests

DEFAULT_BASE_URL = "https://multiball-admin.net/api/v1.0"
REQUEST_TIMEOUT = 10  # secondes ; le cloud est plus lent que le réseau local
DEFAULT_START_DELAY = 3.0
MAX_START_DELAY = 60.0
ACTIONS = ("start", "switch", "play", "stop", "status")
LOG_BODY_MAX = 300


class ActionError(Exception):
    """Action impossible : le message est montré tel quel dans les logs et renvoyé à COGS."""


class ApiResult:
    def __init__(self, ok, status, data, message):
        self.ok = ok
        self.status = status
        self.data = data
        self.message = message


########################################
# Helpers
########################################

def redact(text, token):
    """Remplace le jeton par *** (défense en profondeur : il ne devrait jamais être dans un message)."""
    text = str(text)
    if token and len(token) >= 4:
        text = text.replace(token, "***")
    return text


def base_url_of(target):
    return (str(target.get("base_url") or "").strip() or DEFAULT_BASE_URL).rstrip("/")


def start_delay_of(target):
    try:
        delay = float(target.get("start_delay", DEFAULT_START_DELAY))
    except (TypeError, ValueError):
        return DEFAULT_START_DELAY
    return min(max(delay, 0.0), MAX_START_DELAY)


def _message_from(data, text, status):
    if isinstance(data, dict):
        for key in ("message", "error"):
            if data.get(key):
                return str(data[key])
    elif isinstance(data, str) and data:
        return data
    text = (text or "").strip()
    return text[:200] if text else f"HTTP {status}"


def api_request(target, method, path, body=None, log=None):
    """Appel à l'API Multiball. Ne lève jamais d'exception : renvoie un ApiResult."""
    url = base_url_of(target) + path
    token = str(target.get("token") or "")
    api_key = str(target.get("api_key") or "")
    body_txt = "" if body is None else " " + json.dumps(body)

    def _log(msg, level="INFO"):
        if log:
            log(redact(msg, token), level)

    try:
        r = requests.request(method, url, json=body, auth=(api_key, token),
                             headers={"Accept": "application/json"}, timeout=REQUEST_TIMEOUT)
    except requests.Timeout:
        msg = f"No answer from the Multiball API after {REQUEST_TIMEOUT} s"
        _log(f"[MULTIBALL] {method} {url}{body_txt} -> {msg}", "ERROR")
        return ApiResult(False, None, None, msg)
    except Exception as e:
        msg = redact(f"Network error: {e}", token)
        _log(f"[MULTIBALL] {method} {url}{body_txt} -> {msg}", "ERROR")
        return ApiResult(False, None, None, msg)

    text = r.text or ""
    try:
        data = r.json()
    except ValueError:
        data = None
    ok = 200 <= r.status_code < 300
    message = redact(_message_from(data, text, r.status_code), token)
    _log(f"[MULTIBALL] {method} {url}{body_txt} -> {r.status_code} {text[:LOG_BODY_MAX]}",
         "INFO" if ok else "ERROR")
    return ApiResult(ok, r.status_code, data, message)


def _ok_message(res, default):
    """Message de l'API si elle en donne un, sinon un texte par défaut."""
    if isinstance(res.data, dict) and res.data.get("message"):
        return str(res.data["message"])
    return default


def _arg_text(args, i):
    if i < len(args) and args[i] is not None:
        s = str(args[i]).strip()
        return s or None
    return None


def _number(value, label):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ActionError(f"Invalid {label} '{value}': a number is expected")


########################################
# Contrôleur des actions
########################################

class Controller:
    def __init__(self, log=None, send_osc=None):
        self._log = log or (lambda msg, level="INFO": None)
        self._send_osc = send_osc
        self._states = {}
        self._lock = threading.Lock()

    def log(self, msg, level="INFO", token=""):
        self._log(redact(msg, token), level)

    def state(self, target):
        """Mémoire par mur : dernier jeu chargé, dernier jeu lancé, séquence start en attente."""
        key = (base_url_of(target), str(target.get("court_id") or ""))
        with self._lock:
            return self._states.setdefault(key, {"last_loaded": None, "last_started": None, "pending": None})

    def dispatch(self, target, sub_address, args, response_cfg=None):
        """Lance l'action dans un thread et rend la main tout de suite."""
        t = threading.Thread(target=self.handle, args=(dict(target), sub_address, list(args), response_cfg),
                             daemon=True, name="multiball")
        t.start()
        return t

    def handle(self, target, sub_address, args, response_cfg=None):
        """Exécute une action (bloquant). Renvoie (ok, valeurs du retour OSC)."""
        token = str(target.get("token") or "")
        raw = (sub_address or "").strip("/")
        action = raw.lower()
        label = action
        try:
            if not action:
                raise ActionError("No action after the prefix: use start, switch, play, stop or status")
            if action not in ACTIONS:
                raise ActionError(f"Unknown action '{raw}': use start, switch, play, stop or status")
            missing = [f for f in ("api_key", "token", "court_id") if not str(target.get(f) or "").strip()]
            if missing:
                raise ActionError("Incomplete Multiball connection, missing: " + ", ".join(missing))
            values = getattr(self, "_do_" + action)(target, args)
        except ActionError as e:
            msg = redact(str(e), token)
            label = action if action in ACTIONS else raw
            self.log(f"[MULTIBALL] {label or '(no action)'} failed: {msg}", "ERROR", token)
            self._feedback(response_cfg, [label, 0, msg], token)
            return False, [label, 0, msg]
        except Exception as e:  # ne jamais laisser mourir le thread en silence
            msg = redact(f"Unexpected error: {e}", token)
            self.log(f"[MULTIBALL] {label} failed: {msg}", "ERROR", token)
            self._feedback(response_cfg, [label, 0, msg], token)
            return False, [label, 0, msg]

        out = [action, 1] + [str(v) for v in values]
        summary = " | ".join(str(v) for v in values if str(v)) or "-"
        self.log(f"[MULTIBALL] {action} OK: {summary}", "INFO", token)
        self._feedback(response_cfg, out, token)
        return True, out

    # ---------- appels ----------

    def _api(self, target, method, path, body=None):
        return api_request(target, method, path, body, log=self._log)

    def _call(self, target, method, path, body, what):
        res = self._api(target, method, path, body)
        if not res.ok:
            raise ActionError(f"{what} failed: {res.message}")
        return res

    def _court_path(self, target, suffix=""):
        return f"/courts/{target['court_id']}{suffix}"

    def _current_game(self, target):
        res = self._api(target, "GET", self._court_path(target))
        if not res.ok:
            raise ActionError(f"Could not read the court status: {res.message}")
        game = res.data.get("game") if isinstance(res.data, dict) else None
        return (game or {}).get("id") if isinstance(game, dict) else None

    def _cancel_pending(self, state):
        with self._lock:
            if state["pending"] is not None:
                state["pending"].set()
                state["pending"] = None

    def _start_game(self, target, game_id):
        return self._api(target, "PUT", f"/games/{game_id}/start", {"courtId": target["court_id"]})

    # ---------- actions ----------

    def _do_start(self, target, args):
        game_id = _arg_text(args, 0)
        if not game_id:
            raise ActionError("Missing gameId: /start <gameId> [duration] [difficulty]")
        duration = None
        d = _arg_text(args, 1)
        if d is not None:
            seconds = _number(d, "duration")
            duration = int(round(seconds)) if seconds > 0 else None
        difficulty = None
        v = _arg_text(args, 2)
        if v is not None:
            difficulty = _number(v, "difficulty")
            if not 0 <= difficulty <= 1:
                raise ActionError(f"Invalid difficulty {v}: it must be between 0 and 1")

        state = self.state(target)
        cancel = threading.Event()
        self._cancel_pending(state)
        with self._lock:
            state["pending"] = cancel
        try:
            self._call(target, "PUT", self._court_path(target, "/switchGame"),
                       {"gameId": game_id, "versionNumber": None}, "Switch game")
            state["last_loaded"] = game_id

            values = {}
            if duration is not None:
                values["duration"] = duration
            if difficulty is not None:
                values["difficulty"] = difficulty
            if values:
                self._call(target, "PUT", self._court_path(target, "/setConfiguration"),
                           {"gameId": game_id, "values": values}, "Set configuration")

            delay = start_delay_of(target)
            if cancel.wait(delay):
                raise ActionError("Cancelled before the game started (a newer command arrived)")
            res = self._start_game(target, game_id)
            if not res.ok:
                self.log(f"[MULTIBALL] Start failed ({res.message}), retrying once in {delay:g} s", "WARNING",
                         str(target.get("token") or ""))
                if cancel.wait(delay):
                    raise ActionError("Cancelled before the game started (a newer command arrived)")
                res = self._start_game(target, game_id)
                if not res.ok:
                    raise ActionError(f"Start failed: {res.message}")
            state["last_started"] = game_id
            return [_ok_message(res, "Game started")]
        finally:
            with self._lock:
                if state["pending"] is cancel:
                    state["pending"] = None

    def _do_switch(self, target, args):
        game_id = _arg_text(args, 0)
        if not game_id:
            raise ActionError("Missing gameId: /switch <gameId>")
        state = self.state(target)
        self._cancel_pending(state)
        res = self._call(target, "PUT", self._court_path(target, "/switchGame"),
                         {"gameId": game_id, "versionNumber": None}, "Switch game")
        state["last_loaded"] = game_id
        return [_ok_message(res, "Game loaded")]

    def _do_play(self, target, args):
        state = self.state(target)
        game_id = _arg_text(args, 0) or state["last_loaded"] or self._current_game(target)
        if not game_id:
            raise ActionError("No game to start: give a gameId or load a game first")
        res = self._start_game(target, game_id)
        if not res.ok:
            raise ActionError(f"Start failed: {res.message}")
        state["last_started"] = game_id
        return [_ok_message(res, "Game started")]

    def _do_stop(self, target, args):
        state = self.state(target)
        self._cancel_pending(state)
        game_id = _arg_text(args, 0) or state["last_started"] or self._current_game(target)
        if not game_id:
            raise ActionError("No game to stop: no gameId given and no game running on the court")
        res = self._call(target, "PUT", f"/games/{game_id}/stop/", {"courtId": target["court_id"]}, "Stop")
        return [_ok_message(res, "Game stopped")]

    def _do_status(self, target, args):
        res = self._call(target, "GET", self._court_path(target), None, "Status")
        data = res.data if isinstance(res.data, dict) else {}
        game = data.get("game") if isinstance(data.get("game"), dict) else {}
        status = str(data.get("status") or "")
        name = str(game.get("dispName") or game.get("name") or "")
        game_id = str(game.get("id") or "")
        self.log(f"[MULTIBALL] Court '{data.get('title', '')}': status={status or '?'}, "
                 f"game={name or 'none'}{' (' + game_id + ')' if game_id else ''}")
        return [status, name, game_id]

    # ---------- retour vers COGS ----------

    def _feedback(self, resp_cfg, values, token=""):
        if not resp_cfg or not resp_cfg.get("enabled"):
            return
        ip, port, address = resp_cfg.get("ip"), resp_cfg.get("port"), resp_cfg.get("address")
        if not ip or not port or not address:
            self.log("[MULTIBALL] OSC feedback is enabled but its IP, port or address is missing: nothing sent",
                     "WARNING", token)
            return
        if not self._send_osc:
            return
        try:
            self._send_osc(ip, int(port), address, values)
        except Exception as e:
            self.log(f"[MULTIBALL] Could not send the OSC feedback to {ip}:{port}: {e}", "ERROR", token)


########################################
# Lecture pour le bouton « Test and list »
########################################

def list_resources(what, target, log=None):
    """Lecture seule : terrains (what="courts") ou jeux d'un terrain (what="games")."""
    path = "/courts" if what == "courts" else f"/courts/{target.get('court_id')}/games"
    res = api_request(target, "GET", path, log=log)
    if not res.ok:
        return {"ok": False, "status": res.status, "error": res.message}
    results = res.data.get("results") if isinstance(res.data, dict) else None
    if not isinstance(results, list):
        return {"ok": False, "status": res.status, "error": "Unexpected answer from the Multiball API"}
    items = [r for r in results if isinstance(r, dict)]
    if what == "courts":
        return {"ok": True, "courts": [{"id": str(r.get("id", "")), "title": r.get("title", ""),
                                        "description": r.get("description", "")} for r in items]}
    return {"ok": True, "games": [{"id": str(r.get("id", "")), "name": r.get("name", ""),
                                   "dispName": r.get("dispName", ""), "versions": r.get("versions") or []}
                                  for r in items]}


########################################
# Configuration et secrets
########################################

def is_multiball(conn):
    return (isinstance(conn, dict) and isinstance(conn.get("to"), dict)
            and conn["to"].get("protocol") == "multiball")


def normalize_config(cfg):
    """Complète base_url et start_delay des connexions Multiball (appelé par validate_config)."""
    for conn in cfg.get("connections", []):
        if is_multiball(conn):
            conn["to"].setdefault("base_url", DEFAULT_BASE_URL)
            conn["to"].setdefault("start_delay", DEFAULT_START_DELAY)
            conn["to"].pop("token_set", None)
    return cfg


def has_tokens(cfg):
    return any(is_multiball(c) and c["to"].get("token") for c in cfg.get("connections", []))


def mask_config(cfg):
    """Copie pour l'interface : jeton vidé, token_set indique s'il y en a un."""
    out = copy.deepcopy(cfg)
    for conn in out.get("connections", []):
        if is_multiball(conn):
            conn["to"]["token_set"] = bool(conn["to"].get("token"))
            conn["to"]["token"] = ""
    return out


def strip_tokens(cfg):
    """Copie pour l'export : jetons retirés."""
    out = copy.deepcopy(cfg)
    for conn in out.get("connections", []):
        if is_multiball(conn):
            conn["to"]["token"] = ""
            conn["to"].pop("token_set", None)
    return out


def clean_connection(conn, previous=None):
    """Avant enregistrement : retire token_set ; un jeton vide garde celui de la connexion précédente."""
    if isinstance(conn.get("to"), dict):
        conn["to"].pop("token_set", None)
    if is_multiball(conn) and not conn["to"].get("token") and is_multiball(previous or {}):
        if previous["to"].get("token"):
            conn["to"]["token"] = previous["to"]["token"]
    return conn


def restore_tokens(new_cfg, old_cfg):
    """À l'import : une connexion Multiball sans jeton reprend celui de l'ancienne config (même clé API)."""
    known = {}
    for conn in (old_cfg or {}).get("connections", []):
        if is_multiball(conn) and conn["to"].get("token") and conn["to"].get("api_key"):
            known.setdefault(conn["to"]["api_key"], conn["to"]["token"])
    restored = 0
    for conn in new_cfg.get("connections", []):
        if is_multiball(conn) and not conn["to"].get("token") and conn["to"].get("api_key") in known:
            conn["to"]["token"] = known[conn["to"]["api_key"]]
            restored += 1
    return restored
