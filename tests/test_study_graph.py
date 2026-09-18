"""Unit and integration test suite for StudyGraph Milestone 4.

Covers:
- General lookup API (by subject, domain, visit, testcd, field_filters)
- Cut awareness & non-leakage
- Subject chronological timeline
- Finding and rich evidence retrieval
- Dashboard summary consistency
- Graph view structure, finding nodes, and referential integrity
- Full rebuild idempotency (Cut 12 -> Cut 1)
"""

import datetime
import json
import unittest
from stage1.atlas import StudyGraph


class TestStudyGraphMilestone4(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.graph = StudyGraph(data_dir="hackathon-data")

    # -------------------------------------------------------------------------
    # 1. Lookup API Tests
    # -------------------------------------------------------------------------
    def test_01_lookup_by_subject_and_domain(self):
        self.graph.build(cut=12)
        recs = self.graph.lookup(domain="LB", usubjid="042-S07-001")
        self.assertGreater(len(recs), 0)
        for r in recs:
            self.assertEqual(r["_domain"], "LB")
            self.assertEqual(r["_usubjid"], "042-S07-001")
            self.assertIn("LBTESTCD", r)
            self.assertIn("LBORRES", r)
            # Ensure JSON-safe
            self.assertNotIn("_LBDTC_parsed", r)

    def test_02_lookup_by_visit_and_testcd(self):
        self.graph.build(cut=12)
        alt_w8 = self.graph.lookup(domain="LB", usubjid="042-S07-001", visit="WEEK8", testcd="ALT")
        self.assertEqual(len(alt_w8), 1)
        rec = alt_w8[0]
        self.assertEqual(rec["LBTESTCD"], "ALT")
        self.assertEqual(rec["VISIT"], "WEEK8")
        self.assertEqual(rec["_seq"], 25)
        self.assertEqual(rec["LBORRES"], "3.995")
        self.assertEqual(rec["LBORRESU"], "ukat/L")

    def test_03_lookup_by_field_filters(self):
        self.graph.build(cut=12)
        sulf = self.graph.lookup(domain="CM", field_filters={"CMCLAS": "SULFONYLUREA"})
        self.assertEqual(len(sulf), 6)
        for s in sulf:
            self.assertEqual(s["CMCLAS"], "SULFONYLUREA")

    def test_04_lookup_respects_cut_boundaries(self):
        # Cut 4: S07 WEEK8 lab records (available at cut 5) must not be returned
        self.graph.build(cut=4)
        recs_cut4 = self.graph.lookup(domain="LB", usubjid="042-S07-001", visit="WEEK8")
        self.assertEqual(len(recs_cut4), 0)

        # Cut 5: records become available
        self.graph.build(cut=5)
        recs_cut5 = self.graph.lookup(domain="LB", usubjid="042-S07-001", visit="WEEK8")
        self.assertGreater(len(recs_cut5), 0)

    def test_05_lookup_no_match_returns_empty_list(self):
        self.graph.build(cut=12)
        none_recs = self.graph.lookup(domain="LB", usubjid="NON_EXISTENT_ID")
        self.assertEqual(none_recs, [])

        none_test = self.graph.lookup(domain="LB", testcd="NON_EXISTENT_TEST")
        self.assertEqual(none_test, [])

    # -------------------------------------------------------------------------
    # 2. Timeline API Tests
    # -------------------------------------------------------------------------
    def test_06_timeline_chronological_ordering_and_structure(self):
        self.graph.build(cut=12)
        tl = self.graph.timeline("042-S07-001")
        self.assertGreater(len(tl), 0)

        prev_date = None
        for item in tl:
            self.assertIn("date", item)
            self.assertIn("domain", item)
            self.assertIn("label", item)
            self.assertIn("details", item)
            d_str = item["date"]
            if d_str is not None:
                curr_date = datetime.date.fromisoformat(d_str)
                if prev_date is not None:
                    self.assertGreaterEqual(curr_date, prev_date)
                prev_date = curr_date

        # Ensure 100% JSON serializable
        json_str = json.dumps(tl)
        self.assertIsInstance(json_str, str)

    def test_07_timeline_cut_awareness_no_leakage(self):
        self.graph.build(cut=4)
        tl_cut4 = self.graph.timeline("042-S07-001")
        dates_cut4 = [i["date"] for i in tl_cut4 if i["date"]]

        # 2026-03-30 (WEEK8) appeared in Cut 5
        self.assertNotIn("2026-03-30", dates_cut4)

        self.graph.build(cut=5)
        tl_cut5 = self.graph.timeline("042-S07-001")
        dates_cut5 = [i["date"] for i in tl_cut5 if i["date"]]
        self.assertIn("2026-03-30", dates_cut5)

    # -------------------------------------------------------------------------
    # 3. Finding and Rich Evidence Detail API Tests
    # -------------------------------------------------------------------------
    def test_08_get_finding_valid_and_unknown(self):
        self.graph.build(cut=12)
        findings = self.graph.get_findings()
        self.assertGreater(len(findings), 0)

        first_fid = findings[0]["finding_id"]
        f = self.graph.get_finding(first_fid)
        self.assertIsNotNone(f)
        self.assertEqual(f["finding_id"], first_fid)

        # Unknown ID
        self.assertIsNone(self.graph.get_finding("UNKNOWN_FINDING_ID"))

    def test_09_get_evidence_returns_rich_supporting_data(self):
        self.graph.build(cut=12)
        hys = self.graph.find_hys_law_candidates()
        self.assertEqual(len(hys), 3)

        cand_s07 = [c for c in hys if c["usubjid"] == "042-S07-001"][0]
        ev_details = self.graph.get_evidence(cand_s07["finding_id"])
        self.assertEqual(len(ev_details), 2)

        # Transaminase evidence item
        alt_ev = [e for e in ev_details if e["details"].get("test") == "ALT"][0]
        self.assertEqual(alt_ev["reference"]["domain"], "LB")
        self.assertEqual(alt_ev["reference"]["usubjid"], "042-S07-001")
        self.assertEqual(alt_ev["reference"]["seq"], 25)
        self.assertEqual(alt_ev["details"]["raw_value"], "3.995")
        self.assertEqual(alt_ev["details"]["unit"], "ukat/L")
        self.assertEqual(alt_ev["details"]["uln"], 0.93)
        self.assertAlmostEqual(alt_ev["details"]["ratio_to_uln"], 4.2957, places=3)
        self.assertEqual(alt_ev["details"]["visit"], "WEEK8")
        self.assertEqual(alt_ev["details"]["date"], "2026-03-30")

    # -------------------------------------------------------------------------
    # 4. Dashboard Summary Consistency
    # -------------------------------------------------------------------------
    def test_10_dashboard_summary_matches_underlying_data(self):
        self.graph.build(cut=12)
        dash = self.graph.dashboard_summary()

        self.assertEqual(dash["cut"], 12)
        self.assertEqual(dash["protocol_version"], 3)
        self.assertEqual(dash["subjects"], 241)
        self.assertEqual(dash["sites"], 12)
        self.assertEqual(dash["potential_hys_law_count"], 3)
        self.assertEqual(dash["serious_ae_count"], 5)
        self.assertEqual(dash["creatinine_exclusion_count"], 4)
        self.assertEqual(dash["prohibited_medication_count"], 14)
        self.assertEqual(dash["visit_deviation_count"], 254)
        self.assertEqual(dash["total_findings"], 280)

        # JSON safe
        json_dash = json.dumps(dash)
        self.assertIsInstance(json_dash, str)

    # -------------------------------------------------------------------------
    # 5. Graph View, Finding Nodes, and Edge Referential Integrity
    # -------------------------------------------------------------------------
    def test_11_graph_view_finding_nodes_and_evidence_edges(self):
        self.graph.build(cut=12)
        gview = self.graph.graph_view("042-S07-001")

        nodes = gview["nodes"]
        edges = gview["edges"]
        node_ids = set(n["id"] for n in nodes)

        # 1. Check finding node exists
        finding_nodes = [n for n in nodes if n["type"] == "FINDING"]
        self.assertGreater(len(finding_nodes), 0)

        # 2. Check edges: HAS_FINDING and SUPPORTED_BY
        has_finding_edges = [e for e in edges if e["relationship"] == "HAS_FINDING"]
        supported_by_edges = [e for e in edges if e["relationship"] == "SUPPORTED_BY"]

        self.assertGreater(len(has_finding_edges), 0)
        self.assertGreater(len(supported_by_edges), 0)

        # 3. Referential integrity: Every source and target must exist in node_ids
        for e in edges:
            self.assertIn(e["source"], node_ids, f"Edge source {e['source']} not in node_ids")
            self.assertIn(e["target"], node_ids, f"Edge target {e['target']} not in node_ids")

        # 4. JSON safe
        json_gview = json.dumps(gview)
        self.assertIsInstance(json_gview, str)

    # -------------------------------------------------------------------------
    # 6. Rebuild Idempotency (Cut 12 -> Cut 1 -> Cut 12)
    # -------------------------------------------------------------------------
    def test_12_rebuild_clears_indexes_and_findings(self):
        # Build Cut 12
        self.graph.build(cut=12)
        self.assertEqual(len(self.graph.findings), 280)
        self.assertEqual(self.graph.dashboard_summary()["total_findings"], 280)

        # Rebuild Cut 1
        self.graph.build(cut=1)
        self.assertEqual(self.graph.current_cut, 1)
        self.assertEqual(self.graph.current_protocol_version, 1)
        self.assertEqual(len(self.graph.find_hys_law_candidates()), 0)
        self.assertEqual(len(self.graph.find_exclusion_violations()), 0)
        dash1 = self.graph.dashboard_summary()
        self.assertEqual(dash1["potential_hys_law_count"], 0)
        self.assertEqual(dash1["creatinine_exclusion_count"], 0)

        # Rebuild Cut 12 again
        self.graph.build(cut=12)
        self.assertEqual(self.graph.dashboard_summary()["total_findings"], 280)
        self.assertEqual(len(self.graph.findings), 280)


if __name__ == "__main__":
    unittest.main()
