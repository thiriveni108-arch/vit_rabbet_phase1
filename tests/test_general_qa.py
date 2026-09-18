"""Comprehensive General-Purpose QA Test Suite for ATLAS AI Agent.

Validates that ATLAS interprets randomly phrased questions, builds structured QueryPlans,
executes against StudyGraph/DocumentKnowledge deterministically, validates evidence,
and handles edge cases (zero results, ambiguities, out-of-scope queries, follow-ups, cut progression).
"""

import unittest
import time
from stage1.atlas import StudyGraph
from backend.study_service import StudyService
from backend.schemas import Answer, RecordRef
from backend.config import DATA_DIR


class TestGeneralQA(unittest.TestCase):
    """Regression and random phrasing test suite for general study QA."""

    @classmethod
    def setUpClass(cls):
        cls.service = StudyService(DATA_DIR)
        cls.agent = cls.service.agent
        cls.graph = cls.service.graph

    def setUp(self):
        # Reset conversation state between test cases unless testing follow-ups
        self.agent.reset_conversation()

    # =========================================================================
    # 1. BASELINE CUT 12 VERIFICATION
    # =========================================================================
    def test_01_baseline_cut_12(self):
        self.assertEqual(len(self.graph.subjects), 241)
        self.assertEqual(self.graph.last_build_stats["records"], 26482)
        findings = self.graph.get_findings()
        self.assertEqual(len(findings), 280)
        hys = self.graph.find_hys_law_candidates()
        self.assertEqual(len(hys), 3)
        sae = self.graph.find_serious_adverse_events()
        self.assertEqual(len(sae), 5)
        creat = self.graph.find_exclusion_violations()
        self.assertEqual(len(creat), 4)
        meds = self.graph.find_prohibited_medications()
        self.assertEqual(len(meds), 14)
        vis = self.graph.find_visit_window_deviations()
        self.assertEqual(len(vis), 254)

    # =========================================================================
    # 2. COUNT QUERIES (VARIOUS PHRASINGS)
    # =========================================================================
    def test_02_count_site_subjects_phrasings(self):
        phrasings = [
            "How many subjects are at site S07?",
            "How many people were enrolled at site S07?",
            "Participant count for S07?",
            "Number of patients from S07?",
            "Count subjects at site S07",
        ]
        for q in phrasings:
            ans = self.agent.answer(q)
            self.assertEqual(ans.answer, 20, f"Failed on phrasing: '{q}'")
            self.assertEqual(len(ans.evidence), 20)
            for ev in ans.evidence:
                self.assertTrue(self.graph.has_record(ev.domain, ev.usubjid, ev.seq))

    def test_03_count_female_subjects(self):
        ans = self.agent.answer("How many women are in the study?")
        self.assertIsInstance(ans.answer, int)
        self.assertGreater(ans.answer, 50)
        self.assertIn("female", ans.text.lower())
        self.assertGreater(len(ans.evidence), 0)

    def test_04_count_placebo_subjects(self):
        ans = self.agent.answer("How many patients are on placebo?")
        self.assertIsInstance(ans.answer, int)
        self.assertEqual(ans.answer, 113)
        self.assertIn("placebo", ans.text.lower())

    def test_05_count_hospitalized_aes(self):
        ans = self.agent.answer("How many hospitalized adverse events happened?")
        self.assertIsInstance(ans.answer, int)
        self.assertGreaterEqual(ans.answer, 5)
        for ev in ans.evidence:
            self.assertEqual(ev.domain, "AE")
            self.assertTrue(self.graph.has_record(ev.domain, ev.usubjid, ev.seq))

    def test_06_count_alt_measurements(self):
        ans = self.agent.answer("How many ALT measurements are there?")
        self.assertIsInstance(ans.answer, int)
        self.assertGreater(ans.answer, 1000)

    def test_07_count_findings_at_cut_12(self):
        ans = self.agent.answer("How many findings occurred at Cut 12?")
        self.assertEqual(ans.answer, 280)
        self.assertIn("280", ans.text)

    def test_08_count_serious_adverse_events(self):
        ans = self.agent.answer("How many serious adverse events are there?")
        self.assertEqual(ans.answer, 5)

    def test_09_count_discontinued_due_to_ae(self):
        ans = self.agent.answer("How many subjects discontinued due to an adverse event?")
        self.assertIsInstance(ans.answer, int)
        self.assertGreater(ans.answer, 0)

    # =========================================================================
    # 3. GROUP BY QUERIES
    # =========================================================================
    def test_10_group_by_site(self):
        ans = self.agent.answer("How many subjects per site?")
        self.assertIsInstance(ans.answer, dict)
        self.assertIn("S07", ans.answer)
        self.assertEqual(ans.answer["S07"], 20)
        self.assertIn("structured_data", ans.to_dict())

    def test_11_group_by_arm(self):
        ans = self.agent.answer("How many subjects in each arm?")
        self.assertIsInstance(ans.answer, dict)
        self.assertTrue(any("DRUG" in k or "PLACEBO" in k for k in ans.answer.keys()))

    def test_12_group_by_finding_type(self):
        ans = self.agent.answer("Count findings by type.")
        self.assertIsInstance(ans.answer, dict)
        self.assertIn("potential_hys_law", ans.answer)
        self.assertEqual(ans.answer["potential_hys_law"], 3)

    # =========================================================================
    # 4. LOOKUP QUERIES
    # =========================================================================
    def test_13_lookup_lab_subject_visit(self):
        phrasings = [
            "What was ALT for 042-S07-001 at Week 8?",
            "Give me ALT for 042-S07-001 at WEEK8",
            "Show Week 8 ALT for patient 042-S07-001",
        ]
        for q in phrasings:
            ans = self.agent.answer(q)
            self.assertIn("3.995", ans.text)
            self.assertTrue(any(ev.domain == "LB" and ev.usubjid == "042-S07-001" and ev.seq == 25 for ev in ans.evidence))

    def test_14_lookup_baseline_lab(self):
        ans = self.agent.answer("What was ALT at baseline for 042-S07-001?")
        self.assertIn("0.283", ans.text)
        self.assertEqual(len(ans.evidence), 1)

    def test_15_lookup_latest_lab(self):
        ans = self.agent.answer("What is the latest ALT for 042-S07-001?")
        self.assertIn("EOS", ans.text.upper())
        self.assertIn("0.33", ans.text)

    def test_16_lookup_earliest_lab(self):
        ans = self.agent.answer("What was the earliest ALT for 042-S07-001?")
        self.assertIn("SCREENING", ans.text.upper())

    def test_17_lookup_adverse_events_for_subject(self):
        ans = self.agent.answer("Show adverse events for 042-S01-007.")
        self.assertGreaterEqual(len(ans.answer), 1)
        for ev in ans.evidence:
            self.assertEqual(ev.domain, "AE")
            self.assertEqual(ev.usubjid, "042-S01-007")

    def test_18_lookup_medications_for_subject(self):
        ans = self.agent.answer("Show medications recorded for 042-S05-003.")
        self.assertGreaterEqual(len(ans.answer), 1)
        for ev in ans.evidence:
            self.assertEqual(ev.domain, "CM")
            self.assertEqual(ev.usubjid, "042-S05-003")

    def test_19_lookup_vital_signs(self):
        ans = self.agent.answer("What was the blood pressure for 042-S07-001 at baseline?")
        self.assertGreaterEqual(len(ans.answer), 1)
        for ev in ans.evidence:
            self.assertEqual(ev.domain, "VS")

    # =========================================================================
    # 5. FILTER / LIST QUERIES
    # =========================================================================
    def test_20_filter_subjects_site_s05(self):
        ans = self.agent.answer("Which subjects are at site S05?")
        self.assertIsInstance(ans.answer, list)
        self.assertGreater(len(ans.answer), 0)
        for subj in ans.answer:
            self.assertIn("-S05-", subj)

    def test_21_filter_female_placebo_subjects(self):
        ans = self.agent.answer("Show female placebo subjects.")
        self.assertIsInstance(ans.answer, list)
        self.assertGreater(len(ans.answer), 0)

    def test_22_filter_alt_above_3x_uln(self):
        phrasings = [
            "Which subjects had ALT above 3x ULN?",
            "List subjects with ALT over 3 times ULN",
            "Who had ALT >= 3x ULN?",
        ]
        for q in phrasings:
            ans = self.agent.answer(q)
            self.assertIn("042-S07-001", ans.answer)
            self.assertTrue(any(ev.usubjid == "042-S07-001" and ev.seq == 25 for ev in ans.evidence))

    def test_23_filter_creatinine_above_threshold(self):
        ans = self.agent.answer("Who had creatinine > 1.5?")
        self.assertIsInstance(ans.answer, list)
        self.assertGreaterEqual(len(ans.answer), 4)

    def test_24_filter_sulfonylurea_subjects(self):
        ans = self.agent.answer("Which subjects received sulfonylureas?")
        self.assertIsInstance(ans.answer, list)
        self.assertGreater(len(ans.answer), 0)
        self.assertTrue(any(ev.domain == "CM" for ev in ans.evidence))

    # =========================================================================
    # 6. COMPARISON QUERIES
    # =========================================================================
    def test_25_compare_visits_for_subject(self):
        phrasings = [
            "Compare ALT at baseline and Week 8 for 042-S07-001.",
            "Difference between baseline and Week 8 ALT for 042-S07-001?",
            "Did ALT increase between baseline and Week 8 for 042-S07-001?",
        ]
        for q in phrasings:
            ans = self.agent.answer(q)
            self.assertIn("increased", ans.text.lower())
            self.assertEqual(len(ans.evidence), 2)
            self.assertTrue(any(ev.seq == 25 for ev in ans.evidence))

    def test_26_compare_creatinine(self):
        ans = self.agent.answer("Compare creatinine at screening and Week 4 for 042-S07-001.")
        self.assertEqual(len(ans.evidence), 2)
        self.assertIn("structured_data", ans.to_dict())

    # =========================================================================
    # 7. TREND QUERIES
    # =========================================================================
    def test_27_trend_alt(self):
        phrasings = [
            "Show ALT trend over time for 042-S07-001.",
            "How did ALT change over visits for 042-S07-001?",
            "ALT progression for 042-S07-001",
        ]
        for q in phrasings:
            ans = self.agent.answer(q)
            self.assertIsInstance(ans.answer, list)
            self.assertEqual(len(ans.answer), 10)
            self.assertIn("3.995", ans.text)
            self.assertEqual(len(ans.evidence), 10)
            self.assertEqual(ans.structured_data["type"], "trend")

    def test_28_trend_glucose(self):
        ans = self.agent.answer("Show glucose trend for 042-S07-001.")
        self.assertIsInstance(ans.answer, list)
        self.assertGreaterEqual(len(ans.answer), 3)

    # =========================================================================
    # 8. AGGREGATION QUERIES
    # =========================================================================
    def test_29_average_lab_at_site(self):
        ans = self.agent.answer("What is the average ALT at site S07?")
        self.assertIsInstance(ans.answer, float)
        self.assertGreater(ans.answer, 0.0)
        self.assertIn("average", ans.text.lower())

    def test_30_maximum_lab_for_subject(self):
        ans = self.agent.answer("What was the maximum ALT value for subject 042-S07-001?")
        self.assertAlmostEqual(ans.answer, 3.995, places=2)
        self.assertIn("3.995", ans.text)

    def test_31_minimum_lab_value(self):
        ans = self.agent.answer("What was the minimum ALT for 042-S07-001?")
        self.assertIsInstance(ans.answer, float)
        self.assertLess(ans.answer, 1.0)

    # =========================================================================
    # 9. PATIENT 360 QUERIES
    # =========================================================================
    def test_32_patient_360_phrasings(self):
        phrasings = [
            "Summarize subject 042-S07-001.",
            "Tell me about subject 042-S07-001.",
            "Patient 360 for 042-S07-001",
            "Give patient profile for 042-S07-001",
        ]
        for q in phrasings:
            ans = self.agent.answer(q)
            self.assertIn("042-S07-001", ans.text)
            self.assertIn("Demographics", ans.text)
            self.assertIn("Potential Hy's Law", ans.text)
            self.assertTrue(len(ans.evidence) > 0)
            self.assertEqual(ans.structured_data["type"], "patient_summary")

    # =========================================================================
    # 10. FINDING QUERIES (ALL 5 TYPES)
    # =========================================================================
    def test_33_hys_law_findings(self):
        ans = self.agent.answer("Who meets potential Hy's Law criteria?")
        self.assertEqual(len(ans.answer), 3)
        self.assertIn("042-S07-001", ans.answer)
        self.assertIn("042-S05-003", ans.answer)
        self.assertIn("042-S08-014", ans.answer)
        self.assertIn("adjudication", ans.text.lower())

    def test_34_serious_adverse_events(self):
        ans = self.agent.answer("Which subjects had serious adverse events?")
        self.assertEqual(len(ans.answer), 5)

    def test_35_creatinine_exclusions(self):
        ans = self.agent.answer("Who violated creatinine exclusion criteria?")
        self.assertEqual(len(ans.answer), 4)

    def test_36_prohibited_medications(self):
        ans = self.agent.answer("Which subjects took prohibited concomitant medications?")
        self.assertEqual(len(ans.answer), 14)

    def test_37_visit_deviations(self):
        ans = self.agent.answer("How many subjects had visit window deviations?")
        self.assertIsInstance(ans.answer, int)
        self.assertGreater(ans.answer, 50)

    # =========================================================================
    # 11. PROTOCOL & DOCUMENT QA
    # =========================================================================
    def test_38_visit_window_protocol_v1(self):
        ans = self.agent.answer("What was the visit window in protocol v1?")
        self.assertIn("7 days", ans.text)
        self.assertTrue(any(ev.domain == "DOC" and "protocol_v1.md" in ev.document for ev in ans.evidence))

    def test_39_visit_window_protocol_v3(self):
        ans = self.agent.answer("What is the visit window in protocol v3?")
        self.assertIn("3 days", ans.text)
        self.assertTrue(any(ev.domain == "DOC" and "protocol_v3.md" in ev.document for ev in ans.evidence))

    def test_40_creatinine_exclusion_amendment(self):
        ans = self.agent.answer("When was creatinine exclusion added to the protocol?")
        self.assertIn("Amendment 2", ans.text)
        self.assertTrue(any(ev.domain == "DOC" for ev in ans.evidence))

    def test_41_prohibited_medications_protocol_v3(self):
        ans = self.agent.answer("What medications are prohibited in protocol v3?")
        self.assertIn("Sulfonylurea", ans.text)
        self.assertIn("Glucocorticoid", ans.text)

    def test_42_protocol_differences_v1_v2(self):
        ans = self.agent.answer("What changed between protocol v1 and v2?")
        self.assertIn("±3", ans.text)
        self.assertIn("Creatinine", ans.text)

    def test_43_sap_primary_endpoint(self):
        ans = self.agent.answer("What is the primary endpoint in the SAP?")
        self.assertIn("HbA1c", ans.text)
        self.assertIn("MMRM", ans.text)

    def test_44_lab_manual_units_s07(self):
        ans = self.agent.answer("What does the lab manual say about site S07?")
        self.assertIn("µkat/L", ans.text)
        self.assertIn("60 U/L", ans.text)

    # =========================================================================
    # 12. STUDY METADATA QUERIES
    # =========================================================================
    def test_45_study_metadata_cut(self):
        ans = self.agent.answer("What cut are we viewing?")
        self.assertEqual(ans.answer["current_cut"], 12)
        self.assertIn("Cut 12", ans.text)

    def test_46_study_metadata_protocol_version(self):
        ans = self.agent.answer("What protocol version is active?")
        self.assertEqual(ans.answer["protocol_version"], 3)
        self.assertIn("Version 3", ans.text)

    def test_47_study_metadata_sites(self):
        ans = self.agent.answer("How many sites are in the study?")
        self.assertGreaterEqual(ans.answer["subjects"], 241)
        self.assertIn("S07", ans.text)

    # =========================================================================
    # 13. ZERO-RESULT & EDGE CASE QUERIES
    # =========================================================================
    def test_48_zero_result_trap_question(self):
        # Should NOT output fake trap answers; should execute genuinely and return empty
        ans = self.agent.answer("Which subjects had wrong dose at site S01?")
        self.assertEqual(ans.answer, [])
        self.assertEqual(ans.evidence, [])
        self.assertIn("No records matched", ans.text)

    def test_49_invalid_nonexistent_site(self):
        ans = self.agent.answer("How many subjects are at site S99?")
        self.assertEqual(ans.answer, [])
        self.assertEqual(ans.evidence, [])
        self.assertIn("No Site S99 exists", ans.text)

    def test_50_ambiguous_question_handling(self):
        ans = self.agent.answer("What was the value?")
        self.assertEqual(ans.intent, "AMBIGUOUS")
        self.assertIn("specify", ans.text.lower())
        self.assertEqual(ans.evidence, [])

    def test_51_ambiguous_liver_test(self):
        ans = self.agent.answer("Show the liver test.")
        self.assertEqual(ans.intent, "AMBIGUOUS")
        self.assertIn("ALT, AST, or Total Bilirubin", ans.text)

    def test_52_unsupported_question(self):
        ans = self.agent.answer("What is the capital of France?")
        self.assertEqual(ans.intent, "UNSUPPORTED")
        self.assertIn("Atlas is scoped to Study Sentinel", ans.text)
        self.assertEqual(ans.evidence, [])

    def test_53_unsupported_medical_advice(self):
        ans = self.agent.answer("What medication should this patient be prescribed?")
        self.assertEqual(ans.intent, "UNSUPPORTED")
        self.assertIn("does not support that determination", ans.text)

    # =========================================================================
    # 14. CONVERSATIONAL FOLLOW-UP QUERIES
    # =========================================================================
    def test_54_conversational_follow_up(self):
        # Turn 1: Specific query
        ans1 = self.agent.answer("What was ALT for 042-S07-001 at Week 8?")
        self.assertIn("3.995", ans1.text)

        # Turn 2: Follow-up changing only visit
        ans2 = self.agent.answer("What about baseline?")
        self.assertIn("0.283", ans2.text)
        self.assertTrue(any(ev.usubjid == "042-S07-001" for ev in ans2.evidence))

        # Turn 3: Follow-up asking for adverse events for the same patient
        ans3 = self.agent.answer("Show me their adverse events.")
        self.assertGreaterEqual(len(ans3.answer), 1)
        self.assertTrue(all(ev.usubjid == "042-S07-001" for ev in ans3.evidence))

    # =========================================================================
    # 15. PERFORMANCE VERIFICATION
    # =========================================================================
    def test_55_performance_under_one_second(self):
        t0 = time.perf_counter()
        for q in [
            "How many subjects are at site S07?",
            "What was ALT for 042-S07-001 at Week 8?",
            "Who meets potential Hy's Law criteria?",
            "Show ALT trend over time for 042-S07-001."
        ]:
            ans = self.agent.answer(q)
            self.assertIsNotNone(ans.text)
        elapsed = time.perf_counter() - t0
        # 4 queries should easily complete in under 500 ms combined
        self.assertLess(elapsed, 1.0, f"Queries took {elapsed:.2f} seconds, target < 1.0s")

    # =========================================================================
    # 16. FUZZ & PARAPHRASE TESTING
    # =========================================================================
    def test_56_fuzz_paraphrase_templates(self):
        verbs = ["Show", "List", "Give me", "What are", "Which"]
        targets = [
            ("subjects at site S07", 20),
            ("patients with ALT above 3x ULN", 1),
            ("adverse events for 042-S01-007", None),
        ]
        for verb in verbs:
            for phrase, expected_count in targets:
                q = f"{verb} {phrase}"
                ans = self.agent.answer(q)
                self.assertIsNotNone(ans.text)
                for ev in ans.evidence:
                    if ev.domain != "DOC":
                        self.assertTrue(self.graph.has_record(ev.domain, ev.usubjid, ev.seq), f"Hallucinated ref: {ev}")
                if expected_count is not None and isinstance(ans.answer, list):
                    self.assertGreaterEqual(len(ans.answer), expected_count)

    # =========================================================================
    # 17. CUT-AWARE PROGRESSION TEST
    # =========================================================================
    def test_57_cut_aware_progression(self):
        try:
            # Cut 1: 0 Hy's law findings
            self.service.load(cut=1)
            ans_c1 = self.service.ask("Who meets potential Hy's Law criteria?")
            self.assertEqual(len(ans_c1["answer"]), 0)

            # Cut 5: 1 Hy's law finding
            self.service.load(cut=5)
            ans_c5 = self.service.ask("Who meets potential Hy's Law criteria?")
            self.assertEqual(len(ans_c5["answer"]), 1)
            self.assertIn("042-S07-001", ans_c5["answer"])

            # Cut 6: 2 Hy's law findings
            self.service.load(cut=6)
            ans_c6 = self.service.ask("Who meets potential Hy's Law criteria?")
            self.assertEqual(len(ans_c6["answer"]), 2)

            # Cut 9: 3 Hy's law findings
            self.service.load(cut=9)
            ans_c9 = self.service.ask("Who meets potential Hy's Law criteria?")
            self.assertEqual(len(ans_c9["answer"]), 3)

            # Cut 12: 3 Hy's law findings
            self.service.load(cut=12)
            ans_c12 = self.service.ask("Who meets potential Hy's Law criteria?")
            self.assertEqual(len(ans_c12["answer"]), 3)
        finally:
            self.service.load(cut=12)


if __name__ == "__main__":
    unittest.main()
