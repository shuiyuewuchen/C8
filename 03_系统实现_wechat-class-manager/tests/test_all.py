"""Unit + integration tests. Run: python3 -m unittest discover -s tests -v"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from wcm.analyze import detect_submissions, enrich, evaluate_classifier, extract_qa
from wcm.bridge import bridge, normalize
from wcm.core import DATA_DIR, Message, OUT_DIR, load_config, load_json, parse_submission_filename
from wcm.dashboard import build_dashboard_data
from wcm.engines import answer_query, build_weekly_report, run_alerts
from wcm.graph import PropertyGraph, build_graph, build_profiles


class TestBridge(unittest.TestCase):
    def test_normalize_schema(self):
        m = normalize({"msg_id": "x1", "time": "2026-05-11T09:00:00+08:00",
                       "sender": "张三", "type": "FILE", "text": "hi"})
        self.assertEqual(m.msg_id, "x1")
        self.assertEqual(m.type, "file")
        self.assertEqual(m.sender_nickname, "张三")

    def test_fixture_count(self):
        msgs = bridge("fixture", emit_sample=False)
        self.assertGreaterEqual(len(msgs), 100)
        self.assertTrue(all(m.msg_id for m in msgs))


class TestAnalyze(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = load_config()
        cls.challenges, cls.group = cfg["challenges"], cfg["group"]
        cls.msgs = bridge("fixture", emit_sample=False)
        cls.enriched = enrich(cls.msgs, cls.challenges, cls.group)

    def test_filename_parser(self):
        p = parse_submission_filename("张三_C4B_demo.pdf")
        self.assertEqual((p["student"], p["challenge"]), ("张三", "C4"))

    def test_classifier_accuracy(self):
        labels = load_json(DATA_DIR / "fixtures" / "labels.json")
        ev = evaluate_classifier(self.enriched, labels)
        self.assertGreater(ev["accuracy"], 70.0)

    def test_submission_detector_flags_missing_ai_log(self):
        subs, _ = detect_submissions(self.enriched)
        flagged = [s for s in subs if "AI日志" in s.missing]
        self.assertGreaterEqual(len(flagged), 1)
        self.assertTrue(all(s.status == "needs_revision" for s in flagged))

    def test_qa_extractor(self):
        pairs = extract_qa(self.enriched)
        self.assertGreaterEqual(len(pairs), 10)
        self.assertTrue(all(p.question and p.answer for p in pairs))


class TestGraph(unittest.TestCase):
    def test_crud_and_counts(self):
        with tempfile.TemporaryDirectory() as td:
            g = PropertyGraph(Path(td) / "g.sqlite")
            g.upsert_node("student:甲", "Student", name="甲")
            g.upsert_node("challenge:C1", "Challenge", id="C1")
            g.upsert_edge("student:甲", "challenge:C1", "PROGRESSED_TO")
            g.conn.commit()
            self.assertEqual(g.node("student:甲")["label"], "Student")
            self.assertEqual(g.neighbours("student:甲", "PROGRESSED_TO")[0]["node"]["label"], "Challenge")
            self.assertEqual(g.count()["total_edges"], 1)
            g.close()

    def test_graph_populated(self):
        cfg = load_config()
        subs, _ = detect_submissions(self.enriched) if hasattr(self, "enriched") else (None, None)
        # use saved outputs to keep test fast and independent
        data = load_json(OUT_DIR / "qa_pairs.json")
        qa = [__import__("wcm.core", fromlist=["QAPair"]).QAPair(**d) for d in data]
        recs = load_json(OUT_DIR / "submissions.json")["records"]
        subs = [__import__("wcm.core", fromlist=["Submission"]).Submission(**d) for d in recs]
        with tempfile.TemporaryDirectory() as td:
            g = PropertyGraph(Path(td) / "g.sqlite")
            build_graph(TestAnalyze.enriched, subs, qa, cfg["challenges"], g)
            counts = g.count()
            self.assertGreaterEqual(counts["total_nodes"], 20 * 8)
            self.assertGreaterEqual(counts["total_edges"], 100)
            g.close()


class TestEngines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cfg = load_config()
        cls.challenges, cls.group = cfg["challenges"], cfg["group"]
        cls.enriched = enrich(bridge("fixture", emit_sample=False), cls.challenges, cls.group)
        cls.subs, _ = detect_submissions(cls.enriched)
        cls.qa = extract_qa(cls.enriched)
        cls.profiles = build_profiles(cls.enriched, cls.subs, cls.qa)
        cls.alerts = run_alerts(cls.enriched, cls.subs, cls.challenges, cls.group,
                                max(e.message.dt for e in cls.enriched))

    def test_at_least_three_alert_kinds(self):
        kinds = {a.kind for a in self.alerts}
        self.assertGreaterEqual(len(kinds), 3)
        self.assertIn("low_submission_rate", kinds)

    def test_report_sections(self):
        report = build_weekly_report(self.enriched, self.subs, self.qa, self.profiles,
                                     self.alerts, self.challenges)
        for section in ("总览", "最活跃学生", "最佳 Q&A", "各挑战完成情况", "预警清单"):
            self.assertIn(section, report)

    def test_nl_query_families(self):
        answers = [answer_query(q, self.enriched, self.subs, self.qa, self.profiles, self.challenges)
                   for q in ["张三提交了哪些挑战？", "C4 还有谁没交？", "最近一周谁最活跃？",
                             "关于 GitHub 的常见问题有哪些？", "这周班级状态如何？"]]
        self.assertTrue(all(len(a) > 5 for a in answers))
        self.assertIn("张三", answers[0])

    def test_dashboard_payload(self):
        d = build_dashboard_data(self.enriched, self.subs, self.qa, self.profiles,
                                 self.alerts, self.challenges)
        self.assertGreaterEqual(d["summary"]["messages"], 100)
        self.assertGreaterEqual(len(d["by_challenge"]), 8)


if __name__ == "__main__":
    unittest.main(verbosity=2)
