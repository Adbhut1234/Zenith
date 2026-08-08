# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_submodules

mem0_hidden = collect_submodules('mem0')

a = Analysis(
    ['agent.py'],
    pathex=[],
    binaries=[],
    datas=[('venv/Lib/site-packages/livekit', 'livekit'), ('venv/Lib/site-packages/onnxruntime', 'onnxruntime')],
    hiddenimports=['livekit.rtc.resources'] + mem0_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['PyQt5', 'matplotlib', 'tkinter', 'IPython', 'jupyter', 'notebook', 'scipy', 'pandas'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='zenith_backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='zenith_backend',
)
