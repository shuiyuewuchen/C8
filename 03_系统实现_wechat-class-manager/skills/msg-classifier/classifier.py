#!/usr/bin/env python3
"""Standalone entry point for the msg-classifier skill."""
import json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from wcm.bridge import bridge
from wcm.analyze import enrich, evaluate_classifier
from wcm.core import OUT_DIR, DATA_DIR, load_config, load_json, write_text

cfg = load_config()
enriched = enrich(bridge("fixture", emit_sample=False), cfg["challenges"], cfg["group"])
write_text(OUT_DIR / "enriched_messages.jsonl",
           "\n".join(json.dumps(e.to_dict(), ensure_ascii=False) for e in enriched) + "\n")
ev = evaluate_classifier(enriched, load_json(DATA_DIR / "fixtures" / "labels.json"))
print(f"classified {len(enriched)} messages, accuracy {ev['accuracy']}%")
