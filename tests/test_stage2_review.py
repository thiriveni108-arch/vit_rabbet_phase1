"""Unit and Regression Tests for Stage 2 MONITOR: ReviewCrew, ReviewMemory, and 8 Official Failure Modes.

Validates:
1. AESHOSP=Y overrides AESER=N (hospitalisation forces serious classification per protocol §6).
2. CLARIFY retrieves StudyGraph baseline facts and resubmits to monitor.
3. REJECTED cases remain in monitoring and are blocked from auto-re-escalation.
4. Duplicate queries on the same record are strictly blocked by ReviewMemory.
5. ReviewMemory survives across run_cycle() calls.
6. Protocol version changes (v1 -> v2 -> v3) are applied dynamically.
7. Selective escalation: funnel ensures not every finding escalates to human gate.
8. Decision trace entries are emitted at decision time with timestamps.
"""

import unittest
from stage1.atlas import StudyGraph
from backend.review_crew import ReviewCrew, ReviewMemory


class TestStage2Review(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.graph = StudyGraph("hackathon-data")
        cls.graph.build(cut=12)

    def setUp(self):
        self.mem = ReviewMemory()
        self.engine = ReviewCrew(study_graph=self.graph, memory=self.mem)

    def test_failure_mode_1_hospitalization_override(self):
        """1. AESHOSP=Y overrides AESER=N per protocol §6."""
        saes = self.graph.find_serious_adverse_events()
        self.assertGreater(len(saes), 0, "Expected serious adverse events to be detected")

        # Find cases where hospitalization was entered as Y while entered serious was N
        overrides = [s for s in saes if s["details"].get("is_hospitalization_override")]
        self.assertGreater(len(overrides), 0, "Expected at least one hospitalization override finding")

        sample = overrides[0]
        self.assertEqual(sample["details"]["aeshosp"], "Y")
        self.assertNotEqual(sample["details"]["aeser"], "Y")
        self.assertEqual(sample["finding_type"], "serious_adverse_event")

    def test_failure_mode_2_clarify_retrieves_and_resubmits(self):
        """2. CLARIFY retrieves StudyGraph patient 360 baseline facts and resubmits."""
        cycle_data = self.engine.run_cycle(cut=12)
        cases = cycle_data["cases"]

        # Locate case-042 (Potential Hy's Law candidate 042-S07-001)
        hl_cases = [c for c in cases if "042-S07-001" in c["usubjid"]]
        self.assertGreater(len(hl_cases), 0)

        case = hl_cases[0]
        clarify = case.get("humanGate", {}).get("clarifyTarget")
        self.assertIsNotNone(clarify)
        self.assertIn("ALT", clarify["testCode"])
        self.assertIsNotNone(clarify["expectedValue"])

    def test_failure_mode_3_rejected_remains_monitoring(self):
        """3. REJECTED stays in monitoring and cannot auto re-escalate."""
        # First record a rejection in memory
        self.engine.memory.record_decision(
            "HYS_LAW_CANDIDATE",
            "042-S07-001",
            "REJECTED",
            "Baseline transaminases elevated",
            finding_id="HYS_042-S07-001",
        )

        # Run cycle
        self.engine.run_cycle(cut=12)
        self.assertTrue(self.engine.memory.is_auto_escalation_blocked("HYS_042-S07-001"))
        self.assertGreaterEqual(self.engine.memory.duplicate_escalations_prevented, 1)

    def test_failure_mode_4_duplicate_query_blocked(self):
        """4. Duplicate query on same record is blocked by memory."""
        domain, usubjid, seq = "AE", "042-S11-005", 1

        # First check: not dispatched yet
        self.assertFalse(self.engine.memory.is_query_already_dispatched(domain, usubjid, seq))

        # Record dispatch
        self.engine.memory.record_dispatched_query(domain, usubjid, seq)

        # Second check: must be blocked
        self.assertTrue(self.engine.memory.is_query_already_dispatched(domain, usubjid, seq))
        self.assertGreaterEqual(self.engine.memory.duplicate_queries_prevented, 1)

    def test_failure_mode_5_memory_survives_cycles(self):
        """5. ReviewMemory survives across run_cycle() calls."""
        mem = ReviewMemory()
        engine = ReviewCrew(study_graph=self.graph, memory=mem)

        # Record a decision
        mem.record_decision("CODE_A", "042-S01-001", "APPROVED", "Confirmed SAE")
        engine.run_cycle(cut=11)

        # Subsequent cycle with same memory
        engine.run_cycle(cut=12)
        self.assertIn("CODE_A|042-S01-001", mem.adjudicated_decisions)
        self.assertEqual(mem.adjudicated_decisions["CODE_A|042-S01-001"][0], "APPROVED")

    def test_failure_mode_6_protocol_version_applied(self):
        """6. Current protocol version is dynamically applied."""
        self.graph.build(cut=1)  # Protocol v1
        c1 = self.engine.run_cycle(cut=1)
        self.assertEqual(c1["protocolVersion"], 1)

        self.graph.build(cut=6)  # Protocol v2
        c6 = self.engine.run_cycle(cut=6)
        self.assertEqual(c6["protocolVersion"], 2)

        self.graph.build(cut=12)  # Protocol v3
        c12 = self.engine.run_cycle(cut=12)
        self.assertEqual(c12["protocolVersion"], 3)

    def test_failure_mode_7_selective_escalation_funnel(self):
        """7. Not every finding escalates (Selective escalation funnel)."""
        cycle = self.engine.run_cycle(cut=12)
        funnel = cycle["funnel"]

        counts = {step["stage"]: step["count"] for step in funnel}
        self.assertGreater(counts["detected"], counts["medically_relevant"])
        self.assertGreater(counts["medically_relevant"], counts["human_escalation"])
        self.assertLessEqual(counts["human_escalation"], 5)

    def test_failure_mode_8_decision_trace_emitted(self):
        """8. Trace entries are emitted at decision time with timestamps."""
        cycle = self.engine.run_cycle(cut=12)
        cases = cycle["cases"]
        self.assertGreater(len(cases), 0)

        case = cases[0]
        trace = case.get("rawTrace", [])
        self.assertGreater(len(trace), 0)
        for entry in trace:
            self.assertIn("timestamp", entry)
            self.assertIn("stage", entry)
            self.assertIn("action", entry)
            self.assertIn(":", entry["timestamp"])


if __name__ == "__main__":
    unittest.main()
