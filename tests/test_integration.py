"""Integration Test Suite for StudyService, Agent Chatbot, and Multi-Page Backend.

Validates:
1. service loads Cut 12
2. dashboard output equals graph.dashboard_summary()
3. Study Graph service returns valid nodes/edges
4. Evidence service retrieves a real existing finding
5. evidence refs exist in current graph
6. chatbot answers Hy's Law question through StudyGraph
7. chatbot lookup question uses graph.lookup()
8. no-result question returns empty result rather than invented evidence
9. cut change consistency (Cut 1 vs Cut 12) across dashboard, chatbot, and evidence
10. graph rebuild does not require recreating chatbot/service objects
11. everything returned is directly JSON serializable
12. existing StudyGraph unit tests still pass
"""

import json
import unittest
from backend.study_service import StudyService
from backend.schemas import Question, Answer, RecordRef


class TestStudyServiceIntegration(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.service = StudyService()

    def test_01_service_loads_cut_12(self):
        stats = self.service.load(cut=12)
        self.assertEqual(stats["cut"], 12)
        self.assertEqual(stats["protocol_version"], 3)
        self.assertEqual(stats["subjects"], 241)
        self.assertEqual(stats["records"], 26482)

    def test_02_dashboard_output_matches_study_graph(self):
        dash = self.service.get_dashboard()
        direct_dash = self.service.graph.dashboard_summary()

        self.assertEqual(dash["cut"], direct_dash["cut"])
        self.assertEqual(dash["total_findings"], direct_dash["total_findings"])
        self.assertEqual(dash["potential_hys_law_count"], direct_dash["potential_hys_law_count"])
        self.assertEqual(dash["serious_ae_count"], direct_dash["serious_ae_count"])
        self.assertEqual(dash["creatinine_exclusion_count"], direct_dash["creatinine_exclusion_count"])
        self.assertEqual(dash["prohibited_medication_count"], direct_dash["prohibited_medication_count"])
        self.assertEqual(dash["visit_deviation_count"], direct_dash["visit_deviation_count"])

        # JSON serializable
        self.assertIsInstance(json.dumps(dash), str)

    def test_03_study_graph_service_nodes_and_edges(self):
        gview = self.service.get_subject_graph("042-S07-001")
        nodes = gview["nodes"]
        edges = gview["edges"]

        self.assertGreater(len(nodes), 0)
        self.assertGreater(len(edges), 0)

        node_ids = set(n["id"] for n in nodes)
        for e in edges:
            self.assertIn(e["source"], node_ids)
            self.assertIn(e["target"], node_ids)

        # Timeline test
        tl = self.service.get_subject_timeline("042-S07-001")
        self.assertGreater(len(tl), 0)
        self.assertIsInstance(json.dumps(tl), str)

    def test_04_evidence_service_retrieves_real_finding(self):
        findings = self.service.get_findings()
        self.assertGreater(len(findings), 0)

        hys_findings = [f for f in findings if f["finding_type"] == "potential_hys_law"]
        self.assertEqual(len(hys_findings), 3)

        first_fid = hys_findings[0]["finding_id"]
        found = self.service.get_finding(first_fid)
        self.assertIsNotNone(found)
        self.assertEqual(found["finding_id"], first_fid)

        ev_details = self.service.get_evidence(first_fid)
        self.assertGreater(len(ev_details), 0)
        self.assertIn("reference", ev_details[0])
        self.assertIn("details", ev_details[0])

    def test_05_evidence_refs_exist_in_current_graph(self):
        val = self.service.graph.validate_evidence(self.service.get_findings())
        self.assertTrue(val["valid"], f"Validation failed: {val['errors']}")
        self.assertEqual(val["invalid_count"], 0)

    def test_06_chatbot_answers_hys_law_through_study_graph(self):
        ans = self.service.ask("Which subjects meet the Hy's law criteria?")
        self.assertIsInstance(ans, dict)
        self.assertIn("answer", ans)
        self.assertIn("evidence", ans)

        # Answer must contain the 3 Hy's law candidates derived by StudyGraph
        cands = ans["answer"]
        self.assertEqual(sorted(cands), ["042-S05-003", "042-S07-001", "042-S08-014"])
        self.assertEqual(len(ans["evidence"]), 6)

        # Confirm evidence originates in graph
        for ev in ans["evidence"]:
            key = (ev["domain"], ev["usubjid"], ev["seq"])
            self.assertIn(key, self.service.graph.records_by_key)

    def test_07_chatbot_lookup_uses_graph_lookup(self):
        ans = self.service.ask("List laboratory records for 042-S07-001 within 7 days of the WEEK8 visit")
        self.assertIsInstance(ans["answer"], list)
        self.assertGreater(len(ans["answer"]), 0)
        self.assertGreater(len(ans["evidence"]), 0)

        # Check evidence references exist
        for ev in ans["evidence"]:
            self.assertEqual(ev["usubjid"], "042-S07-001")
            self.assertIn((ev["domain"], ev["usubjid"], ev["seq"]), self.service.graph.records_by_key)

    def test_08_no_result_question_returns_empty_result(self):
        ans = self.service.ask("Which subjects at site S01 received a wrong dose?")
        self.assertEqual(ans["answer"], [])
        self.assertEqual(ans["evidence"], [])
        self.assertIn("No dosing errors", ans["text"])

    def test_09_cut_change_consistency_across_dashboard_chatbot_evidence(self):
        # 1. Switch to Cut 1
        self.service.load(cut=1)
        self.assertEqual(self.service.graph.current_cut, 1)

        # Dashboard reflects Cut 1
        dash1 = self.service.get_dashboard()
        self.assertEqual(dash1["cut"], 1)
        self.assertEqual(dash1["potential_hys_law_count"], 0)
        self.assertEqual(dash1["creatinine_exclusion_count"], 0)

        # Chatbot reflects Cut 1
        ans1 = self.service.ask("Which subjects meet the Hy's law criteria?")
        self.assertEqual(ans1["answer"], [])
        self.assertEqual(ans1["evidence"], [])

        # Evidence reflects Cut 1
        findings1 = self.service.get_findings()
        self.assertEqual(len([f for f in findings1 if f["finding_type"] == "potential_hys_law"]), 0)

        # 2. Switch back to Cut 12
        self.service.load(cut=12)
        dash12 = self.service.get_dashboard()
        self.assertEqual(dash12["cut"], 12)
        self.assertEqual(dash12["potential_hys_law_count"], 3)

        ans12 = self.service.ask("Which subjects meet the Hy's law criteria?")
        self.assertEqual(len(ans12["answer"]), 3)
        self.assertEqual(len(ans12["evidence"]), 6)

    def test_10_graph_rebuild_without_recreating_service(self):
        # Rebuilding the graph inside the service updates internal state in-place
        self.service.load(cut=5)
        self.assertEqual(self.service.graph.current_cut, 5)
        self.assertEqual(self.service.get_dashboard()["potential_hys_law_count"], 1)

        self.service.load(cut=12)
        self.assertEqual(self.service.graph.current_cut, 12)
        self.assertEqual(self.service.get_dashboard()["potential_hys_law_count"], 3)

    def test_11_all_page_outputs_json_serializable(self):
        # Page 1: Dashboard
        dash_json = json.dumps(self.service.get_dashboard())
        self.assertIsInstance(dash_json, str)

        # Page 2: Study Graph & Timeline
        g_json = json.dumps(self.service.get_subject_graph("042-S07-001"))
        self.assertIsInstance(g_json, str)
        tl_json = json.dumps(self.service.get_subject_timeline("042-S07-001"))
        self.assertIsInstance(tl_json, str)

        # Page 3: Chatbot
        ans_json = json.dumps(self.service.ask("Which subjects meet the Hy's law criteria?"))
        self.assertIsInstance(ans_json, str)

        # Page 4: Evidence
        f_json = json.dumps(self.service.get_findings())
        self.assertIsInstance(f_json, str)
        ev_json = json.dumps(self.service.get_evidence("POT_HYS_042-S07-001_25_27"))
        self.assertIsInstance(ev_json, str)

    def test_12_freeze_authoritative_baseline(self):
        """Regression test freezing authoritative pre-integration StudyGraph truth."""
        from stage1.atlas import StudyGraph

        direct_graph = StudyGraph(data_dir="hackathon-data")

        # 1. Verify exact cut progression and identity between direct graph and service
        expected_progression = {
            1: {"subjects": 219, "records": 4509, "findings": 3, "hys": 0, "hys_cands": []},
            5: {"subjects": 220, "records": 12216, "findings": 98, "hys": 1, "hys_cands": ["042-S07-001"]},
            9: {"subjects": 241, "records": 20897, "findings": 215, "hys": 3, "hys_cands": ["042-S05-003", "042-S07-001", "042-S08-014"]},
            12: {"subjects": 241, "records": 26482, "findings": 280, "hys": 3, "hys_cands": ["042-S05-003", "042-S07-001", "042-S08-014"]},
        }

        for cut, exp in expected_progression.items():
            direct_graph.build(cut=cut)
            self.service.load(cut=cut)

            dash_direct = direct_graph.dashboard_summary()
            dash_service = self.service.get_dashboard()

            # Verify identical outputs
            for field in [
                "cut", "protocol_version", "subjects", "sites", "total_records",
                "total_findings", "potential_hys_law_count", "serious_ae_count",
                "creatinine_exclusion_count", "prohibited_medication_count", "visit_deviation_count"
            ]:
                self.assertEqual(dash_direct[field], dash_service[field], f"Mismatch at cut {cut} for field {field}")
                if field in exp:
                    self.assertEqual(dash_service[field], exp[field], f"Baseline mismatch at cut {cut} for field {field}")

            # Verify Hy's law subjects
            hys_direct = sorted([c["usubjid"] for c in direct_graph.find_hys_law_candidates()])
            hys_service = sorted([c["usubjid"] for c in self.service.graph.find_hys_law_candidates()])
            self.assertEqual(hys_direct, hys_service)
            self.assertEqual(hys_service, exp["hys_cands"])

        # 2. Detailed Cut 12 Authoritative Baseline Verification
        self.service.load(cut=12)
        dash12 = self.service.get_dashboard()
        self.assertEqual(dash12["subjects"], 241)
        self.assertEqual(dash12["total_records"], 26482)
        self.assertEqual(dash12["potential_hys_law_count"], 3)
        self.assertEqual(dash12["serious_ae_count"], 5)
        self.assertEqual(dash12["creatinine_exclusion_count"], 4)
        self.assertEqual(dash12["prohibited_medication_count"], 14)
        self.assertEqual(dash12["visit_deviation_count"], 254)
        self.assertEqual(dash12["total_findings"], 280)

        # 3. Representative Candidate 042-S07-001 Evidence Trace
        s07_finding = self.service.get_finding("POT_HYS_042-S07-001_25_27")
        self.assertIsNotNone(s07_finding)
        self.assertEqual(s07_finding["status"], "UNCONFIRMED_ADJUDICATION_REQUIRED")
        self.assertTrue(s07_finding["details"]["biochemical_criteria_met"])
        self.assertFalse(s07_finding["details"]["cholestasis_evaluated"])
        self.assertTrue(s07_finding["details"]["requires_adjudication"])

        s07_evidence = self.service.get_evidence("POT_HYS_042-S07-001_25_27")
        self.assertEqual(len(s07_evidence), 2)

        # Check ALT: LBSEQ 25, 3.995 ukat/L, ULN 0.93, ratio ~4.2957
        alt_rec = [e for e in s07_evidence if e["details"]["test"] == "ALT"][0]
        self.assertEqual(alt_rec["reference"]["seq"], 25)
        self.assertEqual(alt_rec["details"]["raw_value"], "3.995")
        self.assertEqual(alt_rec["details"]["unit"], "ukat/L")
        self.assertEqual(alt_rec["details"]["uln"], 0.93)
        self.assertAlmostEqual(alt_rec["details"]["ratio_to_uln"], 4.2957, places=3)

        # Check BILI: LBSEQ 27, 5.38 mg/dL, ULN 1.2, ratio ~4.4833
        bili_rec = [e for e in s07_evidence if e["details"]["test"] == "BILI"][0]
        self.assertEqual(bili_rec["reference"]["seq"], 27)
        self.assertEqual(bili_rec["details"]["raw_value"], "5.38")
        self.assertEqual(bili_rec["details"]["unit"], "mg/dL")
        self.assertEqual(bili_rec["details"]["uln"], 1.2)
        self.assertAlmostEqual(bili_rec["details"]["ratio_to_uln"], 4.4833, places=3)

        # 4. Evidence Validation 100%
        val = self.service.graph.validate_evidence(self.service.get_findings())
        self.assertTrue(val["valid"])
        self.assertEqual(val["invalid_count"], 0)


if __name__ == "__main__":
    unittest.main()
