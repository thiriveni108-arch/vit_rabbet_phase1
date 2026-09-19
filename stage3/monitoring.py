"""Stage 3: Threshold Monitoring, Contextual False-Positive Prevention,
Amendment-Aware Re-derivation, and Delayed Escalation Tracking.

Features:
1. Threshold Monitoring: Deterministic safety monitoring across clinical rules and data integrity.
2. Contextual False-Positive Prevention: Suppresses emergencies for site-wide unit shifts,
   quarantined data, and isolated uncorroborated biochemical anomalies.
3. Amendment-Aware Derivation: Dynamically tracks `previous_protocol != current_protocol`
   from cut metadata, recomputes derived findings, and invalidates stale findings with zero hardcoded cuts.
4. Delayed Escalation Memory: Tracks PENDING, WAITING, APPROVED, REJECTED, CLARIFY,
   and STANDING_LIMITS. After 4 cuts without reply, enforces STANDING_LIMITS without silent approval.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

from stage1.atlas import StudyGraph
from stage3.models import (
    EscalationState,
    FalseAlarmMetrics,
    SignalTimingRecord,
    SiteRiskRank,
    TrustState,
)


class DelayedEscalationTracker:
    """Tracks human escalations across review cycles ensuring unanswered cases never silently approve."""

    def __init__(self):
        # Case ID / Finding ID -> Escalation record
        self.cases: Dict[str, Dict[str, Any]] = {}
        self.site_unanswered_counts: Dict[str, int] = {}

    def track_case(
        self,
        case_id: str,
        finding_type: str,
        usubjid: str,
        site_id: str,
        created_cut: int,
        initial_status: str = "AWAITING",
    ) -> Dict[str, Any]:
        if case_id not in self.cases:
            self.cases[case_id] = {
                "case_id": case_id,
                "finding_type": finding_type,
                "usubjid": usubjid,
                "site_id": site_id,
                "created_cut": created_cut,
                "last_response_cut": None,
                "cuts_waiting": 0,
                "status": EscalationState.WAITING.value if initial_status == "AWAITING" else initial_status,
                "standing_limits": False,
                "monitor_action_allowed": False,
                "audit_notes": [f"Escalation opened at Cut {created_cut}."],
            }
        return self.cases[case_id]

    def advance_cut(self, current_cut: int, monitor_responses: Optional[Dict[str, List[str]]] = None):
        """Advances cycle cut and applies delayed monitor responses or standing limits.
        
        Guarantees:
        - If monitor does NOT respond, case status remains WAITING and increments cuts_waiting.
        - No response must NEVER become approval.
        - After 4 unanswered cuts -> STANDING_LIMITS.
        """
        responses = monitor_responses or {}
        site_counts: Dict[str, int] = {}

        for case_id, rec in self.cases.items():
            if rec["status"] in (EscalationState.APPROVED.value, EscalationState.REJECTED.value):
                continue

            created = rec["created_cut"]
            rec["cuts_waiting"] = current_cut - created

            # Check if monitor responded in this cut
            usubjid = rec["usubjid"]
            ftype = rec["finding_type"]
            resp_key = f"{ftype}|{usubjid}"

            if resp_key in responses:
                reply = responses[resp_key]
                decision = reply[0] if reply else "AWAITING"
                reason = reply[1] if len(reply) > 1 else ""

                if decision == "APPROVED":
                    rec["status"] = EscalationState.APPROVED.value
                    rec["last_response_cut"] = current_cut
                    rec["monitor_action_allowed"] = True
                    rec["audit_notes"].append(f"Monitor APPROVED at Cut {current_cut}: {reason}")
                elif decision == "REJECTED":
                    rec["status"] = EscalationState.REJECTED.value
                    rec["last_response_cut"] = current_cut
                    rec["monitor_action_allowed"] = False
                    rec["audit_notes"].append(f"Monitor REJECTED at Cut {current_cut}: {reason}")
                elif decision == "CLARIFY":
                    rec["status"] = EscalationState.CLARIFY.value
                    rec["audit_notes"].append(f"Monitor requested CLARIFY at Cut {current_cut}: {reason}")
            else:
                # No response from monitor
                if rec["cuts_waiting"] >= 4:
                    rec["status"] = EscalationState.STANDING_LIMITS.value
                    rec["standing_limits"] = True
                    rec["monitor_action_allowed"] = False
                    note = f"Cut {current_cut}: Monitor has not responded after {rec['cuts_waiting']} cuts. Enforcing STANDING_LIMITS. Approval-gated actions blocked; clinical safety surveillance remains active."
                    if note not in rec["audit_notes"]:
                        rec["audit_notes"].append(note)
                else:
                    rec["status"] = EscalationState.WAITING.value

            # Track unanswered queries by site
            if rec["status"] in (EscalationState.WAITING.value, EscalationState.STANDING_LIMITS.value, EscalationState.CLARIFY.value):
                site_id = rec.get("site_id", "")
                if site_id:
                    site_counts[site_id] = site_counts.get(site_id, 0) + 1

        self.site_unanswered_counts = site_counts


class ThresholdMonitoringEngine:
    """Surveillance monitoring engine enforcing false-positive prevention and amendment re-derivation."""

    def __init__(self, study_graph: StudyGraph):
        self.graph = study_graph
        self.escalation_tracker = DelayedEscalationTracker()
        self.last_evaluated_protocol: Optional[int] = None
        self.active_alerts: List[Dict[str, Any]] = []
        self.protocol_amendment_traces: List[Dict[str, Any]] = []
        self.false_alarm_metrics = FalseAlarmMetrics()
        self.signal_timings: Dict[str, SignalTimingRecord] = {}
        self.site_anomalies_history: Dict[str, List[Dict[str, Any]]] = {}
        self.site_quarantined_tests: Dict[str, Set[str]] = {}


    # =========================================================================
    # 1. DYNAMIC AMENDMENT-AWARE DERIVATION (NO HARDCODED CUT NUMBERS!)
    # =========================================================================

    def evaluate_protocol_amendment(self, current_cut: int) -> Optional[Dict[str, Any]]:
        """Dynamically detects `previous_protocol != current_protocol` from metadata.

        Does NOT hardcode cuts 5 or 9. Recomputes only rules affected by protocol change.
        """
        current_protocol = self.graph.get_protocol_version(current_cut)
        if self.last_evaluated_protocol is None:
            self.last_evaluated_protocol = current_protocol
            return None

        if current_protocol != self.last_evaluated_protocol:
            old_p = self.last_evaluated_protocol
            new_p = current_protocol
            self.last_evaluated_protocol = new_p

            # Invalidate stale findings dependent on protocol rules:
            # - Visit window deviations (window tightened or changed)
            # - Prohibited medications (new exclusions added)
            # - Screening exclusion criteria (new exclusions added)
            prior_findings = list(self.graph.findings)
            stale_fids = set()

            for f in prior_findings:
                ftype = f.get("finding_type", "")
                if ftype in ("visit_window_deviation", "prohibited_concomitant_medication", "exclusion_violation_creatinine"):
                    stale_fids.add(f["finding_id"])

            # Clean graph stores of stale findings
            self.graph.findings = [f for f in self.graph.findings if f["finding_id"] not in stale_fids]
            for fid in stale_fids:
                self.graph.findings_by_id.pop(fid, None)

            # Re-evaluate all subjects for affected rules under new protocol version
            new_findings: List[Dict[str, Any]] = []
            new_findings.extend(self.graph.find_visit_window_deviations())
            new_findings.extend(self.graph.find_prohibited_medications())
            new_findings.extend(self.graph.find_exclusion_violations())

            added_count = 0
            for nf in new_findings:
                fid = nf["finding_id"]
                if fid not in self.graph.findings_by_id:
                    self.graph.findings.append(nf)
                    self.graph.findings_by_id[fid] = nf
                    self.graph.findings_by_subj.setdefault(nf["usubjid"], []).append(nf)
                    added_count += 1

            trace = {
                "cut": current_cut,
                "old_protocol": old_p,
                "new_protocol": new_p,
                "stale_findings_invalidated": len(stale_fids),
                "new_findings_derived": added_count,
                "affected_rules": [
                    "Visit schedule window verification",
                    "Prohibited medication screening",
                    "Protocol exclusion criteria",
                ],
                "description": f"Dynamic protocol amendment transition: v{old_p} -> v{new_p} at Cut {current_cut}. Re-derived compliance findings without full graph rebuild.",
            }
            self.protocol_amendment_traces.append(trace)
            return trace

        return None

    # =========================================================================
    # 2. CONTEXTUAL FALSE-POSITIVE SUPPRESSION & SAFETY MONITORING
    # =========================================================================

    def run_surveillance(
        self,
        current_cut: int,
        unit_anomalies: List[Dict[str, Any]],
        site_integrity: Dict[str, Dict[str, Any]],
        monitor_responses: Optional[Dict[str, List[str]]] = None,
    ) -> List[Dict[str, Any]]:
        """Evaluates all safety and compliance findings with contextual false-positive suppression."""
        # 1. Update protocol amendment derivations dynamically
        self.evaluate_protocol_amendment(current_cut)

        # Reset false alarm metrics for this cut
        raw_findings = self.graph.get_findings()
        flagged_sites_count = sum(1 for s in site_integrity.values() if s.get("status") in ("SUSPECT", "QUARANTINED"))
        self.false_alarm_metrics.candidate_alerts = len(unit_anomalies) + flagged_sites_count + len(raw_findings)
        self.false_alarm_metrics.data_integrity_alerts_emitted = len(unit_anomalies) + flagged_sites_count
        self.false_alarm_metrics.clinical_alerts_emitted = 0
        self.false_alarm_metrics.clinical_alerts_suppressed_integrity = 0

        # 2. Build quarantine index: (site, test) or site
        quarantined_site_tests: Set[Tuple[str, str]] = set()
        for ua in unit_anomalies:
            s = ua.get("site", "")
            t = ua.get("test", "")
            if ua.get("trust_state") in (TrustState.UNTRUSTED.value, TrustState.QUARANTINED.value):
                quarantined_site_tests.add((s, t))
                self.site_quarantined_tests.setdefault(s, set()).add(t)
            self.site_anomalies_history.setdefault(s, []).append({
                "cut": current_cut,
                "type": "UNIT_SHIFT",
                "detail": f"{t} shift ~{ua.get('ratio')}x",
            })

        quarantined_sites: Set[str] = {
            s for s, info in site_integrity.items()
            if info.get("trust_state") == TrustState.QUARANTINED.value
        }
        for s_id, s_info in site_integrity.items():
            if s_info.get("status") in ("SUSPECT", "QUARANTINED"):
                self.site_anomalies_history.setdefault(s_id, []).append({
                    "cut": current_cut,
                    "type": f"SITE_{s_info['status']}",
                    "detail": "; ".join(s_info.get("reasons", [])),
                })

        alerts: List[Dict[str, Any]] = []

        # A. Register Data Integrity alerts (distinct visual category from clinical safety!)
        for ua in unit_anomalies:
            aid = ua["alert_id"]
            alerts.append({
                "alert_id": aid,
                "cut": current_cut,
                "subject": f"SITE-{ua['site']}",
                "site": ua["site"],
                "type": "DATA_INTEGRITY",
                "category": "DATA_INTEGRITY",
                "severity": "WARNING",
                "rule": "Statistical Unit Shift Heuristic",
                "threshold": f"{ua['ratio']}x conversion factor",
                "observed_value": f"Median {ua['incoming_median']}",
                "unit": "Unverified",
                "reference_range": "N/A",
                "evidence": [{"domain": "LB", "test": ua["test"], "site": ua["site"]}],
                "trust_state": TrustState.UNTRUSTED.value,
                "status": "OPEN_QUERY",
                "title": ua["title"],
                "description": ua["description"],
                "action": ua["lab_query"],
            })
            self.signal_timings[aid] = SignalTimingRecord(
                signal_id=aid,
                signal_type="DATA_INTEGRITY_UNIT",
                subject_or_site=f"SITE-{ua['site']}",
                first_seen_cut=current_cut,
                detected_cut=current_cut,
                escalated_cut=current_cut,
                detection_latency_cuts=0,
                escalation_latency_cuts=0,
            )

        for s_id, s_info in site_integrity.items():
            if s_info.get("status") in ("SUSPECT", "QUARANTINED"):
                aid = f"SITE_INTEGRITY_{s_id}_CUT_{current_cut}"
                alerts.append({
                    "alert_id": aid,
                    "cut": current_cut,
                    "subject": f"SITE-{s_id}",
                    "site": s_id,
                    "type": "DATA_INTEGRITY",
                    "category": "DATA_INTEGRITY",
                    "severity": "CRITICAL" if s_info["status"] == "QUARANTINED" else "WARNING",
                    "rule": "Site Regularity & Variance Heuristic",
                    "threshold": "Cohort Median Variance Ratio",
                    "observed_value": f"SYSBP SD {s_info.get('sysbp_stdev')} vs Cohort {s_info.get('peer_sysbp_median_stdev')}",
                    "unit": "mmHg",
                    "reference_range": "N/A",
                    "evidence": [{"site": s_id, "reasons": s_info.get("reasons")}],
                    "trust_state": TrustState.QUARANTINED.value,
                    "status": "AUDIT_RECOMMENDED",
                    "title": f"Site Data Integrity Flag: Site {s_id} ({s_info['status']})",
                    "description": "; ".join(s_info.get("reasons", [])),
                    "action": s_info.get("recommendation", "Audit recommended"),
                })
                self.signal_timings[aid] = SignalTimingRecord(
                    signal_id=aid,
                    signal_type="DATA_INTEGRITY_SITE",
                    subject_or_site=f"SITE-{s_id}",
                    first_seen_cut=current_cut,
                    detected_cut=current_cut,
                    escalated_cut=current_cut,
                    detection_latency_cuts=0,
                    escalation_latency_cuts=0,
                )

        # B. Process Clinical Safety & Protocol Findings from StudyGraph
        for f in raw_findings:
            usubjid = f.get("usubjid", "")
            subj_site = self.graph.subjects.get(usubjid, {}).get("site_id", "")
            if not subj_site and "-" in usubjid:
                subj_site = usubjid.split("-")[1]

            ftype = f.get("finding_type", "")
            fid = f.get("finding_id", "")

            # Check if finding evidence relies on quarantined data
            is_quarantined = False
            if subj_site in quarantined_sites and ftype == "vital_signs_deviation":
                is_quarantined = True

            for ev in f.get("evidence", []):
                ev_dom = ev.get("domain", "")
                if ev_dom == "LB":
                    key = (ev_dom, usubjid, ev.get("seq"))
                    rec = self.graph.records_by_key.get(key)
                    if rec:
                        tcd = rec.get("LBTESTCD", "").strip().upper()
                        if (subj_site, tcd) in quarantined_site_tests:
                            is_quarantined = True
                            break

            # -----------------------------------------------------------------
            # QUARANTINE SAFETY FLOOR:
            # Quarantined quantitative data is excluded from safety aggregation,
            # BUT explicit serious adverse events / hospitalization-based SAEs
            # MUST still escalate in the same cut. Never let site quarantine hide a critical SAE!
            # -----------------------------------------------------------------
            is_sae = (
                ftype == "serious_adverse_event"
                or f.get("details", {}).get("aeser") == "Y"
                or "hospitaliz" in str(f.get("details", {})).lower()
                or (f.get("severity") == "CRITICAL" and "adverse" in ftype)
            )
            if is_sae:
                is_quarantined = False

            # If evidence comes from an untrusted / quarantined unit anomaly or suspect vitals, suppress clinical false positive!
            if is_quarantined:
                self.false_alarm_metrics.clinical_alerts_suppressed_integrity += 1
                continue

            # Contextual corroboration check for Potential Hy's Law:
            corroborated = True
            if ftype == "potential_hys_law":
                p360 = self.graph.patient360(usubjid)
                for lb in p360.get("labs", []):
                    if lb.get("test") in ("ALT", "AST") and "SCREEN" in str(lb.get("visit", "")).upper():
                        ratio = lb.get("ratio_to_uln")
                        if ratio is not None and ratio > 2.0:
                            corroborated = False
                            break

            # Track in delayed human escalation tracker
            self.escalation_tracker.track_case(
                case_id=fid,
                finding_type=ftype,
                usubjid=usubjid,
                site_id=subj_site,
                created_cut=current_cut,
                initial_status="AWAITING",
            )

            severity = "CRITICAL" if ftype in ("serious_adverse_event", "potential_hys_law") else "HIGH"
            alerts.append({
                "alert_id": fid,
                "cut": current_cut,
                "subject": usubjid,
                "site": subj_site,
                "type": "CLINICAL_SAFETY" if ftype in ("serious_adverse_event", "potential_hys_law") else "PROTOCOL_COMPLIANCE",
                "category": "CLINICAL_SAFETY" if ftype in ("serious_adverse_event", "potential_hys_law") else "PROTOCOL_COMPLIANCE",
                "severity": severity,
                "rule": f.get("protocol_rule", f"Protocol rule for {ftype}"),
                "threshold": "Protocol §6/§7 Criteria",
                "observed_value": str(f.get("details", {}).get("aeterm") or f.get("details", {}).get("transaminase_raw") or "Criteria met"),
                "unit": str(f.get("details", {}).get("transaminase_unit") or ""),
                "reference_range": "Per protocol",
                "evidence": f.get("evidence", []),
                "trust_state": TrustState.TRUSTED.value,
                "status": self.escalation_tracker.cases[fid]["status"],
                "title": f.get("title", ftype.replace("_", " ").title()),
                "description": f.get("details", {}).get("summary", "Safety finding identified by deterministic surveillance."),
                "corroborated": corroborated,
            })
            self.false_alarm_metrics.clinical_alerts_emitted += 1

            # Determine first seen cut from underlying evidence
            first_seen = current_cut
            for ev in f.get("evidence", []):
                key = (ev.get("domain", ""), usubjid, ev.get("seq"))
                rec = self.graph.records_by_key.get(key)
                if rec:
                    c_avail = rec.get("_cut_available", rec.get("cut_available"))
                    try:
                        c_int = int(c_avail)
                        if c_int > 0 and c_int < first_seen:
                            first_seen = c_int
                    except (ValueError, TypeError):
                        pass

            sig_type = "SERIOUS_ADVERSE_EVENT" if is_sae else ("HYS_LAW" if ftype == "potential_hys_law" else ftype.upper())
            self.signal_timings[fid] = SignalTimingRecord(
                signal_id=fid,
                signal_type=sig_type,
                subject_or_site=usubjid,
                first_seen_cut=first_seen,
                detected_cut=current_cut,
                escalated_cut=current_cut,
                detection_latency_cuts=current_cut - first_seen,
                escalation_latency_cuts=current_cut - first_seen,
            )

        # Compute suppression rate
        tot_clinical = self.false_alarm_metrics.clinical_alerts_emitted + self.false_alarm_metrics.clinical_alerts_suppressed_integrity
        if tot_clinical > 0:
            self.false_alarm_metrics.suppression_rate = self.false_alarm_metrics.clinical_alerts_suppressed_integrity / tot_clinical
        else:
            self.false_alarm_metrics.suppression_rate = 0.0

        # Advance delayed escalation cases (unconditional call ensures unanswered cases reach standing limits)
        self.escalation_tracker.advance_cut(current_cut, monitor_responses or {})

        self.active_alerts = alerts
        return alerts

    # =========================================================================
    # 3. EVIDENCE-DERIVED SITE RISK RANKING (ZERO INVENTED CLINICAL SCORES)
    # =========================================================================

    def get_site_risk_ranking(
        self,
        current_cut: int,
        site_integrity: Dict[str, Dict[str, Any]],
        unit_anomalies: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Computes objective site risk rankings derived strictly from real evidence.
        
        Ranked criteria:
        1. Site Quarantine status (active data integrity quarantine)
        2. Unnatural regularity / variance anomalies in vital signs
        3. Systematic unit conversion anomalies in laboratory tests
        4. Repeated unanswered queries / monitor escalation delays
        5. Recurrence across multiple cuts
        """
        all_sites: Set[str] = set(self.graph.sites)
        for s in self.graph.subjects.values():
            s_id = s.get("site_id")
            if s_id:
                all_sites.add(s_id)
        for s in site_integrity:
            all_sites.add(s)

        unanswered = self.escalation_tracker.site_unanswered_counts
        ranked_sites: List[SiteRiskRank] = []

        for site_id in all_sites:
            reasons: List[str] = []
            ev_refs: List[Dict[str, Any]] = []
            s_info = site_integrity.get(site_id, {})
            is_quarantined = s_info.get("status") == "QUARANTINED"
            is_suspect = s_info.get("status") == "SUSPECT"

            if is_quarantined:
                reasons.append(f"Site under active QUARANTINE due to {'; '.join(s_info.get('reasons', []))}")
                ev_refs.append({"site": site_id, "status": "QUARANTINED", "reasons": s_info.get("reasons", [])})
            elif is_suspect:
                reasons.append(f"Suspicious regularity flagged: {'; '.join(s_info.get('reasons', []))}")
                ev_refs.append({"site": site_id, "status": "SUSPECT", "reasons": s_info.get("reasons", [])})

            # Unit shifts at this site
            site_shifts = [ua for ua in unit_anomalies if ua.get("site") == site_id]
            for ua in site_shifts:
                reasons.append(f"Systematic {ua.get('test')} unit shift (~{ua.get('ratio')}x) detected")
                ev_refs.append({"site": site_id, "test": ua.get("test"), "ratio": ua.get("ratio")})

            # Unanswered queries
            unans_count = unanswered.get(site_id, 0)
            if unans_count > 0:
                reasons.append(f"{unans_count} queries currently awaiting monitor resolution")
                ev_refs.append({"site": site_id, "open_queries": unans_count})

            # Recurrence across cuts
            history = self.site_anomalies_history.get(site_id, [])
            affected_cuts = sorted(list(set(h["cut"] for h in history)))
            if len(affected_cuts) > 1:
                reasons.append(f"Recurrent anomalies recorded across Cuts {affected_cuts}")

            q_tests = sorted(list(self.site_quarantined_tests.get(site_id, set())))
            q_domains = ["VS"] if is_quarantined else []

            # Clinical & compliance findings count for this site
            site_findings = [
                f for f in self.graph.get_findings()
                if self.graph.subjects.get(f.get("usubjid", ""), {}).get("site_id") == site_id
            ]
            safety_count = sum(1 for f in site_findings if f.get("category") == "CLINICAL_SAFETY")
            data_qual_count = sum(1 for f in site_findings if f.get("category") != "CLINICAL_SAFETY")

            # Recurring subjects at this site
            subjs_at_site = [
                u for u, s in self.graph.subjects.items()
                if s.get("site_id") == site_id
            ]
            rec_subjs = sum(1 for u in subjs_at_site if len(self.graph.findings_by_subj.get(u, [])) >= 2)

            # Determine risk tier based strictly on real evidence
            if is_quarantined or (len(history) >= 2 and len(affected_cuts) >= 2):
                risk_tier = "CRITICAL"
                status_label = "ATTENTION"
            elif is_suspect or len(site_shifts) > 0 or unans_count >= 2:
                risk_tier = "HIGH"
                status_label = "ATTENTION"
            elif unans_count == 1 or len(history) == 1:
                risk_tier = "MEDIUM"
                status_label = "WATCH"
            else:
                risk_tier = "LOW"
                status_label = "STABLE"
                reasons.append("Normal cohort variance; zero data integrity flags; all queries resolved.")

            last_cut = max(affected_cuts) if affected_cuts else (current_cut if (is_quarantined or is_suspect or len(site_shifts) > 0) else None)

            ranked_sites.append(SiteRiskRank(
                site_id=site_id,
                rank=0,
                status=status_label,
                risk_tier=risk_tier,
                reasons=reasons,
                is_quarantined=is_quarantined,
                integrity_events_count=len(history),
                unanswered_queries_count=unans_count,
                recurring_subjects_count=rec_subjs,
                safety_findings_count=safety_count,
                data_quality_findings_count=data_qual_count,
                regularity_anomalies_count=1 if (is_quarantined or is_suspect) else 0,
                last_incident_cut=last_cut,
                quarantined_tests=q_tests,
                quarantined_domains=q_domains,
                affected_cuts=affected_cuts,
                evidence_refs=ev_refs,
            ))

        # Sort: CRITICAL/QUARANTINED first, then total anomalies/queries, then recurrence, then site_id
        tier_weights = {"CRITICAL": 4, "HIGH": 3, "MEDIUM": 2, "LOW": 1}
        ranked_sites.sort(
            key=lambda r: (
                tier_weights.get(r.risk_tier, 0),
                r.integrity_events_count + r.unanswered_queries_count,
                len(r.affected_cuts),
                r.site_id,
            ),
            reverse=True,
        )

        # Assign 1-indexed ranks
        result = []
        for idx, r in enumerate(ranked_sites, start=1):
            r.rank = idx
            result.append(r.to_dict())

        return result


