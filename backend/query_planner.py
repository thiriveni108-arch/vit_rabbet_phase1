"""Descriptive Query Planner for ATLAS AI Agent.

Generates transparent, structured QueryPlan models and execution step traces
for explainability, debugging, and live auditing.
Contains NO clinical arithmetic, unit conversions, or hardcoded answers.
"""

from typing import List, Dict, Any, Optional
from backend.schemas import ParsedQuestion, QueryPlan


class QueryPlanner:
    """Generates structured QueryPlan objects for execution explainability."""

    @classmethod
    def create_plan(cls, q: ParsedQuestion) -> QueryPlan:
        intent = q.intent.upper()
        steps: List[Dict[str, Any]] = []

        subject_ids = [q.usubjid] if q.usubjid else []
        if q.secondary_usubjid:
            subject_ids.append(q.secondary_usubjid)

        site_ids = [q.site_id] if q.site_id else []
        visits = [q.visit] if q.visit else []
        if q.secondary_visit:
            visits.append(q.secondary_visit)

        test_codes = [q.test_code] if q.test_code else []
        if q.secondary_test_code:
            test_codes.append(q.secondary_test_code)

        filters = list(q.filters) if q.filters else []

        if q.threshold_type:
            filters.append({
                "type": q.threshold_type,
                "operator": q.operator or ">=",
                "value": q.threshold_multiplier if q.threshold_type == "ULN" else q.numeric_value
            })

        # Build steps
        if intent == "COUNT":
            if q.criterion:
                steps.append({"step": 1, "action": "RETRIEVE_DETERMINISTIC_FINDINGS", "criterion": q.criterion})
                steps.append({"step": 2, "action": "COUNT_FINDINGS", "site_filter": q.site_id})
                steps.append({"step": 3, "action": "VALIDATE_FINDING_EVIDENCE"})
            elif q.group_by:
                steps.append({"step": 1, "action": "FETCH_DOMAIN_RECORDS", "domain": q.domain or "DM"})
                steps.append({"step": 2, "action": "GROUP_BY_FIELD", "group_by": q.group_by})
                steps.append({"step": 3, "action": "AGGREGATE_COUNT_PER_GROUP"})
            elif q.site_id and not q.domain and not q.test_code:
                steps.append({"step": 1, "action": "FILTER_SUBJECTS_BY_SITE", "site_id": q.site_id})
                steps.append({"step": 2, "action": "COUNT_DISTINCT_SUBJECTS"})
                steps.append({"step": 3, "action": "COLLECT_DEMOGRAPHIC_EVIDENCE"})
            else:
                steps.append({"step": 1, "action": "LOOKUP_GRAPH_RECORDS", "domain": q.domain, "test": q.test_code, "site": q.site_id, "filters": filters})
                steps.append({"step": 2, "action": "COUNT_MATCHING_RECORDS"})
                steps.append({"step": 3, "action": "COLLECT_REPRESENTATIVE_EVIDENCE"})

        elif intent == "LOOKUP":
            steps.append({"step": 1, "action": "LOOKUP_SUBJECT_RECORDS", "usubjid": q.usubjid, "domain": q.domain, "visit": q.visit, "test": q.test_code})
            if q.window_days:
                steps.append({"step": 2, "action": "APPLY_TEMPORAL_WINDOW", "window_days": q.window_days})
            if q.temporal_modifier:
                steps.append({"step": 3, "action": "APPLY_TEMPORAL_MODIFIER", "modifier": q.temporal_modifier})
            steps.append({"step": 4, "action": "EXTRACT_NORMALIZED_VALUES_AND_EVIDENCE"})

        elif intent == "FILTER" or intent == "LIST":
            steps.append({"step": 1, "action": "FETCH_CANDIDATE_RECORDS", "domain": q.domain or "LB", "test": q.test_code, "site": q.site_id})
            steps.append({"step": 2, "action": "APPLY_RECORD_FILTERS", "filters": filters})
            steps.append({"step": 3, "action": "AGGREGATE_DISTINCT_SUBJECTS"})
            steps.append({"step": 4, "action": "COLLECT_SUPPORTING_EVIDENCE"})

        elif intent == "COMPARISON":
            steps.append({"step": 1, "action": "FETCH_FIRST_RECORD", "usubjid": q.usubjid, "visit": q.visit, "test": q.test_code})
            steps.append({"step": 2, "action": "FETCH_SECOND_RECORD", "usubjid": q.secondary_usubjid or q.usubjid, "visit": q.secondary_visit, "test": q.secondary_test_code or q.test_code})
            steps.append({"step": 3, "action": "VERIFY_UNIT_COMPATIBILITY_AND_COMPUTE_DELTA"})
            steps.append({"step": 4, "action": "LINK_DUAL_EVIDENCE_RECORDS"})

        elif intent == "TREND":
            steps.append({"step": 1, "action": "FETCH_ALL_TEST_RECORDS", "usubjid": q.usubjid, "test": q.test_code})
            steps.append({"step": 2, "action": "SORT_CHRONOLOGICALLY_BY_DATE"})
            steps.append({"step": 3, "action": "BUILD_NORMALIZED_TIME_SERIES"})
            steps.append({"step": 4, "action": "ATTACH_PER_POINT_EVIDENCE"})

        elif intent == "AGGREGATE":
            steps.append({"step": 1, "action": "QUERY_MATCHING_RECORDS", "domain": q.domain or "LB", "test": q.test_code, "site": q.site_id, "usubjid": q.usubjid})
            steps.append({"step": 2, "action": "COMPUTE_NUMERIC_AGGREGATION", "func": q.aggregation or "AVG", "group_by": q.group_by})
            steps.append({"step": 3, "action": "COLLECT_REPRESENTATIVE_EVIDENCE"})

        elif intent == "SUBJECT_360":
            steps.append({"step": 1, "action": "FETCH_PATIENT_DEMOGRAPHICS", "usubjid": q.usubjid})
            steps.append({"step": 2, "action": "SUMMARIZE_DOMAIN_ACTIVITY", "usubjid": q.usubjid})
            steps.append({"step": 3, "action": "RETRIEVE_DETECTED_FINDINGS", "usubjid": q.usubjid})
            steps.append({"step": 4, "action": "FORMAT_EXECUTIVE_PATIENT_360"})

        elif intent == "FINDING":
            steps.append({"step": 1, "action": "EXECUTE_DETERMINISTIC_FINDING_ENGINE", "criterion": q.criterion, "usubjid": q.usubjid})
            steps.append({"step": 2, "action": "FILTER_BY_SITE_IF_SPECIFIED", "site": q.site_id})
            steps.append({"step": 3, "action": "VERIFY_EXACT_FINDING_EVIDENCE"})

        elif intent == "DOCUMENT_LOOKUP":
            steps.append({"step": 1, "action": "RETRIEVE_LOCAL_PROTOCOL_DOCUMENTS", "version": q.protocol_version})
            steps.append({"step": 2, "action": "MATCH_QUERY_AGAINST_SECTIONS"})
            steps.append({"step": 3, "action": "GENERATE_CITATION_AND_EVIDENCE"})

        elif intent == "STUDY_METADATA":
            steps.append({"step": 1, "action": "INSPECT_CURRENT_GRAPH_METADATA"})
            steps.append({"step": 2, "action": "RETURN_STRUCTURED_STUDY_METRICS"})

        elif intent == "AMBIGUOUS":
            steps.append({"step": 1, "action": "IDENTIFY_AMBIGUITY_CAUSE", "reason": q.clarification_needed})
            steps.append({"step": 2, "action": "FORMULATE_CONCISE_CLARIFICATION_PROMPT"})

        else:
            steps.append({"step": 1, "action": "EVALUATE_UNSUPPORTED_BOUNDARY"})

        return QueryPlan(
            operation=intent,
            domain=q.domain,
            subject_ids=subject_ids,
            site_ids=site_ids,
            visits=visits,
            test_codes=test_codes,
            filters=filters,
            aggregation=q.aggregation,
            group_by=q.group_by,
            time_window_days=q.window_days,
            finding_type=q.criterion,
            temporal_modifier=q.temporal_modifier,
            protocol_version=q.protocol_version,
            needs_evidence=True,
            clarification_needed=q.clarification_needed,
            steps=steps
        )
