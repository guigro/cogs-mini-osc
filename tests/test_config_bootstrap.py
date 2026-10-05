import json
import os

import pytest

import mini_osc
from desktop import ensure_config

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT = os.path.join(ROOT, "config.default.json")


def test_default_config_is_valid():
    cfg = mini_osc.load_config(DEFAULT)
    assert cfg["connections"] == []
    assert cfg["flask_server"]["port"] == 5009


def test_creates_config_when_missing(tmp_path):
    data_dir = tmp_path / "Mini-OSC"
    path = ensure_config(str(data_dir), DEFAULT)
    assert path == str(data_dir / "config.json")
    with open(path, encoding="utf-8") as f, open(DEFAULT, encoding="utf-8") as d:
        assert json.load(f) == json.load(d)


def test_keeps_existing_config(tmp_path):
    existing = tmp_path / "config.json"
    existing.write_bytes(b'{"mine": true}')
    ensure_config(str(tmp_path), DEFAULT)
    assert existing.read_bytes() == b'{"mine": true}'


def test_keeps_invalid_config(tmp_path):
    existing = tmp_path / "config.json"
    existing.write_bytes(b'{"osc_server": {,')
    ensure_config(str(tmp_path), DEFAULT)
    assert existing.read_bytes() == b'{"osc_server": {,'


def test_invalid_json_raises_config_error(tmp_path):
    bad = tmp_path / "config.json"
    bad.write_text('{"osc_server": {,', encoding="utf-8")
    with pytest.raises(mini_osc.ConfigError, match="Error parsing JSON"):
        mini_osc.load_config(str(bad))


def test_missing_section_raises_config_error(tmp_path):
    bad = tmp_path / "config.json"
    bad.write_text('{"flask_server": {}, "connections": []}', encoding="utf-8")
    with pytest.raises(mini_osc.ConfigError, match="osc_server"):
        mini_osc.load_config(str(bad))


def test_missing_file_raises_config_error(tmp_path):
    with pytest.raises(mini_osc.ConfigError, match="can't be found"):
        mini_osc.load_config(str(tmp_path / "absent.json"))


def test_old_format_is_migrated(tmp_path):
    old = {
        "osc_server": {"listen_ip": "127.0.0.1", "listen_port": 53000},
        "flask_server": {"ip": "127.0.0.1", "port": 5009},
        "targets": [{"name": "Cogs", "type": "osc", "ip": "192.168.1.10", "port": 12097}],
        "routes": [{"from": {"protocol": "http", "endpoint": "/send_osc"}, "to": {"target_name": "Cogs"}}],
    }
    path = tmp_path / "config.json"
    path.write_text(json.dumps(old), encoding="utf-8")
    cfg = mini_osc.load_config(str(path))
    assert cfg["connections"] == [{
        "name": "HTTP to Cogs",
        "from": {"protocol": "http", "endpoint": "/send_osc"},
        "to": {"protocol": "osc", "ip": "192.168.1.10", "port": 12097},
    }]


def test_set_data_dir_moves_config_and_logs(tmp_path):
    previous = mini_osc.DATA_DIR
    try:
        mini_osc.set_data_dir(str(tmp_path / "data"))
        assert mini_osc.CONFIG_FILE == str(tmp_path / "data" / "config.json")
        mini_osc.setup_file_logging({"file_logging": {"enabled": True, "retention_days": 1, "log_level": "INFO"}})
        assert (tmp_path / "data" / "logs").is_dir()
    finally:
        mini_osc.setup_file_logging({"file_logging": {"enabled": False}})
        mini_osc.set_data_dir(previous)
