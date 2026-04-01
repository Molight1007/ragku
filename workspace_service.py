from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


_SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9_\-\u4e00-\u9fff ]+")


def _app_base_dir() -> Path:
    # 兼容 PyInstaller 打包运行（launcher.py 也使用同样策略）
    import sys

    if getattr(sys, "frozen", False) and hasattr(sys, "executable"):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


APP_DIR = _app_base_dir()
WORKSPACES_DIR = APP_DIR / "workspaces"
WORKSPACES_DB = APP_DIR / "workspaces.json"


@dataclass(frozen=True)
class Workspace:
    id: str
    name: str
    created_at: int

    @property
    def dir(self) -> Path:
        return WORKSPACES_DIR / self.id

    @property
    def kb_dir(self) -> Path:
        return self.dir / "kb"

    @property
    def index_store(self) -> Path:
        return self.dir / "index_store.npy"

    @property
    def index_meta(self) -> Path:
        return self.dir / "index_meta.npy"


def ensure_workspace_dirs() -> None:
    WORKSPACES_DIR.mkdir(parents=True, exist_ok=True)


def _read_db() -> Dict[str, Any]:
    ensure_workspace_dirs()
    if not WORKSPACES_DB.exists():
        return {"version": 1, "workspaces": []}
    try:
        data = json.loads(WORKSPACES_DB.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {"version": 1, "workspaces": []}
    if not isinstance(data, dict):
        return {"version": 1, "workspaces": []}
    if "workspaces" not in data or not isinstance(data["workspaces"], list):
        data["workspaces"] = []
    if "version" not in data:
        data["version"] = 1
    return data


def _write_db(data: Dict[str, Any]) -> None:
    ensure_workspace_dirs()
    WORKSPACES_DB.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _sanitize_name(name: str) -> str:
    name = (name or "").strip()
    if not name:
        return "未命名工作区"
    name = _SAFE_NAME_RE.sub("", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name[:40] or "未命名工作区"


def list_workspaces() -> List[Workspace]:
    data = _read_db()
    out: List[Workspace] = []
    for w in data["workspaces"]:
        if not isinstance(w, dict):
            continue
        wid = str(w.get("id", "")).strip()
        name = str(w.get("name", "")).strip()
        created_at = int(w.get("created_at", 0) or 0)
        if not wid:
            continue
        out.append(Workspace(id=wid, name=name or "未命名工作区", created_at=created_at))
    out.sort(key=lambda x: x.created_at, reverse=True)
    return out


def get_workspace(workspace_id: str) -> Optional[Workspace]:
    workspace_id = (workspace_id or "").strip()
    if not workspace_id:
        return None
    for w in list_workspaces():
        if w.id == workspace_id:
            return w
    return None


def create_workspace(name: str) -> Workspace:
    ws = Workspace(
        id=uuid.uuid4().hex,
        name=_sanitize_name(name),
        created_at=int(time.time()),
    )
    ensure_workspace_dirs()
    ws.kb_dir.mkdir(parents=True, exist_ok=True)
    data = _read_db()
    data["workspaces"].append({"id": ws.id, "name": ws.name, "created_at": ws.created_at})
    _write_db(data)
    return ws


def delete_workspace(workspace_id: str) -> bool:
    ws = get_workspace(workspace_id)
    if ws is None:
        return False
    data = _read_db()
    data["workspaces"] = [w for w in data["workspaces"] if str(w.get("id", "")).strip() != ws.id]
    _write_db(data)

    # 尝试删除目录（尽量安全：只删 workspaces/<id>）
    try:
        if ws.dir.exists() and ws.dir.is_dir():
            for p in sorted(ws.dir.rglob("*"), key=lambda x: len(str(x)), reverse=True):
                try:
                    if p.is_file():
                        p.unlink(missing_ok=True)
                    elif p.is_dir():
                        p.rmdir()
                except Exception:  # noqa: BLE001
                    pass
            try:
                ws.dir.rmdir()
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        pass
    return True

