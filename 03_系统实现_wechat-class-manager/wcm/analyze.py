"""Layer 2 - message classification, challenge linking, signals extraction."""
from __future__ import annotations

import re
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from .core import (
    EnrichedMessage, Message, QAPair, Submission,
    parse_submission_filename, pct,
)

# --- intent vocabularies (rules-first; a pluggable LLM classifier can replace
# `classify_message` without changing any downstream module) -----------------
QUESTION_WORDS = ("?", "？", "怎么", "为什么", "请问", "如何", "能不能", "可不可以", "是不是", "吗")
ANNOUNCE_WORDS = ("通知", "截止", "deadline", "@全体", "请各位", "注意", "周会", "务必", "提交截止")
RESOURCE_WORDS = ("http://", "https://", "链接", "推荐", "资料", "参考", "文档地址")
DISCUSS_WORDS = ("我觉得", "我认为", "同意", "不同意", "建议", "讨论", "其实", "但是", "原因是")
SOCIAL_WORDS = ("早上好", "晚上好", "哈哈", "收到", "谢谢", "辛苦", "👍", "好的", "加油")


def classify_message(msg: Message, reply_index: Dict[str, str],
                     teacher_ids: set[str]) -> Tuple[str, float, List[str]]:
    """Return (intent, confidence, evidence). Rule engine, deterministic."""
    text = msg.content or ""
    low = text.lower()
    scores: Dict[str, float] = defaultdict(float)
    evidence: Dict[str, List[str]] = defaultdict(list)

    # structural signals
    if msg.type == "file":
        scores["submission"] += 2.6
        evidence["submission"].append("type=file")
        if parse_submission_filename(msg.media_ref or text):
            scores["submission"] += 2.0
            evidence["submission"].append("filename matches naming spec")
    if msg.type == "link":
        scores["resource"] += 2.4
        evidence["resource"].append("type=link")
    if msg.reply_to and reply_index.get(msg.reply_to) == "question":
        scores["answer"] += 3.0
        evidence["answer"].append("reply_to a question")

    # lexical signals
    if msg.sender_wechat_id in teacher_ids:
        scores["announcement"] += 1.2
        evidence["announcement"].append("sender is staff")
    for w in ANNOUNCE_WORDS:
        if w.lower() in low:
            scores["announcement"] += 1.0
            evidence["announcement"].append(f"keyword:{w}")
    for w in QUESTION_WORDS:
        if w.lower() in low:
            scores["question"] += 1.0
            evidence["question"].append(f"keyword:{w}")
    for w in RESOURCE_WORDS:
        if w.lower() in low:
            scores["resource"] += 0.8
            evidence["resource"].append(f"keyword:{w}")
    for w in DISCUSS_WORDS:
        if w in text:
            scores["discussion"] += 0.8
            evidence["discussion"].append(f"keyword:{w}")
    for w in SOCIAL_WORDS:
        if w in text:
            scores["social"] += 0.8
            evidence["social"].append(f"keyword:{w}")
    if re.search(r"(提交|已交|上传|交了|交付)", text):
        scores["submission"] += 0.7
        evidence["submission"].append("submission verb")
    if len(text) > 45:
        scores["discussion"] += 0.6
        evidence["discussion"].append("long message")
    if len(text) < 12 and not msg.reply_to:
        scores["social"] += 0.5
        evidence["social"].append("short message")

    if not scores:
        return "social", 0.4, ["fallback: no matching signal"]
    winner = max(scores, key=lambda k: (scores[k], -list(scores).index(k)))
    top = scores[winner]
    total = sum(scores.values())
    confidence = round(min(0.99, 0.45 + 0.5 * top / total), 3)
    return winner, confidence, evidence[winner][:4]


def link_challenge(msg: Message, challenges: List[Dict[str, Any]]) -> Tuple[str, List[str]]:
    """Attach challenge_ref by filename id first, then keyword signals."""
    text = (msg.content or "") + " " + (msg.media_ref or "")
    parsed = parse_submission_filename(msg.media_ref or text)
    if parsed:
        return parsed["challenge"], [f"filename:{parsed['challenge']}"]
    best, best_hits = "", []
    for c in challenges:
        hits = [kw for kw in c.get("keywords", []) if kw.lower() in text.lower()]
        exts = [e for e in c.get("extensions", []) if text.lower().endswith(e)]
        hits += exts
        if len(hits) > len(best_hits):
            best, best_hits = c["id"], hits
    return (best or "-"), best_hits[:4]


def enrich(messages: List[Message], challenges: List[Dict[str, Any]],
           group: Dict[str, Any]) -> List[EnrichedMessage]:
    teacher_ids = set(group.get("teachers", []))
    # Two passes: first intents for reply targets, then final classification.
    reply_index: Dict[str, str] = {}
    for m in messages:
        intent, _, _ = classify_message(m, {}, teacher_ids)
        reply_index[m.msg_id] = intent
    return [
        EnrichedMessage(
            message=m,
            intent=(res := classify_message(m, reply_index, teacher_ids))[0],
            challenge_ref=(link := link_challenge(m, challenges))[0],
            confidence=res[1],
            evidence=res[2] + link[1],
        )
        for m in messages
    ]


def evaluate_classifier(enriched: List[EnrichedMessage], labels: Dict[str, str]) -> Dict[str, Any]:
    """Compare against the ground-truth intent column kept OUT of the bridge output."""
    ok = sum(1 for e in enriched if labels.get(e.message.msg_id) == e.intent)
    total = len(enriched)
    per_class: Dict[str, Dict[str, int]] = defaultdict(lambda: {"hit": 0, "gold": 0, "pred": 0})
    for e in enriched:
        gold = labels.get(e.message.msg_id, "?")
        per_class[gold]["gold"] += 1
        per_class[e.intent]["pred"] += 1
        if gold == e.intent:
            per_class[gold]["hit"] += 1
    detail = {
        k: {"precision": pct(v["hit"], v["pred"]), "recall": pct(v["hit"], v["gold"]),
            "support": v["gold"]}
        for k, v in sorted(per_class.items())
    }
    return {"accuracy": pct(ok, total), "correct": ok, "total": total, "per_class": detail}


def detect_submissions(enriched: List[EnrichedMessage]) -> Tuple[List[Submission], List[Dict[str, Any]]]:
    """Build the student x challenge matrix and flag missing required artefacts."""
    found: List[Submission] = []
    for e in enriched:
        m = e.message
        if m.type != "file":
            continue
        parsed = parse_submission_filename(m.media_ref or m.content)
        if not parsed:
            continue
        name = parsed["student"]
        found.append(Submission(
            student=name,
            challenge=parsed["challenge"],
            filename=m.media_ref or m.content,
            timestamp=m.timestamp,
            msg_id=m.msg_id,
        ))

    # required companions: a proposal submission needs an AI日志 for the same challenge
    by_pair: Dict[Tuple[str, str], List[Submission]] = defaultdict(list)
    for s in found:
        by_pair[(s.student, s.challenge)].append(s)

    for (student, cid), items in by_pair.items():
        has_ai_log = any("ai日志" in s.filename.lower() or "ai_log" in s.filename.lower()
                         or "ailog" in s.filename.lower() for s in items)
        for s in items:
            if ("ai日志" in s.filename.lower() or "ai_log" in s.filename.lower()
                    or "ailog" in s.filename.lower()):
                s.status = "accepted"
                continue
            if not has_ai_log and "demo" not in s.filename.lower():
                s.missing.append("AI日志")
                s.status = "needs_revision"
            else:
                s.status = "accepted"

    students = sorted({s.student for s in found})
    challenges = sorted({s.challenge for s in found})
    matrix = []
    for student in students:
        row: Dict[str, Any] = {"student": student}
        for cid in challenges:
            row[cid] = [s.to_dict() for s in by_pair.get((student, cid), [])]
        matrix.append(row)
    return found, matrix


def extract_qa(enriched: List[EnrichedMessage], window_minutes: int = 45) -> List[QAPair]:
    """Pair questions with replies (reply chain first, then time window)."""
    by_id = {e.message.msg_id: e for e in enriched}
    questions = [e for e in enriched if e.intent == "question"]
    candidates = [e for e in enriched if e.intent in {"answer", "discussion", "submission"}]
    pairs: List[QAPair] = []
    used_answers: set[str] = set()

    for q in questions:
        qmsg = q.message
        answer = None
        direct = [c for c in candidates
                  if c.message.reply_to == qmsg.msg_id and c.message.msg_id not in used_answers]
        if direct:
            answer = direct[0]
        else:
            for c in candidates:
                if c.message.msg_id in used_answers or c.message.sender_nickname == qmsg.sender_nickname:
                    continue
                delta = (c.message.dt - qmsg.dt).total_seconds() / 60
                if 0 <= delta <= window_minutes:
                    answer = c
                    break
        if answer is None or len(answer.message.content) < 8:
            continue
        used_answers.add(answer.message.msg_id)
        atext = answer.message.content
        quality = 0.45
        if len(atext) > 30:
            quality += 0.2
        if any(k in atext for k in ("可以", "建议", "步骤", "因为", "先", "然后", "https://")):
            quality += 0.2
        if answer.message.reply_to == qmsg.msg_id:
            quality += 0.15
        pairs.append(QAPair(
            question_id=qmsg.msg_id,
            answer_id=answer.message.msg_id,
            asker=qmsg.sender_nickname,
            answerer=answer.message.sender_nickname,
            question=qmsg.content,
            answer=atext,
            topic_tags=[t for t in {q.challenge_ref, answer.challenge_ref} if t and t != "-"] or ["general"],
            quality_score=round(min(1.0, quality), 3),
            timestamp=qmsg.timestamp,
        ))
    pairs.sort(key=lambda p: (-p.quality_score, p.timestamp))
    return pairs
