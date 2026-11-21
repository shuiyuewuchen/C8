"""Shared data models, config loading and small utilities.

Design note: deliberately uses only the Python standard library so the whole
system runs on a clean machine with `python3 run_pipeline.py` and no pip step.
"""
from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
OUT_DIR = ROOT / "outputs"


# --------------------------------------------------------------------------- #
# Config (JSON instead of YAML: zero third-party dependency, see 拿来说明)
# --------------------------------------------------------------------------- #
def load_json(path: Path) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load_config() -> Dict[str, Any]:
    challenges = load_json(CONFIG_DIR / "challenges.json")
    group = load_json(CONFIG_DIR / "group_config.json")
    return {"challenges": challenges["challenges"], "group": group}


# --------------------------------------------------------------------------- #
# Domain models
# --------------------------------------------------------------------------- #
@dataclass
class Message:
    msg_id: str
    timestamp: str
    sender_wechat_id: str
    sender_nickname: str
    type: str                      # text | image | file | voice | link | system
    content: str
    media_ref: str = ""
    reply_to: str = ""
    raw: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Emit the canonical P3394-style schema with a nested sender object."""
        return {
            "msg_id": self.msg_id,
            "timestamp": self.timestamp,
            "sender": {"wechat_id": self.sender_wechat_id, "nickname": self.sender_nickname},
            "type": self.type,
            "content": self.content,
            "media_ref": self.media_ref,
            "reply_to": self.reply_to,
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "Message":
        sender = d.get("sender") or {}
        return cls(
            msg_id=str(d.get("msg_id", "")),
            timestamp=d.get("timestamp", ""),
            sender_wechat_id=sender.get("wechat_id", d.get("sender_wechat_id", "")),
            sender_nickname=sender.get("nickname", d.get("sender_nickname", "")),
            type=d.get("type", "text"),
            content=d.get("content", ""),
            media_ref=d.get("media_ref", ""),
            reply_to=d.get("reply_to", ""),
            raw=d,
        )

    @property
    def dt(self) -> datetime:
        return parse_ts(self.timestamp)


@dataclass
class EnrichedMessage:
    message: Message
    intent: str
    challenge_ref: str
    confidence: float
    evidence: List[str]

    def to_dict(self) -> Dict[str, Any]:
        d = self.message.to_dict()
        d.update({
            "intent": self.intent,
            "challenge_ref": self.challenge_ref,
            "confidence": round(self.confidence, 3),
            "evidence": self.evidence,
        })
        return d


@dataclass
class Submission:
    student: str
    challenge: str
    filename: str
    timestamp: str
    msg_id: str
    status: str = "received"
    missing: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QAPair:
    question_id: str
    answer_id: str
    asker: str
    answerer: str
    question: str
    answer: str
    topic_tags: List[str]
    quality_score: float
    timestamp: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Alert:
    kind: str
    severity: str
    subject: str
    detail: str
    evidence: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def parse_ts(value: str) -> datetime:
    """Parse ISO-8601 with a tolerant fallback."""
    v = value.strip().replace("Z", "+08:00")
    try:
        return datetime.fromisoformat(v)
    except ValueError:
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M"):
            try:
                return datetime.strptime(v, fmt)
            except ValueError:
                continue
    raise ValueError(f"Unparseable timestamp: {value!r}")


def within_days(ts: datetime, reference: datetime, days: int) -> bool:
    return 0 <= (reference - ts).total_seconds() <= days * 86400


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text)


def pct(numerator: int, denominator: int) -> float:
    return round(100.0 * numerator / denominator, 1) if denominator else 0.0


SUBMISSION_FILENAME_RE = re.compile(
    r"(?P<name>[\u4e00-\u9fa5A-Za-z0-9_]+)_C(?P<cid>\d)[A-Za-z]?_(?P<rest>.+?)(?P<ext>\.[A-Za-z0-9]+)$"
)


def parse_submission_filename(filename: str) -> Optional[Dict[str, str]]:
    """Match `张三_C2_proposal.md` / `李四_C4B_demo.pdf` style names."""
    m = SUBMISSION_FILENAME_RE.search(filename)
    if not m:
        return None
    return {
        "student": m.group("name"),
        "challenge": "C" + m.group("cid"),
        "rest": m.group("rest"),
        "ext": m.group("ext"),
    }
