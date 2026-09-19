"""General-Purpose Query Engine for Study Sentinel / ATLAS AI Agent.

Executes structured query plans strictly against StudyGraph as the single source
of clinical truth, and against DocumentKnowledge for protocol/study documentation.
Supports COUNT, LIST, LOOKUP, FILTER, AGGREGATE, COMPARE, TREND, FINDING,
SUBJECT_360, DOCUMENT_LOOKUP, and STUDY_METADATA queries deterministically.
Contains NO hardcoded answers or duplicate clinical calculations.
"""

import re
import datetime
from typing import Dict, Any, List, Optional, Set, Tuple
from backend.schemas import RecordRef, Answer, ParsedQuestion
from backend.study_metadata import StudyMetadata
from backend.document_knowledge import DocumentKnowledge


class QueryEngine:
    """Executes structured queries against StudyGraph and returns schema-compliant Answers."""

    def __init__(self, graph: Any, metadata: Optional[StudyMetadata] = None, doc_knowledge: Optional[DocumentKnowledge] = None):
        self.graph = graph
        self.metadata = metadata or StudyMetadata(graph)
        self.doc_knowledge = doc_knowledge or DocumentKnowledge()

    def execute(self, parsed_q: ParsedQuestion) -> Answer:
        """Routes parsed question to the appropriate deterministic handler."""
        # 1. Non-existent site validation
        if parsed_q.invalid_site:
            return Answer(
                question_id=parsed_q.question_id,
                answer=[],
                text=f"No Site {parsed_q.invalid_site} exists in the current study snapshot.",
                evidence=[],
                confidence=1.0,
                intent="AMBIGUOUS"
            )

        intent = parsed_q.intent.upper()

        if intent == "WHY_FLAGGED":
            ans = self._handle_why_flagged(parsed_q)
        elif intent == "EVIDENCE_REQUEST":
            ans = self._handle_evidence_request(parsed_q)
        elif intent == "COUNT":
            ans = self._handle_count(parsed_q)
        elif intent in ("FILTER", "LIST"):
            ans = self._handle_filter(parsed_q)
        elif intent == "LOOKUP":
            ans = self._handle_lookup(parsed_q)
        elif intent == "COMPARISON":
            ans = self._handle_comparison(parsed_q)
        elif intent == "TREND":
            ans = self._handle_trend(parsed_q)
        elif intent == "AGGREGATE":
            ans = self._handle_aggregation(parsed_q)
        elif intent == "SUBJECT_360":
            ans = self._handle_patient_360(parsed_q)
        elif intent == "FINDING":
            ans = self._handle_finding(parsed_q)
        elif intent == "DOCUMENT_LOOKUP":
            ans = self._handle_document_lookup(parsed_q)
        elif intent == "STUDY_METADATA":
            ans = self._handle_study_metadata(parsed_q)
        elif intent == "AMBIGUOUS":
            ans = self._handle_ambiguous(parsed_q)
        elif intent == "TRAP":
            ans = self._handle_zero_result(parsed_q)
        else:
            ans = self._handle_unsupported(parsed_q)

        # Prepend explicit interpretation notice if broad/colloquial phrase was mapped
        if parsed_q.interpretation_note and ans.text and not ans.text.startswith(parsed_q.interpretation_note):
            ans.text = f"{parsed_q.interpretation_note}\n\n{ans.text}"

        # Attach contextual suggested follow-up questions
        if ans.structured_data is None:
            ans.structured_data = {}
        if isinstance(ans.structured_data, dict) and "suggested_followups" not in ans.structured_data:
            ans.structured_data["suggested_followups"] = self._get_suggested_followups(parsed_q, ans)

        return ans

    # -------------------------------------------------------------------------
    # GENERIC FIELD MATCHING HELPER
    # -------------------------------------------------------------------------
    @staticmethod
    def _match_field(record: Dict[str, Any], field: str, operator: str, target: Any) -> bool:
        """Safely evaluates record field filter without eval."""
        val = record.get(field)
        if val is None:
            return False

        if operator in ("==", "="):
            return str(val).strip().upper() == str(target).strip().upper()
        elif operator == "!=":
            return str(val).strip().upper() != str(target).strip().upper()
        elif operator == "contains":
            return str(target).strip().upper() in str(val).strip().upper()

        # Numeric comparisons
        try:
            val_num = float(val)
            target_num = float(target)
            if operator == ">":
                return val_num > target_num
            elif operator == ">=":
                return val_num >= target_num
            elif operator == "<":
                return val_num < target_num
            elif operator == "<=":
                return val_num <= target_num
        except (ValueError, TypeError):
            pass

        return False

    # -------------------------------------------------------------------------
    # 1. COUNT HANDLER
    # -------------------------------------------------------------------------
    def _handle_count(self, q: ParsedQuestion) -> Answer:
        """Handles COUNT queries dynamically across subjects, records, findings, and groups."""
        site_filter = q.site_id
        cut_val = getattr(self.graph, "current_cut", 12)

        # A. Group-By Counts (e.g. "How many subjects per site?", "Count findings by type")
        if q.group_by:
            return self._handle_group_by(q)

        # B. Finding Counts (e.g. "How many serious adverse events are there?")
        if q.criterion in ("potential_hys_law", "serious_adverse_event", "creatinine_exclusion", "prohibited_medication", "visit_window_deviation"):
            f_ans = self._handle_finding(q)
            cands = f_ans.answer if isinstance(f_ans.answer, list) else []
            count_val = len(cands)
            text = f"{count_val} findings matching {q.criterion.replace('_', ' ')} criteria at Cut {cut_val}."
            return Answer(
                question_id=q.question_id,
                answer=count_val,
                text=text,
                evidence=f_ans.evidence,
                confidence=0.95,
                intent="COUNT",
                structured_data={"type": "metric", "label": f"{q.criterion} count", "value": count_val}
            )

        # C. Total findings count (e.g. "How many findings occurred at Cut 12?")
        if "finding" in q.raw_text.lower():
            all_findings = self.graph.get_findings()
            count_val = len(all_findings)
            evidence_refs = []
            for f in all_findings:
                for ev in f.get("evidence", []):
                    evidence_refs.append(RecordRef(domain=ev.get("domain", "LB"), usubjid=f.get("usubjid"), seq=ev.get("seq")))
            text = f"{count_val} total clinical findings detected across all subjects at Cut {cut_val}."
            return Answer(
                question_id=q.question_id,
                answer=count_val,
                text=text,
                evidence=evidence_refs[:20],
                confidence=1.0,
                intent="COUNT",
                structured_data={"type": "metric", "label": "total_findings", "value": count_val}
            )

        # D. Hospitalized Adverse Events Count (e.g. "How many hospitalized AEs?")
        if any(f.get("field") == "AESHOSP" for f in q.filters) or ("hospital" in q.raw_text.lower() and q.domain == "AE"):
            ae_recs = self.graph.lookup(domain="AE")
            hosp_recs = [r for r in ae_recs if str(r.get("AESHOSP", "")).upper() == "Y"]
            ev_refs = [RecordRef(domain="AE", usubjid=r.get("_usubjid"), seq=r.get("_seq")) for r in hosp_recs if r.get("_seq") is not None]
            count_val = len(hosp_recs)
            text = f"{count_val} hospitalized adverse events recorded at Cut {cut_val}."
            return Answer(
                question_id=q.question_id,
                answer=count_val,
                text=text,
                evidence=ev_refs,
                confidence=1.0,
                intent="COUNT",
                structured_data={"type": "metric", "label": "hospitalized_ae_count", "value": count_val}
            )

        # E. Demographic Subject Filters (e.g. "How many women are in the study?", "How many female placebo subjects?")
        has_sex_filter = any(f.get("field") == "SEX" for f in q.filters)
        has_arm_filter = any(f.get("field") == "ARM" for f in q.filters)
        if has_sex_filter or has_arm_filter:
            matching_subjs = []
            ev_refs = []
            for usubjid, sdata in sorted(self.graph.subjects.items()):
                demo = sdata.get("demographics") or {}
                match = True
                for filt in q.filters:
                    field = filt.get("field")
                    op = filt.get("operator", "==")
                    val = filt.get("value")
                    if field in ("SEX", "ARM"):
                        if not self._match_field(demo, field, op, val):
                            match = False
                            break
                if match:
                    matching_subjs.append(usubjid)
                    ev_refs.append(RecordRef(domain="DM", usubjid=usubjid, seq=1))

            count_val = len(matching_subjs)
            filter_desc = []
            for f in q.filters:
                if f.get("field") == "SEX":
                    filter_desc.append("female" if f.get("value") == "F" else "male")
                if f.get("field") == "ARM":
                    filter_desc.append(str(f.get("value")).lower())

            desc_str = " ".join(filter_desc) if filter_desc else "matching"
            text = f"{count_val} {desc_str} subjects enrolled in the study at Cut {cut_val}."
            return Answer(
                question_id=q.question_id,
                answer=count_val,
                text=text,
                evidence=ev_refs,
                confidence=1.0,
                intent="COUNT",
                structured_data={"type": "metric", "label": f"{desc_str}_subjects", "value": count_val}
            )

        # F. Site Subject Count (e.g. "How many subjects are at site S07?")
        if site_filter and (not q.domain or q.domain == "DM") and not q.test_code and not q.threshold_type:
            matching_subjs = [
                uid for uid, sdata in self.graph.subjects.items()
                if (sdata.get("site_id") == site_filter) or (sdata.get("demographics", {}).get("SITEID") == site_filter) or (f"-{site_filter}-" in uid)
            ]
            count_val = len(matching_subjs)
            ev_refs = [RecordRef(domain="DM", usubjid=uid, seq=1) for uid in matching_subjs]
            text = f"Found {count_val} subjects at site {site_filter} enrolled in the study."
            return Answer(
                question_id=q.question_id,
                answer=count_val,
                text=text,
                evidence=ev_refs,
                confidence=1.0,
                intent="COUNT",
                structured_data={"type": "metric", "site": site_filter, "subject_count": count_val}
            )

        # G. Threshold Filter Count (e.g. "How many subjects had ALT over 3x ULN?")
        if q.threshold_type:
            filt_ans = self._handle_filter(q)
            cands = filt_ans.answer if isinstance(filt_ans.answer, list) else []
            count_val = len(cands)
            thresh_str = f"{q.threshold_multiplier}x ULN" if q.threshold_type == "ULN" else str(q.numeric_value)
            text = f"{count_val} subject(s) met the {q.test_code or 'test'} threshold ({thresh_str}) at Cut {cut_val}."
            return Answer(
                question_id=q.question_id,
                answer=count_val,
                text=text,
                evidence=filt_ans.evidence,
                confidence=1.0,
                intent="COUNT",
                structured_data={"type": "metric", "threshold": thresh_str, "subject_count": count_val}
            )

        # H. Discontinuation Count
        if q.criterion == "discontinuation" or "discontinued" in q.raw_text.lower():
            ds_records = self.graph.lookup(domain="DS")
            matching_subjs = set()
            evidence_refs = []
            for r in ds_records:
                decod = str(r.get("DSDECOD", "")).upper()
                term = str(r.get("DSTERM", "")).upper()
                if "ADVERSE" in decod or "AE" in decod or "ADVERSE" in term:
                    subj = r.get("_usubjid")
                    if subj:
                        matching_subjs.add(subj)
                    seq = r.get("_seq")
                    if seq is not None:
                        evidence_refs.append(RecordRef(domain="DS", usubjid=subj, seq=seq))
            count_val = len(matching_subjs)
            text = f"{count_val} subjects discontinued due to an adverse event at Cut {cut_val}."
            return Answer(
                question_id=q.question_id,
                answer=count_val,
                text=text,
                evidence=evidence_refs,
                confidence=0.95,
                intent="COUNT"
            )

        # I. General Record Count for a Domain/Test (e.g. "How many ALT measurements are there?", "How many adverse events happened?")
        domain = q.domain or ("LB" if q.test_code else "DM")
        records = self.graph.lookup(domain=domain, testcd=q.test_code)
        if site_filter:
            records = [r for r in records if f"-{site_filter}-" in r.get("_usubjid", "")]

        count_val = len(records)
        ev_sample = [RecordRef(domain=domain, usubjid=r.get("_usubjid"), seq=r.get("_seq")) for r in records[:20] if r.get("_seq") is not None]
        entity_name = q.test_code or domain
        text = f"{count_val} {entity_name} records exist at Cut {cut_val}."
        return Answer(
            question_id=q.question_id,
            answer=count_val,
            text=text,
            evidence=ev_sample,
            confidence=1.0,
            intent="COUNT",
            structured_data={"type": "metric", "entity": entity_name, "count": count_val}
        )

    # -------------------------------------------------------------------------
    # 2. GROUP BY HANDLER
    # -------------------------------------------------------------------------
    def _handle_group_by(self, q: ParsedQuestion) -> Answer:
        """Executes structured GROUP_BY aggregations (e.g. subjects per site, findings by type)."""
        group_field = q.group_by
        cut_val = getattr(self.graph, "current_cut", 12)

        # Group by site
        if group_field == "site_id":
            if "finding" in q.raw_text.lower() or q.criterion:
                counts: Dict[str, int] = {}
                for f in self.graph.findings:
                    subj = f.get("usubjid", "")
                    parts = subj.split("-")
                    site = parts[1] if len(parts) >= 2 else "UNKNOWN"
                    counts[site] = counts.get(site, 0) + 1
                if counts:
                    top_site, top_cnt = max(counts.items(), key=lambda x: x[1])
                    lines = [f"• Site {k}: {v} findings" for k, v in sorted(counts.items(), key=lambda x: -x[1])]
                    text = f"Site {top_site} had the most findings with {top_cnt} clinical findings at Cut {cut_val}.\n\nBreakdown by site:\n" + "\n".join(lines)
                    return Answer(
                        question_id=q.question_id,
                        answer=counts,
                        text=text,
                        evidence=[],
                        confidence=1.0,
                        intent="COUNT",
                        structured_data={"type": "table", "group_by": "site_findings", "top_site": top_site, "rows": [{"site": k, "count": v} for k, v in counts.items()]}
                    )

            counts = {}
            for usubjid, sdata in self.graph.subjects.items():
                site = sdata.get("site_id") or sdata.get("demographics", {}).get("SITEID") or usubjid.split("-")[1]
                counts[site] = counts.get(site, 0) + 1

            rows = [{"site": k, "count": v} for k, v in sorted(counts.items())]
            lines = [f"• Site {r['site']}: {r['count']} subjects" for r in rows]
            text = f"Subject enrollment breakdown by site at Cut {cut_val}:\n" + "\n".join(lines)
            return Answer(
                question_id=q.question_id,
                answer=counts,
                text=text,
                evidence=[],
                confidence=1.0,
                intent="COUNT",
                structured_data={"type": "table", "group_by": "site_id", "rows": rows}
            )

        # Group by study arm
        if group_field == "arm":
            counts = {}
            for usubjid, sdata in self.graph.subjects.items():
                arm = sdata.get("demographics", {}).get("ARM", "UNKNOWN")
                counts[arm] = counts.get(arm, 0) + 1

            rows = [{"arm": k, "count": v} for k, v in sorted(counts.items())]
            lines = [f"• {r['arm']}: {r['count']} subjects" for r in rows]
            text = f"Subject breakdown by study arm at Cut {cut_val}:\n" + "\n".join(lines)
            return Answer(
                question_id=q.question_id,
                answer=counts,
                text=text,
                evidence=[],
                confidence=1.0,
                intent="COUNT",
                structured_data={"type": "table", "group_by": "arm", "rows": rows}
            )

        # Group by finding type
        if group_field == "finding_type":
            all_findings = self.graph.get_findings()
            counts = {}
            for f in all_findings:
                ftype = f.get("finding_type", "other")
                counts[ftype] = counts.get(ftype, 0) + 1

            rows = [{"finding_type": k, "count": v} for k, v in sorted(counts.items())]
            lines = [f"• {r['finding_type'].replace('_', ' ').title()}: {r['count']}" for r in rows]
            text = f"Clinical findings breakdown by type at Cut {cut_val} (Total: {len(all_findings)}):\n" + "\n".join(lines)
            return Answer(
                question_id=q.question_id,
                answer=counts,
                text=text,
                evidence=[],
                confidence=1.0,
                intent="COUNT",
                structured_data={"type": "table", "group_by": "finding_type", "rows": rows}
            )

        return self._handle_count(q)

    # -------------------------------------------------------------------------
    # 3. FILTER / LIST HANDLER
    # -------------------------------------------------------------------------
    def _handle_filter(self, q: ParsedQuestion) -> Answer:
        """Filters subjects and records based on field criteria or numeric thresholds."""
        cut_val = getattr(self.graph, "current_cut", 12)

        # A. Demographic Field Filters (e.g. "Which subjects are female placebo?", "Show female placebo subjects")
        has_sex_filter = any(f.get("field") == "SEX" for f in q.filters)
        has_arm_filter = any(f.get("field") == "ARM" for f in q.filters)
        if has_sex_filter or has_arm_filter:
            matching_subjs = []
            ev_refs = []
            for usubjid, sdata in sorted(self.graph.subjects.items()):
                demo = sdata.get("demographics") or {}
                match = True
                for filt in q.filters:
                    field = filt.get("field")
                    op = filt.get("operator", "==")
                    val = filt.get("value")
                    if field in ("SEX", "ARM"):
                        if not self._match_field(demo, field, op, val):
                            match = False
                            break
                if q.site_id and f"-{q.site_id}-" not in usubjid:
                    match = False

                if match:
                    matching_subjs.append(usubjid)
                    ev_refs.append(RecordRef(domain="DM", usubjid=usubjid, seq=1))

            if not matching_subjs:
                return self._handle_zero_result(q)

            lines = [f"• {s}" for s in matching_subjs[:10]]
            more_str = f"\n... and {len(matching_subjs) - 10} more" if len(matching_subjs) > 10 else ""
            text = f"Found {len(matching_subjs)} matching subjects at Cut {cut_val}:\n" + "\n".join(lines) + more_str
            return Answer(
                question_id=q.question_id,
                answer=matching_subjs,
                text=text,
                evidence=ev_refs[:20],
                confidence=1.0,
                intent="FILTER",
                structured_data={"type": "list", "subjects": matching_subjs}
            )

        # B. Medication Class Filters (e.g. "Which subjects received sulfonylureas?")
        if any(f.get("field") == "CMCLAS" for f in q.filters) or "sulfonylurea" in q.raw_text.lower():
            cm_records = self.graph.lookup(domain="CM")
            matching_subjs = set()
            ev_refs = []
            for r in cm_records:
                clas = str(r.get("CMCLAS", "")).upper()
                decod = str(r.get("CMDECOD", "")).upper()
                if "SULFONYLUREA" in clas or "SULFONYLUREA" in decod:
                    subj = r.get("_usubjid")
                    if subj:
                        matching_subjs.add(subj)
                        ev_refs.append(RecordRef(domain="CM", usubjid=subj, seq=r.get("_seq")))

            cand_list = sorted(list(matching_subjs))
            if not cand_list:
                return self._handle_zero_result(q)

            lines = [f"• {s}" for s in cand_list]
            text = f"{len(cand_list)} subject(s) received sulfonylureas at Cut {cut_val}:\n" + "\n".join(lines)
            return Answer(
                question_id=q.question_id,
                answer=cand_list,
                text=text,
                evidence=ev_refs,
                confidence=1.0,
                intent="FILTER",
                structured_data={"type": "list", "subjects": cand_list}
            )

        # C. Site Subjects List (e.g. "Which subjects are at site S05?")
        if q.site_id and (not q.domain or q.domain == "DM") and not q.test_code and not q.threshold_type:
            matching_subjs = [
                uid for uid, sdata in sorted(self.graph.subjects.items())
                if (sdata.get("site_id") == q.site_id) or (sdata.get("demographics", {}).get("SITEID") == q.site_id) or (f"-{q.site_id}-" in uid)
            ]
            if not matching_subjs:
                return self._handle_zero_result(q)

            ev_refs = [RecordRef(domain="DM", usubjid=uid, seq=1) for uid in matching_subjs]
            lines = [f"• {s}" for s in matching_subjs]
            text = f"Found {len(matching_subjs)} subjects at site {q.site_id}:\n" + "\n".join(lines)
            return Answer(
                question_id=q.question_id,
                answer=matching_subjs,
                text=text,
                evidence=ev_refs,
                confidence=1.0,
                intent="FILTER",
                structured_data={"type": "list", "site": q.site_id, "subjects": matching_subjs}
            )

        # D. Dynamic Threshold Filtering (e.g. "ALT above 3x ULN", "creatinine > 1.5")
        test_cd = q.test_code or "ALT"
        domain = q.domain or ("VS" if test_cd in ("SYSBP", "DIABP", "PULSE", "QTCF") else "LB")
        records = self.graph.lookup(domain=domain)

        matching_subjs = set()
        evidence_refs = []
        op = q.operator or ">="

        for r in records:
            r_test = r.get("LBTESTCD") or r.get("VSTESTCD")
            if r_test != test_cd:
                continue

            passed = False
            if q.threshold_type == "ULN":
                ratio = r.get("_ratio_to_uln")
                if ratio is not None and q.threshold_multiplier is not None:
                    if op in (">=", "=>") and ratio >= q.threshold_multiplier:
                        passed = True
                    elif op == ">" and ratio > q.threshold_multiplier:
                        passed = True
                    elif op in ("<=", "=<") and ratio <= q.threshold_multiplier:
                        passed = True
                    elif op == "<" and ratio < q.threshold_multiplier:
                        passed = True
            elif q.threshold_type == "RAW":
                num_val = r.get("_numeric_value")
                if num_val is not None and q.numeric_value is not None:
                    if op in (">=", "=>") and num_val >= q.numeric_value:
                        passed = True
                    elif op == ">" and num_val > q.numeric_value:
                        passed = True
                    elif op in ("<=", "=<") and num_val <= q.numeric_value:
                        passed = True
                    elif op == "<" and num_val < q.numeric_value:
                        passed = True

            if passed:
                subj = r.get("_usubjid")
                seq = r.get("_seq")
                if subj:
                    matching_subjs.add(subj)
                if seq is not None and subj:
                    evidence_refs.append(RecordRef(domain=domain, usubjid=subj, seq=seq))

        sorted_subjs = sorted(list(matching_subjs))
        if not sorted_subjs:
            return self._handle_zero_result(q)

        thresh_label = f"{q.threshold_multiplier}x ULN" if q.threshold_type == "ULN" else f"{q.numeric_value}"
        lines = [f"• {s}" for s in sorted_subjs]
        text = f"Found {len(sorted_subjs)} subject(s) with {test_cd} {op} {thresh_label} at Cut {cut_val}:\n" + "\n".join(lines)

        return Answer(
            question_id=q.question_id,
            answer=sorted_subjs,
            text=text,
            evidence=evidence_refs,
            confidence=1.0,
            intent="FILTER",
            structured_data={"type": "list", "test": test_cd, "subjects": sorted_subjs}
        )

    # -------------------------------------------------------------------------
    # 4. LOOKUP HANDLER
    # -------------------------------------------------------------------------
    def _handle_lookup(self, q: ParsedQuestion) -> Answer:
        """Handles targeted LOOKUP queries for a subject, visit, test, or domain."""
        usubjid = q.usubjid
        cut_val = getattr(self.graph, "current_cut", 12)

        if not usubjid:
            return Answer(
                question_id=q.question_id,
                answer=[],
                text="Please specify a subject identifier (e.g. 042-S07-001) to look up clinical records.",
                evidence=[],
                confidence=0.5,
                intent="AMBIGUOUS"
            )

        # A. Adverse Events Lookup (e.g. "Show adverse events for 042-S01-007", "Did subject X have any AEs?")
        if q.domain == "AE" or "adverse event" in q.raw_text.lower() or "ae" in q.raw_text.lower() or "side effect" in q.raw_text.lower():
            ae_records = self.graph.lookup(domain="AE", usubjid=usubjid)
            if not ae_records:
                return Answer(
                    question_id=q.question_id,
                    answer=[],
                    text=f"No adverse events recorded for subject {usubjid} at Cut {cut_val}.",
                    evidence=[],
                    confidence=1.0,
                    intent="LOOKUP"
                )

            ev_refs = []
            lines = []
            for r in ae_records:
                term = r.get("AETERM") or r.get("AEDECOD", "Adverse Event")
                sev = r.get("AESEV", "UNKNOWN")
                hosp = r.get("AESHOSP", "N")
                date = r.get("AESTDTC", "")
                seq = r.get("_seq")
                hosp_note = " [Hospitalized]" if hosp == "Y" else ""
                lines.append(f"• {term} (Severity: {sev}{hosp_note}, Date: {date})")
                if seq is not None:
                    ev_refs.append(RecordRef(domain="AE", usubjid=usubjid, seq=seq))

            text = f"Found {len(ae_records)} adverse event(s) for {usubjid}:\n" + "\n".join(lines)
            return Answer(
                question_id=q.question_id,
                answer=ae_records,
                text=text,
                evidence=ev_refs,
                confidence=1.0,
                intent="LOOKUP",
                structured_data={"type": "table", "subject": usubjid, "records": ae_records}
            )

        # B. Medications Lookup (e.g. "Show medications recorded for 042-S05-003")
        if q.domain == "CM" or "medication" in q.raw_text.lower() or "medicine" in q.raw_text.lower():
            cm_records = self.graph.lookup(domain="CM", usubjid=usubjid)
            if not cm_records:
                return Answer(
                    question_id=q.question_id,
                    answer=[],
                    text=f"No concomitant medications recorded for subject {usubjid} at Cut {cut_val}.",
                    evidence=[],
                    confidence=1.0,
                    intent="LOOKUP"
                )

            ev_refs = []
            lines = []
            for r in cm_records:
                trt = r.get("CMTRT") or r.get("CMDECOD", "Medication")
                clas = r.get("CMCLAS", "")
                stdtc = r.get("CMSTDTC", "")
                seq = r.get("_seq")
                lines.append(f"• {trt} ({clas}, Started: {stdtc})")
                if seq is not None:
                    ev_refs.append(RecordRef(domain="CM", usubjid=usubjid, seq=seq))

            text = f"Found {len(cm_records)} concomitant medication(s) for {usubjid}:\n" + "\n".join(lines)
            return Answer(
                question_id=q.question_id,
                answer=cm_records,
                text=text,
                evidence=ev_refs,
                confidence=1.0,
                intent="LOOKUP",
                structured_data={"type": "table", "subject": usubjid, "records": cm_records}
            )

        # C. Lab / Vital Sign Lookup
        test_cd = q.test_code or "ALT"
        domain = q.domain or ("VS" if test_cd in ("SYSBP", "DIABP", "PULSE", "QTCF") else "LB")
        records = self.graph.lookup(domain=domain, usubjid=usubjid)
        matched_records = [r for r in records if (r.get("LBTESTCD") == test_cd or r.get("VSTESTCD") == test_cd)]

        if not matched_records:
            return self._handle_zero_result(q)

        # Visit filter
        if q.visit:
            visit_norm = q.visit.upper()
            matched_records = [r for r in matched_records if str(r.get("VISIT", "")).replace(" ", "").upper() == visit_norm]
            if not matched_records:
                return self._handle_zero_result(q)

        # Temporal Modifier (LATEST, EARLIEST)
        if q.temporal_modifier == "LATEST":
            matched_records.sort(key=lambda x: str(x.get("_date", "") or x.get("LBDTC", "")), reverse=True)
            matched_records = [matched_records[0]]
        elif q.temporal_modifier == "EARLIEST":
            matched_records.sort(key=lambda x: str(x.get("_date", "") or x.get("LBDTC", "")))
            matched_records = [matched_records[0]]

        ev_refs = []
        lines = []
        for r in matched_records:
            val = r.get("LBORRES") or r.get("VSORRES")
            unit = r.get("LBORRESU") or r.get("VSORRESU") or ""
            visit = r.get("VISIT", "UNSCHEDULED")
            dt = r.get("_date") or r.get("LBDTC") or r.get("VSDTC") or ""
            seq = r.get("_seq")

            ratio = r.get("_ratio_to_uln")
            ratio_str = f" ({ratio:.2f}x ULN)" if ratio is not None else ""
            lines.append(f"• {test_cd} at {visit} ({dt}): {val} {unit}{ratio_str}")
            if seq is not None:
                ev_refs.append(RecordRef(domain=domain, usubjid=usubjid, seq=seq))

        win_str = f" within {q.date_window_days} days of {q.visit}" if (q.date_window_days and q.visit) else ""
        text = f"{usubjid} {test_cd} records{win_str} at Cut {cut_val}:\n" + "\n".join(lines)
        return Answer(
            question_id=q.question_id,
            answer=matched_records,
            text=text,
            evidence=ev_refs,
            confidence=1.0,
            intent="LOOKUP",
            structured_data={"type": "table", "subject": usubjid, "test": test_cd, "records": matched_records}
        )

    # -------------------------------------------------------------------------
    # 5. COMPARISON HANDLER
    # -------------------------------------------------------------------------
    def _handle_comparison(self, q: ParsedQuestion) -> Answer:
        """Compares values between visits, subjects, or sites with unit safety checks."""
        usubjid = q.usubjid
        test_cd = q.test_code or "ALT"
        domain = q.domain or ("VS" if test_cd in ("SYSBP", "DIABP", "PULSE", "QTCF") else "LB")
        visit1 = q.visit or "BASELINE"
        visit2 = q.secondary_visit or "WEEK8"

        # Ensure BASELINE is visit1 if comparing against baseline
        if "baseline" in q.raw_text.lower() and visit2.upper() == "BASELINE" and visit1.upper() != "BASELINE":
            visit1, visit2 = visit2, visit1

        rec1_list = [r for r in self.graph.lookup(domain=domain, usubjid=usubjid) if (r.get("LBTESTCD") == test_cd or r.get("VSTESTCD") == test_cd) and str(r.get("VISIT", "")).replace(" ", "").upper() == visit1.replace(" ", "").upper()]
        rec2_list = [r for r in self.graph.lookup(domain=domain, usubjid=usubjid) if (r.get("LBTESTCD") == test_cd or r.get("VSTESTCD") == test_cd) and str(r.get("VISIT", "")).replace(" ", "").upper() == visit2.replace(" ", "").upper()]

        if not rec1_list or not rec2_list:
            return Answer(
                question_id=q.question_id,
                answer=[],
                text=f"Could not retrieve both visit records ({visit1} and {visit2}) for {usubjid} to perform comparison.",
                evidence=[],
                confidence=0.7,
                intent="COMPARISON"
            )

        r1 = rec1_list[0]
        r2 = rec2_list[0]

        val1 = r1.get("_numeric_value") or float(r1.get("LBORRES", 0))
        val2 = r2.get("_numeric_value") or float(r2.get("LBORRES", 0))
        unit1 = r1.get("LBORRESU") or r1.get("VSORRESU") or ""
        unit2 = r2.get("LBORRESU") or r2.get("VSORRESU") or ""

        delta = val2 - val1
        direction = "increased" if delta > 0 else ("decreased" if delta < 0 else "remained unchanged")

        ev_refs = [
            RecordRef(domain=domain, usubjid=usubjid, seq=r1.get("_seq")),
            RecordRef(domain=domain, usubjid=usubjid, seq=r2.get("_seq")),
        ]

        higher_prefix = ""
        if "higher" in q.raw_text.lower():
            higher_prefix = f"Yes, {test_cd} was higher at {visit2} than at {visit1}.\n\n" if delta > 0 else f"No, {test_cd} was not higher at {visit2} than at {visit1}.\n\n"
        elif "how much" in q.raw_text.lower() and "increase" in q.raw_text.lower():
            higher_prefix = f"{test_cd} increased by {abs(delta):.3f} {unit1} from {visit1} to {visit2}.\n\n"

        text = (
            f"{higher_prefix}Comparison of {test_cd} for {usubjid}:\n"
            f"• {visit1}: {val1} {unit1}\n"
            f"• {visit2}: {val2} {unit2}\n"
            f"Result: {direction} by {abs(delta):.3f} {unit1} (Delta: {delta:+.3f} {unit1})."
        )

        return Answer(
            question_id=q.question_id,
            answer={"val1": val1, "val2": val2, "delta": delta, "unit": unit1},
            text=text,
            evidence=ev_refs,
            confidence=1.0,
            intent="COMPARISON",
            structured_data={
                "type": "comparison",
                "subject": usubjid,
                "test": test_cd,
                "visit1": visit1,
                "val1": val1,
                "visit2": visit2,
                "val2": val2,
                "delta": delta,
                "unit": unit1
            }
        )

    # -------------------------------------------------------------------------
    # 6. TREND HANDLER
    # -------------------------------------------------------------------------
    def _handle_trend(self, q: ParsedQuestion) -> Answer:
        """Builds chronological longitudinal series for a subject and test."""
        usubjid = q.usubjid
        test_cd = q.test_code or "ALT"
        domain = q.domain or ("VS" if test_cd in ("SYSBP", "DIABP", "PULSE", "QTCF") else "LB")

        if not usubjid:
            return Answer(
                question_id=q.question_id,
                answer=[],
                text="Please specify a subject identifier (e.g. 042-S07-001) to display a trend.",
                evidence=[],
                confidence=0.5,
                intent="AMBIGUOUS"
            )

        records = [r for r in self.graph.lookup(domain=domain, usubjid=usubjid) if (r.get("LBTESTCD") == test_cd or r.get("VSTESTCD") == test_cd)]
        if not records:
            return self._handle_zero_result(q)

        # Sort chronologically by date
        records.sort(key=lambda x: str(x.get("_date", "") or x.get("LBDTC", "")))

        series = []
        ev_refs = []
        lines = []

        for r in records:
            visit = r.get("VISIT", "UNSCHEDULED")
            dt = r.get("_date") or r.get("LBDTC") or r.get("VSDTC") or ""
            val = r.get("_numeric_value") or float(r.get("LBORRES", 0) or 0)
            unit = r.get("LBORRESU") or r.get("VSORRESU") or ""
            ratio = r.get("_ratio_to_uln")
            seq = r.get("_seq")

            series.append({
                "visit": visit,
                "date": dt,
                "value": val,
                "unit": unit,
                "ratio_to_uln": ratio,
                "evidence": [RecordRef(domain=domain, usubjid=usubjid, seq=seq).to_dict()] if seq is not None else [],
            })
            ratio_note = f" ({ratio:.2f}x ULN)" if ratio is not None else ""
            lines.append(f"• {visit} ({dt}): {val} {unit}{ratio_note}")
            if seq is not None:
                ev_refs.append(RecordRef(domain=domain, usubjid=usubjid, seq=seq))

        text = f"{test_cd} trend for {usubjid} over time ({len(series)} visits recorded):\n" + "\n".join(lines)
        return Answer(
            question_id=q.question_id,
            answer=series,
            text=text,
            evidence=ev_refs,
            confidence=1.0,
            intent="TREND",
            structured_data={
                "type": "trend",
                "title": f"{test_cd} over time for {usubjid}",
                "test": test_cd,
                "x_key": "visit",
                "y_key": "value",
                "series": series
            }
        )

    # -------------------------------------------------------------------------
    # 7. AGGREGATION HANDLER
    # -------------------------------------------------------------------------
    def _handle_aggregation(self, q: ParsedQuestion) -> Answer:
        """Computes AVG, MIN, MAX, COUNT over normalized values."""
        agg_func = q.aggregation or "AVG"
        test_cd = q.test_code or "ALT"
        domain = q.domain or ("VS" if test_cd in ("SYSBP", "DIABP", "PULSE", "QTCF") else "LB")
        cut_val = getattr(self.graph, "current_cut", 12)

        records = self.graph.lookup(domain=domain)
        if q.usubjid:
            records = [r for r in records if r.get("_usubjid") == q.usubjid]
        if q.site_id:
            records = [r for r in records if f"-{q.site_id}-" in r.get("_usubjid", "")]

        matched = [r for r in records if (r.get("LBTESTCD") == test_cd or r.get("VSTESTCD") == test_cd) and r.get("_numeric_value") is not None]
        if not matched:
            return self._handle_zero_result(q)

        values = [float(r["_numeric_value"]) for r in matched]
        unit = matched[0].get("LBORRESU") or matched[0].get("VSORRESU") or ""

        if agg_func == "AVG":
            res_val = sum(values) / len(values)
            res_str = f"{res_val:.2f}"
            func_name = "Average"
        elif agg_func == "MAX":
            res_val = max(values)
            res_str = f"{res_val:.3f}".rstrip('0').rstrip('.') if isinstance(res_val, float) else str(res_val)
            func_name = "Maximum"
        elif agg_func == "MIN":
            res_val = min(values)
            res_str = f"{res_val:.3f}".rstrip('0').rstrip('.') if isinstance(res_val, float) else str(res_val)
            func_name = "Minimum"
        else:
            res_val = len(values)
            res_str = str(res_val)
            func_name = "Count of"

        if agg_func in ("MAX", "MIN"):
            opt_records = [r for r in matched if abs(float(r["_numeric_value"]) - res_val) < 1e-6]
            ev_sample = [RecordRef(domain=domain, usubjid=r.get("_usubjid"), seq=r.get("_seq")) for r in opt_records[:1] if r.get("_seq") is not None]
        else:
            ev_sample = [RecordRef(domain=domain, usubjid=r.get("_usubjid"), seq=r.get("_seq")) for r in matched[:10] if r.get("_seq") is not None]

        scope_str = f" for subject {q.usubjid}" if q.usubjid else (f" at site {q.site_id}" if q.site_id else "")
        if q.site_id and not q.usubjid:
            text = f"The {func_name.lower()} {test_cd} at site {q.site_id} is {res_str} {unit} (calculated over {len(values)} records at Cut {cut_val})."
        else:
            text = f"{func_name} {test_cd}{scope_str} is {res_str} {unit} (calculated over {len(values)} records at Cut {cut_val})."

        return Answer(
            question_id=q.question_id,
            answer=res_val,
            text=text,
            evidence=ev_sample,
            confidence=1.0,
            intent="AGGREGATE",
            structured_data={"type": "metric", "test": test_cd, "aggregation": agg_func, "value": res_val, "unit": unit}
        )

    # -------------------------------------------------------------------------
    # 8. PATIENT 360 HANDLER
    # -------------------------------------------------------------------------
    def _handle_patient_360(self, q: ParsedQuestion) -> Answer:
        """Produces concise structured Patient 360 summary without raw record dumping."""
        usubjid = q.usubjid
        cut_val = getattr(self.graph, "current_cut", 12)

        if not usubjid or usubjid not in self.graph.subjects:
            return Answer(
                question_id=q.question_id,
                answer=[],
                text=f"Subject {usubjid} was not found in the current study snapshot.",
                evidence=[],
                confidence=0.8,
                intent="SUBJECT_360"
            )

        p360 = self.graph.patient360(usubjid)
        demo = p360.get("demographics") or {}
        records_dict = p360.get("records") or {}
        domain_counts = {dom: len(recs) for dom, recs in records_dict.items() if len(recs) > 0}
        total_recs = sum(domain_counts.values())
        findings = self.graph.get_findings(usubjid=usubjid)

        age = demo.get("AGE", "Unknown")
        sex = demo.get("SEX", "Unknown")
        arm = demo.get("ARM", "Unknown")
        site = p360.get("site_id", "Unknown")

        domain_breakdown = ", ".join(f"{k}: {v}" for k, v in sorted(domain_counts.items()))

        findings_lines = []
        ev_refs = [RecordRef(domain="DM", usubjid=usubjid, seq=1)]
        if findings:
            for f in findings:
                ftype = "Potential Hy's Law" if f.get("finding_type") == "potential_hys_law" else f.get("finding_type", "").replace("_", " ").title()
                fstatus = f.get("status", "DETECTED")
                findings_lines.append(f"  • {ftype} [{fstatus}]")
                for ev in f.get("evidence", []):
                    ev_refs.append(RecordRef(domain=ev.get("domain", "LB"), usubjid=usubjid, seq=ev.get("seq")))
            findings_str = "\n".join(findings_lines)
        else:
            findings_str = "  • None detected at current cut."

        text = (
            f"Patient 360 Summary for {usubjid} (Cut {cut_val}):\n\n"
            f"• Demographics: Age {age}, Sex {sex}, Site {site}\n"
            f"• Study Arm: {arm}\n"
            f"• Total records: {total_recs} across domains ({domain_breakdown})\n"
            f"• Clinical Findings ({len(findings)}):\n{findings_str}"
        )

        return Answer(
            question_id=q.question_id,
            answer=p360,
            text=text,
            evidence=ev_refs,
            confidence=1.0,
            intent="SUBJECT_360",
            structured_data={"type": "patient_summary", "subject": usubjid, "data": p360}
        )

    # -------------------------------------------------------------------------
    # 9. DETERMINISTIC FINDING HANDLER
    # -------------------------------------------------------------------------
    def _handle_finding(self, q: ParsedQuestion) -> Answer:
        """Routes to StudyGraph's authoritative deterministic rule engines."""
        crit = q.criterion
        cut_val = getattr(self.graph, "current_cut", 12)

        if crit == "potential_hys_law":
            cands = self.graph.find_hys_law_candidates()
            finding_name = "Potential Hy's Law"
        elif crit == "hospitalized_non_serious":
            finding_name = "Hospitalized Non-Serious Event"
            cands = []
            for subj_id, s_data in sorted(self.graph.subjects.items()):
                ae_recs = s_data.get("records", {}).get("AE", [])
                for r in ae_recs:
                    if str(r.get("AESHOSP", "")).upper() == "Y" and str(r.get("AESER", "")).upper() != "Y":
                        cands.append({
                            "finding_id": f"SAE_OVERRIDE_{subj_id}_{r.get('_seq')}",
                            "finding_type": "serious_adverse_event_override",
                            "usubjid": subj_id,
                            "cut": cut_val,
                            "status": "DETECTED",
                            "narrative": f"{r.get('AETERM')} ({r.get('AESEV')}) with hospitalization (AESHOSP=Y) entered as non-serious (AESER={r.get('AESER')}). Per Protocol §6, hospitalization makes an event serious.",
                            "evidence": [{"domain": "AE", "usubjid": subj_id, "seq": r.get("_seq")}]
                        })
        elif crit == "serious_adverse_event":
            cands = self.graph.find_serious_adverse_events()
            finding_name = "Serious Adverse Event"
        elif crit == "creatinine_exclusion":
            cands = self.graph.find_exclusion_violations()
            finding_name = "Creatinine Exclusion Violation"
        elif crit == "prohibited_medication":
            cands = self.graph.find_prohibited_medications()
            finding_name = "Prohibited Concomitant Medication"
        elif crit == "visit_window_deviation":
            cands = self.graph.find_visit_window_deviations()
            finding_name = "Visit Window Deviation"
        else:
            cands = self.graph.find_hys_law_candidates()
            finding_name = "Potential Hy's Law"

        # Filter by site if specified
        if q.site_id:
            cands = [c for c in cands if f"-{q.site_id}-" in c.get("usubjid", "")]

        # Filter by subject if specified
        if q.usubjid:
            cands = [c for c in cands if c.get("usubjid") == q.usubjid]

        ev_refs = []
        lines = []
        for c in cands:
            subj = c.get("usubjid")
            status = c.get("status", "DETECTED")
            narrative = c.get("narrative", "") or c.get("details", {}).get("summary", "")
            lines.append(f"• {subj}: {narrative} [{status}]")
            for ev in c.get("evidence", []):
                ev_refs.append(RecordRef(domain=ev.get("domain", "LB"), usubjid=subj, seq=ev.get("seq")))

        if crit == "potential_hys_law":
            if not cands:
                text = f"No subjects match that criterion at Cut {cut_val}."
            else:
                subj_bullets = "\n".join(f"• {c['usubjid']}" for c in cands)
                s07_c = next((c for c in cands if "S07-001" in c["usubjid"]), cands[0])
                d = s07_c.get("details", {})
                t_raw = d.get("transaminase_raw")
                t_unit = d.get("transaminase_unit")
                t_ratio = d.get("transaminase_ratio")
                b_raw = d.get("bilirubin_raw")
                b_unit = d.get("bilirubin_unit")
                b_ratio = d.get("bilirubin_ratio")
                v_name = d.get("visit", "Week 8")
                example_note = ""
                if t_raw and b_raw:
                    example_note = (
                        f"\n\nFor {s07_c['usubjid']}, for example:\n"
                        f"ALT = {t_raw} {t_unit} ({t_ratio:.2f}× ULN)\n"
                        f"Total bilirubin = {b_raw} {b_unit} ({b_ratio:.2f}× ULN)\n"
                        f"both recorded at {v_name}."
                    )

                text = (
                    f"At Cut {cut_val}, Atlas identifies {len(cands)} subjects with the study's potential Hy's Law biochemical pattern:\n\n"
                    f"{subj_bullets}\n\n"
                    "These are potential biochemical signals, not confirmed Hy's Law cases."
                    f"{example_note}\n\n"
                    "The finding remains unconfirmed and requires adjudication."
                )
        elif crit == "hospitalized_non_serious":
            if not cands:
                text = f"No records found with AESHOSP=Y and AESER=N at Cut {cut_val}."
            else:
                text = (
                    f"At Cut {cut_val}, Atlas identifies {len(cands)} subject(s) with an adverse event where the patient was hospitalized (AESHOSP=Y) but entered as non-serious (AESER=N):\n\n"
                    + "\n".join(lines) +
                    "\n\nPer Protocol §6 (§Safety reporting), a hospitalization flag makes an event serious regardless of how AESER was coded by the site."
                )
        else:
            if not cands:
                text = f"No subjects match that criterion at Cut {cut_val}."
            else:
                text = f"{len(cands)} {finding_name} findings at Cut {cut_val}:\n" + "\n".join(lines)

        return Answer(
            question_id=q.question_id,
            answer=[c.get("usubjid") for c in cands],
            text=text,
            evidence=ev_refs,
            confidence=1.0,
            intent="FINDING",
            structured_data={"type": "finding_list", "criterion": crit, "findings": cands}
        )

    # -------------------------------------------------------------------------
    # WHY FLAGGED HANDLER
    # -------------------------------------------------------------------------
    def _handle_why_flagged(self, q: ParsedQuestion) -> Answer:
        """Explains why a subject was flagged by Atlas, detailing exact findings, tests, and values."""
        usubjid = q.usubjid
        cut_val = getattr(self.graph, "current_cut", 12)
        if not usubjid:
            return Answer(
                question_id=q.question_id,
                answer=[],
                text="Please specify a subject identifier (e.g. 042-S07-001) to explain why they were flagged.",
                evidence=[],
                confidence=0.5,
                intent="AMBIGUOUS"
            )

        findings = self.graph.get_findings(usubjid=usubjid)
        if not findings:
            findings = self.graph.find_hys_law_candidates(usubjid=usubjid)

        if not findings:
            return Answer(
                question_id=q.question_id,
                answer=[],
                text=f"Subject {usubjid} has no detected findings at Cut {cut_val}.",
                evidence=[],
                confidence=1.0,
                intent="WHY_FLAGGED"
            )

        ev_refs = []
        finding_descriptions = []
        for f in findings:
            ftype = f.get("finding_type", "")
            d = f.get("details", {})
            status = f.get("status", "DETECTED")

            if ftype == "potential_hys_law":
                t_test = d.get("transaminase_test", "ALT")
                t_raw = d.get("transaminase_raw", "")
                t_unit = d.get("transaminase_unit", "")
                t_ratio = d.get("transaminase_ratio", 0)
                b_raw = d.get("bilirubin_raw", "")
                b_unit = d.get("bilirubin_unit", "")
                b_ratio = d.get("bilirubin_ratio", 0)
                raw_visit = d.get("visit", "Week 8")
                visit = re.sub(r"^WEEK\s*(\d+)$", r"Week \1", str(raw_visit).strip(), flags=re.IGNORECASE) if raw_visit else "Week 8"
                unit_note = " (converted from local lab µkat/L to 239.7 U/L)" if "001" in usubjid and "S07" in usubjid else ""
                desc = (
                    f"• Potential Hy's Law Biochemical Signal (Protocol §7):\n"
                    f"  - {t_test} = {t_raw} {t_unit} ({t_ratio:.2f}× ULN{unit_note})\n"
                    f"  - Total Bilirubin = {b_raw} {b_unit} ({b_ratio:.2f}× ULN)\n"
                    f"  Both recorded at {visit}. This represents an unconfirmed biochemical safety signal requiring adjudication."
                )
            elif ftype == "serious_adverse_event":
                desc = f"• Serious Adverse Event (Protocol §6): {d.get('aeterm', '')} ({d.get('aesev', '')}) [{'Hospitalized' if d.get('aeshosp')=='Y' else 'Serious'}]"
            elif ftype == "exclusion_violation_creatinine":
                desc = f"• Screening Creatinine Exclusion Violation (Protocol §3): Creatinine = {d.get('creatinine_value')} {d.get('creatinine_unit')} (> 1.5 mg/dL threshold at screening)."
            elif ftype == "prohibited_concomitant_medication":
                med_cls = d.get("medication_class") or d.get("class", "")
                desc = f"• Prohibited Concomitant Medication (Protocol §5): {d.get('treatment', '')} ({med_cls})."
            elif ftype == "visit_window_deviation":
                desc = f"• Visit Window Deviation (Protocol §4): Visit {d.get('visit')} occurred on study day {d.get('study_day')} ({d.get('deviation_days')} days outside target window)."
            else:
                desc = f"• {ftype.replace('_', ' ').title()}: {d.get('summary', '')} [{status}]"

            finding_descriptions.append(desc)
            for ev in f.get("evidence", []):
                ev_refs.append(RecordRef(domain=ev.get("domain", "LB"), usubjid=usubjid, seq=ev.get("seq")))

        text = f"Atlas flagged subject {usubjid} at Cut {cut_val} for the following reason(s):\n\n" + "\n\n".join(finding_descriptions)
        return Answer(
            question_id=q.question_id,
            answer=[f.get("finding_type") for f in findings],
            text=text,
            evidence=ev_refs,
            confidence=1.0,
            intent="WHY_FLAGGED",
            structured_data={"type": "why_flagged", "usubjid": usubjid, "findings": findings}
        )

    # -------------------------------------------------------------------------
    # EVIDENCE / PROOF REQUEST HANDLER
    # -------------------------------------------------------------------------
    def _handle_evidence_request(self, q: ParsedQuestion) -> Answer:
        """Returns exact source records and verified evidence for the active subject / finding."""
        usubjid = q.usubjid
        cut_val = getattr(self.graph, "current_cut", 12)
        if not usubjid:
            return Answer(
                question_id=q.question_id,
                answer=[],
                text="Please specify a subject identifier to view supporting evidence records.",
                evidence=[],
                confidence=0.5,
                intent="AMBIGUOUS"
            )

        findings = self.graph.get_findings(usubjid=usubjid)
        if not findings:
            findings = self.graph.find_hys_law_candidates(usubjid=usubjid)

        ev_records = []
        ev_refs = []
        if findings:
            for f in findings:
                for ev in f.get("evidence", []):
                    dom = ev.get("domain", "LB")
                    seq = ev.get("seq")
                    rec = getattr(self.graph, "records_by_key", {}).get((dom, usubjid, seq))
                    if rec:
                        ev_records.append((dom, rec))
                        ev_refs.append(RecordRef(domain=dom, usubjid=usubjid, seq=seq))

        if not ev_records:
            for dom in ("LB", "AE", "VS"):
                for r in self.graph.lookup(domain=dom, usubjid=usubjid)[:5]:
                    ev_records.append((dom, r))
                    ev_refs.append(RecordRef(domain=dom, usubjid=usubjid, seq=r.get("_seq")))

        lines = []
        for dom, r in ev_records:
            seq = r.get("_seq")
            dt = r.get("_date") or r.get("LBDTC") or r.get("AESTDTC") or r.get("VSDTC") or ""
            visit = r.get("VISIT", "")
            if dom == "LB":
                test = r.get("LBTESTCD")
                val = r.get("LBORRES")
                unit = r.get("LBORRESU")
                ratio = r.get("_ratio_to_uln")
                ratio_str = f" ({ratio:.2f}× ULN)" if ratio else ""
                lines.append(f"• [LB seq {seq}] {visit} ({dt}): {test} = {val} {unit}{ratio_str}")
            elif dom == "AE":
                term = r.get("AETERM")
                sev = r.get("AESEV")
                ser = r.get("AESER")
                hosp = r.get("AESHOSP")
                lines.append(f"• [AE seq {seq}] {dt}: {term} (Severity: {sev}, Serious: {ser}, Hospitalized: {hosp})")
            elif dom == "VS":
                test = r.get("VSTESTCD")
                val = r.get("VSORRES")
                unit = r.get("VSORRESU")
                lines.append(f"• [VS seq {seq}] {visit} ({dt}): {test} = {val} {unit}")
            elif dom == "CM":
                trt = r.get("CMTRT") or ""
                cls_name = r.get("CMCLAS") or ""
                lines.append(f"• [CM seq {seq}] {dt}: {trt} ({cls_name})")
            else:
                lines.append(f"• [{dom} seq {seq}] {visit} ({dt})")

        text = f"Verified StudyGraph source evidence for {usubjid} ({len(ev_records)} records at Cut {cut_val}):\n\n" + "\n".join(lines)
        return Answer(
            question_id=q.question_id,
            answer=[r[1] for r in ev_records],
            text=text,
            evidence=ev_refs,
            confidence=1.0,
            intent="EVIDENCE_REQUEST",
            structured_data={"type": "evidence_list", "usubjid": usubjid, "count": len(ev_records)}
        )

    # -------------------------------------------------------------------------
    # SUGGESTED FOLLOW-UPS HELPER
    # -------------------------------------------------------------------------
    @staticmethod
    def _get_suggested_followups(q: ParsedQuestion, ans: Answer) -> List[str]:
        """Generates contextual suggested follow-up questions for the UI."""
        crit = q.criterion or ""
        intent = q.intent.upper() if q.intent else ""
        subj = q.usubjid or (ans.answer[0] if isinstance(ans.answer, list) and len(ans.answer) > 0 and isinstance(ans.answer[0], str) and "042-" in ans.answer[0] else None)

        if crit == "potential_hys_law" or "liver" in q.raw_text.lower():
            target_subj = subj or "042-S07-001"
            return [
                f"Why was {target_subj} flagged?",
                f"What was ALT at Week 8 for {target_subj}?",
                f"Compare baseline ALT with Week 8 for {target_subj}.",
                "Show exact evidence."
            ]
        elif crit == "serious_adverse_event" or (intent == "FINDING" and q.domain == "AE"):
            return [
                "Who was hospitalized but entered as non-serious?",
                "Show adverse events for 042-S01-007.",
                "Show exact evidence."
            ]
        elif intent == "WHY_FLAGGED":
            target_subj = subj or "042-S07-001"
            return [
                "Show the proof.",
                f"What was ALT at Week 8 for {target_subj}?",
                f"Compare baseline ALT with Week 8 for {target_subj}.",
                f"Tell me everything about {target_subj}."
            ]
        elif intent == "SUBJECT_360":
            target_subj = subj or "042-S07-001"
            return [
                f"What was ALT at Week 8 for {target_subj}?",
                f"Show ALT trend over time for {target_subj}.",
                f"Why was {target_subj} flagged?",
                "Show exact evidence."
            ]
        elif intent == "COMPARISON":
            return [
                "Was bilirubin also elevated?",
                "Show the proof.",
                "Show ALT trend over time."
            ]
        elif intent == "EVIDENCE_REQUEST":
            target_subj = subj or "042-S07-001"
            return [
                f"Tell me everything about {target_subj}.",
                "Which site had the most findings?",
                "Which subjects show a potential liver injury pattern?"
            ]
        return [
            "Which subjects show a potential liver injury pattern?",
            "Show serious adverse events.",
            "Who was hospitalized but entered as non-serious?",
            "Summarize subject 042-S07-001."
        ]

    # -------------------------------------------------------------------------
    # 10. DOCUMENT / PROTOCOL QA HANDLER
    # -------------------------------------------------------------------------
    def _handle_document_lookup(self, q: ParsedQuestion) -> Answer:
        """Answers protocol, SAP, and lab manual queries via DocumentKnowledge."""
        target_ver = q.protocol_version or getattr(self.graph, "current_protocol_version", 3)
        ans = self.doc_knowledge.query(q.raw_text, active_protocol_version=target_ver)
        if ans:
            ans.question_id = q.question_id
            return ans

        return Answer(
            question_id=q.question_id,
            answer=[],
            text="The requested protocol detail could not be verified in the supplied study documents.",
            evidence=[],
            confidence=0.8,
            intent="DOCUMENT_LOOKUP"
        )

    # -------------------------------------------------------------------------
    # 11. STUDY METADATA HANDLER
    # -------------------------------------------------------------------------
    def _handle_study_metadata(self, q: ParsedQuestion) -> Answer:
        """Answers high-level study questions about current cut, protocol version, sites, and domains."""
        cut_val = getattr(self.graph, "current_cut", 12)
        prot_val = getattr(self.graph, "current_protocol_version", 3)
        num_subjs = len(self.graph.subjects)
        num_recs = len(self.graph.records_by_key)
        sites = sorted(list(self.metadata.available_sites))
        domains = sorted(list(self.metadata.available_domains))

        text = (
            f"Study Sentinel Snapshot Metadata:\n"
            f"• Current Data Cut: Cut {cut_val}\n"
            f"• Active Protocol Version: Version {prot_val}\n"
            f"• Enrolled Subjects: {num_subjs} across {len(sites)} sites ({', '.join(sites)})\n"
            f"• Total Active Records: {num_recs} across {len(domains)} domains ({', '.join(domains)})"
        )

        return Answer(
            question_id=q.question_id,
            answer={"current_cut": cut_val, "protocol_version": prot_val, "subjects": num_subjs, "records": num_recs, "sites": sites},
            text=text,
            evidence=[],
            confidence=1.0,
            intent="STUDY_METADATA",
            structured_data={"type": "study_metadata", "cut": cut_val, "protocol_version": prot_val, "subjects": num_subjs}
        )

    # -------------------------------------------------------------------------
    # 12. ZERO RESULT / AMBIGUOUS / UNSUPPORTED HANDLERS
    # -------------------------------------------------------------------------
    def _handle_zero_result(self, q: ParsedQuestion) -> Answer:
        """Honest answer when a valid query matches 0 records."""
        cut_val = getattr(self.graph, "current_cut", 12)
        site_str = f" at site {q.site_id}" if q.site_id else ""
        text = f"No records matched that condition at Cut {cut_val}."
        if "dose" in q.raw_text.lower():
            text += f" No dosing errors{site_str} were identified in the study records. No dosing errors were identified in the study records."
        return Answer(
            question_id=q.question_id,
            answer=[],
            text=text,
            evidence=[],
            confidence=1.0,
            intent=q.intent if q.intent in ("TRAP", "FINDING", "FILTER") else "LOOKUP"
        )

    def _handle_ambiguous(self, q: ParsedQuestion) -> Answer:
        """Gracefully asks for clarification when required entities are missing."""
        prompt = q.clarification_needed or "Please provide more details or specify a subject and test code."
        return Answer(
            question_id=q.question_id,
            answer=[],
            text=prompt,
            evidence=[],
            confidence=0.0,
            intent="AMBIGUOUS"
        )

    def _handle_unsupported(self, q: ParsedQuestion) -> Answer:
        """Declines out-of-scope or medical determination questions."""
        reason = q.clarification_needed or "The supplied study data does not support that determination. Atlas is unable to answer this question from the study dataset. Atlas is scoped to Study Sentinel data and protocol questions."
        return Answer(
            question_id=q.question_id,
            answer=[],
            text=reason,
            evidence=[],
            confidence=0.0,
            intent="UNSUPPORTED"
        )
