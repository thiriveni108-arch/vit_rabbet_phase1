"""Three-Tier Query Router and Mixed Query Identifier for ATLAS Assistant.

Categorizes inbound queries into:
1. STUDY_DATA: Direct queries against study records, subjects, visits, labs, vitals,
   or findings (Executed strictly via StudyGraph).
2. STUDY_KNOWLEDGE: Direct queries about protocol amendments, SAP, inclusion/exclusion rules,
   or lab manuals (Executed strictly via DocumentKnowledge).
3. GENERAL: Explanatory and background questions (clinical trial definitions, general Hy's Law,
   biomarker explanations, or external knowledge).
4. MIXED: Multi-part queries combining general explanation with a study-specific data check.
"""

import re
from enum import Enum
from typing import Dict, Any, Tuple, Optional
from backend.concept_resolver import ConceptResolver, CanonicalConcept


class QueryCategory(str, Enum):
    STUDY_DATA = "STUDY_DATA"
    STUDY_KNOWLEDGE = "STUDY_KNOWLEDGE"
    GENERAL = "GENERAL"
    MIXED = "MIXED"


class QueryRouter:
    """Routes natural language queries to their appropriate architectural subsystem."""

    # Protocol & Document patterns (STUDY_KNOWLEDGE)
    DOC_PATTERNS = [
        re.compile(r"\b(?:protocol|sap|lab\s+manual|laboratory\s+manual)\b", re.IGNORECASE),
        re.compile(r"\bwhat\s+does\s+the\s+protocol\s+say\b", re.IGNORECASE),
        re.compile(r"\bwhat\s+changed\s+in\s+protocol\b", re.IGNORECASE),
        re.compile(r"\bbetween\s+protocol\b", re.IGNORECASE),
        re.compile(r"\bvisit\s+window\s+in\s+(?:protocol|v\d+)\b", re.IGNORECASE),
        re.compile(r"\bwhen\s+was\s+.*added\b", re.IGNORECASE),
        re.compile(r"\binclusion\s+criteria\b", re.IGNORECASE),
        re.compile(r"\bprimary\s+endpoint\b", re.IGNORECASE),
        re.compile(r"\bwhat\s+unit\s+does\s+s\d+\s+use\b", re.IGNORECASE),
        re.compile(r"\bprotocol\s+v[123]\b", re.IGNORECASE),
    ]

    # General concept explanation patterns (GENERAL)
    GENERAL_CONCEPT_PATTERNS = [
        re.compile(r"^what\s+is\s+a\s+clinical\s+trial\??$", re.IGNORECASE),
        re.compile(r"^what\s+is\s+hy'?s\s+law(?:\s+generally)?\??$", re.IGNORECASE),
        re.compile(r"^what\s+does\s+alt\s+mean\??$", re.IGNORECASE),
        re.compile(r"^what\s+is\s+alt\??$", re.IGNORECASE),
        re.compile(r"^what\s+is\s+ast\??$", re.IGNORECASE),
        re.compile(r"^what\s+is\s+bilirubin\??$", re.IGNORECASE),
        re.compile(r"^what\s+is\s+an?\s+adverse\s+event\??$", re.IGNORECASE),
        re.compile(r"^what\s+is\s+an?\s+sae\??$", re.IGNORECASE),
        re.compile(r"^what\s+is\s+creatinine\??$", re.IGNORECASE),
        re.compile(r"^explain\s+hy'?s\s+law\??$", re.IGNORECASE),
    ]

    # General out-of-scope non-clinical patterns (routed to GENERAL / external LLM)
    OUT_OF_SCOPE_PATTERNS = [
        re.compile(r"\bpresident\s+of\b", re.IGNORECASE),
        re.compile(r"\bwho\s+is\s+the\s+president\b", re.IGNORECASE),
        re.compile(r"\bprime\s+minister\b", re.IGNORECASE),
    ]

    # Mixed query indicators (combines general concept + study specific check)
    MIXED_PATTERNS = [
        re.compile(r"what\s+is\s+hy'?s\s+law\s+and\s+(?:do|does|are|did|have)", re.IGNORECASE),
        re.compile(r"what\s+is\s+.*and\s+(?:do|does|are|did|have)\s+any\s+(?:subjects?|patients?|people)\s+(?:in\s+this\s+study|meet)", re.IGNORECASE),
        re.compile(r"explain\s+.*and\s+(?:check|show|tell|see)\s+(?:if|whether|who)", re.IGNORECASE),
    ]

    @classmethod
    def route(cls, text: str) -> Tuple[QueryCategory, Optional[Dict[str, Any]]]:
        """Routes text into QueryCategory with optional decomposition metadata.
        Returns: (category, metadata)
        """
        clean_text = text.strip()
        lower = clean_text.lower()

        # 1. Check for MIXED queries
        for p in cls.MIXED_PATTERNS:
            if p.search(lower):
                # Extract general concept query part and study part
                # e.g. "What is Hy's Law and does anyone in our study meet it?"
                split_m = re.split(r"\s+and\s+", clean_text, maxsplit=1, flags=re.IGNORECASE)
                general_part = split_m[0] if len(split_m) > 0 else clean_text
                study_part = split_m[1] if len(split_m) > 1 else clean_text
                return QueryCategory.MIXED, {
                    "general_query": general_part,
                    "study_query": study_part,
                }

        # 2. Check for explicit DOCUMENT / PROTOCOL questions (STUDY_KNOWLEDGE)
        # Note: Must ensure it's not a study data lookup like "Show visit window deviations for S07"
        has_doc_phrase = any(p.search(lower) for p in cls.DOC_PATTERNS)
        usubjid = ConceptResolver.extract_usubjid(clean_text)
        if has_doc_phrase and not usubjid and "deviations" not in lower and "violations" not in lower:
            return QueryCategory.STUDY_KNOWLEDGE, None

        # 3. Check for standalone GENERAL concept questions
        for p in cls.GENERAL_CONCEPT_PATTERNS:
            if p.search(clean_text):
                return QueryCategory.GENERAL, {"type": "clinical_concept"}

        # 4. Check for arbitrary out-of-scope non-clinical questions
        for p in cls.OUT_OF_SCOPE_PATTERNS:
            if p.search(lower):
                return QueryCategory.GENERAL, {"type": "out_of_scope"}

        # 5. Otherwise, the question queries clinical study data
        return QueryCategory.STUDY_DATA, None
