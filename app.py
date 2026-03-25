from __future__ import annotations

from typing import List

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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


app = FastAPI(
    title="本地知识库RAG问答系统",
    description="基于阿里云通义千问 + 本地多模态知识库的RAG服务，用于大赛展示。",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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


@app.get("/chat-ui", response_class=HTMLResponse)
async def chat_ui() -> str:
    """简单的中文网页聊天界面。"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8" />
    <title>本地知识库RAG问答系统</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "SF Pro Display",
                "Segoe UI", Helvetica, Arial, sans-serif;
            margin: 0;
            padding: 0;
            background: #f2f2f7;
            color: #1d1d1f;
        }
        .container {
            max-width: 960px;
            margin: 0 auto;
            padding: 24px 16px 40px;
        }
        h1 {
            font-size: 24px;
            margin-bottom: 8px;
        }
        .subtitle {
            color: #666;
            font-size: 14px;
            margin-bottom: 16px;
        }
        .chat-box {
            background: rgba(255, 255, 255, 0.72);
            border-radius: 18px;
            padding: 12px;
            height: 520px;
            overflow-y: auto;
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.05);
            border: 1px solid rgba(0, 0, 0, 0.06);
            backdrop-filter: blur(16px);
        }
        .msg {
            margin-bottom: 16px;
        }
        .msg-user {
            text-align: right;
        }
        .bubble {
            white-space: pre-wrap;
            word-break: break-word;
            line-height: 1.55;
        }

        .msg-user .bubble {
            display: inline-block;
            background: #007aff;
            color: #fff;
            padding: 10px 14px;
            border-radius: 18px 4px 18px 18px;
            max-width: 78%;
            box-shadow: 0 12px 26px rgba(0, 122, 255, 0.22);
        }
        .msg-bot .bubble {
            display: inline-block;
            background: #ffffff;
            color: #1d1d1f;
            padding: 10px 14px;
            border-radius: 4px 18px 18px 18px;
            max-width: 86%;
            border: 1px solid rgba(0, 0, 0, 0.06);
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.03);
        }
        .contexts {
            margin-top: 8px;
            padding: 10px 12px;
            font-size: 12.5px;
            color: #6b7280;
            background: #f2f2f7;
            border: 1px solid rgba(0, 0, 0, 0.06);
            border-radius: 14px;
            border-left: 3px solid #d1d5db;
        }
        .input-area {
            margin-top: 16px;
            display: flex;
            gap: 10px;
            padding: 10px 12px;
            border-radius: 22px;
            background: rgba(255, 255, 255, 0.75);
            border: 1px solid rgba(0, 0, 0, 0.06);
            backdrop-filter: blur(16px);
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.05);
        }
        .input-area textarea {
            flex: 1;
            resize: none;
            border-radius: 12px;
            border: none;
            background: transparent;
            padding: 6px 4px;
            font-size: 15px;
            color: #1d1d1f;
            outline: none;
        }
        .input-area textarea::placeholder {
            color: #8e8e93;
        }
        .input-area button {
            width: 44px;
            height: 44px;
            border: none;
            border-radius: 999px;
            background: #007aff;
            color: #fff;
            font-size: 14px;
            font-weight: 600;
            cursor: pointer;
            box-shadow: 0 14px 30px rgba(0, 122, 255, 0.28);
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }
        .input-area button:disabled {
            background: #a5c8ff;
            cursor: not-allowed;
            box-shadow: none;
        }
        .status {
            margin-top: 10px;
            font-size: 12px;
            color: #8e8e93;
        }

        /* iMessage 风格深色模式（跟随系统设置） */
        @media (prefers-color-scheme: dark) {
            body {
                background: #000000;
                color: #ffffff;
            }
            .subtitle {
                color: #8e8e93;
            }
            .chat-box {
                background: rgba(18, 18, 20, 0.78);
                border: 1px solid rgba(255, 255, 255, 0.07);
                box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
            }
            .contexts {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
                color: #a1a1aa;
                border-left: 3px solid rgba(255, 255, 255, 0.18);
            }
            .msg-user .bubble {
                color: #ffffff;
                box-shadow: 0 12px 26px rgba(0, 122, 255, 0.30);
            }
            .msg-bot .bubble {
                background: rgba(28, 28, 31, 0.96);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.08);
                box-shadow: 0 10px 24px rgba(0, 0, 0, 0.25);
            }
            .input-area {
                background: rgba(28, 28, 31, 0.72);
                border: 1px solid rgba(255, 255, 255, 0.08);
                box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
            }
            .input-area textarea {
                color: #ffffff;
            }
            .input-area textarea::placeholder {
                color: #8e8e93;
            }
            .status {
                color: #8e8e93;
            }
        }

        /* iMessage 风格深色模式（手动切换） */
        body[data-theme="dark"] {
            background: #000000;
            color: #ffffff;
        }
        body[data-theme="dark"] .subtitle {
            color: #8e8e93;
        }
        body[data-theme="dark"] .chat-box {
            background: rgba(18, 18, 20, 0.78);
            border: 1px solid rgba(255, 255, 255, 0.07);
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
        }
        body[data-theme="dark"] .contexts {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
            color: #a1a1aa;
            border-left: 3px solid rgba(255, 255, 255, 0.18);
        }
        body[data-theme="dark"] .msg-user .bubble {
            color: #ffffff;
            box-shadow: 0 12px 26px rgba(0, 122, 255, 0.30);
        }
        body[data-theme="dark"] .msg-bot .bubble {
            background: rgba(28, 28, 31, 0.96);
            color: #ffffff;
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.25);
        }
        body[data-theme="dark"] .input-area {
            background: rgba(28, 28, 31, 0.72);
            border: 1px solid rgba(255, 255, 255, 0.08);
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
        }
        body[data-theme="dark"] .input-area textarea {
            color: #ffffff;
        }
        body[data-theme="dark"] .input-area textarea::placeholder {
            color: #8e8e93;
        }
        body[data-theme="dark"] .status {
            color: #8e8e93;
        }

        .subtitle-row {
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 12px;
        }
        .theme-toggle {
            border: none;
            border-radius: 999px;
            padding: 8px 12px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            background: rgba(0, 122, 255, 0.10);
            color: #007aff;
            box-shadow: 0 8px 20px rgba(0, 122, 255, 0.12);
            user-select: none;
            white-space: nowrap;
        }
        .theme-toggle:hover {
            background: rgba(0, 122, 255, 0.16);
        }
        body[data-theme="dark"] .theme-toggle {
            background: rgba(0, 122, 255, 0.20);
            color: #8ec5ff;
            box-shadow: 0 10px 24px rgba(0, 122, 255, 0.18);
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>本地知识库RAG问答系统</h1>
        <div class="subtitle-row">
            <div class="subtitle">
                基于阿里云通义千问 + 本地多模态知识库 · 支持中文问答与溯源展示
            </div>
            <button id="themeToggle" class="theme-toggle" type="button">深色</button>
        </div>
        <div class="chat-box" id="chatBox"></div>
        <div class="input-area">
            <textarea id="questionInput" rows="3" placeholder="请输入你的问题，例如：根据知识库介绍一下项目背景和主要内容"></textarea>
            <button id="sendBtn" onclick="sendQuestion()">发送</button>
        </div>
        <div class="status" id="statusText">就绪</div>
    </div>
    <script>
        const chatBox = document.getElementById('chatBox');
        const questionInput = document.getElementById('questionInput');
        const sendBtn = document.getElementById('sendBtn');
        const statusText = document.getElementById('statusText');
        const themeToggle = document.getElementById('themeToggle');

        const THEME_KEY = 'ragku_ui_theme_v1';

        function applyTheme(theme) {
            // theme: 'dark' | 'light'
            if (!document.body) return;
            if (theme === 'dark') {
                document.body.setAttribute('data-theme', 'dark');
                if (themeToggle) themeToggle.textContent = '浅色';
            } else {
                document.body.removeAttribute('data-theme');
                if (themeToggle) themeToggle.textContent = '深色';
            }
            try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
        }

        function initTheme() {
            var saved = null;
            try { saved = localStorage.getItem(THEME_KEY); } catch (e) {}
            if (saved === 'dark' || saved === 'light') {
                applyTheme(saved);
                return;
            }
            // 默认跟随系统
            var prefersDark = false;
            try { prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches; } catch (e) {}
            applyTheme(prefersDark ? 'dark' : 'light');
        }

        if (themeToggle) {
            initTheme();
            themeToggle.addEventListener('click', function () {
                var curDark = document.body && document.body.getAttribute('data-theme') === 'dark';
                applyTheme(curDark ? 'light' : 'dark');
            });
        }

        function appendMessage(role, text, contexts) {
            const wrap = document.createElement('div');
            wrap.className = 'msg ' + (role === 'user' ? 'msg-user' : 'msg-bot');

            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.textContent = text;
            wrap.appendChild(bubble);

            if (role === 'bot' && Array.isArray(contexts) && contexts.length > 0) {
                const ctxDiv = document.createElement('div');
                ctxDiv.className = 'contexts';
                ctxDiv.innerHTML = '<strong>参考片段：</strong><br>' + contexts.map((c, idx) =>
                    `【${idx + 1}】来源：${c.source}<br/>预览：${c.text_preview}`
                ).join('<br><br>');
                wrap.appendChild(ctxDiv);
            }

            chatBox.appendChild(wrap);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        async function sendQuestion() {
            const q = questionInput.value.trim();
            if (!q) return;

            appendMessage('user', q);
            questionInput.value = '';
            sendBtn.disabled = true;
            statusText.textContent = '正在向后端检索知识并生成回答，请稍候…';

            try {
                const resp = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: q })
                });
                if (!resp.ok) {
                    throw new Error('HTTP ' + resp.status);
                }
                const data = await resp.json();
                appendMessage('bot', data.answer || '后端未返回回答。', data.contexts || []);
            } catch (err) {
                console.error(err);
                appendMessage('bot', '请求后端失败，请检查服务是否在运行，或稍后再试。', []);
            } finally {
                sendBtn.disabled = false;
                statusText.textContent = '就绪';
            }
        }

        questionInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendQuestion();
            }
        });
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

