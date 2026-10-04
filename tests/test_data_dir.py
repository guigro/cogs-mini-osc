import os

from desktop import default_data_dir

HOME = os.path.expanduser("~")


def test_macos():
    assert default_data_dir("darwin", {}) == os.path.join(HOME, "Library", "Application Support", "Mini-OSC")


def test_windows_appdata():
    env = {"APPDATA": r"C:\Users\op\AppData\Roaming"}
    assert default_data_dir("win32", env) == os.path.join(r"C:\Users\op\AppData\Roaming", "Mini-OSC")


def test_windows_without_appdata():
    assert default_data_dir("win32", {}) == os.path.join(HOME, "AppData", "Roaming", "Mini-OSC")


def test_linux_xdg():
    assert default_data_dir("linux", {"XDG_CONFIG_HOME": "/xdg"}) == os.path.join("/xdg", "mini-osc")


def test_linux_default():
    assert default_data_dir("linux", {}) == os.path.join(HOME, ".config", "mini-osc")


def test_override_wins_everywhere():
    for platform in ("darwin", "win32", "linux"):
        assert default_data_dir(platform, {"MINI_OSC_DATA_DIR": "/custom"}) == "/custom"
