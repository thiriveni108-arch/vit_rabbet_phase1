"""Comprehensive Test Suite for Chatbot NL Capabilities, Query Planning, and Evidence Validation.

Validates all 17 user-mandated criteria:
1. Site subject count
2. Lab lookup for subject + visit
3. AE lookup
4. within-N-days parsing
5. 3x ULN parsing
6. raw numeric comparison parsing
7. patient summary
8. ALT trend
9. baseline vs Week 8 comparison
10. average lab value
11. maximum lab value
12. supported finding query
13. unknown question
14. ambiguous question
15. genuine zero-result / trap question
16. evidence refs all valid
17. Cut 1 vs Cut 12 answers differ correctly
"""

import unittest
from backend.study_service import StudyService
from backend.schemas import Question, Answer, RecordRef


class TestChatbotCapabilities(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = StudyService()
        cls.service.load(cut=12)

    # -------------------------------------------------------------------------
    # 1. Site subject count
    # -------------------------------------------------------------------------
    def test_01_site_subject_count(self):
        res = self.service.ask("How many subjects are at site S07?")
        self.assertEqual(res["intent"], "COUNT")
        self.assertIsInstance(res["answer"], int)
        self.assertGreater(res["answer"], 0)
        self.assertIn("subjects at site S07", res["text"])
        self.assertGreater(len(res["evidence"]), 0)
        for ev in res["evidence"]:
            self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 2. Lab lookup for subject + visit
    # -------------------------------------------------------------------------
    def test_02_lab_lookup_subject_visit(self):
        res = self.service.ask("What was ALT for 042-S07-001 at WEEK8?")
        self.assertEqual(res["intent"], "LOOKUP")
        self.assertIn("3.995", res["text"])
        self.assertIn("4.30x ULN", res["text"])
        self.assertEqual(len(res["evidence"]), 1)
        ev = res["evidence"][0]
        self.assertEqual(ev["domain"], "LB")
        self.assertEqual(ev["usubjid"], "042-S07-001")
        self.assertEqual(ev["seq"], 25)
        self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 3. AE lookup
    # -------------------------------------------------------------------------
    def test_03_ae_lookup(self):
        res = self.service.ask("Show adverse events for 042-S01-007.")
        self.assertEqual(res["intent"], "LOOKUP")
        self.assertIn("Myocardial infarction", res["text"])
        self.assertGreaterEqual(len(res["evidence"]), 1)
        ev = res["evidence"][0]
        self.assertEqual(ev["domain"], "AE")
        self.assertEqual(ev["usubjid"], "042-S01-007")
        self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 4. within-N-days parsing
    # -------------------------------------------------------------------------
    def test_04_within_n_days_parsing(self):
        res = self.service.ask("Show records within 14 days of WEEK8 for 042-S07-001")
        self.assertEqual(res["intent"], "LOOKUP")
        self.assertIsInstance(res["answer"], list)
        self.assertGreater(len(res["answer"]), 0)
        self.assertIn("within 14 days of WEEK8", res["text"])
        for ev in res["evidence"]:
            self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 5. 3x ULN parsing
    # -------------------------------------------------------------------------
    def test_05_three_x_uln_parsing(self):
        res = self.service.ask("Which subjects had ALT above 3x ULN?")
        self.assertEqual(res["intent"], "FILTER")
        self.assertIsInstance(res["answer"], list)
        self.assertIn("042-S07-001", res["answer"])
        self.assertIn("042-S05-003", res["answer"])
        self.assertIn("042-S08-014", res["answer"])
        self.assertGreaterEqual(len(res["evidence"]), 3)
        for ev in res["evidence"]:
            self.assertEqual(ev["domain"], "LB")
            self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 6. Raw numeric comparison parsing
    # -------------------------------------------------------------------------
    def test_06_raw_numeric_comparison_parsing(self):
        res = self.service.ask("Which subjects had creatinine above 1.5?")
        self.assertEqual(res["intent"], "FILTER")
        self.assertIsInstance(res["answer"], list)
        self.assertIn("042-S01-003", res["answer"])
        for ev in res["evidence"]:
            self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 7. Patient summary / Patient 360
    # -------------------------------------------------------------------------
    def test_07_patient_summary(self):
        res = self.service.ask("Summarize subject 042-S07-001")
        self.assertEqual(res["intent"], "SUBJECT_360")
        self.assertIn("042-S07-001", res["text"])
        self.assertIn("Site S07", res["text"])
        self.assertIn("Total records", res["text"])
        self.assertIn("finding", res["text"].lower())
        self.assertGreater(len(res["evidence"]), 0)
        for ev in res["evidence"]:
            self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 8. ALT trend
    # -------------------------------------------------------------------------
    def test_08_alt_trend(self):
        res = self.service.ask("Show ALT trend over time for 042-S07-001")
        self.assertEqual(res["intent"], "TREND")
        self.assertIsInstance(res["answer"], list)
        self.assertGreaterEqual(len(res["answer"]), 3)
        self.assertIn("trend for 042-S07-001", res["text"])
        # Check structured series format
        first_pt = res["answer"][0]
        self.assertIn("visit", first_pt)
        self.assertIn("value", first_pt)
        self.assertIn("unit", first_pt)
        self.assertIn("evidence", first_pt)
        for ev in res["evidence"]:
            self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 9. Baseline vs Week 8 comparison
    # -------------------------------------------------------------------------
    def test_09_baseline_vs_week8_comparison(self):
        res = self.service.ask("Compare ALT at baseline and Week 8 for 042-S07-001")
        self.assertEqual(res["intent"], "COMPARISON")
        self.assertIn("BASELINE", res["text"])
        self.assertIn("WEEK8", res["text"])
        self.assertIn("increase", res["text"])
        self.assertEqual(len(res["evidence"]), 2)
        for ev in res["evidence"]:
            self.assertEqual(ev["domain"], "LB")
            self.assertEqual(ev["usubjid"], "042-S07-001")
            self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 10. Average lab value
    # -------------------------------------------------------------------------
    def test_10_average_lab_value(self):
        res = self.service.ask("What is the average ALT at site S07?")
        self.assertEqual(res["intent"], "AGGREGATE")
        self.assertIsInstance(res["answer"], (int, float))
        self.assertGreater(res["answer"], 0)
        self.assertIn("average ALT at site S07 is", res["text"])
        self.assertGreater(len(res["evidence"]), 0)
        for ev in res["evidence"]:
            self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 11. Maximum lab value
    # -------------------------------------------------------------------------
    def test_11_maximum_lab_value(self):
        res = self.service.ask("What was the maximum bilirubin value for 042-S07-001?")
        self.assertEqual(res["intent"], "AGGREGATE")
        self.assertIsInstance(res["answer"], (int, float))
        self.assertAlmostEqual(float(res["answer"]), 5.38, places=2)
        self.assertIn("5.38", res["text"])
        self.assertEqual(len(res["evidence"]), 1)
        ev = res["evidence"][0]
        self.assertEqual(ev["seq"], 27)
        self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 12. Supported finding query
    # -------------------------------------------------------------------------
    def test_12_supported_finding_query(self):
        res = self.service.ask("Which subjects meet the Hy's law criteria?")
        self.assertEqual(res["intent"], "FINDING")
        self.assertIsInstance(res["answer"], list)
        self.assertEqual(len(res["answer"]), 3)
        self.assertIn("042-S07-001", res["answer"])
        self.assertIn("042-S05-003", res["answer"])
        self.assertIn("042-S08-014", res["answer"])
        self.assertGreaterEqual(len(res["evidence"]), 6)
        for ev in res["evidence"]:
            self.assertTrue(self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]))

    # -------------------------------------------------------------------------
    # 13. Unknown question
    # -------------------------------------------------------------------------
    def test_13_unknown_question(self):
        res = self.service.ask("What is the weather in Paris?")
        self.assertEqual(res["intent"], "UNSUPPORTED")
        self.assertEqual(res["answer"], [])
        self.assertEqual(res["evidence"], [])
        self.assertEqual(res["confidence"], 0.0)
        self.assertIn("unable to answer this question from the study dataset", res["text"])

    # -------------------------------------------------------------------------
    # 14. Ambiguous question
    # -------------------------------------------------------------------------
    def test_14_ambiguous_question(self):
        res = self.service.ask("What was the value?")
        self.assertEqual(res["intent"], "AMBIGUOUS")
        self.assertEqual(res["answer"], [])
        self.assertEqual(res["evidence"], [])
        self.assertEqual(res["confidence"], 0.0)
        self.assertIn("specify a subject", res["text"])

    # -------------------------------------------------------------------------
    # 15. Genuine zero-result / trap question
    # -------------------------------------------------------------------------
    def test_15_genuine_zero_result_trap_question(self):
        res = self.service.ask("Which subjects at site S01 received a wrong dose?")
        self.assertIn(res["intent"], ("FINDING", "TRAP"))
        self.assertEqual(res["answer"], [])
        self.assertEqual(res["evidence"], [])
        self.assertIn("No dosing errors at site S01", res["text"])

    # -------------------------------------------------------------------------
    # 16. Strict evidence validation: All evidence references physically exist
    # -------------------------------------------------------------------------
    def test_16_all_evidence_refs_exist_in_current_graph(self):
        questions = [
            "How many subjects are at site S07?",
            "What was ALT for 042-S07-001 at WEEK8?",
            "Show adverse events for 042-S01-007.",
            "Which subjects had ALT above 3x ULN?",
            "Compare ALT at baseline and Week 8 for 042-S07-001",
            "Show ALT trend over time for 042-S07-001",
            "What is the average ALT at site S07?",
            "Summarize subject 042-S07-001",
            "Which subjects meet the Hy's law criteria?",
        ]
        for q in questions:
            res = self.service.ask(q)
            for ev in res["evidence"]:
                self.assertTrue(
                    self.service.graph.has_record(ev["domain"], ev["usubjid"], ev["seq"]),
                    f"Invalid evidence reference ({ev['domain']}, {ev['usubjid']}, {ev['seq']}) found for query: '{q}'",
                )

    # -------------------------------------------------------------------------
    # 17. Cut 1 vs Cut 12 answers differ correctly
    # -------------------------------------------------------------------------
    def test_17_cut_change_consistency_across_chatbot(self):
        # At Cut 1: 0 Hy's law candidates
        self.service.load(cut=1)
        res_cut1 = self.service.ask("Which subjects meet the Hy's law criteria?")
        self.assertEqual(res_cut1["answer"], [])
        self.assertEqual(res_cut1["evidence"], [])

        # At Cut 12: 3 Hy's law candidates
        self.service.load(cut=12)
        res_cut12 = self.service.ask("Which subjects meet the Hy's law criteria?")
        self.assertEqual(len(res_cut12["answer"]), 3)
        self.assertEqual(len(res_cut12["evidence"]), 6)


if __name__ == "__main__":
    unittest.main()
