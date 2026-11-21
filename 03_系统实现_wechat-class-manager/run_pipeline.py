#!/usr/bin/env python3
"""End-to-end pipeline: WeChat message stream -> class-management artefacts.

Usage:
  python3 run_pipeline.py                       # offline fixture (default)
  python3 run_pipeline.py --adapter cli --group "Elite20" --days 7
  python3 run_pipeline.py --serve                # also start the dashboard

Every run rewrites outputs/ deterministically (SQLite excluded - it is updated).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from wcm import bridge, engines, watcher
from wcm.analyze import detect_submissions, enrich, evaluate_classifier, extract_qa
from wcm.core import DATA_DIR, OUT_DIR, load_config, load_json, write_json, write_text
from wcm.dashboard import build_dashboard_data, serve, write_dashboard_html
from wcm.graph import PropertyGraph, build_graph, build_profiles


def main() -> int:
    ap = argparse.ArgumentParser(description="WeChat -> class management pipeline")
    ap.add_argument("--adapter", choices=["fixture", "cli"], default="fixture")
    ap.add_argument("--group", default="Elite20-项目协同群")
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--serve", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    args = ap.parse_args()

    cfg = load_config()
    challenges, group = cfg["challenges"], cfg["group"]
    # deterministic full rebuild; the watcher's incremental behaviour is
    # exercised separately in verify.py with an isolated checkpoint file.
    watcher.CHECKPOINT.unlink(missing_ok=True)

    print("[1/8] Layer 1  bridge ..................", end=" ")
    messages = bridge.bridge(args.adapter, args.group, args.days)
    print(f"{len(messages)} messages")

    print("[2/8] Layer 2  classify + link .........", end=" ")
    enriched = enrich(messages, challenges, group)
    write_text(OUT_DIR / "enriched_messages.jsonl",
               "\n".join(json.dumps(e.to_dict(), ensure_ascii=False) for e in enriched) + "\n")
    print(f"intents: {len({e.intent for e in enriched})}")

    labels = load_json(DATA_DIR / "fixtures" / "labels.json")
    evaluation = evaluate_classifier(enriched, labels)
    write_json(OUT_DIR / "classification_eval.json", evaluation)
    print(f"          accuracy = {evaluation['accuracy']}% ({evaluation['correct']}/{evaluation['total']})")

    print("[3/8] Layer 2  submission detector .....", end=" ")
    submissions, matrix = detect_submissions(enriched)
    write_json(OUT_DIR / "submissions.json", {"records": [s.to_dict() for s in submissions], "matrix": matrix})
    print(f"{len(submissions)} submissions")

    print("[4/8] Layer 2  QA extractor ............", end=" ")
    qa_pairs = extract_qa(enriched)
    write_json(OUT_DIR / "qa_pairs.json", [q.to_dict() for q in qa_pairs])
    print(f"{len(qa_pairs)} pairs")

    print("[5/8] Layer 3  property graph .........", end=" ")
    graph = PropertyGraph()
    build_graph(enriched, submissions, qa_pairs, challenges, graph)
    stats = graph.count()
    write_json(OUT_DIR / "graph_stats.json", stats)
    print(f"{stats['total_nodes']} nodes / {stats['total_edges']} edges")
    graph.close()

    print("[6/8] Layer 3  student profiles ........", end=" ")
    profiles = build_profiles(enriched, submissions, qa_pairs)
    print(f"{len(profiles)} students")

    print("[7/8] Layer 4  alerts + report .........", end=" ")
    reference = max(e.message.dt for e in enriched)
    alerts = engines.run_alerts(enriched, submissions, challenges, group, reference)
    report = engines.build_weekly_report(enriched, submissions, qa_pairs, profiles,
                                         alerts, challenges, week_label="W4")
    write_text(OUT_DIR / "weekly_report.md", report)
    print(f"{len(alerts)} alerts")

    print("[8/8] Layer 4  dashboard + NL queries  ", end=" ")
    build_dashboard_data(enriched, submissions, qa_pairs, profiles, alerts, challenges)
    write_dashboard_html()
    demo = [{"query": q, "answer": engines.answer_query(q, enriched, submissions,
                                                        qa_pairs, profiles, challenges)}
            for q in engines.DEMO_QUERIES]
    write_json(OUT_DIR / "nl_query_demo.json", demo)
    print(f"{len(demo)} demo queries")

    summary = {
        "adapter": args.adapter,
        "group": args.group,
        "messages": len(messages),
        "intent_distribution": {k: sum(1 for e in enriched if e.intent == k)
                                for k in sorted({e.intent for e in enriched})},
        "classification_accuracy_pct": evaluation["accuracy"],
        "submissions": len(submissions),
        "qa_pairs": len(qa_pairs),
        "graph": stats,
        "students": len(profiles),
        "alerts": len(alerts),
        "data_window": [min(e.message.timestamp for e in enriched),
                        max(e.message.timestamp for e in enriched)],
    }
    write_json(OUT_DIR / "pipeline_summary.json", summary)
    print("\nDone. Artefacts in outputs/. Run `python3 verify.py` for acceptance check.")
    if args.serve:
        serve(port=args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
