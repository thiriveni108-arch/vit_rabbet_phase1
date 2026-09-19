"""Dedicated Test Suite for Upgraded ATLAS Conversational Assistant.

Validates:
- All 11 user-mandated conversational test flows
- Paraphrase synonym coverage mapping to the same deterministic StudyGraph rule
- Broad phrase explicit interpretation notice requirement
- Mixed question answering (general concept explanation + StudyGraph candidate query)
- Conversation memory strictly for reference resolution
- Unconfigured LLM graceful fallback
- Strict physical evidence validation
"""

import unittest
from backend.study_service import StudyService
from backend.schemas import Answer


class TestConversationalAssistant(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.service = StudyService()
        cls.service.load(cut=12)
        cls.agent = cls.service.agent
        cls.graph = cls.service.graph

    def setUp(self):
        # Reset conversation state before each test unless explicitly testing multi-turn
        self.agent.reset_conversation()

    # =========================================================================
    # THE 11 USER-MANDATED TESTS
    # =========================================================================

    def test_01_liver_injury_pattern(self):
        """TEST 1: Which subjects show a potential liver injury pattern?"""
        res = self.agent.answer("Which subjects show a potential liver injury pattern?")
        self.assertEqual(res.intent, "FINDING")
        self.assertIsInstance(res.answer, list)
        self.assertEqual(len(res.answer), 3)
        self.assertIn("042-S05-003", res.answer)
        self.assertIn("042-S07-001", res.answer)
        self.assertIn("042-S08-014", res.answer)
        # Check clinical wording guardrails: potential signal, unconfirmed
        self.assertIn("potential", res.text.lower())
        self.assertIn("adjudication", res.text.lower())
        self.assertIn("not confirmed", res.text.lower())
        # Evidence must physically exist
        self.assertGreaterEqual(len(res.evidence), 6)
        for ev in res.evidence:
            self.assertTrue(self.graph.has_record(ev.domain, ev.usubjid, ev.seq))

    def test_02_liver_signal_paraphrase(self):
        """TEST 2: Anyone with a liver signal?"""
        res = self.agent.answer("Anyone with a liver signal?")
        self.assertEqual(res.intent, "FINDING")
        self.assertEqual(len(res.answer), 3)
        self.assertIn("042-S05-003", res.answer)
        self.assertIn("042-S07-001", res.answer)
        self.assertIn("042-S08-014", res.answer)

    def test_03_why_flagged_shorthand(self):
        """TEST 3: Why was S07-001 flagged?"""
        res = self.agent.answer("Why was S07-001 flagged?")
        self.assertEqual(res.intent, "WHY_FLAGGED")
        self.assertIn("042-S07-001", res.text)
        self.assertIn("3.995", res.text)
        self.assertIn("5.38", res.text)
        self.assertIn("Week 8", res.text)
        self.assertIn("adjudication", res.text.lower())
        self.assertGreaterEqual(len(res.evidence), 2)
        for ev in res.evidence:
            self.assertTrue(self.graph.has_record(ev.domain, ev.usubjid, ev.seq))

    def test_04_show_the_proof_multiturn(self):
        """TEST 4: Multi-turn flow leading to 'Show the proof.'"""
        # Turn 1: Flagged query establishing active subject 042-S07-001
        self.agent.answer("Why was S07-001 flagged?")
        # Turn 2: Proof request
        res = self.agent.answer("Show the proof.")
        self.assertEqual(res.intent, "EVIDENCE_REQUEST")
        self.assertIn("042-S07-001", res.text)
        self.assertIn("LB seq", res.text)
        self.assertGreaterEqual(len(res.evidence), 2)
        for ev in res.evidence:
            self.assertEqual(ev.usubjid, "042-S07-001")
            self.assertTrue(self.graph.has_record(ev.domain, ev.usubjid, ev.seq))

    def test_05_what_is_hys_law(self):
        """TEST 5: What is Hy's Law?"""
        res = self.agent.answer("What is Hy's Law?")
        self.assertEqual(res.intent, "GENERAL")
        self.assertIn("Zimmerman", res.text)
        self.assertIn("3× ULN", res.text)
        self.assertIn("2× ULN", res.text)
        self.assertEqual(res.evidence, [])

    def test_06_mixed_question_hys_law_and_study(self):
        """TEST 6: What is Hy's Law and does anyone in our study meet it?"""
        res = self.agent.answer("What is Hy's Law and does anyone in our study meet it?")
        self.assertEqual(res.intent, "MIXED")
        # Part 1: general explanation present
        self.assertIn("Zimmerman", res.text)
        # Part 2: real StudyGraph candidates present
        self.assertIn("042-S05-003", res.text)
        self.assertIn("042-S07-001", res.text)
        self.assertIn("042-S08-014", res.text)
        # Evidence must physically exist
        self.assertGreaterEqual(len(res.evidence), 6)
        for ev in res.evidence:
            self.assertTrue(self.graph.has_record(ev.domain, ev.usubjid, ev.seq))

    def test_07_hospitalized_non_serious(self):
        """TEST 7: Who was hospitalized but entered as non-serious?"""
        res = self.agent.answer("Who was hospitalized but entered as non-serious?")
        self.assertEqual(res.intent, "FINDING")
        self.assertIn("042-S02-004", res.answer)
        self.assertIn("Cellulitis", res.text)
        self.assertIn("AESHOSP=Y", res.text)
        self.assertIn("AESER=N", res.text)
        self.assertGreaterEqual(len(res.evidence), 1)
        for ev in res.evidence:
            self.assertEqual(ev.domain, "AE")
            self.assertEqual(ev.usubjid, "042-S02-004")
            self.assertTrue(self.graph.has_record(ev.domain, ev.usubjid, ev.seq))

    def test_08_patient_360_tell_me_everything(self):
        """TEST 8: Tell me everything about 042-S07-001."""
        res = self.agent.answer("Tell me everything about 042-S07-001.")
        self.assertEqual(res.intent, "SUBJECT_360")
        self.assertIn("Patient 360 Summary for 042-S07-001", res.text)
        self.assertIn("Demographics", res.text)
        self.assertIn("Site S07", res.text)
        self.assertGreater(len(res.evidence), 0)
        for ev in res.evidence:
            self.assertTrue(self.graph.has_record(ev.domain, ev.usubjid, ev.seq))

    def test_09_multiturn_alt_at_week_8(self):
        """TEST 9: What was ALT at Week 8? (using conversation context)"""
        # Turn 1: Discuss subject 042-S07-001
        self.agent.answer("Tell me everything about 042-S07-001.")
        # Turn 2: Contextual follow-up omitting subject
        res = self.agent.answer("What was ALT at Week 8?")
        self.assertEqual(res.intent, "LOOKUP")
        self.assertIn("042-S07-001", res.text)
        self.assertIn("3.995", res.text)
        self.assertIn("4.30x ULN", res.text)
        self.assertEqual(len(res.evidence), 1)
        self.assertEqual(res.evidence[0].usubjid, "042-S07-001")
        self.assertTrue(self.graph.has_record(res.evidence[0].domain, res.evidence[0].usubjid, res.evidence[0].seq))

    def test_10_what_is_a_clinical_trial(self):
        """TEST 10: What is a clinical trial?"""
        res = self.agent.answer("What is a clinical trial?")
        self.assertEqual(res.intent, "GENERAL")
        self.assertIn("Phase I", res.text)
        self.assertIn("Phase IV", res.text)
        self.assertEqual(res.evidence, [])

    def test_11_president_of_france_graceful_fallback(self):
        """TEST 11: Who is the president of France?"""
        res = self.agent.answer("Who is the president of France?")
        self.assertEqual(res.intent, "GENERAL")
        # Must NOT claim "not found in study"
        self.assertNotIn("not found in study", res.text.lower())
        self.assertNotIn("no records matched", res.text.lower())
        # If no LLM configured, graceful fallback stated
        if not self.agent.llm_service.is_llm_configured():
            self.assertIn("General knowledge mode is not configured in this deployment.", res.text)

    # =========================================================================
    # PARAPHRASE AND SYNONYM COVERAGE
    # =========================================================================

    def test_paraphrase_equivalence_liver_signal(self):
        """All variations of liver injury questions must yield identical deterministic results."""
        paraphrases = [
            "Which subjects show a potential liver injury pattern?",
            "Anyone with a liver safety signal?",
            "Who has ALT and bilirubin elevation?",
            "Possible Hy's Law cases?",
            "Show me liver-related findings.",
            "Who has hepatic safety signal?",
            "possible DILI pattern candidates",
        ]
        expected_candidates = ["042-S05-003", "042-S07-001", "042-S08-014"]
        for p in paraphrases:
            ans = self.agent.answer(p)
            self.assertEqual(sorted(ans.answer), sorted(expected_candidates), f"Failed on paraphrase: '{p}'")

    def test_broad_phrase_explicit_interpretation_notice(self):
        """Broad phrases must explicitly state the interpretation before answering."""
        res = self.agent.answer("Who has liver problems?")
        self.assertIn("I interpreted 'liver problems' as the study's potential liver-safety / Hy's Law biochemical findings.", res.text)
        self.assertEqual(len(res.answer), 3)

    def test_followup_site_s07_to_subject_resolution(self):
        """Turn 1: Liver signal -> Turn 2: 'Why was S07 flagged?' resolves to 042-S07-001."""
        # Turn 1
        self.agent.answer("Which subjects show a potential liver injury pattern?")
        # Turn 2
        res = self.agent.answer("Why was S07 flagged?")
        self.assertEqual(res.intent, "WHY_FLAGGED")
        self.assertIn("042-S07-001", res.text)
        self.assertIn("3.995", res.text)


if __name__ == "__main__":
    unittest.main()
