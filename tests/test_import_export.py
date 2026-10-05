import json
import os

import pytest

import mini_osc

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def client(tmp_path):
    previous = mini_osc.DATA_DIR
    mini_osc.set_data_dir(str(tmp_path))
    with open(os.path.join(ROOT, "config.default.json"), encoding="utf-8") as f:
        (tmp_path / "config.json").write_text(f.read(), encoding="utf-8")
    yield mini_osc.app.test_client()
    mini_osc.set_data_dir(previous)


def test_data_paths(client, tmp_path):
    data = client.get("/get_data_paths").get_json()
    assert data["config_file"] == str(tmp_path / "config.json")
    assert data["logs_dir"] == str(tmp_path / "logs")
    assert data["can_open"] is True


def test_open_folder_refused_from_network(client):
    res = client.post("/open_folder", json={"target": "logs"}, environ_base={"REMOTE_ADDR": "192.168.1.20"})
    assert res.status_code == 403
    assert client.get("/get_data_paths", environ_base={"REMOTE_ADDR": "192.168.1.20"}).get_json()["can_open"] is False


def test_export_downloads_current_config(client, tmp_path):
    res = client.get("/export_config")
    assert res.status_code == 200
    assert "attachment" in res.headers["Content-Disposition"]
    assert "mini-osc-config-" in res.headers["Content-Disposition"]
    assert json.loads(res.data) == json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))


def test_import_replaces_config_and_keeps_backup(client, tmp_path):
    before = (tmp_path / "config.json").read_text(encoding="utf-8")
    new_cfg = {
        "osc_server": {"listen_ip": "127.0.0.1", "listen_port": 53001},
        "flask_server": {"ip": "127.0.0.1", "port": 5009},
        "connections": [{"name": "Imported", "from": {"protocol": "http", "endpoint": "/send_osc"},
                         "to": {"protocol": "osc", "ip": "127.0.0.1", "port": 12097}}],
    }
    res = client.post("/import_config", json=new_cfg)
    assert res.status_code == 200
    assert res.get_json()["connections"] == 1
    saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert saved["connections"][0]["name"] == "Imported"
    backups = list((tmp_path / "backups").iterdir())
    assert len(backups) == 1 and backups[0].read_text(encoding="utf-8") == before


def test_import_migrates_old_format(client, tmp_path):
    old = {
        "osc_server": {"listen_ip": "127.0.0.1", "listen_port": 53000},
        "flask_server": {"ip": "127.0.0.1", "port": 5009},
        "targets": [{"name": "Cogs", "type": "osc", "ip": "192.168.1.10", "port": 12097}],
        "routes": [{"from": {"protocol": "http", "endpoint": "/send_osc"}, "to": {"target_name": "Cogs"}}],
    }
    assert client.post("/import_config", json=old).status_code == 200
    saved = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert saved["connections"][0]["name"] == "HTTP to Cogs"


def test_invalid_import_is_rejected_and_config_untouched(client, tmp_path):
    before = (tmp_path / "config.json").read_text(encoding="utf-8")
    res = client.post("/import_config", json={"connections": []})
    assert res.status_code == 400
    assert "osc_server" in res.get_json()["message"]
    res = client.post("/import_config", data="not json", content_type="application/json")
    assert res.status_code == 400
    assert (tmp_path / "config.json").read_text(encoding="utf-8") == before
    assert not (tmp_path / "backups").exists()
