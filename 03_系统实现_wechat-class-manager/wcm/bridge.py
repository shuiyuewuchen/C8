"""Layer 1 - WeChat Channel Adapter.

Two adapters share one normalized output schema:
  * `cli`     : calls an installed `wechat-cli` and normalises its JSON (real data)
  * `fixture` : reads a de-identified JSONL file (offline demo / reproducible tests)

The adapter boundary is the whole point: swapping the transport never touches
Layers 2-4. In this delivery the fixture adapter is the one exercised, because
the production WeChat database is not accessible from the build machine. That
constraint is recorded honestly in the W1/W2 AARs.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .core import DATA_DIR, Message, OUT_DIR, write_json, write_text


VALID_TYPES = {"text", "image", "file", "voice", "link", "system"}


def normalize(raw: Dict[str, Any]) -> Message:
    """Map a heterogeneous raw record onto the canonical Message schema."""
    sender = raw.get("sender") or {}
    if isinstance(sender, str):
        sender = {"nickname": sender, "wechat_id": ""}
    msg_type = str(raw.get("type", "text")).lower()
    if msg_type not in VALID_TYPES:
        msg_type = "text"
    msg = Message.from_dict({
        "msg_id": str(raw.get("msg_id") or raw.get("id") or raw.get("local_id") or ""),
        "timestamp": raw.get("timestamp") or raw.get("time") or "",
        "sender": {
            "wechat_id": sender.get("wechat_id") or raw.get("sender_wechat_id") or "",
            "nickname": sender.get("nickname") or raw.get("sender_nickname") or "未知",
        },
        "type": msg_type,
        "content": raw.get("content") or raw.get("text") or "",
        "media_ref": raw.get("media_ref") or raw.get("file_path") or "",
        "reply_to": str(raw.get("reply_to") or ""),
    })
    if not msg.msg_id:
        raise ValueError("raw message has no msg_id")
    return msg


def read_fixture(path: Path) -> List[Message]:
    messages: List[Message] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, 1):
            line = line.strip()
            if not line:
                continue
            raw = json.loads(line)
            raw.setdefault("msg_id", f"fx-{line_no:04d}")
            messages.append(normalize(raw))
    return messages


def read_cli(group: str, days: int, cli: str = "wechat-cli") -> List[Message]:
    """Real-data adapter. Assumes `wechat-cli history <group> --limit N --format json`.

    A `--days` flag is not present in every wechat-cli version, so we over-fetch
    and filter by timestamp here instead. Never writes back to WeChat.
    """
    if shutil.which(cli) is None:
        raise RuntimeError(
            f"{cli!r} not found on PATH. Install it (see SETUP.md) or use --adapter fixture."
        )
    cmd = [cli, "history", group, "--limit", "5000", "--format", "json"]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=True)
    raw_items = json.loads(proc.stdout)
    if isinstance(raw_items, dict):
        raw_items = raw_items.get("messages", raw_items.get("data", []))
    messages = [normalize(r) for r in raw_items]
    if days > 0:
        from datetime import datetime, timedelta
        cutoff = datetime.now().astimezone() - timedelta(days=days)
        messages = [m for m in messages if m.dt >= cutoff]
    return messages


def load_messages(adapter: str = "fixture", group: str = "Elite20",
                  days: int = 30, fixture: Path | None = None) -> List[Message]:
    if adapter == "fixture":
        path = fixture or (DATA_DIR / "sample_messages.jsonl")
        msgs = read_fixture(path)
    elif adapter == "cli":
        msgs = read_cli(group, days)
    else:
        raise ValueError(f"unknown adapter: {adapter}")
    msgs.sort(key=lambda m: (m.dt, m.msg_id))
    return msgs


def bridge(adapter: str = "fixture", group: str = "Elite20", days: int = 30,
           fixture: Path | None = None, emit_sample: bool = True) -> List[Message]:
    """Public entry point. Writes the canonical JSONL to outputs/messages.jsonl."""
    msgs = load_messages(adapter, group, days, fixture)
    if emit_sample:
        write_text(OUT_DIR / "messages.jsonl",
                   "\n".join(json.dumps(m.to_dict(), ensure_ascii=False) for m in msgs) + "\n")
    return msgs
