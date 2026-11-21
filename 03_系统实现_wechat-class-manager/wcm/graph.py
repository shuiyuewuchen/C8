"""Layer 3 - property graph store (SQLite) + student profile builder."""
from __future__ import annotations

import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .core import OUT_DIR, EnrichedMessage, QAPair, Submission, write_json


class PropertyGraph:
    """Minimal labelled property graph: nodes(id,label,props) + edges(src,dst,label,props).

    SQLite was chosen over Neo4j deliberately: zero services to run, and the
    whole graph is a single portable file that reviewers can open and query.
    """

    def __init__(self, path: Path | str = OUT_DIR / "class_graph.sqlite"):
        self.path = str(path)
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.execute("PRAGMA journal_mode=WAL")
        self._schema()

    def _schema(self) -> None:
        self.conn.executescript("""
        CREATE TABLE IF NOT EXISTS nodes (
          id TEXT PRIMARY KEY, label TEXT NOT NULL, props TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS edges (
          src TEXT NOT NULL, dst TEXT NOT NULL, label TEXT NOT NULL,
          props TEXT NOT NULL, PRIMARY KEY (src, dst, label)
        );
        CREATE INDEX IF NOT EXISTS idx_nodes_label ON nodes(label);
        CREATE INDEX IF NOT EXISTS idx_edges_label ON edges(label);
        """)
        self.conn.commit()

    # CRUD -----------------------------------------------------------------
    def upsert_node(self, node_id: str, label: str, **props: Any) -> None:
        self.conn.execute(
            "INSERT INTO nodes(id,label,props) VALUES(?,?,?) "
            "ON CONFLICT(id) DO UPDATE SET label=excluded.label, props=excluded.props",
            (node_id, label, json.dumps(props, ensure_ascii=False)),
        )

    def upsert_edge(self, src: str, dst: str, label: str, **props: Any) -> None:
        self.conn.execute(
            "INSERT OR REPLACE INTO edges(src,dst,label,props) VALUES(?,?,?,?)",
            (src, dst, label, json.dumps(props, ensure_ascii=False)),
        )

    def node(self, node_id: str) -> Optional[Dict[str, Any]]:
        row = self.conn.execute("SELECT label,props FROM nodes WHERE id=?", (node_id,)).fetchone()
        return {"id": node_id, "label": row[0], "props": json.loads(row[1])} if row else None

    def neighbours(self, node_id: str, label: str | None = None) -> List[Dict[str, Any]]:
        sql = "SELECT dst,label,props FROM edges WHERE src=?"
        args: List[Any] = [node_id]
        if label:
            sql += " AND label=?"
            args.append(label)
        out = []
        for dst, elabel, props in self.conn.execute(sql, args):
            n = self.node(dst)
            out.append({"edge": elabel, "edge_props": json.loads(props), "node": n})
        return out

    def count(self) -> Dict[str, int]:
        nodes = self.conn.execute("SELECT label,COUNT(*) FROM nodes GROUP BY label").fetchall()
        edges = self.conn.execute("SELECT label,COUNT(*) FROM edges GROUP BY label").fetchall()
        return {"nodes": dict(nodes), "edges": dict(edges),
                "total_nodes": sum(n for _, n in nodes), "total_edges": sum(n for _, n in edges)}

    def close(self) -> None:
        self.conn.close()


def build_graph(enriched: List[EnrichedMessage], submissions: List[Submission],
                qa_pairs: List[QAPair], challenges: List[Dict[str, Any]],
                graph: PropertyGraph | None = None) -> PropertyGraph:
    g = graph or PropertyGraph()

    for c in challenges:
        g.upsert_node("challenge:" + c["id"], "Challenge",
                      id=c["id"], name_cn=c["name_cn"], deadline=c["deadline"])

    students: set[str] = set()
    for e in enriched:
        m = e.message
        if m.sender_wechat_id.startswith("staff"):
            continue
        students.add(m.sender_nickname)
        g.upsert_node("student:" + m.sender_nickname, "Student",
                      name=m.sender_nickname, wechat_id=m.sender_wechat_id)
        g.upsert_node("message:" + m.msg_id, "Message",
                      msg_id=m.msg_id, timestamp=m.timestamp, type=m.type,
                      content=m.content[:200], intent=e.intent)
        g.upsert_edge("student:" + m.sender_nickname, "message:" + m.msg_id, "SENT",
                      timestamp=m.timestamp)
        if e.challenge_ref != "-" and e.challenge_ref:
            g.upsert_edge("message:" + m.msg_id, "challenge:" + e.challenge_ref,
                          "TAGGED_WITH", confidence=e.confidence)
        if m.reply_to:
            parent = next((x for x in enriched if x.message.msg_id == m.reply_to), None)
            if parent:
                g.upsert_edge("student:" + m.sender_nickname,
                              "student:" + parent.message.sender_nickname,
                              "MENTORED", via_msg=m.msg_id)

    for s in submissions:
        students.add(s.student)
        g.upsert_node("student:" + s.student, "Student", name=s.student)
        sub_id = f"submission:{s.student}:{s.challenge}:{s.msg_id}"
        g.upsert_node(sub_id, "Submission", **s.to_dict())
        g.upsert_edge("student:" + s.student, sub_id, "SUBMITTED", timestamp=s.timestamp)
        if "challenge:" + s.challenge in {n[0] for n in g.conn.execute("SELECT id FROM nodes")}:
            g.upsert_edge(sub_id, "challenge:" + s.challenge, "FOR_CHALLENGE")

    for qa in qa_pairs:
        qa_id = "qa:" + qa.question_id
        g.upsert_node(qa_id, "QAPair", **qa.to_dict())
        g.upsert_edge("student:" + qa.asker, qa_id, "ASKED")
        g.upsert_edge("student:" + qa.answerer, qa_id, "ANSWERED")

    g.conn.commit()
    return g


def build_profiles(enriched: List[EnrichedMessage], submissions: List[Submission],
                   qa_pairs: List[QAPair]) -> List[Dict[str, Any]]:
    stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
        "messages": 0, "questions": 0, "answers": 0,
        "submissions": 0, "challenges": set(), "last_active": "", "skill_tags": [],
    })
    for e in enriched:
        m = e.message
        if m.sender_wechat_id.startswith("staff"):
            continue
        s = stats[m.sender_nickname]
        s["messages"] += 1
        if e.intent == "question":
            s["questions"] += 1
        if e.intent == "answer":
            s["answers"] += 1
        if m.timestamp > s["last_active"]:
            s["last_active"] = m.timestamp
    for sub in submissions:
        s = stats[sub.student]
        s["submissions"] += 1
        s["challenges"].add(sub.challenge)
    for qa in qa_pairs:
        if qa.answerer.startswith("助教") or qa.answerer.startswith("老师"):
            continue
        stats[qa.answerer]["answers"] += 1

    profiles = []
    for name, s in sorted(stats.items()):
        tags = []
        if s["submissions"] >= 2:
            tags.append("稳定交付者")
        if s["answers"] >= 2:
            tags.append("答疑贡献者")
        if s["questions"] >= 2:
            tags.append("主动提问者")
        if s["messages"] >= 10:
            tags.append("高活跃")
        if not tags:
            tags.append("待激活")
        profiles.append({
            "name": name,
            "messages": s["messages"],
            "questions": s["questions"],
            "answers": s["answers"],
            "submissions": s["submissions"],
            "challenges": sorted(s["challenges"]),
            "last_active": s["last_active"],
            "skill_tags": tags,
        })
    write_json(OUT_DIR / "student_profiles.json", profiles)
    return profiles
