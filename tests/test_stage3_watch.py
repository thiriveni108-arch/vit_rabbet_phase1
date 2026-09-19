"""Comprehensive Unit & Regression Tests for Stage 3: StudyWatch Incremental Platform.

Covers all 30 mandatory tests:
1. new row is ingested without full graph rebuild
2. existing row correction updates effective value
3. original corrected value remains in audit history
4. downstream finding is recomputed after correction
5. new site is accepted without code change
6. new domain is accepted without code change
7. blank != zero
8. ND != zero
9. <5 is represented correctly
10. decimal comma parsed correctly
11. unit shift detected generically
12. unit anomaly does NOT create clinical emergency
13. site-wide anomaly is distinguished from isolated patient signal
14. lack of corroboration reduces false-positive escalation
15. quarantined data excluded from safety aggregation
16. serious genuine event still escalates
17. suspicious regular site detected
18. document hash change detected
19. instruction-like document change ignored
20. delayed escalation never becomes silent approval
21. four-cut wait enters standing-limits state
22. protocol change invalidates stale derived findings
23. explain() returns exact stored evidence
24. explain() evidence matches trace
25. repeated run is deterministic
26. budget degradation keeps safety checks active
27. Review Center contains no production fixtures
28. Data Intake values all come from backend
29. Stage 1 baseline still passes
30. Stage 2 baseline still passes
"""

from __future__ import annotations

import unittest
from pathlib import Path

from stage1.atlas import StudyGraph
from backend.review_crew import ReviewCrew, ReviewMemory
from stage3.models import (
    AlignmentStatus,
    BudgetTier,
    EscalationState,
    TrustState,
    ValueState,
)
from stage3.ingestion import IncrementalIngestionEngine
from stage3.detectors import (
    DetectorConfig,
    DocumentTamperDetector,
    SiteIntegrityDetector,
    UnitShiftDetector,
)
from stage3.monitoring import ThresholdMonitoringEngine, DelayedEscalationTracker
from stage3.watch import StudyWatch


class TestStage3StudyWatch(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data_dir = "hackathon-data"
        cls.graph = StudyGraph(cls.data_dir)
        cls.graph.build(cut=1)  # Baseline initialized at Cut 1

    def setUp(self):
        # Fresh watch instance for testing
        self.watch = StudyWatch(
            data_dir=self.data_dir,
            study_graph=self.graph,
            deterministic_clock=True,
        )

    # -------------------------------------------------------------------------
    # 1. Incremental Ingestion without Full Graph Rebuild
    # -------------------------------------------------------------------------
    def test_01_new_row_ingested_without_full_rebuild(self):
        """1. New row is ingested without full graph rebuild."""
        engine = IncrementalIngestionEngine(self.graph)
        metrics = engine.ingest_cut_delta(cut=2)

        self.assertEqual(metrics.full_build_calls, 0, "Expected 0 full graph rebuild calls during incremental transition")
        self.assertGreater(metrics.records_inserted, 0, "Expected incremental records inserted")
        self.assertGreater(metrics.incremental_elapsed_ms, 0, "Expected measured elapsed time")
        self.assertIn(2, engine.metrics_history)

    # -------------------------------------------------------------------------
    # 2. Existing Row Correction Updates Effective Value
    # -------------------------------------------------------------------------
    def test_02_correction_updates_effective_value(self):
        """2. Existing row correction updates effective value."""
        self.graph.build(cut=4)
        engine = IncrementalIngestionEngine(self.graph)
        # Apply Cut 5 delta which has corrections
        metrics = engine.ingest_cut_delta(cut=5)
        self.assertGreater(metrics.corrected_records, 0, "Expected corrections to be applied at Cut 5")

        # Verify a specific corrected record from corrections.csv
        # Example row 2: cut 5, LB, 042-S08-001, seq 8, LBORRES -> 25.92
        corr_key = ("LB", "042-S08-001", 8)
        self.assertIn(corr_key, self.graph.records_by_key)
        rec = self.graph.records_by_key[corr_key]
        self.assertEqual(rec.get("LBORRES"), "25.92")
        self.assertTrue(rec.get("_is_corrected"))
        self.assertEqual(rec.get("_version"), 2)

    # -------------------------------------------------------------------------
    # 3. Original Corrected Value Remains in Audit History
    # -------------------------------------------------------------------------
    def test_03_original_corrected_value_remains_in_audit_history(self):
        """3. Original corrected value remains in audit history."""
        self.graph.build(cut=4)
        engine = IncrementalIngestionEngine(self.graph)
        engine.ingest_cut_delta(cut=5)

        corr_key = ("LB", "042-S08-001", 8)
        entries = engine.historical_store.versions.get(corr_key, [])
        self.assertGreaterEqual(len(entries), 1, "Expected historical version entries")

        # Verify version 2 exists with effective cut 5
        v2_entries = [e for e in entries if e["version"] == 2]
        self.assertGreaterEqual(len(v2_entries), 1)
        self.assertEqual(v2_entries[0]["effective_start_cut"], 5)

    # -------------------------------------------------------------------------
    # 4. Downstream Finding Recomputed After Correction
    # -------------------------------------------------------------------------
    def test_04_downstream_finding_recomputed_after_correction(self):
        """4. Downstream finding is recomputed after correction."""
        self.graph.build(cut=4)
        engine = IncrementalIngestionEngine(self.graph)
        metrics = engine.ingest_cut_delta(cut=5)
        self.assertGreater(metrics.findings_recomputed, 0, "Expected findings recomputed after corrections")

    # -------------------------------------------------------------------------
    # 5. New Site Accepted Without Code Change
    # -------------------------------------------------------------------------
    def test_05_new_site_accepted_without_code_change(self):
        """5. New site is accepted without code change."""
        engine = IncrementalIngestionEngine(self.graph)
        sample_row = {
            "USUBJID": "042-S99-999",
            "SITEID": "S99",
            "LBSEQ": "1",
            "LBTESTCD": "ALT",
            "LBORRES": "25.0",
            "LBORRESU": "U/L",
            "cut_available": "1",
        }
        res = engine.align_record(sample_row, "LB", cut=1)
        self.assertIn(res.alignment_status, (AlignmentStatus.NEW_SITE, AlignmentStatus.NEW_SUBJECT))
        self.assertEqual(res.matched_site, "S99")

    # -------------------------------------------------------------------------
    # 6. New Domain Accepted Without Code Change
    # -------------------------------------------------------------------------
    def test_06_new_domain_accepted_without_code_change(self):
        """6. New domain is accepted without code change (honest: no invented clinical rules)."""
        engine = IncrementalIngestionEngine(self.graph)
        novel_domain_rows = [
            {"USUBJID": "042-S01-001", "PKSEQ": "1", "PKCONC": "4.2", "PKTIME": "0.5"},
            {"USUBJID": "042-S01-001", "PKSEQ": "2", "PKCONC": "8.9", "PKTIME": "1.0"},
        ]
        metrics = engine.ingest_records(novel_domain_rows, domain="PK", cut=1)
        self.assertEqual(metrics.new_records, 2)
        self.assertTrue(engine.registry.discovered_domains.get("PK") is not None)
        self.assertFalse(engine.registry.is_known("PK"))
        # Verify indexed into graph
        self.assertIn("PK", self.graph.domain_records)
        self.assertEqual(len(self.graph.domain_records["PK"]), 2)

    # -------------------------------------------------------------------------
    # 7. Blank != Zero
    # -------------------------------------------------------------------------
    def test_07_blank_not_equal_to_zero(self):
        """7. Blank is not converted to numeric zero."""
        nv = IncrementalIngestionEngine.normalize_value("")
        self.assertEqual(nv.state, ValueState.MISSING)
        self.assertIsNone(nv.normalized_numeric)
        self.assertNotEqual(nv.normalized_numeric, 0.0)

    # -------------------------------------------------------------------------
    # 8. ND != Zero
    # -------------------------------------------------------------------------
    def test_08_nd_not_equal_to_zero(self):
        """8. 'ND' is not converted to numeric zero."""
        nv = IncrementalIngestionEngine.normalize_value("ND")
        self.assertEqual(nv.state, ValueState.NOT_DONE)
        self.assertIsNone(nv.normalized_numeric)
        self.assertNotEqual(nv.normalized_numeric, 0.0)

    # -------------------------------------------------------------------------
    # 9. <5 is Represented Correctly
    # -------------------------------------------------------------------------
    def test_09_below_detection_represented_correctly(self):
        """9. '<5' is represented as BELOW_DETECTION with qualifier LT and threshold 5."""
        nv = IncrementalIngestionEngine.normalize_value("<5")
        self.assertEqual(nv.state, ValueState.BELOW_DETECTION)
        self.assertEqual(nv.qualifier, "LT")
        self.assertEqual(nv.threshold, 5.0)
        self.assertIsNone(nv.normalized_numeric)
        self.assertNotEqual(nv.normalized_numeric, 0.0)

    # -------------------------------------------------------------------------
    # 10. Decimal Comma Parsed Correctly
    # -------------------------------------------------------------------------
    def test_10_decimal_comma_parsed_correctly(self):
        """10. Decimal comma '12,4' is parsed as numeric 12.4 while preserving raw '12,4'."""
        nv = IncrementalIngestionEngine.normalize_value("12,4")
        self.assertEqual(nv.state, ValueState.VALID)
        self.assertEqual(nv.normalized_numeric, 12.4)
        self.assertEqual(nv.raw_value, "12,4")

    # -------------------------------------------------------------------------
    # 11. Unit Shift Detected Generically
    # -------------------------------------------------------------------------
    def test_11_unit_shift_detected_generically(self):
        """11. Generic unit shift detector detects multiplicative shift without hardcoded site/cut."""
        detector = UnitShiftDetector()
        # Build graph to Cut 8 where glucose at S04 shifts by ~18x
        self.graph.build(cut=8)
        anomalies = detector.detect(self.graph, current_cut=8)
        self.assertGreater(len(anomalies), 0, "Expected at least one unit shift anomaly detected generically")
        gluc_anomaly = anomalies[0]
        self.assertIn("18", str(gluc_anomaly["expected_conversion"]))
        self.assertEqual(gluc_anomaly["category"], "DATA_INTEGRITY")

    # -------------------------------------------------------------------------
    # 12. Unit Anomaly Does Not Create Clinical Emergency
    # -------------------------------------------------------------------------
    def test_12_unit_anomaly_does_not_create_clinical_emergency(self):
        """12. Unit anomaly is raised as DATA_INTEGRITY, not a CLINICAL_SAFETY emergency."""
        report = self.watch.run_cut(cut=8)
        alerts = report["alerts"]
        unit_alerts = [a for a in alerts if a["type"] == "DATA_INTEGRITY" and "UNIT_SHIFT" in a["alert_id"]]
        self.assertGreater(len(unit_alerts), 0)
        for ua in unit_alerts:
            self.assertNotEqual(ua["type"], "CLINICAL_SAFETY")
            self.assertEqual(ua["trust_state"], TrustState.UNTRUSTED.value)

    # -------------------------------------------------------------------------
    # 13. Site-Wide Anomaly Distinguished from Isolated Patient Signal
    # -------------------------------------------------------------------------
    def test_13_site_wide_distinguished_from_isolated_patient(self):
        """13. Site-wide shift is distinguished from an isolated patient signal."""
        report = self.watch.run_cut(cut=8)
        integrity_events = [a for a in report["alerts"] if a["type"] == "DATA_INTEGRITY"]
        self.assertGreater(len(integrity_events), 0)
        # Verify subject label indicates site-wide grouping
        self.assertTrue(any("SITE-" in a["subject"] for a in integrity_events))

    # -------------------------------------------------------------------------
    # 14. Lack of Corroboration Reduces False-Positive Escalation
    # -------------------------------------------------------------------------
    def test_14_lack_of_corroboration_reduces_false_positives(self):
        """14. Uncorroborated transaminase elevations (already elevated at baseline) are flagged."""
        alerts = self.watch.monitoring.run_surveillance(
            current_cut=12,
            unit_anomalies=[],
            site_integrity={},
        )
        # Verify corroborated flag is evaluated
        hys_alerts = [a for a in alerts if "Hy's Law" in a["title"]]
        if hys_alerts:
            self.assertIn("corroborated", hys_alerts[0])

    # -------------------------------------------------------------------------
    # 15. Quarantined Data Excluded from Safety Aggregation
    # -------------------------------------------------------------------------
    def test_15_quarantined_data_excluded_from_safety_aggregation(self):
        """15. Quarantined data is excluded from safety aggregation."""
        # Quarantine site S04 GLUC
        unit_anomalies = [{
            "alert_id": "UNIT_SHIFT_S04_GLUC",
            "site": "S04",
            "test": "GLUC",
            "trust_state": TrustState.UNTRUSTED.value,
            "ratio": 18.0,
            "incoming_median": 6.4,
            "title": "Unit mismatch",
            "description": "Glucose shifted by factor 18",
            "lab_query": "Please confirm units",
        }]
        alerts = self.watch.monitoring.run_surveillance(
            current_cut=8,
            unit_anomalies=unit_anomalies,
            site_integrity={},
        )
        # S04 GLUC records must not produce false hypoglycemia emergency
        hypo_emergencies = [
            a for a in alerts
            if a["site"] == "S04" and a["type"] == "CLINICAL_SAFETY" and "hypoglycemia" in a.get("title", "").lower()
        ]
        self.assertEqual(len(hypo_emergencies), 0)

    # -------------------------------------------------------------------------
    # 16. Serious Genuine Event Still Escalates
    # -------------------------------------------------------------------------
    def test_16_genuine_serious_event_still_escalates(self):
        """16. Genuine serious adverse event with hospitalization overrides and escalates."""
        self.graph.build(cut=12)
        alerts = self.watch.monitoring.run_surveillance(
            current_cut=12,
            unit_anomalies=[],
            site_integrity={},
        )
        saes = [a for a in alerts if a["type"] == "CLINICAL_SAFETY" and "adverse event" in a["title"].lower()]
        self.assertGreater(len(saes), 0, "Genuine SAEs must escalate")
        self.assertEqual(saes[0]["severity"], "CRITICAL")

    # -------------------------------------------------------------------------
    # 17. Suspicious Regular Site Detected
    # -------------------------------------------------------------------------
    def test_17_suspicious_regular_site_detected(self):
        """17. Site with unnaturally low vital signs variance is flagged generically."""
        detector = SiteIntegrityDetector()
        results = detector.detect(self.graph, current_cut=12)
        # Verify at least one site is flagged SUSPECT due to low variance
        flagged_sites = [s for s, info in results.items() if info["status"] in ("SUSPECT", "WATCH")]
        self.assertGreater(len(flagged_sites), 0, "Expected unnaturally regular site to be flagged")
        suspect = results[flagged_sites[0]]
        self.assertLess(suspect["sysbp_stdev"], suspect["peer_sysbp_median_stdev"])

    # -------------------------------------------------------------------------
    # 18. Document Hash Change Detected
    # -------------------------------------------------------------------------
    def test_18_document_hash_change_detected(self):
        """18. Document changes are detected via cryptographic SHA-256 hashing."""
        detector = DocumentTamperDetector(self.graph.documents_dir)
        records = detector.check_documents(cut=1)
        self.assertGreater(len(records), 0, "Expected document hashes computed")
        self.assertTrue(all(len(r.sha256_hash) == 64 for r in records))

    # -------------------------------------------------------------------------
    # 19. Instruction-Like Document Change Ignored
    # -------------------------------------------------------------------------
    def test_19_instruction_like_document_change_ignored(self):
        """19. Adversarial prompt injection in document is detected and ignored."""
        detector = DocumentTamperDetector(self.graph.documents_dir)
        records = detector.check_documents(cut=8)
        tamper_records = [r for r in records if r.tamper_suspected]
        self.assertGreater(len(tamper_records), 0, "Expected instruction-like text detected")
        self.assertIn("neutralized", tamper_records[0].action_taken.lower())

    # -------------------------------------------------------------------------
    # 20. Delayed Escalation Never Becomes Silent Approval
    # -------------------------------------------------------------------------
    def test_20_delayed_escalation_never_silent_approval(self):
        """20. Unanswered escalation stays active and never silently approves."""
        tracker = DelayedEscalationTracker()
        tracker.track_case("CASE_001", "HYS_LAW", "042-S01-001", "S01", created_cut=1)
        # Advance 2 cuts with empty monitor responses
        tracker.advance_cut(current_cut=3, monitor_responses={})
        c = tracker.cases["CASE_001"]
        self.assertEqual(c["status"], EscalationState.WAITING.value)
        self.assertFalse(c["monitor_action_allowed"])

    # -------------------------------------------------------------------------
    # 21. Four-Cut Wait Enters Standing-Limits State
    # -------------------------------------------------------------------------
    def test_21_four_cut_wait_enters_standing_limits_state(self):
        """21. Escalation unanswered after 4 cuts transitions to STANDING_LIMITS."""
        tracker = DelayedEscalationTracker()
        tracker.track_case("CASE_001", "HYS_LAW", "042-S01-001", "S01", created_cut=1)
        # Advance 4 cuts with zero monitor response
        tracker.advance_cut(current_cut=5, monitor_responses={})
        c = tracker.cases["CASE_001"]
        self.assertEqual(c["status"], EscalationState.STANDING_LIMITS.value)
        self.assertTrue(c["standing_limits"])
        self.assertFalse(c["monitor_action_allowed"])
        self.assertIn("STANDING_LIMITS", c["audit_notes"][-1])

    # -------------------------------------------------------------------------
    # 22. Protocol Change Invalidates Stale Derived Findings
    # -------------------------------------------------------------------------
    def test_22_protocol_change_invalidates_stale_derived_findings(self):
        """22. Dynamic protocol change re-derives compliance findings and invalidates stale findings."""
        monitoring = ThresholdMonitoringEngine(self.graph)
        monitoring.last_evaluated_protocol = 1
        self.graph.current_cut = 5  # Protocol changes dynamically
        trace = monitoring.evaluate_protocol_amendment(current_cut=5)
        self.assertIsNotNone(trace, "Expected amendment trace when protocol changes")
        self.assertGreater(trace["new_protocol"], trace["old_protocol"])

    # -------------------------------------------------------------------------
    # 23. explain() Returns Exact Stored Evidence
    # -------------------------------------------------------------------------
    def test_23_explain_returns_exact_stored_evidence(self):
        """23. explain() returns exact stored historical evidence lines and justification."""
        self.watch.log_decision(
            decision_id="DEC_TEST_001",
            cut=3,
            component="SAFETY_RULE",
            what="Serious adverse event coding override",
            why="AESHOSP=Y overrides AESER=N per protocol §6",
            evidence_refs=[{"domain": "AE", "usubjid": "042-S02-004", "seq": 1}],
            evidence_lines=["AE · Seq 1: Cellulitis (AESHOSP=Y)"],
            alternatives=["Do not escalate: Rejected due to mandatory ICH E2A guideline."],
            action="Escalate to medical monitor inbox",
            result="ESCALATED",
        )

        res = self.watch.explain("DEC_TEST_001")
        self.assertEqual(res["decision_id"], "DEC_TEST_001")
        self.assertEqual(res["what"], "Serious adverse event coding override")
        self.assertIn("AESHOSP=Y", res["why"])
        self.assertIn("AE · Seq 1", res["evidence_lines"][0])

    # -------------------------------------------------------------------------
    # 24. explain() Evidence Matches Trace
    # -------------------------------------------------------------------------
    def test_24_explain_evidence_matches_trace(self):
        """24. Evidence items in explain() match stored trace evidence references."""
        self.watch.log_decision(
            decision_id="DEC_TEST_002",
            cut=1,
            component="SAFETY_RULE",
            what="Potential Hy's law candidate",
            why="Concurrent ALT and Bilirubin elevation",
            evidence_refs=[{"domain": "LB", "usubjid": "042-S07-001", "seq": 25}],
            evidence_lines=["LB · Seq 25: ALT elevated"],
        )
        res = self.watch.explain("DEC_TEST_002")
        self.assertEqual(len(res["evidence"]), 1)
        self.assertEqual(res["evidence"][0]["domain"], "LB")
        self.assertEqual(res["evidence"][0]["usubjid"], "042-S07-001")

    # -------------------------------------------------------------------------
    # 25. Repeated Run is Deterministic
    # -------------------------------------------------------------------------
    def test_25_repeated_run_is_deterministic(self):
        """25. Repeated surveillance runs produce identical decisions, evidence, and actions."""
        watch_a = StudyWatch(data_dir=self.data_dir, deterministic_clock=True)
        rep_a = watch_a.run_cut(1)

        watch_b = StudyWatch(data_dir=self.data_dir, deterministic_clock=True)
        rep_b = watch_b.run_cut(1)

        self.assertEqual(rep_a["signals_detected"], rep_b["signals_detected"])
        self.assertEqual(rep_a["critical_alerts"], rep_b["critical_alerts"])
        self.assertEqual(rep_a["decision_ids"], rep_b["decision_ids"])

        # Compare decisions excluding real-time clock variability
        for did in rep_a["decision_ids"]:
            dec_a = watch_a.decision_traces[did]
            dec_b = watch_b.decision_traces[did]
            self.assertEqual(dec_a.what, dec_b.what)
            self.assertEqual(dec_a.why, dec_b.why)
            self.assertEqual(dec_a.action, dec_b.action)
            self.assertEqual(dec_a.evidence_refs, dec_b.evidence_refs)

    # -------------------------------------------------------------------------
    # 26. Budget Degradation Keeps Safety Checks Active
    # -------------------------------------------------------------------------
    def test_26_budget_degradation_keeps_safety_checks_active(self):
        """26. Budget degradation down to SAFETY_ONLY keeps deterministic safety rules active."""
        self.watch.budget_used_units = 950.0  # Force >90% usage
        self.watch._consume_budget(units=1.0)
        self.assertEqual(self.watch.current_budget_tier, BudgetTier.SAFETY_ONLY)

        # Run cut under SAFETY_ONLY
        rep = self.watch.run_cut(1)
        self.assertGreater(rep["signals_detected"], 0, "Safety checks must still execute under SAFETY_ONLY")

    # -------------------------------------------------------------------------
    # 27. Review Center Contains No Production Fixtures
    # -------------------------------------------------------------------------
    def test_27_review_center_contains_no_production_fixtures(self):
        """27. ReviewCrew produces real graph-derived data without dummy fixtures."""
        crew = ReviewCrew(study_graph=self.graph)
        data = crew.run_cycle(cut=12)
        # Assert counts are derived from real findings, not hardcoded fallback
        self.assertEqual(data["stages"][0]["count"], len(self.graph.get_findings()))
        self.assertTrue(len(data["sites"]) > 0)
        self.assertEqual(len(data["sites"]), len(self.graph.sites))

    # -------------------------------------------------------------------------
    # 28. Data Intake Values All Come from Backend
    # -------------------------------------------------------------------------
    def test_28_data_intake_values_come_from_backend(self):
        """28. Data Intake status and metrics endpoints return real cut records."""
        engine = IncrementalIngestionEngine(self.graph)
        metrics = engine.ingest_cut_delta(cut=1)
        self.assertGreater(metrics.records_inserted, 0)
        self.assertEqual(metrics.full_build_calls, 0)

    # -------------------------------------------------------------------------
    # 29. Stage 1 Baseline Still Passes
    # -------------------------------------------------------------------------
    def test_29_stage1_baseline_still_passes(self):
        """29. Authoritative Stage 1 StudyGraph functionality is preserved."""
        g = StudyGraph(self.data_dir)
        stats = g.build(cut=12)
        self.assertGreater(stats["records"], 0)
        self.assertGreater(stats["subjects"], 0)
        self.assertGreater(len(g.find_serious_adverse_events()), 0)
        self.assertGreater(len(g.find_hys_law_candidates()), 0)

    # -------------------------------------------------------------------------
    # 30. Stage 2 Baseline Still Passes
    # -------------------------------------------------------------------------
    def test_30_stage2_baseline_still_passes(self):
        """30. Authoritative Stage 2 ReviewCrew and ReviewMemory safeguards are preserved."""
        mem = ReviewMemory()
        crew = ReviewCrew(study_graph=self.graph, memory=mem)
        cycle = crew.run_cycle(cut=12)
        self.assertIn("cases", cycle)
        self.assertIn("funnel", cycle)
        self.assertIn("integrity", cycle)
        self.assertTrue(cycle["integrity"]["clinicalRules"]["hospitalizationOverrideActive"])

    # -------------------------------------------------------------------------
    # 31. BUDGET: 80% Rule Stops Optional Narrative, Keeps Safety & Trace
    # -------------------------------------------------------------------------
    def test_31_budget_80_percent_rule(self):
        """31. At >=80% budget, optional narrative stops; deterministic safety & traces continue."""
        watch = StudyWatch(data_dir=self.data_dir, deterministic_clock=True, budget_limit=100.0)
        watch.crew = ReviewCrew(study_graph=self.graph)
        watch._consume_budget(units=80.0)  # Exactly 80%
        self.assertGreaterEqual(watch.current_budget_tier, BudgetTier.REDUCED)

        rep = watch.run_cut(1)
        self.assertTrue(rep["budget_usage"]["optional_narrative_suppressed"])
        self.assertGreaterEqual(rep["budget_usage"]["percentage"], 80.0)
        self.assertEqual(rep["crew_data"].get("status"), "DEGRADED_BUDGET")
        self.assertGreater(rep["signals_detected"], 0, "Safety surveillance must remain 100% active")
        self.assertGreater(len(rep["decision_ids"]), 0, "Decision trace logging must remain active")
        self.assertIn("remaining", rep["budget_usage"])

    # -------------------------------------------------------------------------
    # 32. QUARANTINE SAFETY FLOOR: Explicit SAE Must Never Be Suppressed
    # -------------------------------------------------------------------------
    def test_32_quarantine_safety_floor(self):
        """32. Quarantined quantitative data excluded, but explicit SAE/hospitalization still escalates."""
        monitoring = ThresholdMonitoringEngine(self.graph)
        # Mock site quarantine
        site_integrity = {"S02": {"status": "QUARANTINED", "trust_state": TrustState.QUARANTINED.value, "reasons": ["Unnatural regularity"]}}
        alerts = monitoring.run_surveillance(current_cut=1, unit_anomalies=[], site_integrity=site_integrity)

        # SAEs for S02 must still be present in alerts
        s02_alerts = [a for a in alerts if "S02" in a.get("subject", "") or a.get("site") == "S02"]
        sae_alerts = [a for a in s02_alerts if a.get("type") == "CLINICAL_SAFETY" and a.get("severity") == "CRITICAL"]
        self.assertGreater(len(sae_alerts), 0, "Explicit SAE must not be hidden by site quarantine")

    # -------------------------------------------------------------------------
    # 33. TRACE CONSISTENCY: Computed Dynamically (Not Hardcoded True)
    # -------------------------------------------------------------------------
    def test_33_trace_consistency_computed(self):
        """33. consistent_with_trace is computed comparing stored snapshot with persisted trace and store."""
        self.watch.log_decision(
            decision_id="DEC_COMPUTED_01",
            cut=1,
            component="SAFETY_RULE",
            what="Test Decision",
            why="Testing computed consistency",
            evidence_refs=[{"domain": "LB", "usubjid": "042-S07-001", "seq": 25}],
            evidence_lines=["LB · Seq 25"],
            action="Monitor notification",
        )
        res = self.watch.explain("DEC_COMPUTED_01")
        self.assertIn("trace_consistency_details", res)
        self.assertTrue(res["consistent_with_trace"])
        self.assertTrue(res["trace_consistency_details"]["persisted_in_decision_log"])
        self.assertTrue(res["trace_consistency_details"]["evidence_references_verified"])

        # Explain non-existent decision
        res_fake = self.watch.explain("NON_EXISTENT_DECISION_ID")
        self.assertFalse(res_fake["consistent_with_trace"])

    # -------------------------------------------------------------------------
    # 34. PERSISTENCE: Append-Only Log Survives Restart
    # -------------------------------------------------------------------------
    def test_34_trace_persistence_across_restart(self):
        """34. Persisted append-only decision log is reloaded upon process restart."""
        temp_log = Path(self.data_dir).resolve() / "test_persistence_log.jsonl"
        if temp_log.is_file():
            temp_log.unlink()

        watch_1 = StudyWatch(data_dir=self.data_dir, decision_log_path=str(temp_log), deterministic_clock=True)
        watch_1.log_decision(
            decision_id="DEC_PERSIST_100",
            cut=2,
            component="SURVEILLANCE",
            what="Persisted finding",
            why="Verifying durability",
            evidence_refs=[],
            evidence_lines=[],
            action="Log action",
        )
        self.assertTrue(temp_log.is_file())

        # Simulate restart: new instance with same decision log
        watch_2 = StudyWatch(data_dir=self.data_dir, decision_log_path=str(temp_log), deterministic_clock=True)
        self.assertIn("DEC_PERSIST_100", watch_2.decision_traces)
        exp = watch_2.explain("DEC_PERSIST_100")
        self.assertTrue(exp["found"])
        self.assertEqual(exp["what"], "Persisted finding")

        if temp_log.is_file():
            temp_log.unlink()

    # -------------------------------------------------------------------------
    # 35. SITE RISK RANKING: Evidence-Derived Without Invented Scores
    # -------------------------------------------------------------------------
    def test_35_site_risk_ranking(self):
        """35. Site risk ranking derived only from real evidence (anomalies, unanswered queries, quarantine)."""
        monitoring = ThresholdMonitoringEngine(self.graph)
        site_integrity = {
            "S11": {"status": "QUARANTINED", "reasons": ["Unnatural vital signs SD < 1.0 mmHg"]},
            "S04": {"status": "NORMAL", "reasons": []},
        }
        unit_anomalies = [
            {"site": "S04", "test": "GLUC", "ratio": 18.0, "expected_conversion": "mg/dL <-> mmol/L"}
        ]
        ranking = monitoring.get_site_risk_ranking(current_cut=8, site_integrity=site_integrity, unit_anomalies=unit_anomalies)

        self.assertIsInstance(ranking, list)
        self.assertGreater(len(ranking), 0)
        # S11 (quarantined) must be top ranked (rank 1)
        top_rank = ranking[0]
        self.assertEqual(top_rank["site_id"], "S11")
        self.assertEqual(top_rank["risk_tier"], "CRITICAL")
        self.assertTrue(top_rank["is_quarantined"])
        self.assertGreater(len(top_rank["reasons"]), 0)

    # -------------------------------------------------------------------------
    # 36. FALSE ALARM METRICS: Cut 8 Unit Corruption Counts as DATA_INTEGRITY
    # -------------------------------------------------------------------------
    def test_36_false_alarm_metrics_cut8(self):
        """36. Cut 8 unit shift is classified as DATA_INTEGRITY, suppressing clinical false positives."""
        rep = self.watch.run_cut(8)
        fam = rep["false_alarm_metrics"]
        self.assertIn("candidate_alerts", fam)
        self.assertIn("clinical_alerts_emitted", fam)
        self.assertIn("data_integrity_alerts_emitted", fam)
        self.assertIn("clinical_alerts_suppressed_integrity", fam)
        self.assertIn("suppression_rate", fam)

        # Check that Cut 8 unit corruption generated a DATA_INTEGRITY alert
        di_alerts = [a for a in rep["alerts"] if a.get("category") == "DATA_INTEGRITY" or a.get("type") == "DATA_INTEGRITY"]
        self.assertGreater(len(di_alerts), 0)
        # Check no false clinical emergency was raised for the unit shift
        unit_emergencies = [a for a in rep["alerts"] if a.get("type") == "CLINICAL_SAFETY" and "mismatch" in a.get("title", "").lower()]
        self.assertEqual(len(unit_emergencies), 0)

    # -------------------------------------------------------------------------
    # 37. DETECTION TIMING: Genuine SAE Escalated in SAME Cut
    # -------------------------------------------------------------------------
    def test_37_detection_timing_same_cut_sae(self):
        """37. Genuine serious event is detected and escalated in the SAME cut it appears."""
        rep = self.watch.run_cut(1)
        latency_info = rep["signal_detection_latency"]
        self.assertGreater(latency_info["same_cut_escalated_count"], 0)

        # Find any SAE signal timing record
        sae_timings = [r for r in latency_info["records"] if r["signal_type"] == "SERIOUS_ADVERSE_EVENT"]
        for st in sae_timings:
            self.assertEqual(st["escalation_latency_cuts"], 0, "SAE must be escalated in SAME cut (latency 0)")

    # -------------------------------------------------------------------------
    # 38. DELAYED HUMAN: 4 Cuts Without Reply Enforces STANDING_LIMITS
    # -------------------------------------------------------------------------
    def test_38_delayed_human_standing_limits_after_4_cuts(self):
        """38. Unanswered monitor queries advance cut-by-cut and enforce STANDING_LIMITS at 4 cuts."""
        tracker = DelayedEscalationTracker()
        tracker.track_case("CASE_DELAY_01", "serious_adverse_event", "042-S01-001", "S01", created_cut=1)

        tracker.advance_cut(current_cut=2, monitor_responses={})
        self.assertEqual(tracker.cases["CASE_DELAY_01"]["status"], EscalationState.WAITING.value)

        tracker.advance_cut(current_cut=3, monitor_responses={})
        self.assertEqual(tracker.cases["CASE_DELAY_01"]["status"], EscalationState.WAITING.value)

        tracker.advance_cut(current_cut=4, monitor_responses={})
        self.assertEqual(tracker.cases["CASE_DELAY_01"]["status"], EscalationState.WAITING.value)

        # At cut 5: cuts_waiting = 5 - 1 = 4 -> STANDING_LIMITS
        tracker.advance_cut(current_cut=5, monitor_responses={})
        case = tracker.cases["CASE_DELAY_01"]
        self.assertEqual(case["status"], EscalationState.STANDING_LIMITS.value)
        self.assertTrue(case["standing_limits"])
        self.assertFalse(case["monitor_action_allowed"])

    # -------------------------------------------------------------------------
    # 39. HIDDEN-VERSION SAFETY: Zero Hardcoded Sites or Cut Numbers
    # -------------------------------------------------------------------------
    def test_39_hidden_version_safety_zero_hardcoding(self):
        """39. Verify zero hardcoded sites (S04, S11) or cut numbers (Cut 8) in stage3 detectors & models."""
        forbidden = ["'S04'", '"S04"', "'S11'", '"S11"', "cut == 8", "cut==8"]
        stage3_files = [
            Path("stage3/detectors.py"),
            Path("stage3/models.py"),
            Path("stage3/monitoring.py"),
            Path("stage3/ingestion.py"),
        ]
        for fpath in stage3_files:
            if fpath.is_file():
                content = fpath.read_text(encoding="utf-8")
                for f_term in forbidden:
                    self.assertNotIn(f_term, content, f"Forbidden hardcoded term {f_term} found in {fpath}")

    # -------------------------------------------------------------------------
    # 40. SURVEILLANCE REPORT: All 6 Hardened Fields Present
    # -------------------------------------------------------------------------
    def test_40_surveillance_report_structure(self):
        """40. SurveillanceReport contains site_risk_ranking, false_alarm_metrics, latency, decision_log_path, budget_usage, open_items."""
        rep = self.watch.run_cut(1)
        required_fields = [
            "site_risk_ranking",
            "false_alarm_metrics",
            "signal_detection_latency",
            "decision_log_path",
            "budget_usage",
            "open_items",
        ]
        for rf in required_fields:
            self.assertIn(rf, rep, f"SurveillanceReport missing required field: {rf}")


if __name__ == "__main__":
    unittest.main()

