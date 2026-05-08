# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec — gera executável standalone do Video Poker.

Funciona em Linux (gera ./dist/videopoker) e Windows (gera .\\dist\\videopoker.exe).

Uso:
    pip install pyinstaller
    pyinstaller videopoker.spec

Saída:
    Linux:   ./dist/videopoker        (~ 30-50 MB, single-file)
    Windows: .\\dist\\videopoker.exe   (sem janela de terminal)

Limpa builds antigos com `--clean` se trocar deps:
    pyinstaller --clean videopoker.spec
"""
from pathlib import Path

block_cipher = None

# Pasta raiz do projeto (onde mora o spec). Resolve em ambas plataformas.
ROOT = Path(SPECPATH).resolve()  # noqa: F821 - SPECPATH é injetado pelo PyInstaller

a = Analysis(
    [str(ROOT / "run.py")],
    pathex=[str(ROOT / "src")],
    binaries=[],
    datas=[
        # Tupla (source, dest_dir_dentro_do_bundle). Copia assets/fonts/*
        # mantendo a estrutura — `assets.py` lê via sys._MEIPASS / "assets".
        (str(ROOT / "assets"), "assets"),
    ],
    # `pkg_resources` é puxado por um runtime hook do próprio PyInstaller e
    # depende dos submódulos abaixo — sem isso o exe falha no startup.
    hiddenimports=[
        "jaraco.text",
        "jaraco.functools",
        "jaraco.context",
        "more_itertools",
        "platformdirs",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Dependências de teste/dev não vão no bundle final.
    excludes=["pytest", "numpy", "PIL", "tkinter"],
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
    name="videopoker",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,            # comprime se UPX estiver instalado (opcional)
    upx_exclude=[],
    runtime_tmpdir=None,
    # console=False esconde a janela de terminal no Windows. No Linux
    # também roda direto sem terminal preso.
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon: aponte para um .ico (Windows) ou .icns (macOS) se quiser.
    # icon=str(ROOT / "assets" / "icon.ico"),
)
