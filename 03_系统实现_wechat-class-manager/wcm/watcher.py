"""Layer 4 - Watcher Agent: incremental processing with a durable checkpoint."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from .bridge import load_messages
from .core import OUT_DIR, Message, write_json


CHECKPOINT = OUT_DIR / "watcher_checkpoint.json"


def load_checkpoint(path: Path = CHECKPOINT) -> Dict[str, Any]:
    if not path.exists():
        return {"last_msg_id": "", "last_timestamp": "", "processed_total": 0, "runs": 0}
    return json.loads(path.read_text(encoding="utf-8"))


def incremental_messages(path: Path = CHECKPOINT, adapter: str = "fixture",
                         group: str = "Elite20-项目协同群",
                         fixture: Path | None = None) -> tuple[List[Message], Dict[str, Any]]:
    """Return only messages after the checkpoint. Safe to call repeatedly."""
    cp = load_checkpoint(path)
    all_msgs = load_messages(adapter, group, 30, fixture)
    if cp["last_timestamp"]:
        new = [m for m in all_msgs if m.timestamp > cp["last_timestamp"]]
    else:
        new = list(all_msgs)
    # never reprocess an already seen id even if timestamps tie
    new = [m for m in new if m.msg_id != cp["last_msg_id"]]
    if new:
        tail = new[-1]
        cp.update({"last_msg_id": tail.msg_id, "last_timestamp": tail.timestamp,
                   "processed_total": cp.get("processed_total", 0) + len(new),
                   "runs": cp.get("runs", 0) + 1})
    else:
        cp["runs"] = cp.get("runs", 0) + 1
    write_json(path, cp)
    return new, cp
