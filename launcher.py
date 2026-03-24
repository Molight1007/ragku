from __future__ import annotations

import contextlib
import io
import os
import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import END, DISABLED, NORMAL, Button, Frame, Label, Message, StringVar, Text, Tk, Toplevel
from tkinter import filedialog, messagebox

import uvicorn


def _app_base_dir() -> Path:
    """获取应用运行目录。

    说明：
    - 开发运行：以源码所在目录为准
    - 打包运行（PyInstaller）：以 EXE 所在目录为准，便于读写 .env 和索引文件
    """
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_base_dir()
ENV_FILE = APP_DIR / ".env"
INDEX_STORE = APP_DIR / "index_store.npy"
INDEX_META = APP_DIR / "index_meta.npy"

DEFAULT_DATA_DIR = Path(r"D:\知识库资料20")


def _read_env_key() -> str:
    """从 .env 读取 DASHSCOPE_API_KEY（若存在）。"""
    if not ENV_FILE.exists():
        return ""
    try:
        text = ENV_FILE.read_text(encoding="utf-8", errors="ignore")
    except Exception:  # noqa: BLE001
        return ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("DASHSCOPE_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def _write_env_key(key: str) -> None:
    """将密钥写入 .env（UTF-8）。"""
    ENV_FILE.write_text(f"DASHSCOPE_API_KEY={key}\n", encoding="utf-8")


def _apply_env_key_to_process() -> None:
    """将 .env 的密钥写入当前进程环境变量，供 DashScope 读取。"""
    key = _read_env_key()
    if key:
        os.environ["DASHSCOPE_API_KEY"] = key


class LauncherApp:
    """Windows 一键启动器（用于比赛展示）。"""

    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("本地知识库RAG问答系统 - 启动器")
        self.root.geometry("860x560")
        self.root.minsize(860, 560)

        self.status_var = StringVar(value="就绪")
        self.server_thread: threading.Thread | None = None
        self.uvicorn_server: uvicorn.Server | None = None
        self.data_dir: Path = DEFAULT_DATA_DIR

        self._build_ui()
        self._refresh_status()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        top = Frame(self.root, padx=16, pady=12)
        top.pack(fill="x")

        Label(top, text="本地知识库RAG问答系统", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        Message(
            top,
            text="点击按钮即可配置密钥、构建索引并启动网页服务。适合比赛现场演示：可展示回答与参考片段溯源。",
            width=820,
            font=("Segoe UI", 10),
        ).pack(anchor="w", pady=(6, 0))

        btns = Frame(self.root, padx=16, pady=8)
        btns.pack(fill="x")

        Button(btns, text="1) 配置密钥", width=16, command=self.action_config_key).pack(side="left", padx=(0, 10))
        Button(btns, text="选择知识库目录", width=16, command=self.action_choose_dir).pack(side="left", padx=(0, 10))
        Button(btns, text="2) 重建索引", width=16, command=self.action_build_index).pack(side="left", padx=(0, 10))
        Button(btns, text="3) 启动网页", width=16, command=self.action_start_server).pack(side="left", padx=(0, 10))
        Button(btns, text="打开聊天页面", width=16, command=self.action_open_chat).pack(side="left", padx=(0, 10))
        Button(btns, text="停止服务", width=16, command=self.action_stop_server).pack(side="left")

        mid = Frame(self.root, padx=16, pady=8)
        mid.pack(fill="both", expand=True)

        Label(mid, text="运行日志（用于排错/展示）", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.log_text = Text(mid, height=20, wrap="word", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True, pady=(6, 0))
        self.log_text.insert(END, "提示：首次运行请先点击“配置密钥”，然后“重建索引”。\n")
        self.log_text.config(state=DISABLED)

        bottom = Frame(self.root, padx=16, pady=10)
        bottom.pack(fill="x")
        Label(bottom, textvariable=self.status_var, font=("Segoe UI", 10)).pack(anchor="w")

    def log(self, msg: str) -> None:
        now = time.strftime("%H:%M:%S")
        line = f"[{now}] {msg}\n"
        self.log_text.config(state=NORMAL)
        self.log_text.insert(END, line)
        self.log_text.see(END)
        self.log_text.config(state=DISABLED)

    def _refresh_status(self) -> None:
        key_ok = bool(_read_env_key())
        idx_ok = INDEX_STORE.exists() and INDEX_META.exists()
        srv_ok = self.uvicorn_server is not None and self.uvicorn_server.started

        parts = []
        parts.append("密钥：已配置" if key_ok else "密钥：未配置")
        parts.append("索引：已就绪" if idx_ok else "索引：未构建")
        parts.append("服务：运行中" if srv_ok else "服务：未启动")
        parts.append(f"知识库目录：{self.data_dir}")
        self.status_var.set(" | ".join(parts))

        self.root.after(1000, self._refresh_status)

    def action_config_key(self) -> None:
        win = Toplevel(self.root)
        win.title("配置密钥")
        win.geometry("520x220")
        win.resizable(False, False)

        Label(win, text="请输入阿里云 DashScope 密钥（DASHSCOPE_API_KEY）", font=("Segoe UI", 10, "bold")).pack(
            anchor="w", padx=16, pady=(14, 6)
        )
        Message(
            win,
            text="说明：密钥将写入本机项目目录下的 .env（UTF-8）。请勿把 .env 上传或分享给他人。",
            width=480,
            font=("Segoe UI", 9),
        ).pack(anchor="w", padx=16)

        entry = Text(win, height=2, font=("Consolas", 10))
        entry.pack(fill="x", padx=16, pady=(10, 10))
        entry.insert(END, _read_env_key())

        def on_save() -> None:
            key = entry.get("1.0", END).strip()
            if not key:
                messagebox.showwarning("提示", "密钥不能为空。")
                return
            _write_env_key(key)
            self.log("已写入 .env（密钥已配置）。")
            win.destroy()

        Frame(win).pack(fill="x")
        Button(win, text="保存", width=10, command=on_save).pack(side="right", padx=16, pady=(0, 14))

    def action_choose_dir(self) -> None:
        """选择知识库目录（用于构建索引）。"""
        path = filedialog.askdirectory(title="选择知识库目录", initialdir=str(self.data_dir))
        if not path:
            return
        self.data_dir = Path(path)
        self.log(f"已选择知识库目录：{self.data_dir}")

    def action_build_index(self) -> None:
        def worker() -> None:
            self.log("准备重建索引……")
            if not _read_env_key():
                self.log("未配置密钥，请先点击“配置密钥”。")
                return
            _apply_env_key_to_process()

            data_dir = self.data_dir
            if not data_dir.exists():
                self.log(f"知识库目录不存在：{data_dir}")
                return

            self.log(f"开始构建索引，知识库目录：{data_dir}")
            try:
                # 关键：打包后不要在模块导入阶段就加载 config/.env
                # 因此这里延迟导入 ingest，并在导入前确保 cwd 和环境变量已就绪
                os.chdir(str(APP_DIR))
                from ingest import build_embeddings, collect_documents  # noqa: WPS433

                docs = collect_documents(data_dir)
                self.log(f"完成收集，共得到文档分片数量: {len(docs)}")
                self.log("开始生成文本向量……（数据量大时会较久）")

                # 捕获 build_embeddings 内部 print 的详细错误，显示给用户
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    embeddings, metadatas = build_embeddings(docs)
                detail = buf.getvalue().strip()
                if detail:
                    for line in detail.splitlines():
                        self.log(line)

                # 直接用 APP_DIR 下的文件名保存，避免路径混乱
                import numpy as np  # noqa: WPS433

                np.save(INDEX_STORE, embeddings)
                np.save(INDEX_META, np.array(metadatas, dtype=object))

                self.log("索引构建完成：已生成 index_store.npy / index_meta.npy")
            except Exception as e:  # noqa: BLE001
                self.log(f"索引构建失败：{e}")

        threading.Thread(target=worker, daemon=True).start()

    def action_start_server(self) -> None:
        if self.uvicorn_server is not None and self.uvicorn_server.started:
            self.log("服务已在运行中。")
            return
        if not _read_env_key():
            self.log("未配置密钥，请先点击“配置密钥”。")
            return
        if not (INDEX_STORE.exists() and INDEX_META.exists()):
            self.log("未检测到索引文件，请先点击“重建索引”。")
            return
        _apply_env_key_to_process()

        self.log("正在启动网页服务（uvicorn）……")
        # 延迟导入 FastAPI app，避免打包环境下导入时读取不到 .env
        os.chdir(str(APP_DIR))
        from app import app as fastapi_app  # noqa: WPS433

        config = uvicorn.Config(
            fastapi_app,
            host="0.0.0.0",
            port=8000,
            log_level="info",
            access_log=False,
        )
        self.uvicorn_server = uvicorn.Server(config)

        def run_server() -> None:
            try:
                self.uvicorn_server.run()
            except Exception as e:  # noqa: BLE001
                self.log(f"服务启动异常：{e}")

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()
        self.root.after(1200, self.action_open_chat)

    def action_open_chat(self) -> None:
        webbrowser.open("http://127.0.0.1:8000/chat-ui")
        self.log("已尝试打开浏览器：/chat-ui")

    def action_stop_server(self) -> None:
        if self.uvicorn_server is None or not self.uvicorn_server.started:
            self.log("服务未运行。")
            self.uvicorn_server = None
            return

        self.log("正在停止服务……")
        try:
            self.uvicorn_server.should_exit = True
            time.sleep(0.8)
        except Exception as e:  # noqa: BLE001
            self.log(f"停止服务失败：{e}")
        finally:
            self.uvicorn_server = None
            self.log("服务已停止。")

    def on_close(self) -> None:
        if self.uvicorn_server is not None and self.uvicorn_server.started:
            if not messagebox.askyesno("退出确认", "检测到服务仍在运行，是否停止服务并退出？"):
                return
            self.action_stop_server()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    os.chdir(str(APP_DIR))
    LauncherApp().run()


if __name__ == "__main__":
    main()

