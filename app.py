from __future__ import annotations

import asyncio
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from knowledge_store import (
    delete_kb_file,
    knowledge_root,
    list_kb_files,
    rebuild_index_sync,
    save_upload,
)
from rag_service import rag_answer


class ChatRequest(BaseModel):
    """前端发送的问题请求模型。"""

    question: str


class ContextSnippet(BaseModel):
    """返回给前端的参考片段数据结构。"""

    source: str
    text_preview: str
    score: float


class ChatResponse(BaseModel):
    """前端收到的回答数据结构。"""

    answer: str
    contexts: List[ContextSnippet]


class DeleteKnowledgeBody(BaseModel):
    relative_path: str = Field(..., description="相对知识库根目录的路径")


class RebuildResponse(BaseModel):
    ok: bool = True
    chunks: int
    unique_sources: int


app = FastAPI(
    title="本地知识库RAG问答系统",
    description="基于阿里云通义千问 + 本地多模态知识库的RAG服务，用于大赛展示。",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def index() -> dict:
    """简单健康检查接口。"""
    return {
        "message": "本地知识库RAG问答系统已启动。",
        "docs": "/docs",
    }


# ----- 知识库管理 API -----


@app.get("/api/knowledge/status")
async def api_knowledge_status() -> dict:
    root = knowledge_root()
    exists = root.exists()
    files = list_kb_files() if exists else []
    return {
        "knowledge_dir": str(root),
        "exists": exists,
        "file_count": len(files),
    }


@app.get("/api/knowledge/files")
async def api_knowledge_files() -> dict:
    return {"files": list_kb_files()}


@app.post("/api/knowledge/upload")
async def api_knowledge_upload(file: UploadFile = File(...)) -> dict:
    try:
        data = await file.read()
        rel = save_upload(file.filename or "upload.bin", data)
        return {"ok": True, "relative_path": rel}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.delete("/api/knowledge/file")
async def api_knowledge_delete(body: DeleteKnowledgeBody) -> dict:
    try:
        delete_kb_file(body.relative_path)
        return {"ok": True}
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/api/knowledge/rebuild", response_model=RebuildResponse)
async def api_knowledge_rebuild() -> RebuildResponse:
    """全量重建索引（可能较慢，在线程池中执行）。"""

    def _run() -> dict[str, int]:
        return rebuild_index_sync()

    try:
        result = await asyncio.to_thread(_run)
        return RebuildResponse(
            chunks=result["chunks"],
            unique_sources=result["unique_sources"],
        )
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except Exception as e:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.get("/chat-ui", response_class=HTMLResponse)
async def chat_ui() -> str:
    """中文网页：问答 + 知识库增删与重建索引。"""
    kb_dir = str(settings.default_knowledge_dir)
    return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>本地知识库RAG问答系统</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: #f5f5f7;
        }}
        .container {{
            max-width: 960px;
            margin: 0 auto;
            padding: 24px 16px 40px;
        }}
        h1 {{ font-size: 24px; margin-bottom: 8px; }}
        .subtitle {{ color: #666; font-size: 14px; margin-bottom: 16px; }}
        .tabs {{
            display: flex;
            gap: 8px;
            margin-bottom: 16px;
        }}
        .tabs button {{
            padding: 8px 16px;
            border: 1px solid #d9d9d9;
            background: #fff;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
        }}
        .tabs button.active {{
            background: #1677ff;
            color: #fff;
            border-color: #1677ff;
        }}
        .panel {{ display: none; }}
        .panel.active {{ display: block; }}
        .chat-box {{
            background: #ffffff;
            border-radius: 12px;
            padding: 16px;
            height: 420px;
            overflow-y: auto;
            box-shadow: 0 8px 24px rgba(0,0,0,0.06);
        }}
        .msg {{ margin-bottom: 16px; }}
        .msg-user {{ text-align: right; }}
        .msg-user .bubble {{
            display: inline-block;
            background: #1677ff;
            color: #fff;
            padding: 8px 12px;
            border-radius: 16px 4px 16px 16px;
            max-width: 70%;
        }}
        .msg-bot .bubble {{
            display: inline-block;
            background: #f0f0f0;
            color: #222;
            padding: 8px 12px;
            border-radius: 4px 16px 16px 16px;
            max-width: 80%;
        }}
        .contexts {{
            margin-top: 8px;
            padding-left: 16px;
            font-size: 12px;
            color: #555;
            border-left: 2px solid #ddd;
        }}
        .input-area {{
            margin-top: 16px;
            display: flex;
            gap: 8px;
        }}
        .input-area textarea {{
            flex: 1;
            resize: none;
            border-radius: 8px;
            border: 1px solid #d9d9d9;
            padding: 8px;
            font-size: 14px;
        }}
        .input-area button, .kb-actions button {{
            border: none;
            border-radius: 8px;
            background: #1677ff;
            color: #fff;
            font-size: 14px;
            cursor: pointer;
            padding: 8px 14px;
        }}
        .input-area button {{ width: 96px; }}
        .input-area button:disabled {{ background: #b0c7f5; cursor: not-allowed; }}
        .kb-actions {{ display: flex; flex-wrap: wrap; gap: 8px; align-items: center; margin-bottom: 12px; }}
        .kb-actions .secondary {{ background: #fff; color: #1677ff; border: 1px solid #1677ff; }}
        .kb-actions .danger {{ background: #ff4d4f; }}
        .kb-hint {{ font-size: 12px; color: #666; margin-bottom: 12px; word-break: break-all; }}
        .file-list {{
            background: #fff;
            border-radius: 12px;
            padding: 12px;
            max-height: 320px;
            overflow-y: auto;
            box-shadow: 0 4px 16px rgba(0,0,0,0.06);
        }}
        .file-row {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 0;
            border-bottom: 1px solid #f0f0f0;
            font-size: 13px;
        }}
        .file-row:last-child {{ border-bottom: none; }}
        .file-meta {{ color: #888; font-size: 12px; }}
        .status {{ margin-top: 8px; font-size: 12px; color: #888; }}
        #kbStatus {{ min-height: 1.2em; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>本地知识库RAG问答系统</h1>
        <div class="subtitle">
            基于阿里云通义千问 + 本地多模态知识库 · 问答、溯源与知识库维护
        </div>
        <div class="tabs">
            <button type="button" class="active" id="tabChat" onclick="switchTab('chat')">问答</button>
            <button type="button" id="tabKb" onclick="switchTab('kb')">知识库</button>
        </div>

        <div id="panelChat" class="panel active">
            <div class="chat-box" id="chatBox"></div>
            <div class="input-area">
                <textarea id="questionInput" rows="3" placeholder="请输入你的问题"></textarea>
                <button id="sendBtn" type="button" onclick="sendQuestion()">发送</button>
            </div>
            <div class="status" id="statusText">就绪</div>
        </div>

        <div id="panelKb" class="panel">
            <div class="kb-hint">
                当前知识库目录（由配置/环境变量 KNOWLEDGE_DIR 决定）：<strong>{kb_dir}</strong>
            </div>
            <div class="kb-actions">
                <input type="file" id="kbFile" />
                <button type="button" class="secondary" onclick="uploadFile()">上传到知识库</button>
                <button type="button" onclick="refreshFiles()">刷新列表</button>
                <button type="button" class="danger" onclick="deleteSelected()">删除选中</button>
                <button type="button" onclick="rebuildIndex()">重建索引</button>
            </div>
            <div class="file-list" id="fileList">加载中…</div>
            <div class="status" id="kbStatus"></div>
        </div>
    </div>
    <script>
        const chatBox = document.getElementById('chatBox');
        const questionInput = document.getElementById('questionInput');
        const sendBtn = document.getElementById('sendBtn');
        const statusText = document.getElementById('statusText');
        const fileListEl = document.getElementById('fileList');
        const kbStatus = document.getElementById('kbStatus');
        let selectedPath = null;

        function switchTab(name) {{
            document.getElementById('tabChat').classList.toggle('active', name === 'chat');
            document.getElementById('tabKb').classList.toggle('active', name === 'kb');
            document.getElementById('panelChat').classList.toggle('active', name === 'chat');
            document.getElementById('panelKb').classList.toggle('active', name === 'kb');
            if (name === 'kb') refreshFiles();
        }}

        function appendMessage(role, text, contexts) {{
            const wrap = document.createElement('div');
            wrap.className = 'msg ' + (role === 'user' ? 'msg-user' : 'msg-bot');
            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.textContent = text;
            wrap.appendChild(bubble);
            if (role === 'bot' && Array.isArray(contexts) && contexts.length > 0) {{
                const ctxDiv = document.createElement('div');
                ctxDiv.className = 'contexts';
                ctxDiv.innerHTML = '<strong>参考片段：</strong><br>' + contexts.map((c, idx) =>
                    `【${{idx + 1}}】来源：${{c.source}}<br/>预览：${{c.text_preview}}`
                ).join('<br><br>');
                wrap.appendChild(ctxDiv);
            }}
            chatBox.appendChild(wrap);
            chatBox.scrollTop = chatBox.scrollHeight;
        }}

        async function sendQuestion() {{
            const q = questionInput.value.trim();
            if (!q) return;
            appendMessage('user', q);
            questionInput.value = '';
            sendBtn.disabled = true;
            statusText.textContent = '正在检索并生成回答…';
            try {{
                const resp = await fetch('/chat', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ question: q }})
                }});
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
                const data = await resp.json();
                appendMessage('bot', data.answer || '后端未返回回答。', data.contexts || []);
            }} catch (err) {{
                console.error(err);
                appendMessage('bot', '请求失败，请确认服务已启动。', []);
            }} finally {{
                sendBtn.disabled = false;
                statusText.textContent = '就绪';
            }}
        }}

        questionInput.addEventListener('keydown', function (e) {{
            if (e.key === 'Enter' && !e.shiftKey) {{
                e.preventDefault();
                sendQuestion();
            }}
        }});

        async function refreshFiles() {{
            kbStatus.textContent = '加载列表…';
            selectedPath = null;
            try {{
                const resp = await fetch('/api/knowledge/files');
                const data = await resp.json();
                const files = data.files || [];
                if (!files.length) {{
                    fileListEl.textContent = '（暂无文件，请先上传支持的文档）';
                    kbStatus.textContent = '';
                    return;
                }}
                fileListEl.innerHTML = '';
                files.forEach((f) => {{
                    const row = document.createElement('div');
                    row.className = 'file-row';
                    const left = document.createElement('div');
                    left.innerHTML = '<div>' + escapeHtml(f.relative_path) + '</div>' +
                        '<div class="file-meta">' + formatSize(f.size_bytes) + '</div>';
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.textContent = '选择';
                    btn.style.cssText = 'padding:4px 10px;font-size:12px;width:auto;background:#fff;color:#1677ff;border:1px solid #1677ff;';
                    btn.onclick = () => {{
                        selectedPath = f.relative_path;
                        kbStatus.textContent = '已选中：' + f.relative_path;
                    }};
                    row.appendChild(left);
                    row.appendChild(btn);
                    fileListEl.appendChild(row);
                }});
                kbStatus.textContent = '共 ' + files.length + ' 个文件，点击「选择」后点「删除选中」。';
            }} catch (e) {{
                fileListEl.textContent = '加载失败';
                kbStatus.textContent = String(e);
            }}
        }}

        function escapeHtml(s) {{
            const d = document.createElement('div');
            d.textContent = s;
            return d.innerHTML;
        }}

        function formatSize(n) {{
            if (n < 1024) return n + ' B';
            if (n < 1024*1024) return (n/1024).toFixed(1) + ' KB';
            return (n/1024/1024).toFixed(1) + ' MB';
        }}

        async function uploadFile() {{
            const inp = document.getElementById('kbFile');
            if (!inp.files || !inp.files[0]) {{
                kbStatus.textContent = '请先选择文件';
                return;
            }}
            kbStatus.textContent = '上传中…';
            const fd = new FormData();
            fd.append('file', inp.files[0]);
            try {{
                const resp = await fetch('/api/knowledge/upload', {{ method: 'POST', body: fd }});
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.detail || resp.status);
                kbStatus.textContent = '已上传：' + data.relative_path + '。请「重建索引」后问答生效。';
                inp.value = '';
                refreshFiles();
            }} catch (e) {{
                kbStatus.textContent = '上传失败：' + e;
            }}
        }}

        async function deleteSelected() {{
            if (!selectedPath) {{
                kbStatus.textContent = '请先在列表中点击「选择」要删除的文件';
                return;
            }}
            if (!confirm('确定删除：' + selectedPath + ' ？')) return;
            kbStatus.textContent = '删除中…';
            try {{
                const resp = await fetch('/api/knowledge/file', {{
                    method: 'DELETE',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify({{ relative_path: selectedPath }})
                }});
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.detail || resp.status);
                kbStatus.textContent = '已删除。请「重建索引」后生效。';
                selectedPath = null;
                refreshFiles();
            }} catch (e) {{
                kbStatus.textContent = '删除失败：' + e;
            }}
        }}

        async function rebuildIndex() {{
            kbStatus.textContent = '正在重建索引（可能需几分钟）…';
            try {{
                const resp = await fetch('/api/knowledge/rebuild', {{ method: 'POST' }});
                const data = await resp.json();
                if (!resp.ok) throw new Error(data.detail || resp.status);
                kbStatus.textContent = '索引重建完成：共 ' + data.chunks + ' 条片段，来自约 ' +
                    data.unique_sources + ' 个文件。';
            }} catch (e) {{
                kbStatus.textContent = '重建失败：' + e;
            }}
        }}
    </script>
</body>
</html>
    """


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    """核心聊天接口：接收问题，返回回答和参考片段。"""
    question = body.question.strip()
    if not question:
        return ChatResponse(answer="问题不能为空。", contexts=[])

    answer, contexts_raw = rag_answer(question)

    contexts: List[ContextSnippet] = []
    for c in contexts_raw:
        text = c.get("text", "") or ""
        if len(text) > 200:
            text = text[:200] + "..."
        contexts.append(
            ContextSnippet(
                source=str(c.get("source", "")),
                text_preview=text,
                score=float(c.get("score", 0.0)),
            )
        )

    return ChatResponse(answer=answer, contexts=contexts)
