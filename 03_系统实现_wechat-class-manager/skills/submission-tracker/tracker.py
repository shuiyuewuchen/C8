#!/usr/bin/env python3
"""Standalone entry point for the submission-tracker skill."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from wcm.bridge import bridge
from wcm.analyze import detect_submissions, enrich
from wcm.core import load_config

cfg = load_config()
e = enrich(bridge("fixture", emit_sample=False), cfg["challenges"], cfg["group"])
subs, matrix = detect_submissions(e)
missing = [s for s in subs if s.missing]
print(f"{len(subs)} submissions, {len(matrix)} students, {len(missing)} flagged incomplete")
for s in missing[:5]:
    print(f"  - {s.student} {s.challenge}: missing {', '.join(s.missing)}")
