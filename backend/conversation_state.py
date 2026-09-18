"""Conversational context manager for ATLAS Clinical QA Assistant.

Maintains small, short-term conversational references:
    - last_subject
    - last_site
    - last_test
    - last_visit
    - last_domain
    - last_finding
    - last_operation

CRITICAL RULE:
Never stores clinical conclusions as truth.
Only stores conversational entity references to enable follow-ups.
Every follow-up always queries StudyGraph freshly.
"""

from typing import Optional, Dict, Any
from backend.schemas import ParsedQuestion


class ConversationState:
    """Manages short-term conversation context for resolving anaphora and follow-up queries."""

    def __init__(self):
        self.last_subject: Optional[str] = None
        self.last_site: Optional[str] = None
        self.last_test: Optional[str] = None
        self.last_visit: Optional[str] = None
        self.last_domain: Optional[str] = None
        self.last_finding: Optional[str] = None
        self.last_operation: Optional[str] = None

    def update(self, parsed_q: ParsedQuestion) -> None:
        """Updates conversational references from the latest parsed question."""
        if parsed_q.usubjid:
            self.last_subject = parsed_q.usubjid
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

    def apply_context(self, parsed_q: ParsedQuestion, raw_text: str) -> ParsedQuestion:
        """Injects retained conversational context into a follow-up query if entities are omitted."""
        lower = raw_text.lower().strip()

        # Check if question is an explicit population or standalone query
        is_population_query = any(lower.startswith(p) for p in (
            "which subjects", "which patients", "who had", "who has", "who meets",
            "how many", "list subjects", "show subjects", "find subjects", "count",
            "participant count", "number of", "what is the average", "average ", "mean "
        ))
        has_all_or_plural = any(w in lower for w in ("all subjects", "all patients", "per site", "by site", "by arm", "by type"))
        has_site_only = (parsed_q.site_id is not None and not any(w in lower for w in ("their", "this", "his", "her", "that")))

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
            (not parsed_q.usubjid and self.last_subject and ("adverse event" in lower or "medication" in lower or "lab" in lower or "vitals" in lower or "dose" in lower) and any(w in lower for w in ("show", "give", "list", "their", "more", "now"))),
            (not parsed_q.usubjid and self.last_subject and parsed_q.visit and not parsed_q.test_code and self.last_test),
            (not parsed_q.usubjid and self.last_subject and (lower.startswith("what was") or lower.startswith("what is")) and (parsed_q.visit or "latest" in lower or "earliest" in lower or "baseline" in lower)),
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
            if parsed_q.visit or "compare" in lower or "trend" in lower:
                parsed_q.test_code = self.last_test
                if not parsed_q.domain:
                    parsed_q.domain = self.last_domain or "LB"

        # If comparing with baseline / another visit, and primary visit is already last_visit
        if "compare" in lower and parsed_q.visit and not parsed_q.secondary_visit and self.last_visit:
            if parsed_q.visit != self.last_visit:
                parsed_q.secondary_visit = parsed_q.visit
                parsed_q.visit = self.last_visit

        # If subject was injected and query was classified as FILTER/LIST, switch to LOOKUP
        if parsed_q.usubjid and parsed_q.intent in ("FILTER", "LIST"):
            parsed_q.intent = "LOOKUP"

        return parsed_q

    def reset(self) -> None:
        """Clears all conversation state."""
        self.last_subject = None
        self.last_site = None
        self.last_test = None
        self.last_visit = None
        self.last_domain = None
        self.last_finding = None
        self.last_operation = None
