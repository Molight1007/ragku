from __future__ import annotations

import contextlib
import io
import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import END, DISABLED, NORMAL, Button, Frame, Label, Message, StringVar, Text, Tk, Toplevel
from tkinter import filedialog, messagebox


def _app_base_dir() -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_base_dir()
ENV_FILE = APP_DIR / ".env"
INDEX_STORE = APP_DIR / "index_store.npy"
INDEX_META = APP_DIR / "index_meta.npy"
CHAT_URL = "http://127.0.0.1:8000/chat-ui"
SERVER_PORT = 8000


def _port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def _read_env_key() -> str:
    if not ENV_FILE.exists():
        return ""
    try:
        text = ENV_FILE.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return ""
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("DASHSCOPE_API_KEY="):
            return line.split("=", 1)[1].strip()
    return ""


def _write_env_key(key: str) -> None:
    ENV_FILE.write_text(f"DASHSCOPE_API_KEY={key.strip()}\n", encoding="utf-8")


def _apply_env_key() -> None:
    key = _read_env_key()
    if key:
        os.environ["DASHSCOPE_API_KEY"] = key


def _default_data_dir() -> Path:
    try:
        os.chdir(str(APP_DIR))
        from config import settings

        return Path(settings.default_knowledge_dir)
    except Exception:
        return Path(r"D:\知识库资料20")


# ---------------------------------------------------------------------------
# 控制台模式（双击 RAG启动器.cmd / 终端运行：python launcher.py --console）
# ---------------------------------------------------------------------------


def _console_pause(msg: str = "按 Enter 返回菜单…") -> None:
    try:
        input(msg)
    except EOFError:
        pass


def console_main() -> None:
    os.chdir(str(APP_DIR))
    data_dir = _default_data_dir()
    server_proc: subprocess.Popen[bytes] | None = None

    while True:
        key_ok = bool(_read_env_key())
        idx_ok = INDEX_STORE.exists() and INDEX_META.exists()
        srv_ok = server_proc is not None and server_proc.poll() is None

        print("\n" + "=" * 40)
        print("  本地知识库 RAG - 控制台菜单")
        print("=" * 40)
        print(f"  工作目录：{APP_DIR}")
        print(f"  密钥：{'已配置' if key_ok else '未配置'}  |  索引：{'已就绪' if idx_ok else '未构建'}  |  网页：{'运行中' if srv_ok else '未启动'}")
        print(f"  当前知识库目录：{data_dir}")
        print("-" * 40)
        print("  [1] 配置密钥（写入 .env）")
        print("  [2] 选择知识库目录")
        print("  [3] 重建索引（需密钥与有效目录）")
        print("  [4] 启动网页服务（需密钥与索引）")
        print("  [5] 停止网页服务")
        print("  [6] 在浏览器打开聊天页")
        print("  [7] 命令行问答（main.py）")
        print("  [0] 退出")
        print("-" * 40)
        choice = input("请选择 [0-7]: ").strip()

        if choice == "0":
            if server_proc and server_proc.poll() is None:
                server_proc.terminate()
                server_proc.wait(timeout=5)
            print("已退出。")
            break

        if choice == "1":
            print("请输入 DashScope 密钥（直接回车取消）：")
            key = input().strip()
            if key:
                _write_env_key(key)
                _apply_env_key()
                print("已保存到 .env")
            _console_pause()

        elif choice == "2":
            print(f"请输入知识库文件夹完整路径（直接回车保持 {data_dir}）：")
            p = input().strip()
            if p:
                data_dir = Path(p)
            print(f"已设为：{data_dir}")
            _console_pause()

        elif choice == "3":
            if not _read_env_key():
                print("请先选择 [1] 配置密钥。")
                _console_pause()
                continue
            if not data_dir.is_dir():
                print(f"目录不存在：{data_dir}")
                _console_pause()
                continue
            _apply_env_key()
            print("正在构建索引，请稍候……")
            r = subprocess.run(
                [sys.executable, "ingest.py", "--data_dir", str(data_dir)],
                cwd=str(APP_DIR),
            )
            if r.returncode == 0:
                print("索引构建完成。")
            else:
                print(f"失败，退出码 {r.returncode}，请根据上方日志排查。")
            _console_pause()

        elif choice == "4":
            if not _read_env_key():
                print("请先选择 [1] 配置密钥。")
                _console_pause()
                continue
            if not (INDEX_STORE.exists() and INDEX_META.exists()):
                print("请先选择 [3] 重建索引。")
                _console_pause()
                continue
            if server_proc and server_proc.poll() is None:
                print("服务已在运行。")
                _console_pause()
                continue
            if _port_in_use(SERVER_PORT):
                print(
                    f"端口 {SERVER_PORT} 已被占用，无法启动。请先 [5] 停止本菜单启动的服务，"
                    "或关闭其它占用该端口的程序。"
                )
                _console_pause()
                continue
            _apply_env_key()
            server_proc = subprocess.Popen(
                [sys.executable, "-m", "uvicorn", "app:app", "--host", "0.0.0.0", "--port", str(SERVER_PORT)],
                cwd=str(APP_DIR),
                env=os.environ.copy(),
            )
            print(f"已启动：http://127.0.0.1:{SERVER_PORT}/chat-ui")
            _console_pause()

        elif choice == "5":
            if server_proc and server_proc.poll() is None:
                server_proc.terminate()
                try:
                    server_proc.wait(timeout=8)
                except subprocess.TimeoutExpired:
                    server_proc.kill()
                print("已停止网页服务。")
            else:
                print("当前没有由本菜单启动的服务进程。")
            server_proc = None
            _console_pause()

        elif choice == "6":
            webbrowser.open(CHAT_URL)
            print(f"已尝试打开：{CHAT_URL}")
            _console_pause()

        elif choice == "7":
            if not _read_env_key():
                print("请先配置密钥。")
                _console_pause()
                continue
            if not (INDEX_STORE.exists() and INDEX_META.exists()):
                print("请先重建索引。")
                _console_pause()
                continue
            _apply_env_key()
            subprocess.run([sys.executable, "main.py"], cwd=str(APP_DIR))
            _console_pause()

        else:
            print("无效选择。")
            _console_pause()


# ---------------------------------------------------------------------------
# 图形界面（python launcher.py 或打包后的 EXE）
# ---------------------------------------------------------------------------


class LauncherApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("本地知识库 RAG - 启动器")
        self.root.geometry("820x520")
        self.root.minsize(720, 480)

        self.status_var = StringVar(value="就绪")
        self.server_proc: subprocess.Popen | None = None
        self.data_dir: Path = _default_data_dir()

        self._build_ui()
        self._refresh_status()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_ui(self) -> None:
        font_title = ("Microsoft YaHei UI", 20, "bold")
        font_body = ("Microsoft YaHei UI", 10)
        font_small = ("Microsoft YaHei UI", 9)
        font_mono = ("Consolas", 10)

        top = Frame(self.root, padx=14, pady=10)
        top.pack(fill="x")
        Label(top, text="本地知识库 RAG 问答", font=font_title).pack(anchor="w")
        Message(
            top,
            text="配置密钥 → 重建索引 → 启动网页。日志区可用来答辩展示或排错。",
            width=780,
            font=font_small,
        ).pack(anchor="w", pady=(4, 0))

        btns = Frame(self.root, padx=14, pady=6)
        btns.pack(fill="x")
        for txt, cmd, w in (
            ("1 配置密钥", self.action_config_key, 12),
            ("知识库目录", self.action_choose_dir, 12),
            ("2 重建索引", self.action_build_index, 12),
            ("3 启动网页", self.action_start_server, 12),
            ("打开聊天", self.action_open_chat, 10),
            ("停止服务", self.action_stop_server, 10),
        ):
            Button(btns, text=txt, width=w, command=cmd, font=font_body).pack(side="left", padx=(0, 8))

        mid = Frame(self.root, padx=14, pady=6)
        mid.pack(fill="both", expand=True)
        Label(mid, text="运行日志", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w")
        self.log_text = Text(mid, height=18, wrap="word", font=font_mono)
        self.log_text.pack(fill="both", expand=True, pady=(4, 0))
        self.log_text.insert(END, "提示：首次请先「配置密钥」，再「重建索引」。\n")
        self.log_text.config(state=DISABLED)

        bottom = Frame(self.root, padx=14, pady=8)
        bottom.pack(fill="x")
        Label(bottom, textvariable=self.status_var, font=font_small).pack(anchor="w")

    def log(self, msg: str) -> None:
        def append() -> None:
            line = f"[{time.strftime('%H:%M:%S')}] {msg}\n"
            self.log_text.config(state=NORMAL)
            self.log_text.insert(END, line)
            self.log_text.see(END)
            self.log_text.config(state=DISABLED)

        try:
            self.root.after(0, append)
        except Exception:
            pass

    def _refresh_status(self) -> None:
        key_ok = bool(_read_env_key())
        idx_ok = INDEX_STORE.exists() and INDEX_META.exists()
        srv_ok = self.server_proc is not None and self.server_proc.poll() is None
        self.status_var.set(
            " | ".join(
                [
                    "密钥：已配置" if key_ok else "密钥：未配置",
                    "索引：已就绪" if idx_ok else "索引：未构建",
                    "服务：运行中" if srv_ok else "服务：未启动",
                    f"目录：{self.data_dir}",
                ]
            )
        )
        self.root.after(1000, self._refresh_status)

    def action_config_key(self) -> None:
        win = Toplevel(self.root)
        win.title("配置密钥")
        win.geometry("500x200")
        win.resizable(False, False)
        Label(win, text="DASHSCOPE_API_KEY", font=("Microsoft YaHei UI", 10, "bold")).pack(anchor="w", padx=12, pady=(12, 4))
        entry = Text(win, height=3, font=("Consolas", 10))
        entry.pack(fill="x", padx=12, pady=4)
        entry.insert(END, _read_env_key())

        def save() -> None:
            key = entry.get("1.0", END).strip()
            if not key:
                messagebox.showwarning("提示", "密钥不能为空")
                return
            _write_env_key(key)
            self.log("已写入 .env")
            win.destroy()

        Button(win, text="保存", width=10, command=save).pack(side="right", padx=12, pady=(0, 12))

    def action_choose_dir(self) -> None:
        path = filedialog.askdirectory(title="选择知识库目录", initialdir=str(self.data_dir))
        if path:
            self.data_dir = Path(path)
            self.log(f"知识库目录：{self.data_dir}")

    def action_build_index(self) -> None:
        def worker() -> None:
            self.log("开始重建索引……")
            if not _read_env_key():
                self.log("请先配置密钥")
                return
            if not self.data_dir.is_dir():
                self.log(f"目录不存在：{self.data_dir}")
                return
            _apply_env_key()
            try:
                os.chdir(str(APP_DIR))
                from ingest import build_embeddings, collect_documents

                docs = collect_documents(self.data_dir)
                self.log(f"已收集分片数：{len(docs)}")
                buf = io.StringIO()
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(buf):
                    embeddings, metadatas = build_embeddings(docs)
                for line in buf.getvalue().strip().splitlines():
                    self.log(line)
                import numpy as np

                np.save(INDEX_STORE, embeddings)
                np.save(INDEX_META, np.array(metadatas, dtype=object))
                self.log("索引已写入 index_store.npy / index_meta.npy")
            except Exception as e:  # noqa: BLE001
                self.log(f"失败：{e}")

        threading.Thread(target=worker, daemon=True).start()

    def action_start_server(self) -> None:
        if self.server_proc is not None and self.server_proc.poll() is None:
            self.log("服务已在运行")
            return
        if not _read_env_key():
            self.log("请先配置密钥")
            return
        if not (INDEX_STORE.exists() and INDEX_META.exists()):
            self.log("请先重建索引")
            return
        if _port_in_use(SERVER_PORT):
            self.log(
                f"端口 {SERVER_PORT} 已被占用。请先「停止服务」，或关闭其它占用该端口的程序。"
            )
            return
        _apply_env_key()
        os.chdir(str(APP_DIR))
        self.log("启动 uvicorn（子进程）……")
        env = os.environ.copy()
        try:
            kw: dict[str, object] = {
                "cwd": str(APP_DIR),
                "env": env,
                "stdout": subprocess.PIPE,
                "stderr": subprocess.STDOUT,
                "text": True,
                "bufsize": 1,
            }
            if sys.platform == "win32":
                kw["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            self.server_proc = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "app:app",
                    "--host",
                    "0.0.0.0",
                    "--port",
                    str(SERVER_PORT),
                ],
                **kw,
            )
        except Exception as e:  # noqa: BLE001
            self.log(f"启动失败：{e}")
            self.server_proc = None
            return

        def read_stdout() -> None:
            proc = self.server_proc
            if proc is None or proc.stdout is None:
                return
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                self.log(line.rstrip("\r\n"))
            with contextlib.suppress(Exception):
                proc.stdout.close()

        threading.Thread(target=read_stdout, daemon=True).start()

        def check_fast_fail() -> None:
            p = self.server_proc
            if p is None:
                return
            if p.poll() is not None:
                self.log(f"服务未能保持运行，退出码 {p.returncode}。请查看上方日志。")
                self.server_proc = None

        self.root.after(1500, check_fast_fail)
        self.root.after(800, self.action_open_chat)

    def action_open_chat(self) -> None:
        webbrowser.open(CHAT_URL)
        self.log(f"已打开 {CHAT_URL}")

    def action_stop_server(self) -> None:
        if self.server_proc is None or self.server_proc.poll() is not None:
            self.log("服务未运行")
            self.server_proc = None
            return
        self.log("正在停止……")
        try:
            self.server_proc.terminate()
            self.server_proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            self.server_proc.kill()
        except Exception as e:  # noqa: BLE001
            self.log(f"停止异常：{e}")
        finally:
            self.server_proc = None
            self.log("已停止")

    def on_close(self) -> None:
        if self.server_proc is not None and self.server_proc.poll() is None:
            if not messagebox.askyesno("退出", "服务仍在运行，是否停止并退出？"):
                return
            self.action_stop_server()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main_gui() -> None:
    os.chdir(str(APP_DIR))
    LauncherApp().run()


def main() -> None:
    if "--console" in sys.argv:
        console_main()
    else:
        main_gui()


if __name__ == "__main__":
    main()
