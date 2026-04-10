# app-data/RAP_GUI.spec
# One-folder EXE with metadata, icon, TkinterMapView, boto3, botocore, pytz

from PyInstaller.utils.hooks import collect_data_files

# Collect required data files
tkmap_data = collect_data_files('tkintermapview')
boto_data = collect_data_files('botocore')
pytz_data = collect_data_files('pytz')

block_cipher = None

a = Analysis(
    ['../RAP_GUI.py'],          # main entry script
    pathex=['..'],            # project root
    binaries=[],
    datas=tkmap_data + boto_data + pytz_data + [
    ('../Outputs', 'Outputs'),
    ('../version.txt', '.'),  
    ],
    hiddenimports=[
        # GUI + utilities
        'tkintermapview',
        'requests',
        'PIL',
        'geocoder',
        'pyperclip',
        'pywin32',

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
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
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
    version='version.txt',     # metadata file inside app-data
    icon='RAP_GUI.ico'         # icon inside app-data
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    name='RAP_GUI'
)