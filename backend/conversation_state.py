"""Conversational context manager for ATLAS Clinical QA Assistant.

Maintains small, short-term conversational references:
    - last_subject (e.g. '042-S07-001')
    - last_subjects_list (e.g. ['042-S05-003', '042-S07-001', '042-S08-014'])
    - last_site (e.g. 'S07')
    - last_test (e.g. 'ALT')
    - last_visit (e.g. 'WEEK8')
    - last_domain (e.g. 'LB')
    - last_finding (e.g. 'potential_hys_law')
    - last_operation (e.g. 'FINDING')

CRITICAL ARCHITECTURAL RULE:
Never stores clinical conclusions as truth.
Only stores conversational entity references to enable follow-ups and anaphora resolution.
Every follow-up always queries StudyGraph freshly.
"""

from typing import Optional, Dict, Any, List
import re
from backend.schemas import ParsedQuestion
from backend.concept_resolver import ConceptResolver, CanonicalConcept


class ConversationState:
    """Manages short-term conversation context for resolving anaphora and follow-up queries."""

    def __init__(self):
        self.last_subject: Optional[str] = None
        self.last_subjects_list: List[str] = []
        self.last_site: Optional[str] = None
        self.last_test: Optional[str] = None
        self.last_visit: Optional[str] = None
        self.last_domain: Optional[str] = None
        self.last_finding: Optional[str] = None
        self.last_operation: Optional[str] = None

    def update(self, parsed_q: ParsedQuestion, result_subjects: Optional[List[str]] = None) -> None:
        """Updates conversational references from the latest parsed question and returned subject IDs."""
        if parsed_q.usubjid:
            self.last_subject = parsed_q.usubjid
            # If subject has a site component, record site
            m = re.match(r"^042-(S\d{2})-\d{3}$", parsed_q.usubjid)
            if m:
                self.last_site = m.group(1)

        if parsed_q.site_id:
            self.last_site = parsed_q.site_id

        if parsed_q.test_code:
            self.last_test = parsed_q.test_code

        if parsed_q.visit:
            self.last_visit = parsed_q.visit

        if parsed_q.domain:
            self.last_domain = parsed_q.domain

        if parsed_q.criterion:
            self.last_finding = parsed_q.criterion

        if parsed_q.intent:
            self.last_operation = parsed_q.intent

        if result_subjects:
            self.last_subjects_list = list(result_subjects)
            if not self.last_subject and len(result_subjects) == 1:
                self.last_subject = result_subjects[0]

    def apply_context(self, parsed_q: ParsedQuestion, raw_text: str) -> ParsedQuestion:
        """Injects retained conversational context into a follow-up query if entities are omitted."""
        lower = raw_text.lower().strip()

        # Check for explicit population queries that should NOT inherit a single subject
        is_population_query = any(lower.startswith(p) for p in (
            "which subjects", "which patients", "who had", "who has", "who meets",
            "how many", "list subjects", "show subjects", "find subjects", "count",
            "participant count", "number of", "what is the average", "average ", "mean "
        ))
        has_all_or_plural = any(w in lower for w in ("all subjects", "all patients", "per site", "by site", "by arm", "by type"))

        # Check for Proof / Evidence request ("Show the proof", "Show exact evidence")
        is_evidence_req = (
            parsed_q.intent == "EVIDENCE_REQUEST" or
            any(w in lower for w in ("show the proof", "show proof", "show the evidence", "show evidence", "show exact evidence", "exact source records"))
        )
        if is_evidence_req:
            parsed_q.intent = "EVIDENCE_REQUEST"
            if not parsed_q.usubjid and self.last_subject:
                parsed_q.usubjid = self.last_subject
            if not parsed_q.criterion and self.last_finding:
                parsed_q.criterion = self.last_finding
            return parsed_q

        # Check for "Why was S07 flagged?" or "Why was this patient flagged?"
        if parsed_q.intent == "WHY_FLAGGED" or "why" in lower and "flag" in lower:
            parsed_q.intent = "WHY_FLAGGED"
            # If no usubjid parsed, but site S07 was mentioned:
            if not parsed_q.usubjid:
                # Check if site matches a subject in last_subjects_list or last_subject
                if parsed_q.site_id:
                    target_site = parsed_q.site_id
                    matched_subjs = [s for s in self.last_subjects_list if f"-{target_site}-" in s]
                    if matched_subjs:
                        parsed_q.usubjid = matched_subjs[0]
                    elif self.last_subject and f"-{target_site}-" in self.last_subject:
                        parsed_q.usubjid = self.last_subject
                elif self.last_subject:
                    parsed_q.usubjid = self.last_subject

            if not parsed_q.criterion and self.last_finding:
                parsed_q.criterion = self.last_finding
            return parsed_q

        # Standalone site query check:
        # If user asked e.g. "How many subjects at S07?" or "Show records at S07"
        has_site_only = (
            parsed_q.site_id is not None and
            not parsed_q.usubjid and
            not any(w in lower for w in ("their", "this", "his", "her", "that", "why", "flag"))
        )
        if is_population_query or has_all_or_plural or has_site_only:
            return parsed_q

        # Follow-up indicators
        is_follow_up = any([
            lower.startswith("what about"),
            lower.startswith("how about"),
            lower.startswith("now "),
            lower.startswith("and "),
            "their" in lower,
            "this patient" in lower or "this subject" in lower,
            "for this patient" in lower or "for this subject" in lower,
            "compare it" in lower or "compare with" in lower,
            "was bilirubin also elevated" in lower,
            "was alt higher" in lower,
            "how much did alt increase" in lower,
            "how much did it increase" in lower,
            (not parsed_q.usubjid and self.last_subject and ("adverse event" in lower or "medication" in lower or "lab" in lower or "vitals" in lower or "dose" in lower) and any(w in lower for w in ("show", "give", "list", "their", "more", "now"))),
            (not parsed_q.usubjid and self.last_subject and parsed_q.visit and not parsed_q.test_code and self.last_test),
            (not parsed_q.usubjid and self.last_subject and (lower.startswith("what was") or lower.startswith("what is")) and (parsed_q.visit or "latest" in lower or "earliest" in lower or "baseline" in lower)),
            (not parsed_q.usubjid and self.last_subject and parsed_q.test_code and parsed_q.visit),
        ])

        if not is_follow_up:
            return parsed_q

        # Inject retained subject if missing
        if not parsed_q.usubjid and self.last_subject:
            parsed_q.usubjid = self.last_subject

        # Inject retained site if missing and no subject
        if not parsed_q.site_id and not parsed_q.usubjid and self.last_site:
            parsed_q.site_id = self.last_site

        # Inject retained test code if query provides a visit or comparison without test
        if not parsed_q.test_code and self.last_test:
            if parsed_q.visit or "compare" in lower or "trend" in lower or "increase" in lower or "higher" in lower:
                parsed_q.test_code = self.last_test
                if not parsed_q.domain:
                    parsed_q.domain = self.last_domain or "LB"

        # If question asks about bilirubin also ("was bilirubin also elevated?")
        if "bilirubin" in lower and not parsed_q.visit and self.last_visit:
            parsed_q.visit = self.last_visit

        # If comparing with baseline / another visit, and primary visit is already last_visit
        if ("compare" in lower or "higher" in lower or "increase" in lower) and parsed_q.visit and not parsed_q.secondary_visit and self.last_visit:
            if parsed_q.visit != self.last_visit:
                parsed_q.secondary_visit = parsed_q.visit
                parsed_q.visit = self.last_visit

        # If subject was injected and query was classified as FILTER/LIST, switch to LOOKUP
        if parsed_q.usubjid and parsed_q.intent in ("FILTER", "LIST"):
            parsed_q.intent = "LOOKUP"

        return parsed_q

    def reset(self) -> None:
        """Clears all short-term conversation state."""
        self.last_subject = None
        self.last_subjects_list = []
        self.last_site = None
        self.last_test = None
        self.last_visit = None
        self.last_domain = None
        self.last_finding = None
        self.last_operation = None
