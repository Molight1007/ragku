# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['launcher.py'],
    pathex=['.'],  # 添加当前目录到 Python 路径
    binaries=[],
    datas=[
        ('.env', '.'),  # .env 文件作为数据文件复制
    ],
    hiddenimports=[
        'tkinter',
        'tkinter.ttk',
        'tkinter.filedialog',
        'tkinter.messagebox',
        'uvicorn',
        'uvicorn.run',
        'fastapi',
        'fastapi.app',
        'numpy',
        'dashscope',
        'dashscope.base',
        'faiss',
        'sentence_transformers',
        'sentence_transformers.SentenceTransformer',
        'python-docx',
        'docx',
        'PyPDF2',
        'httpx',
        'python-multipart',
        'config',
        'app',
        'ingest',
        'main',
        'rag_service',
        'upload_api',
        'chunked_upload',
        'document_extract',
        'bailian_ocr',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_pre_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='RAG启动器',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='RAG启动器',
)
