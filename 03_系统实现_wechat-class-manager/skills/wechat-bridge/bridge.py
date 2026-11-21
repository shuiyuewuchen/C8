#!/usr/bin/env python3
"""Standalone entry point for the wechat-bridge skill."""
import argparse, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from wcm.bridge import bridge

p = argparse.ArgumentParser()
p.add_argument("--adapter", default="fixture", choices=["fixture", "cli"])
p.add_argument("--group", default="Elite20-项目协同群")
p.add_argument("--days", type=int, default=30)
a = p.parse_args()
msgs = bridge(a.adapter, a.group, a.days)
print(f"bridged {len(msgs)} messages -> outputs/messages.jsonl")
print("types:", sorted({m.type for m in msgs}))
