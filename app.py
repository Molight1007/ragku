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
    """千问风格的中文网页聊天界面。"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8" />
    <title>本地知识库问答系统</title>
    <style>
        * {
            box-sizing: border-box;
        }
        body {
            font-family: "Microsoft YaHei", "微软雅黑", sans-serif;
            margin: 0;
            background: #f2f2f3;
            color: #1f2330;
        }
        .page {
            min-height: 100vh;
            max-width: 980px;
            margin: 0 auto;
            padding: 24px 20px 36px;
            display: flex;
            flex-direction: column;
        }
        .top-tools {
            display: flex;
            justify-content: flex-end;
            margin-bottom: 28px;
        }
        .clear-btn {
            border: 1px solid #d9dbe2;
            background: #ffffff;
            color: #4a4f5d;
            border-radius: 999px;
            font-size: 13px;
            padding: 8px 14px;
            cursor: pointer;
            box-shadow: 0 2px 6px rgba(28, 39, 64, 0.06);
        }
        .welcome {
            text-align: center;
            font-size: 42px;
            font-weight: 600;
            letter-spacing: 1px;
            margin-top: 40px;
            margin-bottom: 26px;
        }
        .chat-box {
            flex: 1;
            display: block;
            overflow-y: auto;
            padding: 0;
            border-radius: 0;
            background: transparent;
            box-shadow: none;
            transition: padding 0.2s ease;
        }
        .chat-box.active {
            padding: 10px 10px 16px;
            border-radius: 16px;
            background: rgba(255, 255, 255, 0.38);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
        }
        .msg {
            margin-bottom: 12px;
            display: flex;
            align-items: flex-start;
            gap: 8px;
        }
        .msg-user {
            justify-content: flex-end;
        }
        .msg-bot {
            justify-content: flex-start;
        }
        .avatar {
            width: 30px;
            height: 30px;
            border-radius: 50%;
            flex-shrink: 0;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 13px;
            font-weight: 700;
        }
        .avatar-bot {
            background: #e8ebf2;
            color: #374151;
        }
        .avatar-user {
            background: #d8e5ff;
            color: #355ddf;
        }
        .bubble {
            max-width: min(82%, 880px);
            padding: 10px 13px;
            border-radius: 12px;
            line-height: 1.6;
            font-size: 14px;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .msg-user .bubble {
            background: #8eaefb;
            color: #fff;
            border-radius: 12px 12px 4px 12px;
            box-shadow: 0 3px 10px rgba(120, 149, 230, 0.20);
        }
        .msg-bot .bubble {
            background: #fcfcfd;
            color: #1f2937;
            border: 1px solid #e4e6eb;
            border-radius: 4px 12px 12px 12px;
            box-shadow: 0 2px 8px rgba(33, 43, 60, 0.06);
        }
        .contexts {
            margin-top: 8px;
            padding: 8px 10px;
            background: #f7f8fb;
            border: 1px solid #eceef3;
            border-radius: 10px;
            font-size: 12px;
            color: #4b5563;
        }
        .composer-wrap {
            margin-top: 12px;
        }
        .composer {
            display: flex;
            align-items: flex-end;
            gap: 10px;
            background: #f7f7f8;
            border: 1px solid #dcdee4;
            border-radius: 28px;
            box-shadow: 0 10px 24px rgba(50, 59, 81, 0.08), 0 2px 6px rgba(50, 59, 81, 0.05);
            padding: 8px 14px;
        }
        .question-input {
            flex: 1;
            width: 100%;
            border: none;
            outline: none;
            background: transparent;
            font-size: 16px;
            line-height: 1.4;
            min-height: 40px;
            max-height: 220px;
            resize: none;
            overflow-y: auto;
            font-family: inherit;
            color: #1f2330;
        }
        .question-input::placeholder {
            font-size: inherit;
            color: #b6b9c3;
            font-weight: 500;
        }
        .composer-bottom {
            margin-top: 0;
            display: flex;
            align-items: center;
            justify-content: flex-end;
            gap: 8px;
            position: relative;
        }
        .plus-wrap {
            position: relative;
            display: inline-flex;
            align-items: center;
        }
        .plus-btn {
            width: 40px;
            height: 40px;
            border: 1px solid #d7dbe6;
            border-radius: 999px;
            background: #ffffff;
            color: #5d6473;
            font-size: 24px;
            line-height: 1;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            box-shadow: 0 4px 10px rgba(33, 43, 60, 0.10);
        }
        .plus-menu {
            position: absolute;
            right: 0;
            bottom: calc(100% + 10px);
            min-width: 210px;
            background: #ffffff;
            border: 1px solid #e5e7ee;
            border-radius: 16px;
            box-shadow: 0 14px 24px rgba(33, 43, 60, 0.12);
            overflow: hidden;
            display: none;
            z-index: 20;
        }
        .plus-menu.show {
            display: block;
        }
        .plus-item {
            width: 100%;
            border: none;
            background: #fff;
            color: #1f2330;
            text-align: left;
            padding: 12px 14px;
            font-size: 15px;
            cursor: pointer;
            display: inline-flex;
            align-items: center;
            gap: 10px;
        }
        .plus-item + .plus-item {
            border-top: 1px solid #edf0f5;
        }
        .plus-item:hover {
            background: #f8f9fc;
        }
        .plus-icon {
            width: 18px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            color: #4b5563;
            font-size: 16px;
        }
        .send-btn {
            width: 40px;
            height: 40px;
            border: none;
            border-radius: 999px;
            background: #bfd0f8;
            color: #fff;
            font-size: 18px;
            font-weight: 700;
            cursor: pointer;
            flex-shrink: 0;
            box-shadow: 0 4px 10px rgba(106, 138, 220, 0.28);
        }
        .send-btn:disabled {
            background: #cad8fb;
            cursor: not-allowed;
        }
        .status {
            margin-top: 8px;
            font-size: 12px;
            color: #7a808f;
            text-align: center;
        }
        @media (max-width: 900px) {
            .page {
                padding: 16px 12px 24px;
            }
            .welcome {
                font-size: 30px;
                margin-top: 26px;
            }
            .question-input {
                font-size: 16px;
            }
        }
    </style>
</head>
<body>
    <div class="page">
        <div class="top-tools">
            <button class="clear-btn" onclick="resetChat()">新对话</button>
        </div>
        <div class="welcome" id="welcomeText">你好，欢迎使用知识库问答</div>
        <div class="chat-box" id="chatBox"></div>
        <div class="composer-wrap">
            <div class="composer">
                <textarea id="questionInput" class="question-input" rows="1" placeholder="请输入你的问题"></textarea>
                <div class="composer-bottom">
                    <div class="plus-wrap">
                        <button id="plusBtn" class="plus-btn" type="button" aria-label="更多功能">+</button>
                        <div id="plusMenu" class="plus-menu">
                            <button class="plus-item" type="button"><span class="plus-icon">📷</span>拍照识文字</button>
                            <button class="plus-item" type="button"><span class="plus-icon">🖼</span>图片识文字</button>
                            <button class="plus-item" type="button"><span class="plus-icon">📎</span>文件</button>
                        </div>
                    </div>
                    <button id="sendBtn" class="send-btn" onclick="sendQuestion()">↑</button>
                </div>
            </div>
            <div class="status" id="statusText">就绪</div>
        </div>
    </div>
    <script>
        const chatBox = document.getElementById('chatBox');
        const questionInput = document.getElementById('questionInput');
        const sendBtn = document.getElementById('sendBtn');
        const statusText = document.getElementById('statusText');
        const welcomeText = document.getElementById('welcomeText');
        const plusBtn = document.getElementById('plusBtn');
        const plusMenu = document.getElementById('plusMenu');

        function setStatus(text) {
            statusText.textContent = text;
        }

        function autoResizeInput() {
            questionInput.style.height = 'auto';
            questionInput.style.height = Math.min(questionInput.scrollHeight, 220) + 'px';
        }

        function hidePlusMenu() {
            plusMenu.classList.remove('show');
        }

        function setChatBoxActive(active) {
            chatBox.classList.toggle('active', active);
        }

        function createAvatar(role) {
            const avatar = document.createElement('span');
            if (role === 'user') {
                avatar.className = 'avatar avatar-user';
                avatar.textContent = '我';
            } else {
                avatar.className = 'avatar avatar-bot';
                avatar.textContent = '助';
            }
            return avatar;
        }

        function appendMessage(role, text, contexts) {
            const wrap = document.createElement('div');
            wrap.className = 'msg ' + (role === 'user' ? 'msg-user' : 'msg-bot');

            const bubble = document.createElement('div');
            bubble.className = 'bubble';
            bubble.textContent = text;

            if (role === 'user') {
                wrap.appendChild(bubble);
                wrap.appendChild(createAvatar(role));
            } else {
                wrap.appendChild(createAvatar(role));
                const contentWrap = document.createElement('div');
                contentWrap.style.maxWidth = 'calc(100% - 40px)';
                contentWrap.appendChild(bubble);

                if (Array.isArray(contexts) && contexts.length > 0) {
                    const ctxDiv = document.createElement('div');
                    ctxDiv.className = 'contexts';
                    ctxDiv.innerHTML = '<strong>参考片段</strong><br>' + contexts.map((c, idx) =>
                        `【${idx + 1}】来源：${c.source}<br/>相关度：${Number(c.score || 0).toFixed(3)}<br/>预览：${c.text_preview}`
                    ).join('<br><br>');
                    contentWrap.appendChild(ctxDiv);
                }
                wrap.appendChild(contentWrap);
            }

            chatBox.appendChild(wrap);
            chatBox.scrollTop = chatBox.scrollHeight;
        }

        function resetChat() {
            chatBox.innerHTML = '';
            setChatBoxActive(false);
            hidePlusMenu();
            welcomeText.style.display = 'block';
            setStatus('就绪');
        }

        async function sendQuestion() {
            const q = questionInput.value.trim();
            if (!q) return;

            welcomeText.style.display = 'none';
            appendMessage('user', q);
            questionInput.value = '';
            autoResizeInput();
            sendBtn.disabled = true;
            setStatus('检索中');

            try {
                const resp = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: q })
                });
                if (!resp.ok) {
                    throw new Error('请求失败，状态码：' + resp.status);
                }
                const data = await resp.json();
                appendMessage('bot', data.answer || '后端未返回回答。', data.contexts || []);
                setChatBoxActive(true);
                setStatus('完成');
            } catch (err) {
                console.error(err);
                appendMessage('bot', '请求后端失败，请检查服务是否在运行，或稍后再试。', []);
                setChatBoxActive(true);
                setStatus('异常');
            } finally {
                sendBtn.disabled = false;
                setTimeout(() => setStatus('就绪'), 800);
            }
        }

        questionInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendQuestion();
            }
        });
        questionInput.addEventListener('input', autoResizeInput);
        plusBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            plusMenu.classList.toggle('show');
        });
        document.addEventListener('click', function (e) {
            if (!plusMenu.contains(e.target) && e.target !== plusBtn) {
                hidePlusMenu();
            }
        });
        plusMenu.addEventListener('click', function () {
            hidePlusMenu();
        });

        resetChat();
        autoResizeInput();
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

