"""Layer 4 - Alert Engine, Report Engine, natural-language query router."""
from __future__ import annotations

import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List

from .core import (OUT_DIR, Alert, EnrichedMessage, QAPair, Submission,
                   parse_ts, pct, write_json, write_text)


# --------------------------------------------------------------------------- #
# Alert Engine
# --------------------------------------------------------------------------- #
def run_alerts(enriched: List[EnrichedMessage], submissions: List[Submission],
               challenges: List[Dict[str, Any]], group: Dict[str, Any],
               reference: datetime | None = None) -> List[Alert]:
    """Three rule-based alerts + one KSTAR-delta style activity alert."""
    ref = reference or max((e.message.dt for e in enriched), default=datetime.now().astimezone())
    alerts: List[Alert] = []
    submitted_pairs = {(s.student, s.challenge) for s in submissions}

    # Rule 1: deadline within 3 days and no submission
    for c in challenges:
        due = parse_ts(c["deadline"])
        days_left = (due - ref).total_seconds() / 86400
        if 0 <= days_left <= 3:
            missing = [n for n in {e.message.sender_nickname for e in enriched
                                   if not e.message.sender_wechat_id.startswith("staff")}
                       if (n, c["id"]) not in submitted_pairs]
            if missing:
                alerts.append(Alert(
                    kind="deadline_risk", severity="high", subject=c["id"],
                    detail=f"{c['name_cn']} 距截止 {days_left:.1f} 天，{len(missing)} 人未提交",
                    evidence=",".join(missing[:8]),
                ))

    # Rule 2: silent student (no message for >= 7 days)
    last: Dict[str, datetime] = {}
    for e in enriched:
        m = e.message
        if m.sender_wechat_id.startswith("staff"):
            continue
        if m.sender_nickname not in last or m.dt > last[m.sender_nickname]:
            last[m.sender_nickname] = m.dt
    for name, ts in last.items():
        silent = (ref - ts).days
        if silent >= 7:
            alerts.append(Alert(
                kind="silent_student", severity="medium", subject=name,
                detail=f"连续 {silent} 天未发言", evidence=f"last_active={ts.isoformat()}",
            ))

    # Rule 3: challenge submission rate below 30%
    students = sorted(last)
    for c in challenges:
        done = sum(1 for s in students if (s, c["id"]) in submitted_pairs)
        rate = pct(done, len(students))
        if rate < 30:
            alerts.append(Alert(
                kind="low_submission_rate", severity="high", subject=c["id"],
                detail=f"提交率 {rate}%（{done}/{len(students)}）低于 30% 阈值",
                evidence=c["name_cn"],
            ))

    # Rule 4: KSTAR-delta - activity dropped sharply in last third of window
    if len(enriched) > 30:
        ordered = sorted(e.message.dt for e in enriched)
        span = (ordered[-1] - ordered[0]).total_seconds() / 3
        cut = ordered[0] + timedelta(seconds=span * 2)
        recent = [e for e in enriched if e.message.dt >= cut]
        earlier = [e for e in enriched if e.message.dt < cut]
        r_week, e_week = len(recent) / 2, len(earlier)
        if e_week and r_week < 0.6 * e_week:
            alerts.append(Alert(
                kind="activity_delta", severity="medium", subject="班级整体",
                detail=f"最近时段消息速率下降 {pct(int(e_week - r_week), int(e_week))}%",
                evidence=f"earlier={e_week}, recent/week={r_week:.1f}",
            ))

    write_json(OUT_DIR / "alerts.json", [a.to_dict() for a in alerts])
    return alerts


# --------------------------------------------------------------------------- #
# Report Engine
# --------------------------------------------------------------------------- #
def build_weekly_report(enriched: List[EnrichedMessage], submissions: List[Submission],
                        qa_pairs: List[QAPair], profiles: List[Dict[str, Any]],
                        alerts: List[Alert], challenges: List[Dict[str, Any]],
                        week_label: str = "W4") -> str:
    dates = [e.message.dt for e in enriched]
    start, end = min(dates), max(dates)
    top = sorted(profiles, key=lambda p: (-p["messages"] - 2 * p["answers"], p["name"]))[:5]
    best_qa = qa_pairs[:3]
    lines = [
        f"# Elite20 班级状态周报 · {week_label}",
        "",
        f"> 数据区间：{start:%Y-%m-%d} ~ {end:%Y-%m-%d} ｜ 数据源：微信群消息流（脱敏样本）",
        f"> 生成方式：`wcm.engines.build_weekly_report`（可重复运行，非人工撰写）",
        "",
        "## 一、总览",
        "",
        "| 指标 | 数值 |",
        "|---|---:|",
        f"| 处理消息数 | {len(enriched)} |",
        f"| 识别提交数 | {len(submissions)} |",
        f"| 提取 Q&A 对 | {len(qa_pairs)} |",
        f"| 画像学生数 | {len(profiles)} |",
        f"| 触发预警数 | {len(alerts)} |",
        "",
        "## 二、最活跃学生 Top 5",
        "",
        "| 学生 | 消息 | 答疑 | 提交 | 标签 |",
        "|---|---:|---:|---:|---|",
    ]
    for p in top:
        lines.append(f"| {p['name']} | {p['messages']} | {p['answers']} | {p['submissions']} | {'/'.join(p['skill_tags'])} |")
    lines += ["", "## 三、最佳 Q&A", ""]
    for qa in best_qa:
        lines.append(f"- **Q**（{qa.asker}）：{qa.question}")
        lines.append(f"  - **A**（{qa.answerer}）：{qa.answer[:120]}")
        lines.append(f"  - 质量分 {qa.quality_score} ｜ 标签 {', '.join(qa.topic_tags)}")
    lines += ["", "## 四、各挑战完成情况", "", "| 挑战 | 提交数 | 完成率 |", "|---|---:|---:|"]
    n_students = len(profiles)
    for c in challenges:
        done = len({s.student for s in submissions if s.challenge == c["id"]})
        lines.append(f"| {c['id']} {c['name_cn']} | {done} | {pct(done, n_students)}% |")
    lines += ["", "## 五、预警清单", ""]
    if alerts:
        for a in alerts:
            lines.append(f"- [{a.severity}] **{a.kind}** · {a.subject}：{a.detail}")
    else:
        lines.append("- 本周期无预警触发。")
    lines += ["", "---", "", "自动生成，可直接转发群内或作为公众号素材（对应 C4C/C4D 联动）。", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------- #
# Natural-language query interface
# --------------------------------------------------------------------------- #
def answer_query(query: str, enriched: List[EnrichedMessage], submissions: List[Submission],
                 qa_pairs: List[QAPair], profiles: List[Dict[str, Any]],
                 challenges: List[Dict[str, Any]]) -> str:
    """Deterministic NL router for the five demo question families."""
    q = query.strip()

    m = re.search(r"([\u4e00-\u9fa5A-Za-z0-9_]+)提交了哪些挑战", q)
    if m:
        name = m.group(1)
        cids = sorted({s.challenge for s in submissions if s.student == name})
        return f"{name} 已提交：{', '.join(cids) if cids else '暂无记录'}。"

    m = re.search(r"(C\d[A-Za-z]?)\s*(还有谁没交|谁没提交|未提交)", q)
    if m:
        cid = m.group(1).upper()
        done = {s.student for s in submissions if s.challenge == cid}
        missing = [p["name"] for p in profiles if p["name"] not in done]
        return f"{cid} 未提交（{len(missing)} 人）：{', '.join(missing) if missing else '全部已交'}。"

    if "活跃" in q or "发言最多" in q:
        top = sorted(profiles, key=lambda p: -p["messages"])[:5]
        return "发言量 Top5：" + "、".join(f"{p['name']}({p['messages']})" for p in top) + "。"

    m = re.search(r"关于(.+?)的(常见问题|问题|FAQ)", q)
    if m:
        topic = m.group(1)
        hits = [qa for qa in qa_pairs if topic.lower() in (qa.question + qa.answer).lower()]
        if not hits:
            return f"未找到关于「{topic}」的 Q&A 记录。"
        return f"关于「{topic}」共 {len(hits)} 条 Q&A：" + "；".join(
            h.question[:40] for h in hits[:3]) + "。"

    if "班级状态" in q or "周报" in q:
        cids = {s.challenge for s in submissions}
        return (f"当前班级：{len(profiles)} 名学生、{len(enriched)} 条消息、"
                f"{len(submissions)} 次提交、{len(qa_pairs)} 条 Q&A，"
                f"覆盖 {len(cids)} 个挑战。")

    m = re.search(r"([\u4e00-\u9fa5A-Za-z0-9_]+)(答疑|回答了)几(次|题)", q)
    if m:
        name = m.group(1)
        n = sum(1 for qa in qa_pairs if qa.answerer == name)
        return f"{name} 共回答 {n} 个问题。"

    return ("暂不支持该类问题。可问：'张三提交了哪些挑战'、'C4 还有谁没交'、"
            "'最近一周谁最活跃'、'关于 GitHub 的常见问题'、'这周班级状态如何'。")


DEMO_QUERIES = [
    "张三提交了哪些挑战？",
    "C4 还有谁没交？",
    "最近一周谁最活跃？",
    "关于 GitHub 的常见问题有哪些？",
    "这周班级状态如何？",
    "李四答疑几次？",
]
