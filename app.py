from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ingest import build_embeddings, collect_documents, save_index
from rag_service import rag_answer
from workspace_service import create_workspace, delete_workspace, get_workspace, list_workspaces


class ChatRequest(BaseModel):
    """前端发送的问题请求模型。"""

    question: str
    workspace_id: Optional[str] = None


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
        .container { max-width: 1280px; margin: 0 auto; padding: 20px 16px 28px; }
        h1 {
            font-size: 24px;
            margin-bottom: 8px;
        }
        .subtitle {
            color: #666;
            font-size: 14px;
            margin-bottom: 16px;
        }
        .layout {
            display: grid;
            grid-template-columns: 280px 1fr 320px;
            gap: 14px;
            align-items: start;
        }
        .panel {
            background: rgba(255, 255, 255, 0.72);
            border-radius: 18px;
            border: 1px solid rgba(0, 0, 0, 0.06);
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.05);
            backdrop-filter: blur(16px);
            overflow: hidden;
        }
        .panel-header {
            padding: 12px 12px 10px;
            border-bottom: 1px solid rgba(0, 0, 0, 0.06);
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 10px;
        }
        .panel-title { font-size: 13px; font-weight: 800; letter-spacing: 0.2px; color: #111827; }
        .panel-body { padding: 10px 12px 12px; }

        .history-list { max-height: 520px; overflow: auto; padding: 8px 8px 12px; }
        .history-item {
            border-radius: 12px;
            padding: 10px 10px;
            margin: 0 0 8px 0;
            cursor: pointer;
            background: rgba(0, 0, 0, 0.03);
            border: 1px solid rgba(0, 0, 0, 0.06);
        }
        .history-item:hover { background: rgba(0, 122, 255, 0.08); border-color: rgba(0, 122, 255, 0.18); }
        .history-item .t { font-size: 13px; font-weight: 700; margin-bottom: 4px; }
        .history-item .s { font-size: 12px; color: #6b7280; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        .history-actions { display: flex; gap: 8px; }

        .chat-wrap { min-width: 0; }
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
            .panel {
                background: rgba(18, 18, 20, 0.78);
                border: 1px solid rgba(255, 255, 255, 0.07);
                box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
            }
            .panel-header { border-bottom: 1px solid rgba(255, 255, 255, 0.08); }
            .panel-title { color: #e5e7eb; }
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
            .history-item {
                background: rgba(255, 255, 255, 0.06);
                border: 1px solid rgba(255, 255, 255, 0.08);
            }
            .history-item:hover { background: rgba(0, 122, 255, 0.18); border-color: rgba(0, 122, 255, 0.30); }
            .history-item .s { color: #a1a1aa; }
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
        body[data-theme="dark"] .panel {
            background: rgba(18, 18, 20, 0.78);
            border: 1px solid rgba(255, 255, 255, 0.07);
            box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
        }
        body[data-theme="dark"] .panel-header { border-bottom: 1px solid rgba(255, 255, 255, 0.08); }
        body[data-theme="dark"] .panel-title { color: #e5e7eb; }
        body[data-theme="dark"] .history-item {
            background: rgba(255, 255, 255, 0.06);
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        body[data-theme="dark"] .history-item:hover { background: rgba(0, 122, 255, 0.18); border-color: rgba(0, 122, 255, 0.30); }
        body[data-theme="dark"] .history-item .s { color: #a1a1aa; }

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

        .btn {
            border: none;
            border-radius: 999px;
            padding: 8px 10px;
            font-size: 12.5px;
            font-weight: 700;
            cursor: pointer;
            background: rgba(0, 0, 0, 0.06);
            color: #111827;
            user-select: none;
            white-space: nowrap;
        }
        .btn.primary { background: rgba(0, 122, 255, 0.14); color: #007aff; }
        .btn.danger { background: rgba(239, 68, 68, 0.14); color: #ef4444; }
        .btn:disabled { opacity: 0.55; cursor: not-allowed; }
        body[data-theme="dark"] .btn { background: rgba(255, 255, 255, 0.10); color: #e5e7eb; }
        body[data-theme="dark"] .btn.primary { background: rgba(0, 122, 255, 0.22); color: #8ec5ff; }
        body[data-theme="dark"] .btn.danger { background: rgba(239, 68, 68, 0.22); color: #ff9aa2; }

        .field {
            width: 100%;
            border-radius: 12px;
            border: 1px solid rgba(0, 0, 0, 0.08);
            background: rgba(255, 255, 255, 0.82);
            padding: 10px 10px;
            font-size: 13.5px;
            outline: none;
        }
        body[data-theme="dark"] .field {
            background: rgba(28, 28, 31, 0.72);
            border: 1px solid rgba(255, 255, 255, 0.10);
            color: #ffffff;
        }

        .ws-row { display: flex; gap: 8px; align-items: center; }
        .ws-select { flex: 1; }
        .muted { font-size: 12px; color: #6b7280; }
        body[data-theme="dark"] .muted { color: #a1a1aa; }
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
        <div class="layout">
            <div class="panel" id="historyPanel">
                <div class="panel-header">
                    <div class="panel-title">历史记录</div>
                    <div class="history-actions">
                        <button class="btn" id="newChatBtn" type="button">新对话</button>
                        <button class="btn danger" id="clearHistoryBtn" type="button">清空</button>
                    </div>
                </div>
                <div class="history-list" id="historyList"></div>
            </div>

            <div class="chat-wrap">
                <div class="chat-box" id="chatBox"></div>
                <div class="input-area">
                    <textarea id="questionInput" rows="3" placeholder="请输入你的问题，例如：根据知识库介绍一下项目背景和主要内容"></textarea>
                    <button id="sendBtn" onclick="sendQuestion()">发送</button>
                </div>
                <div class="status" id="statusText">就绪</div>
            </div>

            <div class="panel" id="workspacePanel">
                <div class="panel-header">
                    <div class="panel-title">工作区</div>
                    <button class="btn primary" id="createWsBtn" type="button">创建</button>
                </div>
                <div class="panel-body">
                    <div class="ws-row" style="margin-bottom:10px;">
                        <select class="field ws-select" id="workspaceSelect"></select>
                        <button class="btn danger" id="deleteWsBtn" type="button" title="删除当前工作区">删除</button>
                    </div>
                    <div style="display:flex; gap:8px; align-items:center; margin-bottom:10px;">
                        <input id="kbFiles" type="file" multiple class="field" style="padding:8px;" />
                    </div>
                    <div style="display:flex; gap:8px; align-items:center;">
                        <button class="btn primary" id="uploadBtn" type="button">上传</button>
                        <button class="btn" id="rebuildBtn" type="button">重建索引</button>
                    </div>
                    <div class="muted" style="margin-top:10px;">
                        提示：不同工作区的知识库与索引彼此隔离。
                    </div>
                </div>
            </div>
        </div>
    </div>
    <script>
        const chatBox = document.getElementById('chatBox');
        const questionInput = document.getElementById('questionInput');
        const sendBtn = document.getElementById('sendBtn');
        const statusText = document.getElementById('statusText');
        const themeToggle = document.getElementById('themeToggle');
        const historyList = document.getElementById('historyList');
        const newChatBtn = document.getElementById('newChatBtn');
        const clearHistoryBtn = document.getElementById('clearHistoryBtn');

        const workspaceSelect = document.getElementById('workspaceSelect');
        const createWsBtn = document.getElementById('createWsBtn');
        const deleteWsBtn = document.getElementById('deleteWsBtn');
        const kbFiles = document.getElementById('kbFiles');
        const uploadBtn = document.getElementById('uploadBtn');
        const rebuildBtn = document.getElementById('rebuildBtn');

        const THEME_KEY = 'ragku_ui_theme_v1';
        const HISTORY_KEY = 'ragku_chat_history_v1';
        const CURRENT_CHAT_KEY = 'ragku_current_chat_v1';
        const CURRENT_WS_KEY = 'ragku_current_workspace_v1';

        function nowTs() { return Date.now ? Date.now() : new Date().getTime(); }
        function safeJsonParse(s, fallback) { try { return JSON.parse(s); } catch (e) { return fallback; } }

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

        function getHistory() {
            var raw = null;
            try { raw = localStorage.getItem(HISTORY_KEY); } catch (e) {}
            var arr = safeJsonParse(raw || '[]', []);
            if (!Array.isArray(arr)) return [];
            return arr;
        }

        function setHistory(arr) {
            try { localStorage.setItem(HISTORY_KEY, JSON.stringify(arr || [])); } catch (e) {}
        }

        function getCurrentChatId() {
            var id = null;
            try { id = localStorage.getItem(CURRENT_CHAT_KEY); } catch (e) {}
            return (id || '').trim();
        }

        function setCurrentChatId(id) {
            try { localStorage.setItem(CURRENT_CHAT_KEY, id || ''); } catch (e) {}
        }

        function ensureCurrentChat() {
            var id = getCurrentChatId();
            var hist = getHistory();
            var found = hist.find(x => x && x.id === id);
            if (found) return found;
            // 创建新对话
            var newId = 'c_' + nowTs() + '_' + Math.random().toString(16).slice(2);
            var chat = { id: newId, title: '新对话', created_at: nowTs(), messages: [] };
            hist.unshift(chat);
            setHistory(hist);
            setCurrentChatId(newId);
            return chat;
        }

        function renderHistory() {
            var hist = getHistory();
            var cur = getCurrentChatId();
            if (!historyList) return;
            historyList.innerHTML = '';
            hist.forEach(item => {
                if (!item) return;
                var div = document.createElement('div');
                div.className = 'history-item';
                div.style.outline = (item.id === cur) ? '2px solid rgba(0, 122, 255, 0.35)' : 'none';
                var t = document.createElement('div');
                t.className = 't';
                t.textContent = item.title || '未命名对话';
                var s = document.createElement('div');
                s.className = 's';
                var last = (item.messages && item.messages.length) ? item.messages[item.messages.length - 1].text : '';
                s.textContent = last ? last.slice(0, 60) : '（暂无消息）';
                div.appendChild(t);
                div.appendChild(s);
                div.addEventListener('click', function () {
                    setCurrentChatId(item.id);
                    loadChatToUI(item.id);
                });
                historyList.appendChild(div);
            });
        }

        function loadChatToUI(chatId) {
            var hist = getHistory();
            var item = hist.find(x => x && x.id === chatId);
            if (!item) {
                ensureCurrentChat();
                renderHistory();
                chatBox.innerHTML = '';
                return;
            }
            chatBox.innerHTML = '';
            (item.messages || []).forEach(m => appendMessage(m.role, m.text, m.contexts || []));
            renderHistory();
        }

        function appendToHistory(role, text, contexts) {
            var hist = getHistory();
            var curId = getCurrentChatId();
            var item = hist.find(x => x && x.id === curId);
            if (!item) item = ensureCurrentChat();
            if (!Array.isArray(item.messages)) item.messages = [];
            item.messages.push({ role: role, text: text, contexts: contexts || [], ts: nowTs() });
            if (!item.title || item.title === '新对话') {
                if (role === 'user' && text) item.title = text.slice(0, 18);
            }
            // 置顶
            hist = hist.filter(x => x && x.id !== item.id);
            hist.unshift(item);
            setHistory(hist);
            renderHistory();
        }

        if (newChatBtn) {
            newChatBtn.addEventListener('click', function () {
                setCurrentChatId('');
                var chat = ensureCurrentChat();
                chatBox.innerHTML = '';
                renderHistory();
            });
        }
        if (clearHistoryBtn) {
            clearHistoryBtn.addEventListener('click', function () {
                if (!confirm('确定要清空所有历史记录吗？此操作仅影响本浏览器。')) return;
                setHistory([]);
                setCurrentChatId('');
                ensureCurrentChat();
                chatBox.innerHTML = '';
                renderHistory();
            });
        }

        function getCurrentWorkspaceId() {
            var id = null;
            try { id = localStorage.getItem(CURRENT_WS_KEY); } catch (e) {}
            return (id || '').trim();
        }

        function setCurrentWorkspaceId(id) {
            try { localStorage.setItem(CURRENT_WS_KEY, id || ''); } catch (e) {}
        }

        async function refreshWorkspaces() {
            if (!workspaceSelect) return;
            workspaceSelect.innerHTML = '';
            const resp = await fetch('/workspaces');
            const data = await resp.json();
            const list = (data && data.workspaces) ? data.workspaces : [];
            list.forEach(w => {
                const opt = document.createElement('option');
                opt.value = w.id;
                opt.textContent = w.name + '  (' + w.id.slice(0, 6) + ')';
                workspaceSelect.appendChild(opt);
            });
            var cur = getCurrentWorkspaceId();
            if (cur && list.some(w => w.id === cur)) {
                workspaceSelect.value = cur;
            } else if (list.length) {
                workspaceSelect.value = list[0].id;
                setCurrentWorkspaceId(list[0].id);
            }
        }

        if (workspaceSelect) {
            workspaceSelect.addEventListener('change', function () {
                setCurrentWorkspaceId(workspaceSelect.value);
            });
        }
        if (createWsBtn) {
            createWsBtn.addEventListener('click', async function () {
                var name = prompt('请输入工作区名称：', '我的工作区');
                if (name === null) return;
                statusText.textContent = '正在创建工作区…';
                const resp = await fetch('/workspaces', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ name: name || '' })
                });
                if (!resp.ok) {
                    statusText.textContent = '创建失败';
                    alert('创建工作区失败：HTTP ' + resp.status);
                    return;
                }
                const ws = await resp.json();
                await refreshWorkspaces();
                setCurrentWorkspaceId(ws.id);
                workspaceSelect.value = ws.id;
                statusText.textContent = '已创建工作区';
            });
        }
        if (deleteWsBtn) {
            deleteWsBtn.addEventListener('click', async function () {
                var wid = getCurrentWorkspaceId();
                if (!wid) return alert('请先选择工作区');
                if (!confirm('确定删除当前工作区吗？会删除该工作区的已上传文件与索引。')) return;
                statusText.textContent = '正在删除工作区…';
                const resp = await fetch('/workspaces/' + encodeURIComponent(wid), { method: 'DELETE' });
                if (!resp.ok) {
                    statusText.textContent = '删除失败';
                    alert('删除工作区失败：HTTP ' + resp.status);
                    return;
                }
                setCurrentWorkspaceId('');
                await refreshWorkspaces();
                statusText.textContent = '已删除工作区';
            });
        }
        if (uploadBtn) {
            uploadBtn.addEventListener('click', async function () {
                var wid = getCurrentWorkspaceId();
                if (!wid) return alert('请先选择工作区');
                if (!kbFiles || !kbFiles.files || !kbFiles.files.length) return alert('请选择要上传的文件');
                statusText.textContent = '正在上传文件…';
                uploadBtn.disabled = true;
                const form = new FormData();
                for (let i = 0; i < kbFiles.files.length; i++) form.append('files', kbFiles.files[i]);
                const resp = await fetch('/workspaces/' + encodeURIComponent(wid) + '/upload', { method: 'POST', body: form });
                uploadBtn.disabled = false;
                if (!resp.ok) {
                    statusText.textContent = '上传失败';
                    alert('上传失败：HTTP ' + resp.status);
                    return;
                }
                const data = await resp.json();
                statusText.textContent = '上传完成：' + (data.saved || 0) + ' 个文件';
            });
        }
        if (rebuildBtn) {
            rebuildBtn.addEventListener('click', async function () {
                var wid = getCurrentWorkspaceId();
                if (!wid) return alert('请先选择工作区');
                statusText.textContent = '正在重建索引（可能需要较久）…';
                rebuildBtn.disabled = true;
                const resp = await fetch('/workspaces/' + encodeURIComponent(wid) + '/rebuild-index', { method: 'POST' });
                rebuildBtn.disabled = false;
                if (!resp.ok) {
                    statusText.textContent = '重建失败';
                    alert('重建索引失败：HTTP ' + resp.status);
                    return;
                }
                const data = await resp.json();
                statusText.textContent = '索引已就绪：分片 ' + (data.chunks || 0);
            });
        }

        (async function bootstrap() {
            // 初始化历史
            ensureCurrentChat();
            loadChatToUI(getCurrentChatId());
            // 初始化工作区
            await refreshWorkspaces();
        })();

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
            appendToHistory('user', q, []);
            questionInput.value = '';
            sendBtn.disabled = true;
            statusText.textContent = '正在向后端检索知识并生成回答，请稍候…';

            try {
                const wid = getCurrentWorkspaceId();
                const resp = await fetch('/chat', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ question: q, workspace_id: wid || null })
                });
                if (!resp.ok) {
                    throw new Error('HTTP ' + resp.status);
                }
                const data = await resp.json();
                appendMessage('bot', data.answer || '后端未返回回答。', data.contexts || []);
                appendToHistory('bot', data.answer || '后端未返回回答。', data.contexts || []);
            } catch (err) {
                console.error(err);
                appendMessage('bot', '请求后端失败，请检查服务是否在运行，或稍后再试。', []);
                appendToHistory('bot', '请求后端失败，请检查服务是否在运行，或稍后再试。', []);
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


class WorkspaceCreateRequest(BaseModel):
    name: str = ""


class WorkspaceInfo(BaseModel):
    id: str
    name: str
    created_at: int


class WorkspaceListResponse(BaseModel):
    workspaces: List[WorkspaceInfo]


@app.get("/workspaces", response_model=WorkspaceListResponse)
async def workspaces() -> WorkspaceListResponse:
    wss = list_workspaces()
    # 若不存在任何工作区，自动创建一个默认工作区，避免 UI 空态
    if not wss:
        ws = create_workspace("默认工作区")
        wss = [ws]
    return WorkspaceListResponse(
        workspaces=[WorkspaceInfo(id=w.id, name=w.name, created_at=w.created_at) for w in wss]
    )


@app.post("/workspaces", response_model=WorkspaceInfo)
async def create_ws(body: WorkspaceCreateRequest) -> WorkspaceInfo:
    ws = create_workspace(body.name)
    return WorkspaceInfo(id=ws.id, name=ws.name, created_at=ws.created_at)


@app.delete("/workspaces/{workspace_id}")
async def delete_ws(workspace_id: str) -> dict:
    ok = delete_workspace(workspace_id)
    if not ok:
        raise HTTPException(status_code=404, detail="workspace not found")
    return {"ok": True}


@app.post("/workspaces/{workspace_id}/upload")
async def upload_kb_files(workspace_id: str, files: List[UploadFile] = File(...)) -> dict:
    ws = get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="workspace not found")
    ws.kb_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    for f in files:
        name = (f.filename or "").strip()
        if not name:
            continue
        dest = ws.kb_dir / Path(name).name
        # 同名覆盖（更符合“重新上传更新”的直觉）
        content = await f.read()
        dest.write_bytes(content)
        saved += 1
    return {"ok": True, "saved": saved}


@app.post("/workspaces/{workspace_id}/rebuild-index")
async def rebuild_index(workspace_id: str) -> dict:
    ws = get_workspace(workspace_id)
    if ws is None:
        raise HTTPException(status_code=404, detail="workspace not found")
    if not ws.kb_dir.exists():
        raise HTTPException(status_code=400, detail="workspace kb is empty")

    docs = collect_documents(ws.kb_dir)
    if not docs:
        raise HTTPException(status_code=400, detail="no supported files found in workspace kb")

    embeddings, metadatas = build_embeddings(docs)
    save_index(embeddings, metadatas, index_file=ws.index_store, meta_file=ws.index_meta)
    return {"ok": True, "chunks": len(metadatas)}


@app.post("/chat", response_model=ChatResponse)
async def chat(body: ChatRequest) -> ChatResponse:
    """核心聊天接口：接收问题，返回回答和参考片段。"""
    question = body.question.strip()
    if not question:
        return ChatResponse(answer="问题不能为空。", contexts=[])

    ws = get_workspace(body.workspace_id or "")
    if ws is None:
        # 兼容旧用法：没有 workspace_id 时，走全局索引
        answer, contexts_raw = rag_answer(question)
    else:
        answer, contexts_raw = rag_answer(
            question,
            index_file=str(ws.index_store),
            meta_file=str(ws.index_meta),
        )

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

