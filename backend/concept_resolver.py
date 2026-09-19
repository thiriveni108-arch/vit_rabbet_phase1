"""Concept Resolver and Canonical Synonym Registry for ATLAS Conversational Assistant.

Translates natural language clinical questions, colloquial expressions, and aliases
into canonical study concepts and entities.

Strict Principle:
Language understanding only. Never calculates or manufactures clinical findings.
Clinical truth is determined exclusively by StudyGraph and official study documents.
"""

import re
from typing import Optional, Dict, Any, List, Tuple


class CanonicalConcept:
    POTENTIAL_HYS_LAW = "POTENTIAL_HYS_LAW"
    SERIOUS_ADVERSE_EVENT = "SERIOUS_ADVERSE_EVENT"
    HOSPITALIZED_NON_SERIOUS = "HOSPITALIZED_NON_SERIOUS"
    CREATININE_EXCLUSION = "CREATININE_EXCLUSION"
    PROHIBITED_MEDICATION = "PROHIBITED_MEDICATION"
    VISIT_WINDOW_DEVIATION = "VISIT_WINDOW_DEVIATION"
    PATIENT_360 = "PATIENT_360"
    WHY_FLAGGED = "WHY_FLAGGED"
    EVIDENCE_REQUEST = "EVIDENCE_REQUEST"
    LAB_LOOKUP = "LAB_LOOKUP"
    SITE_QUERY = "SITE_QUERY"
    GENERAL_KNOWLEDGE = "GENERAL_KNOWLEDGE"
    OUT_OF_SCOPE_GENERAL = "OUT_OF_SCOPE_GENERAL"


class ConceptResolver:
    """Centralized clinical concept and entity resolution engine."""

    # Full and Shorthand Subject Identifiers
    FULL_USUBJID_REGEX = re.compile(r"\b(042-S\d{2}-\d{3})\b", re.IGNORECASE)
    SHORTHAND_USUBJID_REGEX = re.compile(r"\b(S\d{2}-\d{3})\b", re.IGNORECASE)

    # Site Regex (ensures not part of a subject ID like S07-001)
    SITE_EXPLICIT_REGEX = re.compile(r"\bsite\s+(S\d{2})\b", re.IGNORECASE)
    SITE_NUMERIC_REGEX = re.compile(r"\bsite\s+(\d{1,2})\b", re.IGNORECASE)
    STANDALONE_SITE_REGEX = re.compile(r"\b(S\d{2})\b(?!-\d{3})", re.IGNORECASE)

    # Synonyms for POTENTIAL_HYS_LAW
    HYS_LAW_EXACT_SYNONYMS = [
        "hy's law", "hys law", "potential hy's law", "potential hys law",
        "liver safety signal", "potential liver injury", "potential liver safety signal",
        "liver injury pattern", "hepatic injury", "hepatic safety signal", "liver signal",
        "alt and bilirubin elevation", "subjects with high alt and bilirubin",
        "possible drug induced liver injury", "possible dili pattern", "dili signal",
        "potential liver signal", "elevated alt and bilirubin", "high alt with bilirubin",
        "liver-safety signal", "liver safety", "hepatic signal", "dili pattern",
        "liver-related findings", "liver related findings", "liver findings",
        "liver-related finding", "liver related finding", "liver finding",
        "hepatic findings", "hepatic finding", "liver safety findings"
    ]

    # Broad phrases requiring explicit interpretation statement
    BROAD_PHRASE_INTERPRETATIONS: List[Tuple[re.Pattern, str, str]] = [
        (
            re.compile(r"\b(liver\s+problems?|liver\s+issues?|bad\s+liver|trouble\s+with\s+liver)\b", re.IGNORECASE),
            CanonicalConcept.POTENTIAL_HYS_LAW,
            "I interpreted 'liver problems' as the study's potential liver-safety / Hy's Law biochemical findings."
        ),
        (
            re.compile(r"\b(kidney\s+problems?|renal\s+problems?|kidney\s+issues?|renal\s+issues?|kidney\s+function\s+problem)\b", re.IGNORECASE),
            CanonicalConcept.CREATININE_EXCLUSION,
            "I interpreted 'kidney problems' as the study's screening creatinine exclusion criteria (> 1.5 mg/dL)."
        ),
        (
            re.compile(r"\b(dangerous\s+side\s+effects?|dangerous\s+adverse\s+events?|severe\s+reactions?)\b", re.IGNORECASE),
            CanonicalConcept.SERIOUS_ADVERSE_EVENT,
            "I interpreted 'dangerous side effects' as serious adverse events (SAEs) defined by protocol §6."
        )
    ]

    # SERIOUS ADVERSE EVENT synonyms
    SAE_SYNONYMS = [
        "serious ae", "serious adverse event", "serious adverse events", "serious aes",
        "hospitalized event", "hospitalized adverse event", "hospitalisation", "hospitalization",
        "sae", "saes", "serious side effect", "serious side effects", "who was hospitalized",
        "patients hospitalized", "subjects hospitalized", "adverse events requiring hospitalization"
    ]

    # Special query: Hospitalized but entered as non-serious (AESHOSP=Y / AESER=N)
    HOSPITALIZED_NON_SERIOUS_PATTERNS = [
        re.compile(r"hospitalized\s+but\s+(?:entered|coded|marked|reported)\s+as\s+non-?serious", re.IGNORECASE),
        re.compile(r"hospitalized\s+non-?serious", re.IGNORECASE),
        re.compile(r"hospitalization\s+override", re.IGNORECASE),
        re.compile(r"aeshosp\s*=\s*y.*aeser\s*=\s*n", re.IGNORECASE),
        re.compile(r"non-?serious\s+but\s+hospitalized", re.IGNORECASE),
    ]

    # CREATININE / RENAL EXCLUSION synonyms
    CREATININE_SYNONYMS = [
        "high creatinine", "renal exclusion", "kidney exclusion", "renal issue",
        "kidney function problem", "creatinine exclusion", "creatinine violation",
        "screening creatinine", "creatinine > 1.5", "creatinine over 1.5",
        "renal exclusion violations", "renal impairment exclusion"
    ]

    # PROHIBITED MEDICATION synonyms
    PROHIBITED_MED_SYNONYMS = [
        "prohibited medication", "prohibited medications", "banned medication",
        "banned medications", "not allowed medicine", "not allowed medicines",
        "disallowed drug", "disallowed drugs", "protocol prohibited drug",
        "prohibited concomitant medication", "prohibited concomitant medications",
        "medicines they were not allowed to take", "drugs they were not allowed to take",
        "forbidden meds", "forbidden medication", "prohibited drugs", "prohibited meds"
    ]

    # VISIT WINDOW DEVIATION synonyms
    VISIT_WINDOW_SYNONYMS = [
        "late visit", "early visit", "visit outside window", "visit deviation",
        "visit deviations", "missed visit timing", "protocol visit timing",
        "outside the allowed window", "outside visit window", "visit window violation",
        "visit window deviations", "visit window deviation", "window deviation"
    ]

    # PATIENT 360 synonyms
    PATIENT_360_SYNONYMS = [
        "summarize this patient", "tell me everything about", "what happened to",
        "patient history", "subject overview", "patient journey", "summarize subject",
        "patient 360", "subject 360", "tell me about subject", "overview of",
        "patient profile", "subject profile", "profile of"
    ]

    # WHY FLAGGED synonyms
    WHY_FLAGGED_PATTERNS = [
        re.compile(r"why\s+(?:was|did)\s+(?:atlas\s+)?(?:flag|flagged|identify)\b", re.IGNORECASE),
        re.compile(r"why\s+flagged\b", re.IGNORECASE),
        re.compile(r"what\s+caused\s+(?:this\s+)?flag\b", re.IGNORECASE),
        re.compile(r"reason\s+for\s+flag\b", re.IGNORECASE),
        re.compile(r"why\s+was\s+.*flagged\b", re.IGNORECASE),
    ]

    # EVIDENCE / PROOF REQUEST synonyms
    EVIDENCE_REQUEST_PATTERNS = [
        re.compile(r"\bshow\s+(?:the\s+)?proof\b", re.IGNORECASE),
        re.compile(r"\bshow\s+(?:the\s+)?evidence\b", re.IGNORECASE),
        re.compile(r"\bshow\s+exact\s+evidence\b", re.IGNORECASE),
        re.compile(r"\bshow\s+(?:the\s+)?exact\s+source\s+records\b", re.IGNORECASE),
        re.compile(r"\bgive\s+me\s+the\s+proof\b", re.IGNORECASE),
        re.compile(r"\bproof\s+for\s+this\b", re.IGNORECASE),
        re.compile(r"\bview\s+evidence\b", re.IGNORECASE),
    ]

    @classmethod
    def extract_usubjid(cls, text: str) -> Optional[str]:
        """Extracts USUBJID, supporting both standard 042-S07-001 and shorthand S07-001."""
        full_match = cls.FULL_USUBJID_REGEX.search(text)
        if full_match:
            return full_match.group(1).upper()

        shorthand_match = cls.SHORTHAND_USUBJID_REGEX.search(text)
        if shorthand_match:
            raw = shorthand_match.group(1).upper()
            return f"042-{raw}"

        return None

    @classmethod
    def extract_site_id(cls, text: str) -> Optional[str]:
        """Extracts Site ID (e.g. S07), ensuring it is not mistaken for a subject shorthand."""
        # 1. Explicit 'site S07'
        m = cls.SITE_EXPLICIT_REGEX.search(text)
        if m:
            return m.group(1).upper()

        # 2. 'site 7' -> 'S07'
        m_num = cls.SITE_NUMERIC_REGEX.search(text)
        if m_num:
            return f"S{int(m_num.group(1)):02d}"

        # 3. Standalone 'S07' without trailing '-001'
        m_stand = cls.STANDALONE_SITE_REGEX.search(text)
        if m_stand:
            return m_stand.group(1).upper()

        return None

    @classmethod
    def resolve_concept(cls, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Resolves raw text to a canonical concept and an optional interpretation note.
        Returns: (canonical_concept, interpretation_statement)
        """
        lower = text.lower().strip()

        # Check hospitalized non-serious query first (specific SAE subclass)
        for pattern in cls.HOSPITALIZED_NON_SERIOUS_PATTERNS:
            if pattern.search(lower):
                return CanonicalConcept.HOSPITALIZED_NON_SERIOUS, None

        # Check broad phrases requiring explicit interpretation notice
        for pattern, concept, statement in cls.BROAD_PHRASE_INTERPRETATIONS:
            if pattern.search(lower):
                return concept, statement

        # Check exact / specific Hy's Law synonyms
        for s in cls.HYS_LAW_EXACT_SYNONYMS:
            if s in lower:
                return CanonicalConcept.POTENTIAL_HYS_LAW, None

        # Check Why Flagged
        for pattern in cls.WHY_FLAGGED_PATTERNS:
            if pattern.search(lower):
                return CanonicalConcept.WHY_FLAGGED, None

        # Check Proof / Evidence request
        for pattern in cls.EVIDENCE_REQUEST_PATTERNS:
            if pattern.search(lower):
                return CanonicalConcept.EVIDENCE_REQUEST, None

        # Check SAE
        for s in cls.SAE_SYNONYMS:
            if s in lower:
                return CanonicalConcept.SERIOUS_ADVERSE_EVENT, None

        # Check Creatinine / Renal
        for s in cls.CREATININE_SYNONYMS:
            if s in lower:
                return CanonicalConcept.CREATININE_EXCLUSION, None

        # Check Prohibited Meds
        for s in cls.PROHIBITED_MED_SYNONYMS:
            if s in lower:
                return CanonicalConcept.PROHIBITED_MEDICATION, None

        # Check Visit Window
        for s in cls.VISIT_WINDOW_SYNONYMS:
            if s in lower:
                return CanonicalConcept.VISIT_WINDOW_DEVIATION, None

        # Check Patient 360
        for s in cls.PATIENT_360_SYNONYMS:
            if s in lower:
                return CanonicalConcept.PATIENT_360, None

        return None, None
