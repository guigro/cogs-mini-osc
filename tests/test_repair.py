import json

import pytest

from desktop_repair import (RepairApi, apply_listener_edits, backup_config, ip_available,
                            listeners_from_config, repair_html)


def make_cfg():
    return {
        "osc_server": {"listen_ip": "192.168.66.100", "listen_port": 53000},
        "flask_server": {"ip": "192.168.66.100", "port": 5009},
        "connections": [
            {"name": "HTTP to cogs", "from": {"protocol": "http", "endpoint": "/send_osc"},
             "to": {"protocol": "osc", "ip": "192.168.66.100", "port": 12097}},
            {"name": "TCP to cogs", "from": {"protocol": "tcp", "listen_ip": "192.168.66.100", "listen_port": 57676},
             "to": {"protocol": "osc", "ip": "192.168.66.100", "port": 12097}},
        ],
    }


def test_listeners_cover_servers_and_tcp_udp_sources():
    items = listeners_from_config(make_cfg())
    assert [(i["key"], i["index"]) for i in items] == [("osc_server", -1), ("flask_server", -1), ("connection", 1)]
    assert items[2]["label"] == "TCP to cogs (TCP listener)"
    assert items[2]["ip"] == "192.168.66.100" and items[2]["port"] == 57676


def test_apply_edits_changes_only_listen_addresses():
    cfg = make_cfg()
    edits = [dict(i, ip="127.0.0.1") for i in listeners_from_config(cfg)]
    edits[1]["port"] = "5010"
    apply_listener_edits(cfg, edits)
    assert cfg["osc_server"] == {"listen_ip": "127.0.0.1", "listen_port": 53000}
    assert cfg["flask_server"] == {"ip": "127.0.0.1", "port": 5010}
    assert cfg["connections"][1]["from"]["listen_ip"] == "127.0.0.1"
    # Les destinations ne sont pas touchées
    assert cfg["connections"][1]["to"]["ip"] == "192.168.66.100"


@pytest.mark.parametrize("ip,port,message", [
    ("192.168.1", "53000", "valid IP address"),
    ("127.0.0.1", "0", "port"),
    ("127.0.0.1", "70000", "port"),
    ("127.0.0.1", "abc", "port"),
])
def test_apply_edits_rejects_invalid_values(ip, port, message):
    cfg = make_cfg()
    with pytest.raises(ValueError, match=message):
        apply_listener_edits(cfg, [{"key": "osc_server", "index": -1, "label": "OSC server", "ip": ip, "port": port}])


def test_ip_available():
    assert ip_available("127.0.0.1")
    assert ip_available("0.0.0.0")
    assert not ip_available("192.0.2.123")  # plage de documentation, jamais attribuée
    assert not ip_available("pas une ip")


def test_repair_page_flags_missing_ips():
    page = repair_html("boom", "/x/config.json", cfg=make_cfg())
    assert page.count("This IP does not exist on this computer") == 3
    assert "Save and restart" in page


def test_repair_page_without_readable_config_has_no_editor():
    page = repair_html("bad json", "/x/config.json", cfg=None, config_problem=True)
    assert "Unreadable configuration" in page
    assert "Save and restart" not in page
    assert "Restore default configuration" in page


def test_save_writes_config_backs_up_and_relaunches(tmp_path):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(make_cfg()), encoding="utf-8")
    relaunched = []
    api = RepairApi(str(path), "unused", lambda: relaunched.append(True), lambda p: None)
    edits = [dict(i, ip="127.0.0.1") for i in listeners_from_config(make_cfg())]
    assert api.save(edits) is None
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["osc_server"]["listen_ip"] == "127.0.0.1"
    assert relaunched == [True]
    assert len(list((tmp_path / "backups").iterdir())) == 1


def test_save_with_invalid_value_returns_error_and_keeps_file(tmp_path):
    path = tmp_path / "config.json"
    original = json.dumps(make_cfg())
    path.write_text(original, encoding="utf-8")
    api = RepairApi(str(path), "unused", lambda: pytest.fail("ne doit pas redémarrer"), lambda p: None)
    res = api.save([{"key": "osc_server", "index": -1, "label": "OSC server", "ip": "999.1.1.1", "port": "53000"}])
    assert "valid IP address" in res["error"]
    assert path.read_text(encoding="utf-8") == original


def test_restore_default_keeps_unreadable_config_in_backups(tmp_path):
    path = tmp_path / "config.json"
    path.write_text('{"osc_server": {,', encoding="utf-8")
    default = tmp_path / "default.json"
    default.write_text('{"default": true}', encoding="utf-8")
    relaunched = []
    RepairApi(str(path), str(default), lambda: relaunched.append(True), lambda p: None).restore_default()
    assert path.read_text(encoding="utf-8") == '{"default": true}'
    backups = list((tmp_path / "backups").iterdir())
    assert backups[0].read_text(encoding="utf-8") == '{"osc_server": {,'
    assert relaunched == [True]


def test_backup_of_missing_file_is_none(tmp_path):
    assert backup_config(str(tmp_path / "absent.json")) is None


def test_save_warns_when_ips_still_missing(tmp_path):
    path = tmp_path / "config.json"
    original = json.dumps(make_cfg())
    path.write_text(original, encoding="utf-8")
    relaunched = []
    api = RepairApi(str(path), "unused", lambda: relaunched.append(True), lambda p: None)
    edits = listeners_from_config(make_cfg())  # IP 192.168.66.100 inchangées
    res = api.save(edits)
    assert "192.168.66.100" in res["warning"]
    assert path.read_text(encoding="utf-8") == original and relaunched == []
    assert api.save(edits, True) is None
    assert relaunched == [True]
