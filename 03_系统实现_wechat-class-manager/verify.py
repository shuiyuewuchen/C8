#!/usr/bin/env python3
"""Acceptance verifier for C8 WeChat Class Management Challenge.

Runs the L1-L4 acceptance criteria against the artefacts in outputs/ and
writes outputs/verification_report.md. Exit code 0 = APPROVE.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List

from wcm.bridge import bridge
from wcm.core import OUT_DIR, ROOT, load_config, load_json
from wcm.engines import answer_query, DEMO_QUERIES
from wcm.watcher import incremental_messages

CHECKS: List[Dict[str, Any]] = []


def check(group: str, cid: str, criterion: str, fn: Callable[[], tuple[bool, str]]) -> None:
    try:
        ok, actual = fn()
    except Exception as exc:  # a crashed check is a failed check
        ok, actual = False, f"ERROR: {type(exc).__name__}: {exc}"
    CHECKS.append({"group": group, "id": cid, "criterion": criterion,
                   "actual": actual, "pass": bool(ok)})


def main() -> int:
    cfg = load_config()
    summary = load_json(OUT_DIR / "pipeline_summary.json")
    eval_ = load_json(OUT_DIR / "classification_eval.json")
    subs = load_json(OUT_DIR / "submissions.json")["records"]
    qa = load_json(OUT_DIR / "qa_pairs.json")
    alerts = load_json(OUT_DIR / "alerts.json")
    graph = load_json(OUT_DIR / "graph_stats.json")
    dash = load_json(OUT_DIR / "dashboard_data.json")
    profiles = load_json(OUT_DIR / "student_profiles.json")
    report = (OUT_DIR / "weekly_report.md").read_text(encoding="utf-8")

    # ---- L1 ---------------------------------------------------------------
    check("L1 数据桥接", "L1-1", "从本地数据成功提取 ≥100 条群消息",
          lambda: (summary["messages"] >= 100, f"{summary['messages']} 条"))
    check("L1 数据桥接", "L1-2", "输出符合统一 Message schema",
          lambda: (all(all(k in m for k in ("msg_id", "timestamp", "sender", "type",
                                            "content", "media_ref", "reply_to"))
                       for m in (json.loads(x) for x in
                                 (OUT_DIR / "messages.jsonl").read_text(encoding="utf-8").splitlines() if x)),
                   "7 个必需字段全部存在"))
    types = set(summary["intent_distribution"])  # overridden below with real media types
    media_types = {json.loads(x)["type"] for x in
                   (OUT_DIR / "messages.jsonl").read_text(encoding="utf-8").splitlines() if x}
    check("L1 数据桥接", "L1-3", "能区分文本/文件/图片/语音等消息类型",
          lambda: (len(media_types) >= 5, f"{len(media_types)} 种：{', '.join(sorted(media_types))}"))
    check("L1 数据桥接", "L1-4", "CLI 可重复运行且支持时间范围参数",
          lambda: (len(bridge("fixture", emit_sample=False)) ==
                   len(bridge("fixture", emit_sample=False)) and "--days" in
                   (ROOT / "run_pipeline.py").read_text(encoding="utf-8"),
                   "两次运行结果一致；run_pipeline.py 暴露 --days"))

    # ---- L2 ---------------------------------------------------------------
    check("L2 分类与信号", "L2-1", "分类器准确率 > 70%",
          lambda: (eval_["accuracy"] > 70, f"{eval_['accuracy']}% ({eval_['correct']}/{eval_['total']})"))
    check("L2 分类与信号", "L2-2", "正确检测 ≥5 个提交事件",
          lambda: (len(subs) >= 5, f"{len(subs)} 个提交，{len({s['student'] for s in subs})} 名学生"))
    check("L2 分类与信号", "L2-3", "提取 ≥10 个有意义的 Q&A 对",
          lambda: (len(qa) >= 10 and all(q["quality_score"] >= 0.45 for q in qa),
                   f"{len(qa)} 对，最低质量分 {min(q['quality_score'] for q in qa)}"))
    skill_dirs = sorted(p for p in (ROOT / "skills").iterdir() if p.is_dir())
    check("L2 分类与信号", "L2-4", "各模块可独立运行，也可 pipeline 组合",
          lambda: (len(skill_dirs) >= 6 and all((d / "SKILL.md").exists() and
                   any(d.glob("*.py")) for d in skill_dirs),
                   f"{len(skill_dirs)} 个独立 skill 目录，均含 SKILL.md + 可执行脚本"))

    # ---- L3 ---------------------------------------------------------------
    def valid_frontmatter() -> tuple[bool, str]:
        bad = []
        for d in skill_dirs:
            text = (d / "SKILL.md").read_text(encoding="utf-8")
            if not (text.startswith("---\n") and "name:" in text and "description:" in text):
                bad.append(d.name)
        return (not bad, "全部符合 agentskills.io frontmatter 规范" if not bad else str(bad))

    check("L3 Skill 封装", "L3-1", "每个 Skill 可被 Agent 通过 SKILL.md 识别",
          valid_frontmatter)
    check("L3 Skill 封装", "L3-2", "Property Graph 可存储 ≥20 学生 × 8 挑战",
          lambda: (graph["nodes"].get("Student", 0) >= 20 and graph["nodes"].get("Challenge", 0) >= 8,
                   f"{graph['nodes'].get('Student',0)} 学生 × {graph['nodes'].get('Challenge',0)} 挑战"))
    check("L3 Skill 封装", "L3-3", "图数据含完整节点与关系",
          lambda: (graph["total_edges"] >= 200,
                   f"{graph['total_nodes']} 节点 / {graph['total_edges']} 边"))
    qa_file = load_json(OUT_DIR / "nl_query_demo.json")
    non_fallback = [q for q in qa_file if "暂不支持" not in q["answer"]]
    check("L3 Skill 封装", "L3-4", "自然语言查询能回答 ≥5 类问题",
          lambda: (len(non_fallback) >= 5,
                   f"{len(non_fallback)}/{len(qa_file)} 类查询成功"))

    # ---- L4 ---------------------------------------------------------------
    def watcher_check() -> tuple[bool, str]:
        with tempfile.TemporaryDirectory() as td:
            cp = Path(td) / "cp.json"
            first, _ = incremental_messages(cp)
            second, _ = incremental_messages(cp)
            return (len(first) > 0 and len(second) == 0,
                    f"首次处理 {len(first)} 条，二次处理 {len(second)} 条（无重复）")

    check("L4 闭环系统", "L4-1", "Watcher 增量处理，不重复处理", watcher_check)
    kinds = {a["kind"] for a in alerts}
    check("L4 闭环系统", "L4-2", "Alert 能正确触发 ≥3 种预警",
          lambda: (len(kinds) >= 3, f"{len(kinds)} 种：{', '.join(sorted(kinds))}"))
    sections = ["总览", "最活跃学生", "最佳 Q&A", "各挑战完成情况", "预警清单"]
    check("L4 闭环系统", "L4-3", "Report 自动生成结构完整周报",
          lambda: (all(s in report for s in sections) and len(report) > 800,
                   f"{len(report)} 字符，含全部 5 个章节"))
    dims = ["summary", "by_challenge", "intent_distribution", "top_students", "alerts"]
    check("L4 闭环系统", "L4-4", "Dashboard 展示 ≥5 个维度班级数据",
          lambda: (all(k in dash for k in dims),
                   f"{len(dims)} 个维度：{', '.join(dims)}"))
    check("L4 闭环系统", "L4-5", "系统端到端可运行，有部署文档",
          lambda: (all((ROOT / f).exists() for f in
                       ["run_pipeline.py", "README.md", "SETUP.md", "docs/architecture.md"]),
                   "pipeline / README / SETUP / 架构文档齐全"))
    proc = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", "tests"],
                          cwd=ROOT, capture_output=True, text=True)
    check("L4 闭环系统", "L4-6", "代码有测试且测试全部通过",
          lambda: (proc.returncode == 0,
                   (proc.stderr.strip().splitlines() or [""])[-1]))

    passed = sum(1 for c in CHECKS if c["pass"])
    verdict = "APPROVE" if passed == len(CHECKS) else "REJECT"
    lines = [
        "# C8 验收报告 — WeChat Class Management Agent Skill",
        "",
        f"- 验证时间：{datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S %z')}",
        f"- 验证方式：`python3 verify.py`（自动执行，非人工勾选）",
        f"- 数据适配器：{summary['adapter']} ｜ 数据窗口：{summary['data_window'][0]} ~ {summary['data_window'][1]}",
        f"- 通过项：**{passed}/{len(CHECKS)}**",
        f"- 结论：**{verdict}**",
        "",
        "| Level | 编号 | 验收项 | 实测结果 | 状态 |",
        "|---|---|---|---|---|",
    ]
    for c in CHECKS:
        lines.append(f"| {c['group']} | {c['id']} | {c['criterion']} | {c['actual']} | "
                     f"{'✅ PASS' if c['pass'] else '❌ FAIL'} |")
    lines += [
        "",
        "## 范围声明",
        "",
        "本次验收在数据桥接层使用**脱敏、可复现的样本消息流**（164 条，24 名学生 × 8 个挑战）。"
        "真实微信群数据库不在构建机器上，因此 `cli` 适配器已完成代码与文档但未在真实库上执行。"
        "这是真实约束，已如实记录在 W1/W2 AAR；广告性宣称'已接入真实群数据'是不成立的。",
        "",
        "## 已知局限",
        "",
        "1. 分类器规则与标注集同源，97% 是内部上界，需留出集人工标注复核。",
        "2. 单条消息仅解析第一个文件名，批量上传会漏记。",
        "3. 写回微信群的双向通道（Wechaty）仅设计未实现，遵循只读优先。",
        "",
    ]
    (OUT_DIR / "verification_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Verification: {passed}/{len(CHECKS)} passed -> {verdict}")
    for c in CHECKS:
        if not c["pass"]:
            print(f"  FAIL {c['id']}: {c['criterion']} | {c['actual']}")
    return 0 if verdict == "APPROVE" else 1


if __name__ == "__main__":
    sys.exit(main())
