"""Destination Multiball : tout est simulé, aucun appel au vrai cloud."""
import base64
import json
import os
import threading
import time

import pytest
import requests

import mini_osc
import multiball

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BASE = "https://example.test/api/v1.0"
TOKEN = "SECRET-TOKEN-XYZ-123"
KEY = "API-KEY-456"
COURT = "2ea7a1479cf93f8182dc8d7e"
GAME = "288b6480c62001f919d2736e"


class FakeResponse:
    def __init__(self, status=200, data=None, text=None):
        self.status_code = status
        self._data = data
        self.text = text if text is not None else ("" if data is None else json.dumps(data))

    def json(self):
        if self._data is None:
            raise ValueError("no json")
        return self._data


class FakeApi:
    """Remplace requests.request. handler(method, path, body) -> FakeResponse (ou lève)."""

    def __init__(self):
        self.calls = []
        self.handler = lambda method, path, body: FakeResponse(200, {"message": "OK"})

    def __call__(self, method, url, **kw):
        path = url[len(BASE):] if url.startswith(BASE) else url
        self.calls.append({"method": method, "url": url, "path": path, "body": kw.get("json"),
                           "auth": kw.get("auth"), "timeout": kw.get("timeout"), "time": time.monotonic()})
        return self.handler(method, path, kw.get("json"))

    def paths(self):
        return [(c["method"], c["path"]) for c in self.calls]


@pytest.fixture
def api(monkeypatch):
    fake = FakeApi()
    monkeypatch.setattr(multiball.requests, "request", fake)
    return fake


@pytest.fixture
def target():
    return {"type": "multiball", "base_url": BASE, "api_key": KEY, "token": TOKEN,
            "court_id": COURT, "start_delay": 0}


class Recorder:
    def __init__(self):
        self.logs = []
        self.sent = []

    def log(self, msg, level="INFO"):
        self.logs.append((level, msg))

    def send(self, ip, port, address, args):
        self.sent.append((ip, port, address, args))

    def text(self):
        return "\n".join(m for _, m in self.logs)


@pytest.fixture
def rec():
    return Recorder()


@pytest.fixture
def ctrl(rec):
    return multiball.Controller(log=rec.log, send_osc=rec.send)


FEEDBACK = {"enabled": True, "ip": "127.0.0.1", "port": 12097, "address": "/mb/result"}


# ---------- construction des requêtes ----------

def test_requests_are_built_as_the_api_expects(api, ctrl, target):
    ctrl.handle(target, "/start", [GAME, 300, 0.5])
    ctrl.handle(target, "/stop", [])
    ctrl.handle(target, "/status", [])
    assert api.paths() == [
        ("PUT", f"/courts/{COURT}/switchGame"),
        ("PUT", f"/courts/{COURT}/setConfiguration"),
        ("PUT", f"/games/{GAME}/start"),
        ("PUT", f"/games/{GAME}/stop/"),
        ("GET", f"/courts/{COURT}"),
    ]
    bodies = [c["body"] for c in api.calls]
    assert bodies[0] == {"gameId": GAME, "versionNumber": None}
    assert bodies[1] == {"gameId": GAME, "values": {"duration": 300, "difficulty": 0.5}}
    assert bodies[2] == {"courtId": COURT}
    assert bodies[3] == {"courtId": COURT}
    assert bodies[4] is None
    assert all(c["timeout"] == 10 for c in api.calls)
    assert all(c["auth"] == (KEY, TOKEN) for c in api.calls)


def test_basic_header_is_key_then_token(api, ctrl, target):
    ctrl.handle(target, "/status", [])
    auth = api.calls[0]["auth"]
    prepared = requests.Request("GET", BASE, auth=auth).prepare()
    expected = "Basic " + base64.b64encode(f"{KEY}:{TOKEN}".encode()).decode()
    assert prepared.headers["Authorization"] == expected


def test_default_base_url_and_trailing_slash(api, ctrl, target):
    target.pop("base_url")
    ctrl.handle(target, "/status", [])
    assert api.calls[0]["url"] == f"https://multiball-admin.net/api/v1.0/courts/{COURT}"
    target["base_url"] = BASE + "/"
    ctrl.handle(target, "/status", [])
    assert api.calls[1]["url"] == f"{BASE}/courts/{COURT}"


# ---------- séquence start ----------

def test_start_without_configuration(api, ctrl, target):
    ok, out = ctrl.handle(target, "/start", [GAME])
    assert ok and out[:2] == ["start", 1]
    assert ("PUT", f"/courts/{COURT}/setConfiguration") not in api.paths()
    assert api.paths() == [("PUT", f"/courts/{COURT}/switchGame"), ("PUT", f"/games/{GAME}/start")]


@pytest.mark.parametrize("args,values", [
    ([GAME, 120], {"duration": 120}),
    ([GAME, 0, 0.7], {"difficulty": 0.7}),
    ([GAME, "", 0], {"difficulty": 0.0}),
    ([GAME, 90.4, 1], {"duration": 90, "difficulty": 1.0}),
])
def test_start_with_configuration(api, ctrl, target, args, values):
    ok, _ = ctrl.handle(target, "/start", args)
    assert ok
    conf = [c for c in api.calls if c["path"].endswith("/setConfiguration")]
    assert len(conf) == 1 and conf[0]["body"] == {"gameId": GAME, "values": values}
    assert api.paths()[-1] == ("PUT", f"/games/{GAME}/start")


def test_start_waits_the_start_delay(api, ctrl, target):
    target["start_delay"] = 0.3
    ctrl.handle(target, "/start", [GAME])
    switch, start = api.calls
    assert start["time"] - switch["time"] >= 0.29


def test_start_retries_once(api, ctrl, rec, target):
    attempts = []

    def handler(method, path, body):
        if path.endswith("/start"):
            attempts.append(1)
            return FakeResponse(400, {"message": "Game not ready"}) if len(attempts) == 1 \
                else FakeResponse(200, {"message": "Game started"})
        return FakeResponse(200, {"message": "Switched"})
    api.handler = handler
    ok, out = ctrl.handle(target, "/start", [GAME], FEEDBACK)
    assert ok and len(attempts) == 2
    assert rec.sent[-1] == ("127.0.0.1", 12097, "/mb/result", ["start", 1, "Game started"])


def test_start_gives_up_after_one_retry(api, ctrl, rec, target):
    api.handler = lambda m, p, b: FakeResponse(400, {"message": "Game not ready"}) if p.endswith("/start") \
        else FakeResponse(200, {})
    ok, out = ctrl.handle(target, "/start", [GAME], FEEDBACK)
    assert not ok
    assert [p for _, p in api.paths()].count(f"/games/{GAME}/start") == 2
    assert rec.sent[-1][3] == ["start", 0, "Start failed: Game not ready"]


def test_start_stops_when_switch_fails(api, ctrl, rec, target):
    api.handler = lambda m, p, b: FakeResponse(401, {"message": "Invalid api key!"})
    ok, out = ctrl.handle(target, "/start", [GAME], FEEDBACK)
    assert not ok and len(api.calls) == 1
    assert out == ["start", 0, "Switch game failed: Invalid api key!"]
    assert "Invalid api key!" in rec.text()


def test_dispatch_returns_immediately(api, ctrl, target):
    target["start_delay"] = 0.5
    t0 = time.monotonic()
    thread = ctrl.dispatch(target, "/start", [GAME])
    assert time.monotonic() - t0 < 0.1
    thread.join(3)
    assert not thread.is_alive()
    assert api.paths()[-1] == ("PUT", f"/games/{GAME}/start")


def test_stop_cancels_a_pending_start(api, ctrl, target):
    target["start_delay"] = 1.0
    thread = ctrl.dispatch(target, "/start", [GAME])
    time.sleep(0.15)
    ok, _ = ctrl.handle(target, "/stop", [GAME])
    thread.join(3)
    assert ok
    assert ("PUT", f"/games/{GAME}/start") not in api.paths()


# ---------- actions unitaires et mémoire ----------

def test_stop_uses_the_last_started_game(api, ctrl, target):
    ctrl.handle(target, "/start", ["GAME-A"])
    ctrl.handle(target, "/stop", [])
    assert api.paths()[-1] == ("PUT", "/games/GAME-A/stop/")


def test_memory_is_per_court(api, ctrl, target):
    ctrl.handle(target, "/start", ["GAME-A"])
    other = dict(target, court_id="OTHER")
    api.handler = lambda m, p, b: FakeResponse(200, {"status": "online", "game": {}})
    ok, out = ctrl.handle(other, "/stop", [])
    assert not ok and "No game to stop" in out[2]


def test_stop_without_memory_reads_the_court(api, ctrl, target):
    api.handler = lambda m, p, b: FakeResponse(200, {"status": "online", "game": {"id": "RUNNING", "name": "X"}}) \
        if m == "GET" else FakeResponse(200, {"message": "Stopped"})
    ok, out = ctrl.handle(target, "/stop", [])
    assert ok
    assert api.paths() == [("GET", f"/courts/{COURT}"), ("PUT", "/games/RUNNING/stop/")]


def test_switch_then_play_without_game_id(api, ctrl, target):
    ctrl.handle(target, "/switch", ["GAME-B"])
    ctrl.handle(target, "/play", [])
    assert api.paths() == [("PUT", f"/courts/{COURT}/switchGame"), ("PUT", "/games/GAME-B/start")]
    ctrl.handle(target, "/stop", [])
    assert api.paths()[-1] == ("PUT", "/games/GAME-B/stop/")


def test_play_with_game_id(api, ctrl, target):
    ok, _ = ctrl.handle(target, "/PLAY", ["GAME-C"])
    assert ok and api.paths() == [("PUT", "/games/GAME-C/start")]


def test_status_feedback(api, ctrl, rec, target):
    api.handler = lambda m, p, b: FakeResponse(200, {"title": "Eclipsium-Nantes", "status": "online",
                                                     "game": {"id": GAME, "name": "shooting",
                                                              "dispName": "Eclipsium Drone Defense"}})
    ok, out = ctrl.handle(target, "/status", [], FEEDBACK)
    assert ok
    assert rec.sent == [("127.0.0.1", 12097, "/mb/result",
                         ["status", 1, "online", "Eclipsium Drone Defense", GAME])]
    assert "status=online" in rec.text()


@pytest.mark.parametrize("sub,args,expected", [
    ("/foo", [GAME], "Unknown action 'foo'"),
    ("", [], "No action after the prefix"),
    ("/start/now", [GAME], "Unknown action"),
    ("/switch", [], "Missing gameId"),
    ("/start", [], "Missing gameId"),
    ("/start", [GAME, "abc"], "Invalid duration"),
    ("/start", [GAME, 60, 2], "between 0 and 1"),
])
def test_invalid_messages_send_nothing(api, ctrl, rec, target, sub, args, expected):
    ok, out = ctrl.handle(target, sub, args, FEEDBACK)
    assert not ok and api.calls == []
    assert expected in out[2]
    assert expected in rec.text()
    assert rec.sent[-1][3][1] == 0


# ---------- asset flips ----------

TENNIS = "TENNIS-GAME-ID"
FLIP = "4a9e69b06468a52f27380935"
GAMES = {"count": 2, "results": [
    {"id": GAME, "name": "shooting", "dispName": "Eclipsium Drone Defense", "versions": ["0.3.7"]},
    {"id": TENNIS, "name": "tennis", "dispName": "Tennis", "versions": ["1.0"],
     "assetFlips": [{"name": "Padel", "flipId": FLIP}, {"name": "Halloween", "flipId": "FLIP-HALLOWEEN"}]},
]}


BALLOON = "dd049d96a5892a438c97ab5c"
COURT_STATUS = {"title": "Eclipsium-Nantes", "status": "online",
                "game": {"id": BALLOON, "name": "com.funwithballs.balloon", "dispName": "Balloon Mania"}}


def games_api(api, games=GAMES, court=COURT_STATUS):
    def handler(m, p, b):
        if (m, p) == ("GET", f"/courts/{COURT}/games"):
            return FakeResponse(200, games)
        if (m, p) == ("GET", f"/courts/{COURT}"):
            return FakeResponse(200, court)
        return FakeResponse(200, {"message": "OK"})
    api.handler = handler


def test_flip_sends_only_the_flip_id(api, ctrl, rec, target):
    games_api(api)
    ok, out = ctrl.handle(target, "/flip", [FLIP], FEEDBACK)
    assert ok
    assert api.calls[0]["path"] == f"/courts/{COURT}/switchGame"
    assert api.calls[0]["body"] == {"flipId": FLIP}
    assert "gameId" not in api.calls[0]["body"]
    assert api.paths()[1] == ("GET", f"/courts/{COURT}/games")
    assert rec.sent[-1][3][:2] == ["flip", 1]
    assert "based on 'Tennis'" in rec.text()


def test_flip_then_play_and_stop_use_the_base_game(api, ctrl, target):
    games_api(api)
    ctrl.handle(target, "/flip", [FLIP])
    ctrl.handle(target, "/play", [])
    ctrl.handle(target, "/stop", [])
    assert api.paths()[-2:] == [("PUT", f"/games/{TENNIS}/start"), ("PUT", f"/games/{TENNIS}/stop/")]


def test_flip_games_are_cached(api, ctrl, target):
    games_api(api)
    ctrl.handle(target, "/flip", [FLIP])
    ctrl.handle(target, "/flip", ["FLIP-HALLOWEEN"])
    assert [p for m, p in api.paths() if m == "GET"] == [f"/courts/{COURT}/games"]


def test_flip_created_later_is_found(api, ctrl, target):
    games_api(api, {"count": 0, "results": []})
    ctrl.handle(target, "/flip", [FLIP])
    games_api(api)
    ctrl.handle(target, "/flip", [FLIP])
    ctrl.handle(target, "/play", [])
    assert api.paths()[-1] == ("PUT", f"/games/{TENNIS}/start")


def test_unknown_flip_is_loaded_but_play_needs_a_game_id(api, ctrl, rec, target):
    games_api(api, court={"status": "online", "game": None})
    ctrl.handle(target, "/switch", [GAME])
    ok, out = ctrl.handle(target, "/flip", ["NOT-A-FLIP"], FEEDBACK)
    assert ok and api.calls[1]["body"] == {"flipId": "NOT-A-FLIP"}
    assert any(level == "WARNING" and "NOT-A-FLIP was not found" in m and "/play needs" in m
               for level, m in rec.logs)
    calls = len(api.calls)
    ok, out = ctrl.handle(target, "/play", [])
    assert not ok and "use /play <gameId>" in out[2] and len(api.calls) == calls
    ok, _ = ctrl.handle(target, "/play", [TENNIS])
    assert ok and api.paths()[-1] == ("PUT", f"/games/{TENNIS}/start")
    ctrl.handle(target, "/switch", [GAME])
    ok, _ = ctrl.handle(target, "/play", [])
    assert ok and api.paths()[-1] == ("PUT", f"/games/{GAME}/start")


def test_flip_when_games_cannot_be_read(api, ctrl, rec, target):
    api.handler = lambda m, p, b: FakeResponse(500, {"message": "boom"}) if m == "GET" \
        else FakeResponse(200, {"message": "OK"})
    ok, _ = ctrl.handle(target, "/flip", [FLIP])
    assert ok
    ok, out = ctrl.handle(target, "/play", [])
    assert not ok and "gameId" in out[2]


def test_startflip_sequence(api, ctrl, rec, target):
    games_api(api)
    ok, out = ctrl.handle(target, "/startflip", [FLIP, "", 300, 0.5], FEEDBACK)
    assert ok and out[:2] == ["startflip", 1]
    assert api.paths() == [
        ("GET", f"/courts/{COURT}/games"),
        ("PUT", f"/courts/{COURT}/switchGame"),
        ("PUT", f"/courts/{COURT}/setConfiguration"),
        ("PUT", f"/games/{TENNIS}/start"),
    ]
    bodies = [c["body"] for c in api.calls]
    assert bodies[1] == {"flipId": FLIP}
    assert bodies[2] == {"gameId": TENNIS, "values": {"duration": 300, "difficulty": 0.5}}
    ctrl.handle(target, "/stop", [])
    assert api.paths()[-1] == ("PUT", f"/games/{TENNIS}/stop/")


def test_startflip_retries_once(api, ctrl, target):
    attempts = []

    def handler(method, path, body):
        if method == "GET":
            return FakeResponse(200, GAMES)
        if path.endswith("/start"):
            attempts.append(1)
            return FakeResponse(400, {"message": "Game not ready"}) if len(attempts) == 1 \
                else FakeResponse(200, {"message": "Game started"})
        return FakeResponse(200, {})
    api.handler = handler
    ok, _ = ctrl.handle(target, "/startflip", [FLIP])
    assert ok and len(attempts) == 2
    assert ("PUT", f"/courts/{COURT}/setConfiguration") not in api.paths()


def test_startflip_unknown_flip_everywhere_loads_but_does_not_start(api, ctrl, rec, target):
    games_api(api, court={"status": "online", "game": None})
    ok, out = ctrl.handle(target, "/startflip", ["NOT-A-FLIP"], FEEDBACK)
    assert not ok and "loaded but not started" in out[2]
    assert [c for c in api.calls if c["method"] == "PUT"][0]["body"] == {"flipId": "NOT-A-FLIP"}
    assert not any(p.endswith("/start") for _, p in api.paths())
    assert rec.sent[-1][3][:2] == ["startflip", 0]


def test_flip_with_base_game_id_skips_the_list(api, ctrl, target):
    games_api(api)
    ok, _ = ctrl.handle(target, "/flip", ["FLIP-BALLOON", BALLOON])
    assert ok and api.paths() == [("PUT", f"/courts/{COURT}/switchGame")]
    ctrl.handle(target, "/play", [])
    ctrl.handle(target, "/stop", [])
    assert api.paths()[-2:] == [("PUT", f"/games/{BALLOON}/start"), ("PUT", f"/games/{BALLOON}/stop/")]
    ctrl.handle(target, "/flip", ["FLIP-BALLOON"])
    assert [m for m, _ in api.paths()].count("GET") == 0


def test_startflip_with_base_game_id(api, ctrl, target):
    games_api(api)
    ok, _ = ctrl.handle(target, "/startflip", ["FLIP-BALLOON", BALLOON, 120])
    assert ok and api.paths() == [
        ("PUT", f"/courts/{COURT}/switchGame"),
        ("PUT", f"/courts/{COURT}/setConfiguration"),
        ("PUT", f"/games/{BALLOON}/start"),
    ]
    assert api.calls[0]["body"] == {"flipId": "FLIP-BALLOON"}
    assert api.calls[1]["body"] == {"gameId": BALLOON, "values": {"duration": 120}}


def test_flip_missing_from_the_list_uses_the_court_game(api, ctrl, rec, target):
    games_api(api)
    ok, _ = ctrl.handle(target, "/flip", ["FLIP-BALLOON"])
    assert ok
    assert api.paths() == [("PUT", f"/courts/{COURT}/switchGame"), ("GET", f"/courts/{COURT}/games"),
                           ("GET", f"/courts/{COURT}")]
    assert "base game read on the court, 'Balloon Mania'" in rec.text()
    ctrl.handle(target, "/play", [])
    assert api.paths()[-1] == ("PUT", f"/games/{BALLOON}/start")


def test_startflip_missing_from_the_list_reads_the_court_after_loading(api, ctrl, target):
    games_api(api)
    target["start_delay"] = 0.2
    ok, _ = ctrl.handle(target, "/startflip", ["FLIP-BALLOON", "", 0, 0.3])
    assert ok and api.paths() == [
        ("GET", f"/courts/{COURT}/games"),
        ("PUT", f"/courts/{COURT}/switchGame"),
        ("GET", f"/courts/{COURT}"),
        ("PUT", f"/courts/{COURT}/setConfiguration"),
        ("PUT", f"/games/{BALLOON}/start"),
    ]
    switch, court = api.calls[1], api.calls[2]
    assert court["time"] - switch["time"] >= 0.19
    assert api.calls[3]["body"] == {"gameId": BALLOON, "values": {"difficulty": 0.3}}


def test_play_during_the_flip_court_wait_needs_a_game_id(api, ctrl, target):
    games_api(api)
    target["start_delay"] = 0.5
    ctrl.handle(target, "/switch", [GAME])
    thread = ctrl.dispatch(target, "/flip", ["FLIP-BALLOON"])
    time.sleep(0.15)
    ok, out = ctrl.handle(target, "/play", [])
    assert not ok and "use /play <gameId>" in out[2]
    thread.join(3)
    ok, _ = ctrl.handle(target, "/play", [])
    assert ok and api.paths()[-1] == ("PUT", f"/games/{BALLOON}/start")


def test_stop_cancels_a_pending_startflip(api, ctrl, target):
    games_api(api)
    target["start_delay"] = 1.0
    thread = ctrl.dispatch(target, "/startflip", [FLIP])
    time.sleep(0.15)
    ctrl.handle(target, "/stop", [])
    thread.join(3)
    assert ("PUT", f"/games/{TENNIS}/start") not in api.paths()


@pytest.mark.parametrize("sub,args,expected", [
    ("/flip", [], "Missing flipId"),
    ("/startflip", [], "Missing flipId"),
    ("/startflip", [FLIP, "", "abc"], "Invalid duration"),
    ("/startflip", [FLIP, "", 0, 3], "between 0 and 1"),
    ("/startflip", [FLIP, 300], "not the number 300"),
    ("/flip", [FLIP, 2], "base gameId"),
])
def test_invalid_flip_messages_send_nothing(api, ctrl, target, sub, args, expected):
    ok, out = ctrl.handle(target, sub, args)
    assert not ok and api.calls == [] and expected in out[2]


def test_routing_prefix_to_flip(routing):
    mini_osc.handle_osc_in_message("/mb/flip", (FLIP,))
    mini_osc.handle_osc_in_message("/mb/startflip", (FLIP, 300))
    assert [(sub, args) for _, sub, args, _ in routing["mb"]] == [("/flip", [FLIP]), ("/startflip", [FLIP, 300])]


def test_incomplete_connection_sends_nothing(api, ctrl, target):
    target["token"] = ""
    ok, out = ctrl.handle(target, "/status", [])
    assert not ok and api.calls == [] and "token" in out[2]


def test_no_feedback_when_disabled_or_incomplete(api, ctrl, rec, target):
    ctrl.handle(target, "/status", [], {"enabled": False, "ip": "1.2.3.4", "port": 1, "address": "/x"})
    ctrl.handle(target, "/status", [], {"enabled": True, "ip": "", "port": 1, "address": "/x"})
    assert rec.sent == []
    assert "feedback is enabled but" in rec.text()


def test_timeout_and_non_json_answers(api, ctrl, target):
    def boom(m, p, b):
        raise requests.Timeout("slow")
    api.handler = boom
    ok, out = ctrl.handle(target, "/status", [])
    assert not ok and "after 10 s" in out[2]
    api.handler = lambda m, p, b: FakeResponse(502, None, "<html>Bad gateway</html>")
    ok, out = ctrl.handle(target, "/status", [])
    assert not ok and "Bad gateway" in out[2]


# ---------- secrets ----------

def test_token_never_in_logs(api, ctrl, rec, target):
    ctrl.handle(target, "/start", [GAME, 60, 0.5], FEEDBACK)
    api.handler = lambda m, p, b: FakeResponse(401, {"message": "Invalid api key!"})
    ctrl.handle(target, "/stop", [GAME], FEEDBACK)

    def boom(m, p, b):
        raise requests.ConnectionError(f"failed for https://{KEY}:{TOKEN}@example.test")
    api.handler = boom
    ctrl.handle(target, "/status", [], FEEDBACK)
    everything = rec.text() + json.dumps(rec.sent)
    assert TOKEN not in everything
    assert "Authorization" not in everything
    assert base64.b64encode(f"{KEY}:{TOKEN}".encode()).decode() not in everything


def test_default_config_has_no_secret():
    with open(os.path.join(ROOT, "config.default.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    assert not multiball.has_tokens(cfg)
    assert "token" not in json.dumps(cfg)


# ---------- intégration mini_osc ----------

def mb_connection(token=TOKEN, key=KEY):
    return {"name": "OSC to Multiball API", "from": {"protocol": "osc", "address_pattern": "/mb"},
            "to": {"protocol": "multiball", "base_url": BASE, "api_key": key, "token": token,
                   "court_id": COURT, "start_delay": 0},
            "response_to_osc": dict(FEEDBACK)}


TCP_MULTIBALL = {"name": "OSC to Multiball", "from": {"protocol": "osc", "address_pattern": "/multiball",
                                                      "values": ["GameID", "Level", "Difficulty"]},
                 "to": {"protocol": "tcp", "ip": "192.168.66.131", "port": 3232}}


@pytest.fixture
def routing(monkeypatch):
    cfg = mini_osc.validate_config({"osc_server": {"listen_ip": "127.0.0.1", "listen_port": 53000},
                                    "flask_server": {"ip": "127.0.0.1", "port": 5009},
                                    "connections": [TCP_MULTIBALL, mb_connection()]})
    mini_osc.expand_connections(cfg)
    seen = {"tcp": [], "mb": []}
    monkeypatch.setattr(mini_osc, "send_to_tcp", lambda t, a, args: seen["tcp"].append((a, args)))
    monkeypatch.setattr(mini_osc.multiball_controller, "dispatch",
                        lambda t, sub, args, resp=None: seen["mb"].append((t, sub, args, resp)))
    yield seen
    mini_osc.expand_connections({"connections": []})


def test_routing_keeps_the_tcp_multiball_route(routing):
    mini_osc.handle_osc_in_message("/multiball", (7, 2, 1))
    assert routing["tcp"] == [("/multiball", {"GameID": 7, "Level": 2, "Difficulty": 1})]
    assert routing["mb"] == []


def test_routing_prefix_to_multiball(routing):
    mini_osc.handle_osc_in_message("/mb/start", (GAME, 300))
    mini_osc.handle_osc_in_message("/mb", ())
    mini_osc.handle_osc_in_message("/mbx/start", (GAME,))
    assert [(sub, args) for _, sub, args, _ in routing["mb"]] == [("/start", [GAME, 300]), ("", [])]
    t, _, _, resp = routing["mb"][0]
    assert t["type"] == "multiball" and t["token"] == TOKEN and t["court_id"] == COURT
    assert resp["address"] == "/mb/result"
    assert routing["tcp"] == []


def test_real_controller_never_logs_the_token(api, monkeypatch):
    monkeypatch.setattr(mini_osc, "send_osc_message", lambda *a: None)
    mini_osc.logs.clear()
    target = dict(mb_connection()["to"], type="multiball")
    mini_osc.multiball_controller.handle(target, "/start", [GAME, 30, 0.2], FEEDBACK)
    api.handler = lambda m, p, b: FakeResponse(401, {"message": "Invalid api key!"})
    mini_osc.multiball_controller.handle(target, "/stop", [], FEEDBACK)
    joined = "\n".join(mini_osc.logs)
    assert "[MULTIBALL]" in joined and "Invalid api key!" in joined
    assert TOKEN not in joined


@pytest.fixture
def client(tmp_path):
    previous = mini_osc.DATA_DIR
    mini_osc.set_data_dir(str(tmp_path))
    cfg = {"osc_server": {"listen_ip": "127.0.0.1", "listen_port": 53000},
           "flask_server": {"ip": "127.0.0.1", "port": 5009},
           "connections": [TCP_MULTIBALL, mb_connection()]}
    (tmp_path / "config.json").write_text(json.dumps(cfg), encoding="utf-8")
    yield mini_osc.app.test_client()
    mini_osc.set_data_dir(previous)
    mini_osc.expand_connections({"connections": []})


def saved(tmp_path):
    return json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))


def test_get_config_masks_the_token(client):
    body = client.get("/get_config").get_data(as_text=True)
    assert TOKEN not in body
    to = json.loads(body)["connections"][1]["to"]
    assert to["token"] == "" and to["token_set"] is True and to["api_key"] == KEY


def test_update_with_empty_token_keeps_it(client, tmp_path):
    conn = mb_connection(token="")
    conn["to"]["token_set"] = True
    conn["to"]["court_id"] = "NEW-COURT"
    assert client.post("/update_connection", json={"index": 1, **conn}).status_code == 200
    to = saved(tmp_path)["connections"][1]["to"]
    assert to["token"] == TOKEN and to["court_id"] == "NEW-COURT" and "token_set" not in to
    # Un nouveau jeton saisi remplace l'ancien
    client.post("/update_connection", json={"index": 1, **mb_connection(token="NEW-TOKEN-0000")})
    assert saved(tmp_path)["connections"][1]["to"]["token"] == "NEW-TOKEN-0000"


def test_add_connection_accepts_multiball(client, tmp_path):
    assert client.post("/add_connection", json=mb_connection(token="OTHER-TOKEN-1111")).status_code == 200
    conns = saved(tmp_path)["connections"]
    assert len(conns) == 3 and conns[2]["to"]["protocol"] == "multiball"
    assert conns[0] == TCP_MULTIBALL


def test_export_strips_tokens_unless_asked(client, tmp_path):
    res = client.get("/export_config")
    assert res.status_code == 200 and "attachment" in res.headers["Content-Disposition"]
    assert TOKEN not in res.get_data(as_text=True)
    assert json.loads(res.data)["connections"][1]["to"]["api_key"] == KEY
    res = client.get("/export_config?include_secrets=1")
    assert TOKEN in res.get_data(as_text=True)


def test_import_keeps_the_saved_token(client, tmp_path):
    exported = json.loads(client.get("/export_config").data)
    assert client.post("/import_config", json=exported).status_code == 200
    assert saved(tmp_path)["connections"][1]["to"]["token"] == TOKEN
    assert saved(tmp_path)["connections"][0] == TCP_MULTIBALL


def test_validate_config_fills_multiball_defaults():
    conn = mb_connection()
    del conn["to"]["base_url"], conn["to"]["start_delay"]
    cfg = mini_osc.validate_config({"osc_server": {}, "flask_server": {}, "connections": [conn]})
    assert cfg["connections"][0]["to"]["base_url"] == multiball.DEFAULT_BASE_URL
    assert cfg["connections"][0]["to"]["start_delay"] == 3


def test_multiball_list_courts_and_games(client, api):
    api.handler = lambda m, p, b: FakeResponse(200, {"count": 1, "results": [
        {"id": COURT, "title": "Eclipsium-Nantes", "description": "", "status": "online"}]}) if p == "/courts" \
        else FakeResponse(200, {"count": 1, "results": [
            {"id": GAME, "name": "com.funwithballs.eclipsium_shootingrange",
             "dispName": "Eclipsium Drone Defense", "versions": ["0.3.1", "0.3.7"],
             "assetFlips": [{"name": "Padel", "flipId": "4a9e69b06468a52f27380935"}, {"name": "no id"}]}]})
    res = client.post("/multiball_list", json={"what": "courts", "base_url": BASE, "api_key": KEY, "token": TOKEN})
    assert res.get_json() == {"ok": True, "courts": [{"id": COURT, "title": "Eclipsium-Nantes", "description": ""}]}
    res = client.post("/multiball_list", json={"what": "games", "base_url": BASE, "api_key": KEY,
                                               "token": TOKEN, "court_id": COURT})
    games = res.get_json()["games"]
    assert games[0]["id"] == GAME and games[0]["versions"] == ["0.3.1", "0.3.7"]
    assert games[0]["assetFlips"] == [{"name": "Padel", "flipId": "4a9e69b06468a52f27380935"}]
    assert all(c["method"] == "GET" for c in api.calls)


def test_multiball_list_one_game(client, api):
    api.handler = lambda m, p, b: FakeResponse(200, {
        "id": BALLOON, "name": "com.funwithballs.balloon", "dispName": "Balloon Mania", "versions": ["6.0.4"],
        "assetFlips": [{"name": "Halloween", "flipId": "FLIP-H"}]})
    res = client.post("/multiball_list", json={"what": "game", "base_url": BASE, "api_key": KEY,
                                               "token": TOKEN, "game_id": BALLOON})
    data = res.get_json()
    assert data["ok"] and data["games"][0]["id"] == BALLOON
    assert data["games"][0]["assetFlips"] == [{"name": "Halloween", "flipId": "FLIP-H"}]
    assert api.calls[0]["method"] == "GET" and api.calls[0]["path"] == f"/games/{BALLOON}"
    for bad in ("", "../courts", "a b"):
        assert client.post("/multiball_list", json={"what": "game", "api_key": KEY, "token": TOKEN,
                                                    "game_id": bad}).status_code == 400


def test_multiball_list_shows_api_errors(client, api):
    api.handler = lambda m, p, b: FakeResponse(401, {"message": "Invalid api key!"})
    res = client.post("/multiball_list", json={"what": "courts", "base_url": BASE, "api_key": "x", "token": "y"})
    assert res.get_json() == {"ok": False, "status": 401, "error": "Invalid api key!"}
    assert client.post("/multiball_list", json={"what": "courts", "api_key": "", "token": ""}).status_code == 400
    assert client.post("/multiball_list", json={"what": "games", "api_key": "a", "token": "b"}).status_code == 400
    assert client.post("/multiball_list", json={"what": "nope"}).status_code == 400


def test_multiball_list_uses_the_saved_token_and_url(client, api):
    api.handler = lambda m, p, b: FakeResponse(200, {"count": 0, "results": []})
    res = client.post("/multiball_list", json={"what": "courts", "base_url": "https://evil.test",
                                               "api_key": "typed", "token": "", "index": 1})
    assert res.get_json()["ok"] is True
    assert api.calls[0]["url"] == f"{BASE}/courts"
    assert api.calls[0]["auth"] == (KEY, TOKEN)
