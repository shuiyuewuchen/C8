#!/usr/bin/env python3
"""Standalone entry point for the student-profile skill."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from wcm.bridge import bridge
from wcm.analyze import detect_submissions, enrich, extract_qa
from wcm.core import load_config
from wcm.graph import build_profiles

cfg = load_config()
e = enrich(bridge("fixture", emit_sample=False), cfg["challenges"], cfg["group"])
subs, _ = detect_submissions(e)
profiles = build_profiles(e, subs, extract_qa(e))
print(f"built {len(profiles)} profiles; sample: {profiles[0]}")
