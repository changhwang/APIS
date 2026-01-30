# PyInstaller spec for APIS (onedir build)
block_cipher = None

a = Analysis(
    ['../app/main.py'],
    pathex=['..'],
    binaries=[],
    datas=[
        ('../assets/icon.ico', 'assets'),
        ('../app/assets/apis_logo.png', 'app/assets'),
    ],
    hiddenimports=[
        # Add as needed:
        # 'ximea', 'ximea.xiapi',
        # 'cv2',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        'tests', 'firmware',
    ],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='APIS',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    icon='../assets/icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    name='APIS',
)
