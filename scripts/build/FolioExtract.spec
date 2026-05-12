# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
import pymupdf

ROOT = Path.cwd()
PYMUPDF_LAYOUT_RESOURCE_DIR = Path(pymupdf.__file__).resolve().parent / 'layout' / 'resources'
DATAS = [(str(ROOT / 'frontend' / 'dist'), 'frontend/dist')]
if PYMUPDF_LAYOUT_RESOURCE_DIR.exists():
    DATAS.append((str(PYMUPDF_LAYOUT_RESOURCE_DIR), 'pymupdf/layout/resources'))


a = Analysis(
    [str(ROOT / 'backend' / 'desktop' / 'FolioExtract.py')],
    pathex=[str(ROOT)],
    binaries=[],
    datas=DATAS,
    hiddenimports=[
        'easyocr',
        'multipart',
        'pdfplumber',
        'pdf2docx',
        'pymupdf4llm',
        'webview',
        'webview.platforms.winforms',
        '_cffi_backend',
        'clr',
        'clr_loader',
        'backend.app.infrastructure.conversion.md_converter',
        'backend.app.infrastructure.conversion.txt_converter',
        'backend.app.infrastructure.conversion.docx_converter',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='FolioExtract',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=[str(ROOT / 'assets' / 'icon.ico')],
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FolioExtract',
)
