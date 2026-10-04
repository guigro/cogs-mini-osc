# -*- mode: python ; coding: utf-8 -*-
# Spec PyInstaller commune : .app (macOS), .exe fichier unique (Windows), dossier (Linux, emballé en AppImage).
# Lancer depuis la racine du dépôt : pyinstaller packaging/mini_osc.spec
import os
import sys

ROOT = os.path.dirname(SPECPATH)
ICONS = os.path.join(SPECPATH, "icons")
VERSION = os.environ.get("VERSION", "0.0.0").lstrip("v")
if not VERSION[:1].isdigit():
    VERSION = "0.0.0"


def icon(name):
    path = os.path.join(ICONS, name)
    return path if os.path.exists(path) else None


a = Analysis(
    [os.path.join(ROOT, "desktop.py")],
    pathex=[ROOT],
    datas=[
        (os.path.join(ROOT, "index.html"), "."),
        (os.path.join(ROOT, "config.default.json"), "."),
        (os.path.join(ROOT, "vendor"), "vendor"),
    ],
    hiddenimports=["mini_osc"],
    excludes=["tkinter"],
    noarchive=False,
)
pyz = PYZ(a.pure)

if sys.platform == "win32":
    exe = EXE(
        pyz, a.scripts, a.binaries, a.datas, [],
        name="Mini-OSC",
        console=False,
        upx=False,
        icon=icon("mini-osc.ico"),
    )
else:
    exe = EXE(
        pyz, a.scripts, [],
        exclude_binaries=True,
        name="Mini-OSC",
        console=False,
        upx=False,
        icon=icon("mini-osc.icns") if sys.platform == "darwin" else None,
    )
    coll = COLLECT(exe, a.binaries, a.datas, name="Mini-OSC", upx=False)
    if sys.platform == "darwin":
        app = BUNDLE(
            coll,
            name="Mini-OSC.app",
            icon=icon("mini-osc.icns"),
            bundle_identifier="show.eclipsium.mini-osc",
            version=VERSION,
            info_plist={
                "CFBundleDisplayName": "Mini-OSC",
                "CFBundleShortVersionString": VERSION,
                "NSHighResolutionCapable": True,
                # L'interface est servie en HTTP local, sans TLS
                "NSAppTransportSecurity": {"NSAllowsArbitraryLoads": True, "NSAllowsLocalNetworking": True},
            },
        )
