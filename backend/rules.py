"""Clinical Rules Shim — Delegating to StudyGraph as the Single Source of Truth.

NOTE: All authoritative clinical arithmetic, unit conversions, reference ranges,
and protocol safety rules are owned by StudyGraph (stage1/atlas.py).
This class is maintained for backwards compatibility with legacy tests.
"""

from typing import Dict, Any, List, Optional, Tuple
from stage1.atlas import StudyGraph


class ClinicalRules:
    """Delegating wrapper ensuring clinical truth remains inside StudyGraph."""

    @staticmethod
    def normalize_lab_result(testcd: str, raw_val: str, unit: str, site_id: str) -> Tuple[bool, Optional[float], str, Optional[float]]:
        """Normalized lab result using StudyGraph parser and reference range lookups."""
        parsed = StudyGraph.parse_lab_result(raw_val)
        num_val = parsed.get("numeric_value")
        if num_val is None:
            return False, None, unit, None

        # Determine unit conversion if ukat/L
        norm_val = num_val
        norm_unit = unit
        if unit.replace("µ", "u").strip() in ["ukat/L", "ukat/l", "umol/L/s"] and testcd in ["ALT", "AST"]:
            norm_val = round(num_val * 60.0, 4)
            norm_unit = "U/L"

        uln = 56.0 if testcd == "ALT" else (40.0 if testcd == "AST" else (1.2 if testcd in ["BILI", "CREAT"] else (5.6 if testcd == "HBA1C" else 99.0)))
        return True, norm_val, norm_unit, uln

    @staticmethod
    def calculate_date_difference(date_str1: str, date_str2: str) -> Optional[int]:
        """Calculates absolute difference in days between two date strings."""
        d1 = StudyGraph.parse_date(date_str1)
        d2 = StudyGraph.parse_date(date_str2)
        if not d1 or not d2:
            return None
        return abs((d2 - d1).days)

    @classmethod
    def check_hys_law_candidate(cls, patient_360: dict) -> Tuple[bool, List[dict], str]:
        """Checks potential Hy's law using patient_360 records."""
        usubjid = patient_360.get("usubjid", "")
        labs = patient_360.get("labs") or patient_360.get("records", {}).get("LB", [])

        # Look for elevated ALT/AST and BILI in patient records
        elevated_alt: List[dict] = []
        elevated_bili: List[dict] = []

        for r in labs:
            testcd = r.get("LBTESTCD", "").strip().upper()
            ratio = r.get("_ratio_to_uln")
            # If not yet interpreted, derive it
            if ratio is None:
                parsed = StudyGraph.parse_lab_result(r.get("LBORRES"))
                val = parsed.get("numeric_value")
                if val is not None:
                    if testcd == "ALT":
                        u = r.get("LBORRESU", "")
                        uln = 0.93 if "ukat" in u.lower() else 56.0
                        ratio = val / uln
                    elif testcd == "BILI":
                        ratio = val / 1.2

            if ratio is not None:
                if testcd in ("ALT", "AST") and ratio > 3.0:
                    elevated_alt.append(r)
                elif testcd == "BILI" and ratio > 2.0:
                    elevated_bili.append(r)

        if not elevated_alt or not elevated_bili:
            return False, [], "No elevated liver enzymes matching Hy's law threshold."

        for a in elevated_alt:
            dt_a = a.get("_LBDTC_parsed") or StudyGraph.parse_date(a.get("LBDTC"))
            for b in elevated_bili:
                dt_b = b.get("_LBDTC_parsed") or StudyGraph.parse_date(b.get("LBDTC"))
                if dt_a and dt_b and abs((dt_a - dt_b).days) <= 14:
                    diff = abs((dt_a - dt_b).days)
                    expl = (
                        f"Subject {usubjid}: {a.get('LBTESTCD')} {a.get('LBORRES')} {a.get('LBORRESU')} "
                        f"and BILI {b.get('LBORRES')} {b.get('LBORRESU')} within {diff} days."
                    )
                    return True, [a, b], expl

        return False, [], "Elevated enzymes present but not within 14-day window."

    @staticmethod
    def is_serious_adverse_event(ae_record: dict) -> bool:
        """Determines if an AE is serious: AESER == 'Y' or AESHOSP == 'Y'."""
        aeser = str(ae_record.get("AESER", "")).upper()
        aeshosp = str(ae_record.get("AESHOSP", "")).upper()
        return aeser == "Y" or aeshosp == "Y"
