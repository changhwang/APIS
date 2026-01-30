# PyInstaller spec for APIS hardware check (console)
block_cipher = None

a = Analysis(
    ['../scripts/check_hardware.py'],
    pathex=['..'],
    binaries=[],
    datas=[],
    hiddenimports=[
        # Add as needed:
        # 'ximea', 'ximea.xiapi',
        # 'cv2',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tests',
    ],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='check_hardware',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='check_hardware',
)
