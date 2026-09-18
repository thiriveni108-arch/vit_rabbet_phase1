"""Stage 1: ATLAS StudyGraph, Normalization, Clinical Rule Engine, and Backend APIs.

In-memory Study Knowledge Graph for clinical trial surveillance.
Provides deterministic normalization, time-travel cut querying, clinical finding
detection, chronological subject timelines, flexible lookups, and graph data export.
"""

from __future__ import annotations

import csv
import datetime
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


class StudyGraph:
    """In-memory Study Knowledge Graph for clinical trial surveillance.

    Core interfaces:
        - __init__(data_dir: str)
        - build(cut: int | None = None) -> dict
        - lookup(domain=None, usubjid=None, visit=None, testcd=None, field_filters=None) -> list[dict]
        - timeline(usubjid: str) -> list[dict]
        - patient360(usubjid: str) -> dict
        - graph_view(usubjid: str) -> dict
        - get_finding(finding_id: str) -> dict | None
        - get_evidence(finding_or_id: Any) -> list[dict]
        - dashboard_summary() -> dict
        - find_hys_law_candidates(usubjid: str | None = None) -> list[dict]
        - find_serious_adverse_events(usubjid: str | None = None) -> list[dict]
        - find_exclusion_violations(usubjid: str | None = None) -> list[dict]
        - find_prohibited_medications(usubjid: str | None = None) -> list[dict]
        - find_visit_window_deviations(usubjid: str | None = None) -> list[dict]
        - get_findings(usubjid: str | None = None) -> list[dict]
        - validate_evidence(findings: list[dict] | None = None) -> dict
    """

    DOMAINS: Tuple[str, ...] = ("DM", "AE", "LB", "VS", "EX", "CM", "DS", "MH", "EG")

    DATE_FIELDS: Tuple[str, ...] = (
        "LBDTC", "AESTDTC", "AEENDTC", "VSDTC", "EGDTC",
        "CMSTDTC", "EXSTDTC", "DSSTDTC", "BRTHDTC", "RFSTDTC"
    )

    TARGET_SCHEDULE: Dict[str, int] = {
        "SCREENING": -14,
        "BASELINE": 0,
        "WEEK2": 14,
        "WEEK4": 28,
        "WEEK8": 56,
        "WEEK12": 84,
        "WEEK16": 112,
        "WEEK20": 140,
        "WEEK24": 168,
        "EOS": 182,
    }

    def __init__(self, data_dir: str = "hackathon-data"):
        self.data_dir_param: str = data_dir
        self.root_dir, self.data_dir = self._locate_data_dir(data_dir)
        self.documents_dir: Path = self.root_dir / "documents"
        self.responses_dir: Path = self.root_dir / "responses"

        self.reference_ranges_raw: List[Dict[str, Any]] = []
        self.reference_ranges_map: Dict[Tuple[str, str, str], Tuple[Optional[float], Optional[float]]] = {}
        self._load_reference_ranges()

        self.cuts: Dict[int, Dict[str, Any]] = self._load_cuts()

        # State populated by build()
        self.current_cut: Optional[int] = None
        self.current_protocol_version: int = 1
        self.domain_records: Dict[str, List[Dict[str, Any]]] = {}
        self.domain_counts: Dict[str, int] = {}
        self.records_by_key: Dict[Tuple[str, str, int], Dict[str, Any]] = {}
        self.subjects: Dict[str, Dict[str, Any]] = {}
        self.sites: Set[str] = set()
        self.corrections_applied_count: int = 0
        self.last_build_stats: Dict[str, Any] = {}

        # Performance Indexes
        self.records_by_subject: Dict[str, List[Dict[str, Any]]] = {}
        self.records_by_domain: Dict[str, List[Dict[str, Any]]] = {}
        self.records_by_subj_dom: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self.records_by_subj_visit: Dict[Tuple[str, str], List[Dict[str, Any]]] = {}
        self.records_by_lab_test: Dict[str, List[Dict[str, Any]]] = {}

        # Cached Findings and Finding Indexes
        self.findings: List[Dict[str, Any]] = []
        self.findings_by_id: Dict[str, Dict[str, Any]] = {}
        self.findings_by_subj: Dict[str, List[Dict[str, Any]]] = {}
        self.finding_ids_by_record_key: Dict[Tuple[str, str, int], List[str]] = {}

    # =========================================================================
    # A. NORMALIZATION HELPERS & JSON SAFETY
    # =========================================================================

    @staticmethod
    def parse_date(date_str: Optional[str]) -> Optional[datetime.date]:
        """Parse raw date string into standard datetime.date."""
        if not date_str:
            return None
        cleaned = date_str.strip()
        if not cleaned:
            return None

        # ISO format
        try:
            return datetime.datetime.strptime(cleaned, "%Y-%m-%d").date()
        except ValueError:
            pass

        # DD-MON-YYYY format
        try:
            return datetime.datetime.strptime(cleaned, "%d-%b-%Y").date()
        except ValueError:
            pass

        return None

    @staticmethod
    def format_date_iso(dt: Optional[datetime.date]) -> Optional[str]:
        return dt.isoformat() if dt else None

    @staticmethod
    def parse_lab_result(val_str: Optional[str]) -> Dict[str, Any]:
        """Parse raw laboratory result preserving clinical provenance."""
        raw = "" if val_str is None else str(val_str).strip()
        result: Dict[str, Any] = {
            "raw_value": raw,
            "numeric_value": None,
            "is_below_detection": False,
            "is_not_done": False,
            "is_blank": False,
        }

        if not raw:
            result["is_blank"] = True
            return result

        upper = raw.upper()
        if upper == "ND":
            result["is_not_done"] = True
            return result

        if upper.startswith("<"):
            result["is_below_detection"] = True
            return result

        normalized_str = raw.replace(",", ".")
        try:
            result["numeric_value"] = float(normalized_str)
        except ValueError:
            pass

        return result

    @staticmethod
    def _to_json_safe(obj: Any) -> Any:
        """Recursively convert records/findings into 100% JSON-serializable structures."""
        if isinstance(obj, (datetime.date, datetime.datetime)):
            return obj.isoformat()
        if isinstance(obj, dict):
            clean = {}
            for k, v in obj.items():
                if k.startswith("_") and k.endswith("_parsed"):
                    continue
                clean[k] = StudyGraph._to_json_safe(v)
            return clean
        if isinstance(obj, list):
            return [StudyGraph._to_json_safe(item) for item in obj]
        return obj

    def reference_range_lookup(
        self, testcd: str, unit: str, site_id: str
    ) -> Dict[str, Any]:
        """Look up reference range from data/reference_ranges.csv."""
        t = testcd.strip().upper()
        u = unit.strip()
        s = site_id.strip().upper()

        if (t, u, s) in self.reference_ranges_map:
            low, high = self.reference_ranges_map[(t, u, s)]
            return {
                "low": low,
                "high": high,
                "lab_source": s,
                "unit": u,
                "converted": False,
            }

        if (t, u, "CENTRAL") in self.reference_ranges_map:
            low, high = self.reference_ranges_map[(t, u, "CENTRAL")]
            return {
                "low": low,
                "high": high,
                "lab_source": "CENTRAL",
                "unit": u,
                "converted": False,
            }

        # Conversion fallback per lab manual: 1 ukat/L = 60 U/L
        if u == "ukat/L" and (t, "U/L", "CENTRAL") in self.reference_ranges_map:
            c_low, c_high = self.reference_ranges_map[(t, "U/L", "CENTRAL")]
            return {
                "low": round(c_low / 60.0, 4) if c_low is not None else None,
                "high": round(c_high / 60.0, 4) if c_high is not None else None,
                "lab_source": "CENTRAL_CONVERTED",
                "unit": "ukat/L",
                "converted": True,
            }

        if u == "U/L" and (t, "ukat/L", s) in self.reference_ranges_map:
            s_low, s_high = self.reference_ranges_map[(t, "ukat/L", s)]
            return {
                "low": round(s_low * 60.0, 4) if s_low is not None else None,
                "high": round(s_high * 60.0, 4) if s_high is not None else None,
                "lab_source": f"{s}_CONVERTED",
                "unit": "U/L",
                "converted": True,
            }

        return {
            "low": None,
            "high": None,
            "lab_source": None,
            "unit": u,
            "converted": False,
        }

    def interpret_lab(self, record: Dict[str, Any], site_id: str) -> Dict[str, Any]:
        """Derive standardized clinical interpretation for a laboratory record."""
        raw_val = record.get("LBORRES", "")
        unit = record.get("LBORRESU", "").strip()
        testcd = record.get("LBTESTCD", "").strip().upper()

        parsed_val = self.parse_lab_result(raw_val)
        num_val = parsed_val["numeric_value"]

        ref = self.reference_range_lookup(testcd, unit, site_id)
        uln = ref["high"]
        low = ref["low"]

        ratio_to_uln: Optional[float] = None
        above_3x = False
        above_2x = False

        if num_val is not None and uln is not None and uln > 0:
            ratio_to_uln = round(num_val / uln, 4)
            above_3x = ratio_to_uln > 3.0
            above_2x = ratio_to_uln > 2.0

        return {
            "raw_value": parsed_val["raw_value"],
            "numeric_value": num_val,
            "is_below_detection": parsed_val["is_below_detection"],
            "is_not_done": parsed_val["is_not_done"],
            "is_blank": parsed_val["is_blank"],
            "unit": unit,
            "low": low,
            "uln": uln,
            "lab_source": ref["lab_source"],
            "ratio_to_uln": ratio_to_uln,
            "above_3x_uln": above_3x,
            "above_2x_uln": above_2x,
        }

    # =========================================================================
    # B. INITIALIZATION & DATA LOADING
    # =========================================================================

    def _locate_data_dir(self, requested_path: str) -> Tuple[Path, Path]:
        candidates: List[Path] = [
            Path(requested_path),
            Path(requested_path) / "data",
            Path("data"),
            Path("hackathon-data"),
            Path("hackathon-data") / "data",
            Path("..") / "hackathon-data",
            Path("..") / "hackathon-data" / "data",
            Path(__file__).resolve().parent.parent / "data",
            Path(__file__).resolve().parent.parent / "hackathon-data" / "data",
        ]

        for cand in candidates:
            if (cand / "cuts.csv").is_file():
                data_path = cand.resolve()
                root_path = cand.parent.resolve() if cand.name == "data" else cand.resolve()
                return root_path, data_path

            if (cand / "data" / "cuts.csv").is_file():
                root_path = cand.resolve()
                data_path = (cand / "data").resolve()
                return root_path, data_path

        raise FileNotFoundError(
            f"Could not locate clinical data directory with cuts.csv. "
            f"Searched: {[str(c) for c in candidates]}"
        )

    def _load_reference_ranges(self) -> None:
        ref_file = self.data_dir / "reference_ranges.csv"
        self.reference_ranges_raw = []
        self.reference_ranges_map = {}

        if not ref_file.is_file():
            return

        with open(ref_file, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.reference_ranges_raw.append(dict(row))
                test = row["LBTESTCD"].strip().upper()
                unit = row["UNIT"].strip()
                lab = row["LAB"].strip().upper()
                try:
                    low = float(row["LOW"]) if row.get("LOW") else None
                except ValueError:
                    low = None
                try:
                    high = float(row["HIGH"]) if row.get("HIGH") else None
                except ValueError:
                    high = None
                self.reference_ranges_map[(test, unit, lab)] = (low, high)

    def _load_cuts(self) -> Dict[int, Dict[str, Any]]:
        cuts_file = self.data_dir / "cuts.csv"
        cuts_dict: Dict[int, Dict[str, Any]] = {}

        if not cuts_file.is_file():
            return cuts_dict

        with open(cuts_file, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cut_num = int(row["cut"])
                cuts_dict[cut_num] = {
                    "cut": cut_num,
                    "protocol_version": int(row["protocol_version"]),
                    "new_records": int(row["new_records"]),
                    "corrections": int(row["corrections"]),
                }

        return cuts_dict

    def get_protocol_version(self, cut: Optional[int] = None) -> int:
        if not self.cuts:
            return 1

        if cut is None:
            cut = max(self.cuts.keys())

        if cut in self.cuts:
            return self.cuts[cut]["protocol_version"]

        applicable = [c for c in self.cuts.keys() if c <= cut]
        if applicable:
            return self.cuts[max(applicable)]["protocol_version"]

        return 1

    def _load_corrections(self, max_cut: Optional[int] = None) -> Dict[Tuple[str, str, int, str], str]:
        corrections_map: Dict[Tuple[str, str, int, str], str] = {}
        corr_file = self.data_dir / "corrections.csv"

        if not corr_file.is_file():
            return corrections_map

        with open(corr_file, mode="r", encoding="utf-8-sig") as f:
            reader = csv.DictReader(f)
            for row in reader:
                c_cut = int(row["cut"])
                if max_cut is not None and c_cut > max_cut:
                    continue
                domain = row["domain"].strip().upper()
                usubjid = row["usubjid"].strip()
                seq = int(row["seq"])
                field = row["field"].strip()
                new_val = row["new_value"].strip()
                corrections_map[(domain, usubjid, seq, field)] = new_val

        return corrections_map

    # =========================================================================
    # C. GRAPH BUILD & PERFORMANCE INDEXES
    # =========================================================================

    def build(self, cut: Optional[int] = None) -> Dict[str, Any]:
        """Build the in-memory Study Graph up to the specified data cut.

        Constructs all primary indexes for O(1) lookups and recomputes all
        findings with zero stale state.
        """
        start_time = time.perf_counter()

        if cut is None:
            cut = max(self.cuts.keys()) if self.cuts else 1

        self.current_cut = cut
        self.current_protocol_version = self.get_protocol_version(cut)

        corrections_map = self._load_corrections(max_cut=cut)

        # Reset state & primary stores
        self.domain_records = {dom: [] for dom in self.DOMAINS}
        self.domain_counts = {dom: 0 for dom in self.DOMAINS}
        self.records_by_key = {}
        self.subjects = {}
        self.sites = set()
        self.corrections_applied_count = 0

        # Reset Performance Indexes
        self.records_by_subject = {}
        self.records_by_domain = {dom: [] for dom in self.DOMAINS}
        self.records_by_subj_dom = {}
        self.records_by_subj_visit = {}
        self.records_by_lab_test = {}

        # Reset Findings Stores
        self.findings = []
        self.findings_by_id = {}
        self.findings_by_subj = {}
        self.finding_ids_by_record_key = {}

        total_records = 0

        for domain in self.DOMAINS:
            file_path = self.data_dir / f"{domain}.csv"
            if not file_path.is_file():
                continue

            seq_col = f"{domain}SEQ"

            with open(file_path, mode="r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    usubjid = row.get("USUBJID", "").strip()
                    if not usubjid:
                        continue

                    # Filter by cut_available
                    cut_avail_str = row.get("cut_available", "").strip()
                    if cut_avail_str:
                        try:
                            cut_avail = int(cut_avail_str)
                            if cut_avail > cut:
                                continue
                        except ValueError:
                            pass

                    # Extract sequence number
                    seq: Optional[int] = None
                    if seq_col in row and row[seq_col].strip():
                        try:
                            seq = int(row[seq_col].strip())
                        except ValueError:
                            seq = None

                    # Apply corrections valid through cut
                    record_dict = dict(row)
                    if seq is not None:
                        for (c_dom, c_subj, c_seq, c_field), new_val in corrections_map.items():
                            if c_dom == domain and c_subj == usubjid and c_seq == seq:
                                if c_field in record_dict:
                                    record_dict[c_field] = new_val
                                    self.corrections_applied_count += 1

                    # Register subject in Patient360
                    site_id = usubjid.split("-")[1] if len(usubjid.split("-")) > 1 else ""
                    if usubjid not in self.subjects:
                        self.subjects[usubjid] = {
                            "usubjid": usubjid,
                            "site_id": site_id,
                            "demographics": {},
                            "records": {d: [] for d in self.DOMAINS},
                        }
                        self.records_by_subject[usubjid] = []

                    # Demographics metadata & Sites
                    if domain == "DM":
                        self.subjects[usubjid]["demographics"] = record_dict
                        if "SITEID" in record_dict and record_dict["SITEID"].strip():
                            site_id = record_dict["SITEID"].strip()
                            self.subjects[usubjid]["site_id"] = site_id
                            self.sites.add(site_id)

                    # Normalize dates
                    for date_fld in self.DATE_FIELDS:
                        if date_fld in record_dict and record_dict[date_fld]:
                            parsed_dt = self.parse_date(record_dict[date_fld])
                            record_dict[f"_{date_fld}_parsed"] = parsed_dt
                            record_dict[f"_{date_fld}_iso"] = self.format_date_iso(parsed_dt)

                    # Domain-specific normalization: LB interpretation
                    if domain == "LB":
                        interp = self.interpret_lab(record_dict, site_id=site_id)
                        record_dict["_interpretation"] = interp
                        record_dict["_numeric_value"] = interp["numeric_value"]
                        record_dict["_uln"] = interp["uln"]
                        record_dict["_ratio_to_uln"] = interp["ratio_to_uln"]
                        record_dict["_above_3x_uln"] = interp["above_3x_uln"]
                        record_dict["_above_2x_uln"] = interp["above_2x_uln"]

                        testcd = record_dict.get("LBTESTCD", "").strip().upper()
                        if testcd:
                            self.records_by_lab_test.setdefault(testcd, []).append(record_dict)

                    # Provenance metadata
                    record_dict["_domain"] = domain
                    record_dict["_usubjid"] = usubjid
                    record_dict["_seq"] = seq

                    # Store in subject Patient360 and domain lists
                    self.subjects[usubjid]["records"][domain].append(record_dict)
                    self.domain_records[domain].append(record_dict)
                    self.domain_counts[domain] += 1
                    total_records += 1

                    # Index by triple (domain, usubjid, seq)
                    if seq is not None:
                        self.records_by_key[(domain, usubjid, seq)] = record_dict

                    # Performance indexes
                    self.records_by_subject[usubjid].append(record_dict)
                    self.records_by_domain[domain].append(record_dict)
                    self.records_by_subj_dom.setdefault((usubjid, domain), []).append(record_dict)

                    visit_val = record_dict.get("VISIT", "").strip().upper()
                    if visit_val:
                        self.records_by_subj_visit.setdefault((usubjid, visit_val), []).append(record_dict)

        # Build findings & finding indexes ONCE for this cut
        self._reindex_findings()

        nodes_count = len(self.subjects) + total_records
        edges_count = total_records
        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        self.last_build_stats = {
            "cut": self.current_cut,
            "protocol_version": self.current_protocol_version,
            "subjects": len(self.subjects),
            "records": total_records,
            "domain_counts": dict(self.domain_counts),
            "nodes": nodes_count,
            "edges": edges_count,
            "corrections_applied": self.corrections_applied_count,
            "build_time_ms": elapsed_ms,
        }

        return self.last_build_stats

    def _reindex_findings(self) -> None:
        """Compute all findings for current cut and build lookup indexes."""
        self.findings = []
        self.findings_by_id = {}
        self.findings_by_subj = {}
        self.finding_ids_by_record_key = {}

        all_findings = []
        all_findings.extend(self.find_hys_law_candidates())
        all_findings.extend(self.find_serious_adverse_events())
        all_findings.extend(self.find_exclusion_violations())
        all_findings.extend(self.find_prohibited_medications())
        all_findings.extend(self.find_visit_window_deviations())

        self.findings = all_findings

        for f in self.findings:
            fid = f["finding_id"]
            usubjid = f["usubjid"]
            self.findings_by_id[fid] = f
            self.findings_by_subj.setdefault(usubjid, []).append(f)

            for ev in f.get("evidence", []):
                key = (ev["domain"], ev["usubjid"], ev["seq"])
                self.finding_ids_by_record_key.setdefault(key, []).append(fid)

    def patient360(self, usubjid: str) -> Dict[str, Any]:
        """Return connected view of all records and interpretations for a subject."""
        subj_data = self.subjects.get(usubjid, {})
        return self._to_json_safe(subj_data)

    # =========================================================================
    # D. QUERY, TIMELINE, AND BACKEND SERVICE APIS
    # =========================================================================

    def lookup(
        self,
        domain: Optional[str] = None,
        usubjid: Optional[str] = None,
        visit: Optional[str] = None,
        testcd: Optional[str] = None,
        field_filters: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Fast indexed search over current cut-aware graph records.

        Returns list of normalized structured records with full raw provenance.
        Returns [] if no match. 100% JSON-safe.
        """
        # Fast path selection using pre-computed indexes
        if usubjid and domain:
            candidates = self.records_by_subj_dom.get((usubjid, domain.upper()), [])
        elif usubjid and visit:
            candidates = self.records_by_subj_visit.get((usubjid, visit.upper()), [])
        elif usubjid:
            candidates = self.records_by_subject.get(usubjid, [])
        elif domain:
            candidates = self.records_by_domain.get(domain.upper(), [])
        elif testcd and testcd.upper() in self.records_by_lab_test:
            candidates = self.records_by_lab_test.get(testcd.upper(), [])
        else:
            # Fallback: all active records across all domains
            candidates = [r for dom in self.DOMAINS for r in self.domain_records[dom]]

        if not candidates:
            return []

        results: List[Dict[str, Any]] = []

        for rec in candidates:
            # Domain filter
            if domain and rec.get("_domain") != domain.upper():
                continue

            # Subject filter
            if usubjid and rec.get("_usubjid") != usubjid:
                continue

            # Visit filter
            if visit:
                v_clean = rec.get("VISIT", "").strip().upper()
                if v_clean != visit.strip().upper():
                    continue

            # Test code filter
            if testcd:
                t_clean = testcd.strip().upper()
                rec_t = (
                    rec.get("LBTESTCD")
                    or rec.get("VSTESTCD")
                    or rec.get("EGTESTCD")
                    or ""
                ).strip().upper()
                if rec_t != t_clean:
                    continue

            # Custom field filters
            if field_filters:
                match_all = True
                for k, v in field_filters.items():
                    if rec.get(k) != str(v):
                        match_all = False
                        break
                if not match_all:
                    continue

            results.append(self._to_json_safe(rec))

        return results

    def has_record(self, domain: str, usubjid: str, seq: Any) -> bool:
        """Check if a record exists in the current cut-aware graph snapshot."""
        if domain.upper() == "DM" and usubjid in self.subjects:
            return True
        try:
            return (domain.upper(), usubjid, int(seq)) in self.records_by_key
        except (ValueError, TypeError):
            return False

    def timeline(self, usubjid: str) -> List[Dict[str, Any]]:
        """Return a strictly chronological list combining major domain events for a subject.

        Each item contains:
            - date (ISO string YYYY-MM-DD or None)
            - domain
            - visit
            - label (compact human-readable title)
            - seq
            - details
            - evidence reference
        """
        subj_data = self.subjects.get(usubjid)
        if not subj_data:
            return []

        date_col_map = {
            "AE": "AESTDTC",
            "CM": "CMSTDTC",
            "EX": "EXSTDTC",
            "DS": "DSSTDTC",
            "MH": None,
            "LB": "LBDTC",
            "VS": "VSDTC",
            "EG": "EGDTC",
            "DM": "RFSTDTC",
        }

        timeline_items: List[Dict[str, Any]] = []

        for domain in self.DOMAINS:
            records = subj_data["records"].get(domain, [])
            d_col = date_col_map.get(domain)

            for rec in records:
                seq = rec.get("_seq")
                dt_parsed = rec.get(f"_{d_col}_parsed") if d_col else None
                dt_iso = rec.get(f"_{d_col}_iso") if d_col else None
                visit = rec.get("VISIT")

                # Generate clean label and compact details per domain
                if domain == "AE":
                    label = f"Adverse Event: {rec.get('AETERM')} ({rec.get('AESEV')})"
                    details = {
                        "term": rec.get("AETERM"),
                        "severity": rec.get("AESEV"),
                        "serious": rec.get("AESER"),
                        "hospitalized": rec.get("AESHOSP"),
                        "start_date": dt_iso,
                        "end_date": rec.get("_AEENDTC_iso"),
                    }
                elif domain == "CM":
                    label = f"Concomitant Med: {rec.get('CMTRT')} ({rec.get('CMCLAS')})"
                    details = {
                        "treatment": rec.get("CMTRT"),
                        "class": rec.get("CMCLAS"),
                        "dose": rec.get("CMDOSE"),
                        "start_date": dt_iso,
                    }
                elif domain == "EX":
                    label = f"Dose Given: {rec.get('EXTRT')} {rec.get('EXDOSE')} {rec.get('EXDOSU')}"
                    details = {
                        "treatment": rec.get("EXTRT"),
                        "dose": rec.get("EXDOSE"),
                        "unit": rec.get("EXDOSU"),
                        "visit": visit,
                    }
                elif domain == "DS":
                    label = f"Disposition: {rec.get('DSDECOD')}"
                    details = {
                        "status": rec.get("DSDECOD"),
                        "reason": rec.get("DSTERM"),
                    }
                elif domain == "MH":
                    label = f"Medical History: {rec.get('MHTERM')}"
                    details = {"condition": rec.get("MHTERM")}
                elif domain == "LB":
                    label = f"Lab {rec.get('LBTESTCD')}: {rec.get('LBORRES')} {rec.get('LBORRESU')}"
                    details = {
                        "test": rec.get("LBTESTCD"),
                        "value": rec.get("LBORRES"),
                        "numeric_value": rec.get("_numeric_value"),
                        "unit": rec.get("LBORRESU"),
                        "ratio_to_uln": rec.get("_ratio_to_uln"),
                        "visit": visit,
                    }
                elif domain == "VS":
                    label = f"Vital Sign {rec.get('VSTESTCD')}: {rec.get('VSORRES')} {rec.get('VSORRESU')}"
                    details = {
                        "test": rec.get("VSTESTCD"),
                        "value": rec.get("VSORRES"),
                        "unit": rec.get("VSORRESU"),
                        "visit": visit,
                    }
                elif domain == "EG":
                    label = f"ECG {rec.get('EGTESTCD')}: {rec.get('EGORRES')}"
                    details = {"test": rec.get("EGTESTCD"), "value": rec.get("EGORRES"), "visit": visit}
                elif domain == "DM":
                    label = f"Demographics Enrolled (Arm: {rec.get('ARM')})"
                    details = {
                        "arm": rec.get("ARM"),
                        "age": rec.get("AGE"),
                        "sex": rec.get("SEX"),
                        "site_id": rec.get("SITEID"),
                    }
                else:
                    label = f"{domain} Record"
                    details = {}

                timeline_items.append({
                    "_dt": dt_parsed,
                    "date": dt_iso,
                    "domain": domain,
                    "visit": visit,
                    "label": label,
                    "seq": seq,
                    "details": details,
                    "evidence": {"domain": domain, "usubjid": usubjid, "seq": seq} if seq is not None else None,
                })

        # Strict chronological ordering; items without dates placed at the end
        timeline_items.sort(
            key=lambda x: (
                0 if x["_dt"] is not None else 1,
                x["_dt"] if x["_dt"] is not None else datetime.date.max,
                x["domain"],
                x["seq"] if x["seq"] is not None else 0,
            )
        )

        for item in timeline_items:
            item.pop("_dt", None)

        return timeline_items

    def get_finding(self, finding_id: str) -> Optional[Dict[str, Any]]:
        """Return unified finding by finding_id or None."""
        f = self.findings_by_id.get(finding_id)
        return self._to_json_safe(f) if f else None

    def get_evidence(self, finding_or_id: Any) -> List[Dict[str, Any]]:
        """Return rich supporting evidence records for a finding.

        Response format:
        [
          {
            "reference": {"domain": "LB", "usubjid": "...", "seq": 25},
            "details": {"test": "ALT", "raw_value": "3.995", ...}
          }
        ]
        """
        if isinstance(finding_or_id, str):
            finding = self.findings_by_id.get(finding_or_id)
        elif isinstance(finding_or_id, dict):
            finding = finding_or_id
        else:
            return []

        if not finding:
            return []

        results: List[Dict[str, Any]] = []

        for ev in finding.get("evidence", []):
            dom = ev.get("domain")
            subj = ev.get("usubjid")
            seq = ev.get("seq")

            ref = {"domain": dom, "usubjid": subj, "seq": seq}
            details: Dict[str, Any] = {}

            triple = (dom, subj, seq)
            rec = self.records_by_key.get(triple)

            if rec:
                if dom == "LB":
                    details = {
                        "domain": "LB",
                        "test": rec.get("LBTESTCD"),
                        "raw_value": rec.get("LBORRES"),
                        "numeric_value": rec.get("_numeric_value"),
                        "unit": rec.get("LBORRESU"),
                        "uln": rec.get("_uln"),
                        "ratio_to_uln": rec.get("_ratio_to_uln"),
                        "visit": rec.get("VISIT"),
                        "date": rec.get("_LBDTC_iso"),
                    }
                elif dom == "AE":
                    details = {
                        "domain": "AE",
                        "term": rec.get("AETERM"),
                        "severity": rec.get("AESEV"),
                        "serious": rec.get("AESER"),
                        "hospitalized": rec.get("AESHOSP"),
                        "start_date": rec.get("_AESTDTC_iso"),
                        "end_date": rec.get("_AEENDTC_iso"),
                        "outcome": rec.get("AEOUT"),
                    }
                elif dom == "CM":
                    details = {
                        "domain": "CM",
                        "treatment": rec.get("CMTRT"),
                        "class": rec.get("CMCLAS"),
                        "dose": rec.get("CMDOSE"),
                        "start_date": rec.get("_CMSTDTC_iso"),
                        "indication": rec.get("CMINDC"),
                    }
                elif dom == "VS":
                    details = {
                        "domain": "VS",
                        "test": rec.get("VSTESTCD"),
                        "value": rec.get("VSORRES"),
                        "unit": rec.get("VSORRESU"),
                        "visit": rec.get("VISIT"),
                        "date": rec.get("_VSDTC_iso"),
                    }
                else:
                    details = {
                        k: v for k, v in rec.items()
                        if not k.startswith("_")
                    }

            results.append({
                "reference": ref,
                "details": self._to_json_safe(details),
            })

        return results

    def dashboard_summary(self) -> Dict[str, Any]:
        """Return JSON-safe aggregate summary metrics for the CURRENT cut only."""
        findings_by_type: Dict[str, int] = {}
        for f in self.findings:
            ft = f.get("finding_type", "other")
            findings_by_type[ft] = findings_by_type.get(ft, 0) + 1

        return {
            "cut": self.current_cut,
            "protocol_version": self.current_protocol_version,
            "subjects": len(self.subjects),
            "sites": len(self.sites),
            "total_records": sum(self.domain_counts.values()),
            "domain_record_counts": dict(self.domain_counts),
            "total_findings": len(self.findings),
            "potential_hys_law_count": findings_by_type.get("potential_hys_law", 0),
            "serious_ae_count": findings_by_type.get("serious_adverse_event", 0),
            "creatinine_exclusion_count": findings_by_type.get("exclusion_violation_creatinine", 0),
            "prohibited_medication_count": findings_by_type.get("prohibited_concomitant_medication", 0),
            "visit_deviation_count": findings_by_type.get("visit_window_deviation", 0),
            "findings_by_type": findings_by_type,
            "build_time_ms": self.last_build_stats.get("build_time_ms", 0),
        }

    # =========================================================================
    # E. GRAPH VIEW & FINDING CONNECTIONS
    # =========================================================================

    def graph_view(self, usubjid: str) -> Dict[str, Any]:
        """Expose structured graph data (nodes and edges) for a single subject.

        Nodes distinguish:
            SUBJECT, LAB, AE, MEDICATION, EXPOSURE, DISPOSITION,
            HISTORY, VITAL_SIGN, ECG, and FINDING.

        Connects SUBJECT -> FINDING (HAS_FINDING) -> EVIDENCE RECORD (SUPPORTED_BY).
        All edges strictly reference existing node IDs. 100% JSON-safe.
        """
        subj_data = self.subjects.get(usubjid)
        if not subj_data:
            return {"nodes": [], "edges": []}

        nodes: List[Dict[str, Any]] = []
        edges: List[Dict[str, Any]] = []
        node_ids: Set[str] = set()

        subj_id = f"SUBJ_{usubjid}"
        clean_demo = {
            k: v for k, v in subj_data.get("demographics", {}).items()
            if not k.startswith("_")
        }
        nodes.append({
            "id": subj_id,
            "type": "SUBJECT",
            "label": usubjid,
            "properties": {
                "site_id": subj_data.get("site_id", ""),
                "demographics": clean_demo,
            },
        })
        node_ids.add(subj_id)

        domain_meta = {
            "AE": ("AE", "EXPERIENCED"),
            "CM": ("MEDICATION", "TAKES"),
            "EX": ("EXPOSURE", "ADMINISTERED"),
            "DS": ("DISPOSITION", "HAS_DISPOSITION"),
            "MH": ("HISTORY", "HAS_HISTORY"),
            "LB": ("LAB", "TESTED"),
            "VS": ("VITAL_SIGN", "MEASURED"),
            "EG": ("ECG", "ECG_RECORDED"),
            "DM": ("DEMOGRAPHICS", "HAS_DEMOGRAPHICS"),
        }

        # 1. Domain records nodes
        for domain in self.DOMAINS:
            records = subj_data["records"].get(domain, [])
            n_type, rel = domain_meta.get(domain, ("RECORD", "HAS_RECORD"))

            for rec in records:
                seq = rec.get("_seq")
                rec_id = f"{domain}_{usubjid}_{seq}" if seq is not None else f"{domain}_{usubjid}_{len(nodes)}"

                if rec_id in node_ids:
                    rec_id = f"{rec_id}_{len(nodes)}"

                label = (
                    rec.get("AETERM")
                    or rec.get("CMTRT")
                    or rec.get("LBTESTCD")
                    or rec.get("VSTESTCD")
                    or rec.get("EXTRT")
                    or rec.get("DSDECOD")
                    or domain
                )

                # Check if this record is linked to any active finding
                key = (domain, usubjid, seq) if seq is not None else None
                linked_findings = self.finding_ids_by_record_key.get(key, []) if key else []

                props: Dict[str, Any] = {
                    "seq": seq,
                    "visit": rec.get("VISIT"),
                    "cut_available": rec.get("cut_available"),
                    "has_finding": len(linked_findings) > 0,
                    "finding_ids": linked_findings,
                }

                if domain == "LB":
                    props["test"] = rec.get("LBTESTCD")
                    props["value"] = rec.get("LBORRES")
                    props["numeric_value"] = rec.get("_numeric_value")
                    props["unit"] = rec.get("LBORRESU")
                    props["date"] = rec.get("_LBDTC_iso")
                    props["ratio_to_uln"] = rec.get("_ratio_to_uln")
                elif domain == "AE":
                    props["severity"] = rec.get("AESEV")
                    props["serious"] = rec.get("AESER")
                    props["hospitalized"] = rec.get("AESHOSP")
                    props["date"] = rec.get("_AESTDTC_iso")

                nodes.append({
                    "id": rec_id,
                    "type": n_type,
                    "label": str(label),
                    "properties": props,
                })
                node_ids.add(rec_id)

                edges.append({
                    "source": subj_id,
                    "target": rec_id,
                    "relationship": rel,
                })

        # 2. FINDING nodes and evidence links
        subj_findings = self.findings_by_subj.get(usubjid, [])
        for f in subj_findings:
            fid = f["finding_id"]
            if fid not in node_ids:
                nodes.append({
                    "id": fid,
                    "type": "FINDING",
                    "label": f.get("finding_type", "FINDING"),
                    "properties": self._to_json_safe(f.get("details", {})),
                })
                node_ids.add(fid)

                # Subject -> Finding edge
                edges.append({
                    "source": subj_id,
                    "target": fid,
                    "relationship": "HAS_FINDING",
                })

            # Finding -> Evidence Record edges
            for ev in f.get("evidence", []):
                ev_node_id = f"{ev['domain']}_{usubjid}_{ev['seq']}"
                if ev_node_id in node_ids:
                    edges.append({
                        "source": fid,
                        "target": ev_node_id,
                        "relationship": "SUPPORTED_BY",
                    })

        return {"nodes": nodes, "edges": edges}

    # =========================================================================
    # F. PROTOCOL RULE ENGINE — DETERMINISTIC FINDINGS
    # =========================================================================

    def find_hys_law_candidates(self, usubjid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Identify potential Hy's Law candidates according to protocol §7."""
        candidates: List[Dict[str, Any]] = []
        subject_keys = [usubjid] if usubjid is not None and usubjid in self.subjects else sorted(self.subjects.keys())

        for subj_id in subject_keys:
            subj_data = self.subjects[subj_id]
            lb_records = subj_data["records"].get("LB", [])

            high_trans: List[Dict[str, Any]] = []
            high_bili: List[Dict[str, Any]] = []

            for rec in lb_records:
                interp = rec.get("_interpretation", {})
                ratio = interp.get("ratio_to_uln")
                dt = rec.get("_LBDTC_parsed")
                testcd = rec.get("LBTESTCD", "").strip().upper()

                if ratio is None or dt is None:
                    continue

                if testcd in ("ALT", "AST") and ratio > 3.0:
                    high_trans.append({
                        "record": rec,
                        "date": dt,
                        "testcd": testcd,
                        "ratio": ratio,
                        "seq": rec.get("_seq"),
                        "raw_val": rec.get("LBORRES"),
                        "unit": rec.get("LBORRESU"),
                        "uln": interp.get("uln"),
                    })
                elif testcd == "BILI" and ratio > 2.0:
                    high_bili.append({
                        "record": rec,
                        "date": dt,
                        "testcd": testcd,
                        "ratio": ratio,
                        "seq": rec.get("_seq"),
                        "raw_val": rec.get("LBORRES"),
                        "unit": rec.get("LBORRESU"),
                        "uln": interp.get("uln"),
                    })

            matched_pairs: List[Tuple[Dict[str, Any], Dict[str, Any], int]] = []
            for t_item in high_trans:
                for b_item in high_bili:
                    delta_days = abs((t_item["date"] - b_item["date"]).days)
                    if delta_days <= 14:
                        matched_pairs.append((t_item, b_item, delta_days))

            if matched_pairs:
                t_match, b_match, days_diff = matched_pairs[0]

                evidence = [
                    {"domain": "LB", "usubjid": subj_id, "seq": t_match["seq"]},
                    {"domain": "LB", "usubjid": subj_id, "seq": b_match["seq"]},
                ]

                candidates.append({
                    "finding_id": f"POT_HYS_{subj_id}_{t_match['seq']}_{b_match['seq']}",
                    "finding_type": "potential_hys_law",
                    "usubjid": subj_id,
                    "cut": self.current_cut,
                    "protocol_version": self.current_protocol_version,
                    "status": "UNCONFIRMED_ADJUDICATION_REQUIRED",
                    "details": {
                        "biochemical_criteria_met": True,
                        "cholestasis_evaluated": False,
                        "alternative_explanation_evaluated": False,
                        "requires_adjudication": True,
                        "transaminase_test": t_match["testcd"],
                        "transaminase_ratio": t_match["ratio"],
                        "transaminase_date": t_match["date"].isoformat(),
                        "transaminase_raw": t_match["raw_val"],
                        "transaminase_unit": t_match["unit"],
                        "bilirubin_ratio": b_match["ratio"],
                        "bilirubin_date": b_match["date"].isoformat(),
                        "bilirubin_raw": b_match["raw_val"],
                        "bilirubin_unit": b_match["unit"],
                        "delta_days": days_diff,
                        "visit": t_match["record"].get("VISIT"),
                        "protocol_section": "§7 Liver safety",
                        "summary": (
                            f"Potential Hy's Law candidate {subj_id}: {t_match['testcd']} {t_match['raw_val']} {t_match['unit']} "
                            f"({t_match['ratio']:.2f}x ULN) and BILI {b_match['raw_val']} {b_match['unit']} "
                            f"({b_match['ratio']:.2f}x ULN) within {days_diff} days at visit {t_match['record'].get('VISIT')}."
                        ),
                    },
                    "evidence": evidence,
                })

        return candidates

    def find_serious_adverse_events(self, usubjid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Identify serious adverse events according to Protocol §6."""
        findings: List[Dict[str, Any]] = []
        subject_keys = [usubjid] if usubjid is not None and usubjid in self.subjects else sorted(self.subjects.keys())

        for subj_id in subject_keys:
            subj_data = self.subjects[subj_id]
            ae_records = subj_data["records"].get("AE", [])

            for rec in ae_records:
                aeser = rec.get("AESER", "").strip().upper()
                aeshosp = rec.get("AESHOSP", "").strip().upper()
                seq = rec.get("_seq")

                is_serious = (aeser == "Y" or aeshosp == "Y")
                is_override = (aeshosp == "Y" and aeser != "Y")

                if is_serious and seq is not None:
                    findings.append({
                        "finding_id": f"SAE_{subj_id}_{seq}",
                        "finding_type": "serious_adverse_event",
                        "usubjid": subj_id,
                        "cut": self.current_cut,
                        "protocol_version": self.current_protocol_version,
                        "status": "DETECTED",
                        "details": {
                            "aeterm": rec.get("AETERM"),
                            "aesev": rec.get("AESEV"),
                            "aeser": aeser,
                            "aeshosp": aeshosp,
                            "is_hospitalization_override": is_override,
                            "aestdtc": rec.get("_AESTDTC_iso") or rec.get("AESTDTC"),
                            "aeendtc": rec.get("_AEENDTC_iso") or rec.get("AEENDTC"),
                            "aeout": rec.get("AEOUT"),
                            "protocol_section": "§6 Safety reporting",
                        },
                        "evidence": [
                            {"domain": "AE", "usubjid": subj_id, "seq": seq}
                        ],
                    })

        return findings

    def find_exclusion_violations(self, usubjid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Identify screening exclusion violations."""
        if self.current_protocol_version < 2:
            return []

        findings: List[Dict[str, Any]] = []
        subject_keys = [usubjid] if usubjid is not None and usubjid in self.subjects else sorted(self.subjects.keys())

        for subj_id in subject_keys:
            subj_data = self.subjects[subj_id]
            lb_records = subj_data["records"].get("LB", [])

            for rec in lb_records:
                visit = rec.get("VISIT", "").strip().upper()
                testcd = rec.get("LBTESTCD", "").strip().upper()
                seq = rec.get("_seq")

                if visit == "SCREENING" and testcd == "CREAT" and seq is not None:
                    num_val = rec.get("_numeric_value")
                    unit = rec.get("LBORRESU", "").strip()

                    if num_val is not None and num_val > 1.5:
                        findings.append({
                            "finding_id": f"EXCL_CREAT_{subj_id}_{seq}",
                            "finding_type": "exclusion_violation_creatinine",
                            "usubjid": subj_id,
                            "cut": self.current_cut,
                            "protocol_version": self.current_protocol_version,
                            "status": "DETECTED",
                            "details": {
                                "protocol_version_introduced": 2,
                                "criterion": "Creatinine > 1.5 mg/dL at screening (renal impairment)",
                                "test": "CREAT",
                                "value": num_val,
                                "unit": unit,
                                "threshold": 1.5,
                                "visit": "SCREENING",
                                "date": rec.get("_LBDTC_iso"),
                                "protocol_section": "§3 Exclusion criteria (Amendment 2)",
                            },
                            "evidence": [
                                {"domain": "LB", "usubjid": subj_id, "seq": seq}
                            ],
                        })

        return findings

    def find_prohibited_medications(self, usubjid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Identify prohibited concomitant medications according to Protocol §5."""
        findings: List[Dict[str, Any]] = []

        prohibited_classes: Set[str] = {"SYSTEMIC_GLUCOCORTICOID"}
        if self.current_protocol_version >= 3:
            prohibited_classes.add("SULFONYLUREA")

        subject_keys = [usubjid] if usubjid is not None and usubjid in self.subjects else sorted(self.subjects.keys())

        for subj_id in subject_keys:
            subj_data = self.subjects[subj_id]
            cm_records = subj_data["records"].get("CM", [])

            for rec in cm_records:
                cmclas = rec.get("CMCLAS", "").strip().upper()
                seq = rec.get("_seq")

                if cmclas in prohibited_classes and seq is not None:
                    findings.append({
                        "finding_id": f"PROHIB_MED_{subj_id}_{seq}",
                        "finding_type": "prohibited_concomitant_medication",
                        "usubjid": subj_id,
                        "cut": self.current_cut,
                        "protocol_version": self.current_protocol_version,
                        "status": "DETECTED",
                        "details": {
                            "medication_class": cmclas,
                            "treatment": rec.get("CMTRT"),
                            "indication": rec.get("CMINDC"),
                            "dose": rec.get("CMDOSE"),
                            "start_date": rec.get("_CMSTDTC_iso") or rec.get("CMSTDTC"),
                            "prohibited_since_protocol_version": 3 if cmclas == "SULFONYLUREA" else 1,
                            "protocol_section": "§5 Prohibited concomitant medications",
                        },
                        "evidence": [
                            {"domain": "CM", "usubjid": subj_id, "seq": seq}
                        ],
                    })

        return findings

    def find_visit_window_deviations(self, usubjid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Identify visit schedule window deviations according to Protocol §4."""
        findings: List[Dict[str, Any]] = []
        allowed_window = 7 if self.current_protocol_version == 1 else 3

        subject_keys = [usubjid] if usubjid is not None and usubjid in self.subjects else sorted(self.subjects.keys())

        for subj_id in subject_keys:
            subj_data = self.subjects[subj_id]
            dm_rec = subj_data.get("demographics", {})
            baseline_dt = dm_rec.get("_RFSTDTC_parsed")

            if not baseline_dt:
                continue

            vs_records = subj_data["records"].get("VS", [])

            visited_map: Dict[str, Tuple[datetime.date, int, str]] = {}
            for rec in vs_records:
                visit = rec.get("VISIT", "").strip().upper()
                dt = rec.get("_VSDTC_parsed")
                seq = rec.get("_seq")
                if visit in self.TARGET_SCHEDULE and dt is not None and seq is not None:
                    if visit not in visited_map:
                        visited_map[visit] = (dt, seq, rec.get("_VSDTC_iso") or "")

            for visit, (v_date, v_seq, v_iso) in visited_map.items():
                target_day = self.TARGET_SCHEDULE[visit]
                actual_day = (v_date - baseline_dt).days
                delta_days = abs(actual_day - target_day)

                if delta_days > allowed_window:
                    findings.append({
                        "finding_id": f"DEV_VISIT_{subj_id}_{visit}",
                        "finding_type": "visit_window_deviation",
                        "usubjid": subj_id,
                        "cut": self.current_cut,
                        "protocol_version": self.current_protocol_version,
                        "status": "DETECTED",
                        "details": {
                            "visit": visit,
                            "target_day": target_day,
                            "actual_day": actual_day,
                            "delta_days": delta_days,
                            "allowed_window_days": allowed_window,
                            "visit_date": v_iso,
                            "baseline_date": dm_rec.get("_RFSTDTC_iso"),
                            "protocol_section": "§4 Visit schedule and windows",
                        },
                        "evidence": [
                            {"domain": "VS", "usubjid": subj_id, "seq": v_seq}
                        ],
                    })

        return findings

    def get_findings(self, usubjid: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return all deterministic findings for current cut, optionally filtered by subject."""
        if usubjid is not None:
            return [f for f in self.findings if f.get("usubjid") == usubjid]
        return list(self.findings)

    # =========================================================================
    # G. EVIDENCE INTEGRITY CHECKER
    # =========================================================================

    def validate_evidence(self, findings: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """Validate every evidence reference in findings against current cut-aware graph."""
        if findings is None:
            findings = self.get_findings()

        errors: List[Dict[str, Any]] = []
        total_refs = 0

        for finding in findings:
            f_id = finding.get("finding_id", "UNKNOWN")
            evidence_list = finding.get("evidence", [])

            for ev in evidence_list:
                total_refs += 1
                domain = ev.get("domain")
                usubjid = ev.get("usubjid")
                seq = ev.get("seq")

                if domain not in self.DOMAINS:
                    errors.append({
                        "finding_id": f_id,
                        "evidence": ev,
                        "reason": f"Nonexistent domain: {domain}",
                    })
                    continue

                if usubjid not in self.subjects:
                    errors.append({
                        "finding_id": f_id,
                        "evidence": ev,
                        "reason": f"Nonexistent subject: {usubjid}",
                    })
                    continue

                triple = (domain, usubjid, seq)
                if triple not in self.records_by_key:
                    errors.append({
                        "finding_id": f_id,
                        "evidence": ev,
                        "reason": f"Record triple {triple} not found in active graph records",
                    })
                    continue

                record = self.records_by_key[triple]
                cut_avail_str = record.get("cut_available")
                if cut_avail_str:
                    try:
                        c_avail = int(cut_avail_str)
                        if self.current_cut is not None and c_avail > self.current_cut:
                            errors.append({
                                "finding_id": f_id,
                                "evidence": ev,
                                "reason": f"Record from future cut {c_avail} > current {self.current_cut}",
                            })
                    except ValueError:
                        pass

        return {
            "total_findings": len(findings),
            "total_evidence_references": total_refs,
            "valid": len(errors) == 0,
            "invalid_count": len(errors),
            "errors": errors,
        }


class Atlas:
    """Agent that queries the StudyGraph and produces schema-compliant answers."""

    def __init__(self, graph: StudyGraph):
        self.graph = graph
        from backend.atlas_agent import Atlas as BackendAtlas
        self._delegate = BackendAtlas(graph)

    def answer(self, question: Any) -> Any:
        """Answer clinical question citing valid evidence from StudyGraph."""
        return self._delegate.answer(question)
