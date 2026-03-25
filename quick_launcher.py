from __future__ import annotations

import os
import socket
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path
from tkinter import DISABLED, END, NORMAL, Button, Label, StringVar, Text, Tk, messagebox

from launcher import APP_DIR, CHAT_URL, INDEX_META, INDEX_STORE, SERVER_PORT
from launcher import _apply_env_key, _port_in_use, _read_env_key  # noqa: SLF001


def _wait_port_ready(port: int, timeout_s: float = 10.0) -> bool:
    """短时间轮询端口是否就绪。"""
    t0 = time.time()
    while time.time() - t0 < timeout_s:
        if _port_in_use(port):
            return True
        time.sleep(0.2)
    return False


class QuickLauncherApp:
    def __init__(self) -> None:
        self.root = Tk()
        self.root.title("本地知识库 RAG - 一键启动器")
        self.root.geometry("520x320")
        self.root.minsize(480, 300)

        self.status_var = StringVar(value="准备启动……")
        self.server_proc: subprocess.Popen | None = None

        top = Label(self.root, text="一键启动本地 RAG 服务", font=("Microsoft YaHei UI", 14, "bold"))
        top.pack(anchor="w", padx=14, pady=(12, 6))

        Label(
            self.root,
            text="启动后会自动打开聊天页；点击“停止服务”可结束 uvicorn。",
            font=("Microsoft YaHei UI", 10),
        ).pack(anchor="w", padx=14)

        btns = Label(self.root)
        btns.pack(fill="x", padx=14, pady=(10, 6))

        self.btn_stop = Button(self.root, text="停止服务", width=12, command=self.action_stop_server)
        self.btn_stop.place(x=14, y=78)

        self.btn_open = Button(self.root, text="打开聊天页", width=12, command=self.action_open_chat)
        self.btn_open.place(x=118, y=78)

        self.log_text = Text(self.root, height=10, wrap="word", font=("Consolas", 10))
        self.log_text.pack(fill="both", expand=True, padx=14, pady=(8, 12))
        self.log_text.config(state=DISABLED)
        self.log("提示：如果提示缺少 .env 或索引，请先运行 01/02 脚本。")

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.root.after(200, self.auto_start)

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

    def _start_server(self) -> None:
        if not _read_env_key():
            messagebox.showwarning("提示", "未配置 DASHSCOPE_API_KEY。\n请先双击运行：01_一键配置密钥.cmd")
            self.status_var.set("未配置密钥")
            return
        if not (INDEX_STORE.exists() and INDEX_META.exists()):
            messagebox.showwarning("提示", "未找到索引文件。\n请先双击运行：02_重建索引.cmd")
            self.status_var.set("索引未构建")
            return
        if self.server_proc is not None and self.server_proc.poll() is None:
            self.log("服务已在运行")
            return
        if _port_in_use(SERVER_PORT):
            # 端口被占用但我们不一定能控制，先直接打开聊天页
            self.log(f"端口 {SERVER_PORT} 已被占用，尝试打开聊天页。")
            self.status_var.set("检测到已有服务")
            return

        _apply_env_key()
        os.chdir(str(APP_DIR))
        self.log("启动 uvicorn（子进程）……")

        env = os.environ.copy()
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

        def read_stdout() -> None:
            proc = self.server_proc
            if proc is None or proc.stdout is None:
                return
            for line in iter(proc.stdout.readline, ""):
                if not line:
                    break
                self.log(line.rstrip("\r\n"))
            try:
                proc.stdout.close()
            except Exception:
                pass

        threading.Thread(target=read_stdout, daemon=True).start()

    def action_stop_server(self) -> None:
        if self.server_proc is None or self.server_proc.poll() is not None:
            self.log("服务未运行")
            self.status_var.set("服务未运行")
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
            self.status_var.set("已停止")
            self.log("已停止")

    def action_open_chat(self) -> None:
        webbrowser.open(CHAT_URL)
        self.log(f"已打开 {CHAT_URL}")

    def auto_start(self) -> None:
        self.status_var.set("启动中……")
        self._start_server()

        # 等一小会儿端口就绪再打开网页
        if _wait_port_ready(SERVER_PORT, timeout_s=10.0):
            self.status_var.set("运行中")
            self.action_open_chat()
        else:
            self.status_var.set("启动完成/或已占用端口")
            self.log("端口未能在规定时间内就绪，可能已被其他程序占用。")

        self.root.after(1000, self._refresh_status)

    def _refresh_status(self) -> None:
        srv_ok = self.server_proc is not None and self.server_proc.poll() is None
        if srv_ok:
            self.status_var.set("运行中")
        else:
            # 如果端口被占用但我们没有 server_proc，也算“可能在运行”
            if _port_in_use(SERVER_PORT):
                self.status_var.set("检测到已有服务")
            else:
                self.status_var.set(self.status_var.get() if self.status_var.get() else "已停止")
        self.root.after(2000, self._refresh_status)

    def on_close(self) -> None:
        if self.server_proc is not None and self.server_proc.poll() is None:
            if not messagebox.askyesno("退出", "服务仍在运行，是否停止并退出？"):
                return
            self.action_stop_server()
        self.root.destroy()

    def run(self) -> None:
        self.root.mainloop()


def main() -> None:
    QuickLauncherApp().run()


if __name__ == "__main__":
    main()

