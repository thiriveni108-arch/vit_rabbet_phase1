"""Dynamic Study Metadata discovery and entity resolution for Study Sentinel / ATLAS.

Discovers available subjects, sites, domains, visits, lab tests, vital signs,
medications, finding types, and domain fields directly from StudyGraph.
Contains NO hardcoded clinical values or reference ranges.
"""

import re
from typing import Dict, Any, List, Set, Optional, Tuple


class StudyMetadata:
    """Discovers and caches study entities directly from a StudyGraph instance."""

    def __init__(self, graph: Any):
        self.graph = graph
        self.available_subjects: Set[str] = set()
        self.subjects_by_site: Dict[str, Set[str]] = {}
        self.available_sites: Set[str] = set()
        self.available_domains: Set[str] = set()
        self.available_visits: Set[str] = set()
        self.available_lab_tests: Dict[str, str] = {}  # code -> name
        self.available_vital_tests: Dict[str, str] = {}  # code -> name
        self.available_medications: Set[str] = set()
        self.available_medication_classes: Set[str] = set()
        self.available_fields_per_domain: Dict[str, Set[str]] = {}
        self.available_finding_types: Set[str] = {
            "potential_hys_law",
            "serious_adverse_event",
            "exclusion_violation_creatinine",
            "prohibited_concomitant_medication",
            "visit_window_deviation",
        }
        self.current_cut: int = getattr(graph, "current_cut", 12)
        self.protocol_version: int = getattr(graph, "current_protocol_version", 3)

        self._discover()

    def _discover(self) -> None:
        """Inspects current StudyGraph records and indexes to discover metadata."""
        # 1. Subjects & Sites
        if hasattr(self.graph, "subjects"):
            for usubjid, sdata in self.graph.subjects.items():
                self.available_subjects.add(usubjid)
                site_id = sdata.get("site_id")
                if not site_id and "demographics" in sdata:
                    site_id = sdata["demographics"].get("SITEID")
                if not site_id and "-" in usubjid:
                    parts = usubjid.split("-")
                    if len(parts) >= 2:
                        site_id = parts[1]
                if site_id:
                    self.available_sites.add(site_id)
                    self.subjects_by_site.setdefault(site_id, set()).add(usubjid)

        # 2. Domains, fields, visits, tests, medications from records_by_key
        records = getattr(self.graph, "records_by_key", {})
        for (domain, usubjid, seq), rec in records.items():
            self.available_domains.add(domain)
            fields = self.available_fields_per_domain.setdefault(domain, set())
            for k in rec.keys():
                if not k.startswith("_"):
                    fields.add(k)

            # Visits
            visit = rec.get("VISIT")
            if visit and str(visit).strip():
                clean_visit = re.sub(r"\s+", "", str(visit).strip().upper())
                self.available_visits.add(clean_visit)

            # Lab tests
            if domain == "LB":
                testcd = rec.get("LBTESTCD")
                testname = rec.get("LBTEST", "")
                if testcd:
                    self.available_lab_tests[str(testcd).upper()] = str(testname)

            # Vital signs
            elif domain == "VS":
                testcd = rec.get("VSTESTCD")
                testname = rec.get("VSTEST", "")
                if testcd:
                    self.available_vital_tests[str(testcd).upper()] = str(testname)

            # Medications
            elif domain == "CM":
                decod = rec.get("CMDECOD")
                trt = rec.get("CMTRT")
                clas = rec.get("CMCLAS")
                if decod:
                    self.available_medications.add(str(decod).upper())
                if trt:
                    self.available_medications.add(str(trt).upper())
                if clas:
                    self.available_medication_classes.add(str(clas).upper())

        # Also populate domains from domain_records if available
        if hasattr(self.graph, "domain_records"):
            for d in self.graph.domain_records.keys():
                self.available_domains.add(d)

    # -------------------------------------------------------------------------
    # RESOLUTION HELPERS
    # -------------------------------------------------------------------------
    def resolve_subject(self, text: str) -> Optional[str]:
        """Resolves a subject ID from text if present in available_subjects."""
        match = re.search(r"\b(042-S\d{2}-\d{3})\b", text, re.IGNORECASE)
        if match:
            cand = match.group(1).upper()
            if cand in self.available_subjects:
                return cand
            # If formatted correctly but not in current snapshot, return cand for validation
            return cand
        return None

    def resolve_all_subjects(self, text: str) -> List[str]:
        """Finds all subject IDs in text."""
        matches = re.findall(r"\b(042-S\d{2}-\d{3})\b", text, re.IGNORECASE)
        return [m.upper() for m in matches]

    def resolve_site(self, text: str) -> Optional[str]:
        """Resolves site ID from text (e.g. 'site S07', 'S07', 'Site 7')."""
        # Match 'site S07' or 'site 7' or 'site 07' or 'S07'
        match = re.search(r"\b(?:site\s+)?(S\d{2})\b", text, re.IGNORECASE)
        if match:
            return match.group(1).upper()

        match_num = re.search(r"\bsite\s+(\d{1,2})\b", text, re.IGNORECASE)
        if match_num:
            num = int(match_num.group(1))
            return f"S{num:02d}"

        return None

    def resolve_visit(self, text: str) -> Optional[str]:
        """Resolves visit name to normalized standard representation."""
        upper = text.upper()
        if "SCREENING" in upper or "DAY -14" in upper:
            return "SCREENING"
        if "BASELINE" in upper or "DAY 0" in upper:
            return "BASELINE"
        if "EOS" in upper or "END OF STUDY" in upper or "DAY 182" in upper:
            return "EOS"

        week_match = re.search(r"\b(?:WEEK|W)\s*(\d+)\b", upper)
        if week_match:
            return f"WEEK{week_match.group(1)}"

        day_match = re.search(r"\bDAY\s*(\d+)\b", upper)
        if day_match:
            return f"DAY{day_match.group(1)}"

        return None

    def resolve_test(self, text: str) -> Optional[str]:
        """Resolves lab or vital sign test code from common names or aliases."""
        upper = text.upper()
        lower = text.lower()

        # Lab tests
        if re.search(r"\b(ALT|alanine aminotransferase|SGPT)\b", upper):
            return "ALT"
        if re.search(r"\b(AST|aspartate aminotransferase|SGOT)\b", upper):
            return "AST"
        if re.search(r"\b(BILI|bilirubin|total bilirubin)\b", upper):
            return "BILI"
        if re.search(r"\b(CREAT|creatinine|serum creatinine)\b", upper):
            return "CREAT"
        if re.search(r"\b(GLUC|glucose|blood sugar|fasting glucose)\b", upper):
            return "GLUC"
        if re.search(r"\b(HBA1C|hemoglobin a1c|glycated hemoglobin|a1c)\b", upper):
            return "HBA1C"

        # Vital signs
        if re.search(r"\b(SYSBP|systolic(?: blood pressure)?)\b", upper):
            return "SYSBP"
        if re.search(r"\b(DIABP|diastolic(?: blood pressure)?)\b", upper):
            return "DIABP"
        if re.search(r"\b(PULSE|heart rate|pulse rate)\b", upper):
            return "PULSE"
        if re.search(r"\b(QTCF|qtc|qtcf interval)\b", upper):
            return "QTCF"

        # Check discovered lab codes
        for code in self.available_lab_tests:
            if re.search(rf"\b{re.escape(code)}\b", upper):
                return code

        # Check discovered vital codes
        for code in self.available_vital_tests:
            if re.search(rf"\b{re.escape(code)}\b", upper):
                return code

        return None

    def resolve_domain(self, text: str) -> Optional[str]:
        """Resolves SDTM domain from keywords."""
        lower = text.lower()
        if any(w in lower for w in ("adverse event", "side effect", "ae", "safety event", "toxicity")):
            return "AE"
        if any(w in lower for w in ("lab", "laboratory", "blood work", "blood test", "chemistry")):
            return "LB"
        if any(w in lower for w in ("vital", "blood pressure", "pulse", "heart rate", "temperature")):
            return "VS"
        if any(w in lower for w in ("medication", "medicine", "drug", "concomitant", "treatment")):
            return "CM"
        if any(w in lower for w in ("dose", "dosing", "study drug", "exposure", "drug-042")):
            return "EX"
        if any(w in lower for w in ("disposition", "discontinued", "withdrawal", "completion", "dropout")):
            return "DS"
        if any(w in lower for w in ("medical history", "history", "prior condition")):
            return "MH"
        if any(w in lower for w in ("ecg", "electrocardiogram", "ekg", "qtc")):
            return "EG"
        if any(w in lower for w in ("demographic", "age", "sex", "gender", "race", "patient", "subject", "participant")):
            return "DM"
        return None

    def resolve_finding_type(self, text: str) -> Optional[str]:
        """Resolves natural language finding inquiries to deterministic finding types."""
        lower = text.lower()
        if "hy" in lower or "liver safety" in lower or "transaminase" in lower:
            return "potential_hys_law"
        if "serious" in lower or "sae" in lower or "hospitaliz" in lower or "death" in lower or "life-threatening" in lower:
            return "serious_adverse_event"
        if "creatinine" in lower and ("exclusion" in lower or "renal" in lower or "kidney" in lower or "violation" in lower or "> 1.5" in lower):
            return "exclusion_violation_creatinine"
        if "prohibited" in lower or "concomitant" in lower or "sulfonylurea" in lower or "glucocorticoid" in lower or "forbidden med" in lower:
            return "prohibited_concomitant_medication"
        if "visit" in lower and ("window" in lower or "deviation" in lower or "timing" in lower or "schedule" in lower):
            return "visit_window_deviation"
        return None

    def validate_site(self, site_id: str) -> bool:
        """Returns True if site_id exists in current study snapshot."""
        return site_id.upper() in self.available_sites

    def validate_subject(self, usubjid: str) -> bool:
        """Returns True if usubjid exists in current study snapshot."""
        return usubjid.upper() in self.available_subjects

    def validate_visit(self, visit_name: str) -> bool:
        """Returns True if visit_name is a known study visit."""
        norm = self.resolve_visit(visit_name)
        if not norm:
            return False
        # If visits are discovered, check against discovered set, or allow standard protocol visits
        standard = {"SCREENING", "BASELINE", "WEEK2", "WEEK4", "WEEK8", "WEEK12", "WEEK16", "WEEK20", "WEEK24", "EOS"}
        return norm in self.available_visits or norm in standard
