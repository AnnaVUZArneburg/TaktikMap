# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Spezifikation für Taktik.

Baut eine eigenständige Ein-Datei-Anwendung und bettet den
mitgelieferten Symbolsatz (``symbole/``) ein. Aufruf::

    pyinstaller --noconfirm taktik.spec

Erzeugt ``dist/Taktik.exe`` (Windows) bzw. ``dist/Taktik`` (Linux/macOS).
"""

block_cipher = None

a = Analysis(
    ["run_taktik.py"],
    pathex=[],
    binaries=[],
    # Mitgelieferter Symbolsatz – im Bundle unter <root>/symbole,
    # passend zu taktik.resource_path("symbole").
    datas=[("symbole", "symbole")],
    hiddenimports=[
        "PySide6.QtSvg",
        "PySide6.QtPrintSupport",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Nicht benötigte, große Qt-Module ausschließen (kleinere EXE)
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtQml",
        "PySide6.QtQuick",
        "PySide6.Qt3DCore",
        "PySide6.QtMultimedia",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="Taktik",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # GUI-Anwendung, kein Konsolenfenster
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon="packaging/taktik.ico" if __import__("os").path.exists(
        "packaging/taktik.ico") else None,
)
