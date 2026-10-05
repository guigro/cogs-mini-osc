from desktop import window_url


def test_localhost():
    assert window_url({"ip": "127.0.0.1", "port": 5000}) == "http://127.0.0.1:5000/"


def test_all_interfaces_ipv4_uses_localhost():
    assert window_url({"ip": "0.0.0.0", "port": 5009}) == "http://127.0.0.1:5009/"


def test_all_interfaces_ipv6_uses_localhost():
    assert window_url({"ip": "::", "port": 5000}) == "http://127.0.0.1:5000/"


def test_lan_ip_is_kept():
    assert window_url({"ip": "192.168.50.12", "port": 8080}) == "http://192.168.50.12:8080/"
