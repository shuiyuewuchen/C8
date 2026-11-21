#!/usr/bin/env python3
"""Standalone entry point for the qa-sink skill."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from wcm.bridge import bridge
from wcm.analyze import enrich, extract_qa
from wcm.core import load_config

cfg = load_config()
e = enrich(bridge("fixture", emit_sample=False), cfg["challenges"], cfg["group"])
pairs = extract_qa(e)
print(f"extracted {len(pairs)} Q&A pairs")
for qa in pairs[:3]:
    print(f"  [{qa.quality_score}] {qa.question[:36]} -> {qa.answerer}")
