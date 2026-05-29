# app-data/RAP-GUI.spec
# Single-file EXE — TkinterMapView, boto3, botocore, pytz
# Run from the app-data/ directory:
#   pyinstaller RAP-GUI.spec --distpath ../dist --workpath ../build

from PyInstaller.utils.hooks import collect_data_files

tkmap_data = collect_data_files('tkintermapview')
boto_data  = collect_data_files('botocore')
pytz_data  = collect_data_files('pytz')

block_cipher = None

a = Analysis(
    ['../RAP_GUI.py'],
    pathex=['..'],
    binaries=[],
    datas=tkmap_data + boto_data + pytz_data,
    hiddenimports=[
        # GUI + map
        'tkintermapview',
        'requests',
        'PIL',
        'geocoder',
        'pyperclip',

        # AWS SDK
        'boto3',
        'botocore',
        'botocore.configloader',
        'botocore.hooks',
        'botocore.loaders',
        'botocore.parsers',
        'botocore.retryhandler',
        'botocore.utils',
        's3transfer',
        'jmespath',

        # timezone support
        'pytz',
    ],
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    name='RAP_GUI',
    debug=False,
    strip=False,
    upx=False,
    console=False,
    icon='RAP_GUI.ico',
)
# No COLLECT() — single-file mode so the auto-updater can swap the exe directly