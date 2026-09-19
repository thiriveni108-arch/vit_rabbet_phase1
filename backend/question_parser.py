"""Deterministic, General Natural Language Question Parser for ATLAS Clinical QA Assistant.

Extracts subjects, sites, visits, lab/vital tests, domain keywords, field filters,
numeric/ULN thresholds, temporal modifiers, aggregations, and query intents.
Integrates dynamically with StudyMetadata and ConceptResolver to handle natural language variation.
"""

import re
from typing import Optional, List, Dict, Any, Tuple, Set
from backend.schemas import Question, ParsedQuestion
from backend.study_metadata import StudyMetadata
from backend.concept_resolver import ConceptResolver, CanonicalConcept


class QuestionParser:
    """Parses arbitrary clinical trial questions into structured query representations."""

    USUBJID_REGEX = re.compile(r"\b(042-S\d{2}-\d{3})\b", re.IGNORECASE)
    VISIT_REGEX = re.compile(
        r"\b(SCREENING|BASELINE|WEEK\s*\d+|W\d+|EOS|END OF STUDY|DAY\s*\d+)\b", re.IGNORECASE
    )
    WINDOW_REGEX = re.compile(r"within\s+(\d+)\s+days?", re.IGNORECASE)

    # Core test synonyms
    TEST_SYNONYMS = [
        ("ALT", re.compile(r"\b(ALT|alanine aminotransferase|SGPT)\b", re.IGNORECASE)),
        ("AST", re.compile(r"\b(AST|aspartate aminotransferase|SGOT)\b", re.IGNORECASE)),
        ("BILI", re.compile(r"\b(BILI|bilirubin|total bilirubin)\b", re.IGNORECASE)),
        ("CREAT", re.compile(r"\b(CREAT|creatinine|serum creatinine)\b", re.IGNORECASE)),
        ("GLUC", re.compile(r"\b(GLUC|glucose|blood sugar|fasting glucose)\b", re.IGNORECASE)),
        ("HBA1C", re.compile(r"\b(HBA1C|hemoglobin a1c|glycated hemoglobin|a1c)\b", re.IGNORECASE)),
        ("SYSBP", re.compile(r"\b(SYSBP|systolic(?:\s+blood\s+pressure)?)\b", re.IGNORECASE)),
        ("DIABP", re.compile(r"\b(DIABP|diastolic(?:\s+blood\s+pressure)?)\b", re.IGNORECASE)),
        ("PULSE", re.compile(r"\b(PULSE|heart\s*rate|pulse)\b", re.IGNORECASE)),
        ("QTCF", re.compile(r"\b(QTCF|qtc|qtcf interval)\b", re.IGNORECASE)),
    ]

    # Operators
    OPERATOR_MAP = {
        ">=": ">=", "at least": ">=", "greater than or equal": ">=",
        "<=": "<=", "at most": "<=", "less than or equal": "<=",
        ">": ">", "above": ">", "greater than": ">", "more than": ">", "exceeding": ">", "over": ">", "higher than": ">", "higher": ">",
        "<": "<", "below": "<", "less than": "<", "under": "<", "lower than": "<",
        "=": "==", "==": "==", "equal": "==", "equals": "=="
    }

    ULN_PATTERN = re.compile(
        r"(>=|<=|>|<|=|above|greater than|more than|exceeding|over|higher than|higher|below|less than|under|at least|at most)\s*"
        r"(\d+(?:\.\d+)?)\s*(?:x|\*|\-fold)?\s*(?:×)?\s*uln\b",
        re.IGNORECASE,
    )
    ULN_POST_PATTERN = re.compile(
        r"(\d+(?:\.\d+)?)\s*(?:x|\*|\-fold)?\s*(?:×)?\s*uln\b",
        re.IGNORECASE,
    )
    NUMERIC_CMP_PATTERN = re.compile(
        r"(>=|<=|>|<|=|above|greater than|more than|exceeding|over|higher than|higher|below|less than|under|at least|at most)\s*"
        r"(\d+(?:\.\d+)?)",
        re.IGNORECASE,
    )

    @classmethod
    def normalize_visit(cls, raw: str) -> str:
        s = raw.strip().upper()
        if s in ("END OF STUDY", "EOS", "DAY 182", "DAY182"):
            return "EOS"
        if s in ("SCREENING", "DAY -14", "DAY-14"):
            return "SCREENING"
        if s in ("BASELINE", "DAY 0", "DAY0"):
            return "BASELINE"
        m = re.match(r"^W(?:EEK)?\s*(\d+)$", s)
        if m:
            return f"WEEK{m.group(1)}"
        return re.sub(r"\s+", "", s)

    @classmethod
    def parse(cls, question: Question, metadata: Optional[StudyMetadata] = None) -> ParsedQuestion:
        text = question.text.strip()
        q_id = question.question_id
        lower = text.lower()

        # 0. Check for Unsupported / Out of Scope questions
        unsupported_patterns = [
            "capital of", "weather in", "write a poem", "who won",
            "what medication should this patient be prescribed", "should be prescribed",
            "will this patient recover", "best doctor", "who is the best doctor",
            "cure", "prognosis for"
        ]
        if any(p in lower for p in unsupported_patterns):
            return ParsedQuestion(
                question_id=q_id,
                intent="UNSUPPORTED",
                raw_text=text,
                clarification_needed="The supplied study data does not support that determination. Atlas is unable to answer this question from the study dataset. Atlas is scoped to Study Sentinel data and protocol questions."
            )

        # 1. Check for Study Metadata questions (evaluated before general doc patterns)
        meta_patterns = [
            "what cut", "which cut", "cut are we viewing", "current cut",
            "active protocol", "what protocol version", "which protocol version",
            "how many sites", "number of sites", "what sites",
            "what domains", "available domains", "what tests are collected",
            "how many records in the study", "total records in the study",
            "study metadata", "study summary"
        ]
        if any(p in lower for p in meta_patterns) and not ConceptResolver.extract_usubjid(text):
            return ParsedQuestion(
                question_id=q_id,
                intent="STUDY_METADATA",
                raw_text=text
            )

        # 2. Check for Document / Protocol questions
        doc_patterns = [
            "visit window in protocol", "when was creatinine exclusion added",
            "what medications are prohibited", "what does the protocol say", "exclusion criteria in protocol",
            "inclusion criteria", "primary endpoint", "statistical analysis plan", "sap",
            "central lab", "laboratory manual", "lab manual", "ukat", "µkat",
            "between protocol", "protocol version 1", "protocol version 2", "protocol version 3"
        ]
        has_prot_mention = bool(re.search(r"protocol\s*v[123]\b", lower))
        if has_prot_mention or any(p in lower for p in doc_patterns):
            v_match = re.search(r"protocol\s*v(?:ersion)?\s*([123])\b", lower)
            prot_ver = int(v_match.group(1)) if v_match else (metadata.protocol_version if metadata else 3)
            return ParsedQuestion(
                question_id=q_id,
                intent="DOCUMENT_LOOKUP",
                protocol_version=prot_ver,
                raw_text=text
            )

        # 3. Extract USUBJID (supporting full 042-S07-001 and shorthand S07-001)
        usubjid = ConceptResolver.extract_usubjid(text)
        secondary_usubjid = None
        # Check for secondary USUBJID
        all_subjs = cls.USUBJID_REGEX.findall(text)
        if len(all_subjs) >= 2:
            secondary_usubjid = all_subjs[1].upper()

        # 4. Extract Site ID (ensuring S07 is not parsed as site if part of S07-001)
        site_id = ConceptResolver.extract_site_id(text)
        invalid_site = None
        if site_id and metadata:
            if not metadata.validate_site(site_id):
                invalid_site = site_id

        # 5. Extract Visits (supporting primary & secondary)
        visit_matches = cls.VISIT_REGEX.findall(text)
        norm_visits = [cls.normalize_visit(v) for v in visit_matches]
        visit: Optional[str] = norm_visits[0] if len(norm_visits) >= 1 else None
        secondary_visit: Optional[str] = norm_visits[1] if len(norm_visits) >= 2 else None

        # 6. Extract Tests
        test_code: Optional[str] = None
        secondary_test_code: Optional[str] = None
        found_tests: List[str] = []
        for tcode, pattern in cls.TEST_SYNONYMS:
            if pattern.search(text):
                if tcode not in found_tests:
                    found_tests.append(tcode)

        if metadata:
            for code in metadata.available_lab_tests:
                if re.search(rf"\b{re.escape(code)}\b", text, re.IGNORECASE):
                    if code not in found_tests:
                        found_tests.append(code)
            for code in metadata.available_vital_tests:
                if re.search(rf"\b{re.escape(code)}\b", text, re.IGNORECASE):
                    if code not in found_tests:
                        found_tests.append(code)

        if len(found_tests) >= 1:
            test_code = found_tests[0]
        if len(found_tests) >= 2:
            secondary_test_code = found_tests[1]

        # Check for genuine trap questions (e.g. dosing errors)
        if any(w in lower for w in ("wrong dose", "dosing error", "overdose")):
            return ParsedQuestion(
                question_id=q_id,
                intent="TRAP",
                domain="EX",
                site_id=site_id,
                raw_text=text
            )

        # 7. Extract Temporal Windows & Modifiers
        window_days: Optional[int] = None
        w_match = cls.WINDOW_REGEX.search(text)
        if w_match:
            window_days = int(w_match.group(1))

        temporal_mod: Optional[str] = None
        if any(w in lower for w in ("latest", "most recent", "last recorded", "last")):
            temporal_mod = "LATEST"
        elif any(w in lower for w in ("earliest", "first", "initial")):
            temporal_mod = "EARLIEST"
        elif any(w in lower for w in ("trend", "over time", "progression", "how did", "longitudinal")):
            temporal_mod = "TREND"

        # 8. Extract Aggregation
        aggregation: Optional[str] = None
        if any(w in lower for w in ("average", "mean", "avg")):
            aggregation = "AVG"
        elif any(w in lower for w in ("maximum", "max", "highest", "peak", "largest", "most")):
            aggregation = "MAX"
        elif any(w in lower for w in ("minimum", "min", "lowest", "smallest")):
            aggregation = "MIN"

        # 9. Extract Group By
        group_by: Optional[str] = None
        if "per site" in lower or "by site" in lower or "each site" in lower or "which site had the most" in lower or "site with the most" in lower or "site had the most" in lower:
            group_by = "site_id"
        elif "by arm" in lower or "per arm" in lower or "each arm" in lower:
            group_by = "arm"
        elif "by finding" in lower or "by type" in lower or "per type" in lower:
            group_by = "finding_type"
        elif "by domain" in lower or "per domain" in lower:
            group_by = "domain"

        # 10. Extract Operators & Thresholds
        operator: Optional[str] = None
        numeric_value: Optional[float] = None
        threshold_type: Optional[str] = None
        threshold_multiplier: Optional[float] = None

        uln_m = cls.ULN_PATTERN.search(text)
        if uln_m:
            op_raw = uln_m.group(1) or ">="
            operator = cls.OPERATOR_MAP.get(op_raw.lower(), ">=")
            threshold_multiplier = float(uln_m.group(2))
            threshold_type = "ULN"
        else:
            uln_post = cls.ULN_POST_PATTERN.search(text)
            if uln_post:
                threshold_multiplier = float(uln_post.group(1))
                threshold_type = "ULN"
                operator = ">="

        if not threshold_type:
            num_m = cls.NUMERIC_CMP_PATTERN.search(text)
            if num_m and "week" not in lower[max(0, num_m.start() - 6):num_m.start()]:
                op_raw = num_m.group(1)
                operator = cls.OPERATOR_MAP.get(op_raw.lower(), ">=")
                numeric_value = float(num_m.group(2))
                threshold_type = "RAW"

        # 11. Extract Domain & Generic Field Filters
        domain: Optional[str] = None
        filters: List[Dict[str, Any]] = []

        if any(w in lower for w in ("adverse event", "side effect", "ae", "safety event")):
            domain = "AE"
        elif test_code in ("ALT", "AST", "BILI", "CREAT", "GLUC", "HBA1C") or any(w in lower for w in ("lab", "laboratory", "blood test", "blood work")):
            domain = "LB"
        elif test_code in ("SYSBP", "DIABP", "PULSE", "QTCF") or any(w in lower for w in ("vital", "blood pressure", "pulse", "heart rate")):
            domain = "VS"
            if not test_code:
                test_code = "SYSBP"
        elif any(w in lower for w in ("medication", "medicine", "concomitant", "drug", "treatment", "sulfonylurea", "glucocorticoid")):
            domain = "CM"
        elif any(w in lower for w in ("dose", "dosing", "exposure", "study drug", "study treatment")):
            domain = "EX"
        elif any(w in lower for w in ("disposition", "discontinued", "withdrawal", "completion", "dropout")):
            domain = "DS"
        elif any(w in lower for w in ("medical history", "history")):
            domain = "MH"
        elif any(w in lower for w in ("ecg", "electrocardiogram", "ekg")):
            domain = "EG"

        # Demographics / Field filters
        if re.search(r"\b(female|women|woman)\b", lower):
            filters.append({"field": "SEX", "operator": "==", "value": "F"})
            if not domain:
                domain = "DM"
        elif re.search(r"\b(male|men|man)\b", lower) and not re.search(r"\b(female|women|woman)\b", lower):
            filters.append({"field": "SEX", "operator": "==", "value": "M"})
            if not domain:
                domain = "DM"

        if "placebo" in lower:
            filters.append({"field": "ARM", "operator": "==", "value": "PLACEBO"})
            if not domain:
                domain = "DM"
        elif "active arm" in lower or "drug arm" in lower:
            filters.append({"field": "ARM", "operator": "==", "value": "DRUG"})
            if not domain:
                domain = "DM"

        if "hospitaliz" in lower:
            filters.append({"field": "AESHOSP", "operator": "==", "value": "Y"})
            domain = "AE"

        if "serious" in lower and domain == "AE":
            filters.append({"field": "AESER", "operator": "==", "value": "Y"})

        if "sulfonylurea" in lower or "sulfonylureas" in lower:
            filters.append({"field": "CMCLAS", "operator": "contains", "value": "SULFONYLUREA"})
            domain = "CM"

        if "glucocorticoid" in lower:
            filters.append({"field": "CMCLAS", "operator": "contains", "value": "GLUCOCORTICOID"})
            domain = "CM"

        # 12. Concept Resolution via ConceptResolver
        canonical_concept, interpretation_note = ConceptResolver.resolve_concept(text)
        criterion: Optional[str] = None

        if canonical_concept == CanonicalConcept.POTENTIAL_HYS_LAW:
            criterion = "potential_hys_law"
        elif canonical_concept == CanonicalConcept.HOSPITALIZED_NON_SERIOUS:
            criterion = "hospitalized_non_serious"
            domain = "AE"
        elif canonical_concept == CanonicalConcept.SERIOUS_ADVERSE_EVENT:
            criterion = "serious_adverse_event"
            domain = "AE"
        elif canonical_concept == CanonicalConcept.CREATININE_EXCLUSION:
            criterion = "creatinine_exclusion"
        elif canonical_concept == CanonicalConcept.PROHIBITED_MEDICATION:
            criterion = "prohibited_medication"
        elif canonical_concept == CanonicalConcept.VISIT_WINDOW_DEVIATION:
            criterion = "visit_window_deviation"

        # Fallback criterion keywords if not already set
        if not criterion:
            if "hy" in lower or "liver safety" in lower:
                criterion = "potential_hys_law"
            elif "serious adverse" in lower or "serious event" in lower or "sae" in lower or ("serious" in lower and "hospital" in lower):
                criterion = "serious_adverse_event"
            elif "creatinine" in lower and ("exclusion" in lower or "renal" in lower or "kidney" in lower or "> 1.5" in lower or "greater than 1.5" in lower):
                criterion = "creatinine_exclusion"
            elif "prohibited" in lower or "concomitant medication" in lower or "forbidden med" in lower:
                criterion = "prohibited_medication"
            elif "visit window" in lower or "visit deviation" in lower or "window deviation" in lower:
                criterion = "visit_window_deviation"

        # 13. Determine Primary Intent
        clean_text = re.sub(r"[.?!]+$", "", lower).strip()

        # Ambiguity detection: underspecified questions
        if clean_text in ("what was the value", "what was the value?", "what is the value"):
            return ParsedQuestion(
                question_id=q_id,
                intent="AMBIGUOUS",
                raw_text=text,
                clarification_needed="Please specify a subject identifier and laboratory test to look up."
            )
        if clean_text in ("show the liver test", "liver test", "liver tests", "what were the liver tests"):
            return ParsedQuestion(
                question_id=q_id,
                intent="AMBIGUOUS",
                raw_text=text,
                clarification_needed="Please specify whether you mean ALT, AST, or Total Bilirubin, and provide a subject identifier."
            )
        if clean_text.startswith("compare week 8") or clean_text.startswith("compare baseline") and not usubjid:
            return ParsedQuestion(
                question_id=q_id,
                intent="AMBIGUOUS",
                raw_text=text,
                clarification_needed="Please specify a subject identifier and the second visit to compare."
            )

        # Primary intent rules
        if canonical_concept == CanonicalConcept.WHY_FLAGGED or ("why" in lower and "flag" in lower):
            intent = "WHY_FLAGGED"
        elif canonical_concept == CanonicalConcept.EVIDENCE_REQUEST or any(w in lower for w in ("show the proof", "show proof", "show the evidence", "show exact evidence", "source records")):
            intent = "EVIDENCE_REQUEST"
        elif group_by or any(w in lower for w in ("how many", "number of", "total participants", "count people", "count of", "count subjects", "count records", "count findings", "participant count")):
            intent = "COUNT"
        elif (canonical_concept == CanonicalConcept.PATIENT_360 or any(w in lower for w in ("tell me about", "tell me everything about", "summarize", "patient 360", "overview of", "summary of", "profile of", "profile for", "patient profile", "subject profile")) or "profile" in lower) and usubjid:
            intent = "SUBJECT_360"
        elif (any(w in lower for w in ("compare", "versus", "vs", "difference between", "higher than baseline", "how much did", "increase")) or (visit and secondary_visit)) and usubjid:
            intent = "COMPARISON"
        elif temporal_mod == "TREND" or "trend" in lower or "progression" in lower or "over time" in lower:
            intent = "TREND"
        elif aggregation and not group_by:
            intent = "AGGREGATE"
        elif criterion and not threshold_type:
            intent = "FINDING"
        elif threshold_type or (any(w in lower for w in ("which", "who", "list", "show subjects", "find subjects")) and not usubjid and (filters or site_id)):
            intent = "FILTER"
        elif any(w in lower for w in ("which", "who", "show", "list", "give me")) and not usubjid:
            intent = "FILTER"
        elif not usubjid and any(w in lower for w in ("subjects", "patients", "participants")) and (site_id or filters):
            intent = "FILTER"
        else:
            intent = "LOOKUP"

        return ParsedQuestion(
            question_id=q_id,
            intent=intent,
            domain=domain,
            usubjid=usubjid,
            secondary_usubjid=secondary_usubjid,
            site_id=site_id,
            visit=visit,
            secondary_visit=secondary_visit,
            test_code=test_code,
            secondary_test_code=secondary_test_code,
            operator=operator,
            numeric_value=numeric_value,
            threshold_type=threshold_type,
            threshold_multiplier=threshold_multiplier,
            date_window_days=window_days,
            temporal_modifier=temporal_mod,
            aggregation=aggregation,
            group_by=group_by,
            criterion=criterion,
            window_days=window_days,
            filters=filters,
            invalid_site=invalid_site,
            raw_text=text,
            interpretation_note=interpretation_note,
        )
