#!/usr/bin/env python3
"""Standalone entry point for the class-report skill."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from wcm.bridge import bridge
from wcm.analyze import detect_submissions, enrich, extract_qa
from wcm.core import load_config
from wcm.engines import run_alerts, build_weekly_report
from wcm.graph import build_profiles

cfg = load_config()
e = enrich(bridge("fixture", emit_sample=False), cfg["challenges"], cfg["group"])
subs, _ = detect_submissions(e)
qa = extract_qa(e)
profiles = build_profiles(e, subs, qa)
alerts = run_alerts(e, subs, cfg["challenges"], cfg["group"], max(x.message.dt for x in e))
report = build_weekly_report(e, subs, qa, profiles, alerts, cfg["challenges"])
print(f"report generated: {len(report)} chars, {len(alerts)} alerts")
