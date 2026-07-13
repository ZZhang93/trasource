# -*- mode: python ; coding: utf-8 -*-
# PyInstaller 配置：将 FastAPI 后端打包为 Tauri sidecar 单文件二进制
# 用法: python -m PyInstaller trasource-backend.spec --clean --noconfirm

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

# jieba 需要词典数据文件
datas = collect_data_files('jieba')

hiddenimports = (
    ['config']
    + collect_submodules('backend')
    + collect_submodules('core')
    + collect_submodules('uvicorn')      # uvicorn 的 loop/protocol 实现是动态导入的
    + ['multipart', 'python_multipart']
)

a = Analysis(
    ['backend/server.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'PyQt5', 'PySide6', 'IPython', 'pytest'],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='trasource-backend',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
