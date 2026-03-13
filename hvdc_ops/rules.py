from __future__ import annotations

from collections import Counter
from typing import Any


OFFSHORE_SITES = {"AGI", "DAS"}
DOT_THRESHOLD_TONS = 90.0
MOSB_UTIL_WARN_PCT = 85.0
MOSB_UTIL_BLOCK_PCT = 100.0
COMPLETED_STATUSES = {
    "delivered",
    "delivered to site",
    "closed",
    "complete",
    "completed",
}
KPI_THRESHOLDS = {
    "invoice_ocr": {"threshold": 98.0, "direction": ">=", "unit": "%"},
    "invoice_audit_delta": {"threshold": 2.0, "direction": "<=", "unit": "%"},
    "cost_guard_warn_rate": {"threshold": 5.0, "direction": "<=", "unit": "%"},
    "hs_risk_misclass": {"threshold": 0.5, "direction": "<=", "unit": "%"},
    "cert_chk_auto_pass": {"threshold": 90.0, "direction": ">=", "unit": "%"},
    "wh_forecast_util": {"threshold": 85.0, "direction": "<=", "unit": "%"},
    "weather_tie_eta_mape": {"threshold": 12.0, "direction": "<=", "unit": "%"},
}


def _status_text(value: Any) -> str:
    return str(value or "").strip()


def _public_record(record: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in record.items() if not key.startswith("_")}


def _path_signature(record: dict[str, Any]) -> list[str]:
    legs = ["Port"] if record.get("port_date") else []
    if record.get("warehouse_leg_count"):
        legs.extend(["WH"] * int(record["warehouse_leg_count"]))
    if record.get("mosb_date"):
        legs.append("MOSB")
    if record.get("site_date") or record.get("actual_date"):
        legs.append("Site")
    return legs


def assess_flow(record: dict[str, Any]) -> dict[str, Any]:
    destination = str(record.get("destination") or "").upper()
    status = _status_text(record.get("status")).lower()
    wh_count = int(record.get("warehouse_leg_count") or 0)
    has_port = bool(record.get("port_date"))
    has_mosb = bool(record.get("mosb_date"))
    has_site = bool(record.get("site_date") or record.get("actual_date"))

    reasons: list[str] = []
    pre_arrival = (not has_port and not has_mosb and not has_site) or "pre arrival" in status
    if has_mosb and not has_site:
        observed_code = 5
        reasons.append("MOSB leg exists but site delivery is still missing.")
    elif wh_count >= 2 and not has_mosb:
        observed_code = 5
        reasons.append("Multiple warehouse legs exist without a MOSB leg.")
    elif pre_arrival:
        observed_code = 0
        reasons.append("Shipment is still in pre-arrival state.")
    else:
        observed_code = max(1, min(4, wh_count + (1 if has_mosb else 0) + 1))

    minimum_code = 3 if destination in OFFSHORE_SITES else 1
    recommended_code = observed_code
    auto_upgraded = False
    if observed_code != 5 and observed_code < minimum_code:
        recommended_code = minimum_code
        auto_upgraded = True
        reasons.append(f"{destination} requires Flow Code >= {minimum_code}.")
    elif observed_code == 5 and minimum_code >= 3:
        recommended_code = 4 if wh_count else 3
    elif observed_code == 5:
        recommended_code = 2 if wh_count else 1

    compliant = observed_code != 5 and observed_code >= minimum_code
    return {
        "observed_flow_code": observed_code,
        "recommended_flow_code": recommended_code,
        "minimum_flow_code": minimum_code,
        "auto_upgraded": auto_upgraded,
        "compliant": compliant,
        "destination": destination or None,
        "path_signature": _path_signature(record),
        "reasons": reasons,
    }


def _gate_result(
    *,
    name: str,
    status: str,
    value: Any,
    rule: str,
    block_action: str,
    reason: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": status,
        "value": value,
        "rule": rule,
        "block_action": block_action,
    }
    if reason:
        payload["reason"] = reason
    return {name: payload}


def evaluate_zero_gate_context(record: dict[str, Any]) -> dict[str, Any]:
    destination = str(record.get("destination") or "").upper()
    weight_tons = record.get("weight_tons")
    mosb_util = record.get("mosb_utilization_pct")
    gate_results: dict[str, dict[str, Any]] = {}

    def add(result: dict[str, dict[str, Any]]) -> None:
        gate_results.update(result)

    def bool_gate(field: str, name: str, rule: str, block_action: str) -> None:
        value = record.get(field)
        if value is None:
            add(_gate_result(name=name, status="not_evaluated", value=None, rule=rule, block_action=block_action))
        elif value:
            add(_gate_result(name=name, status="pass", value=True, rule=rule, block_action=block_action))
        else:
            add(_gate_result(name=name, status="block", value=False, rule=rule, block_action=block_action))

    bool_gate(
        "ebl_match",
        "eBL mismatch",
        "eBL mismatch blocks berth confirmation.",
        "Hold berth confirmation until eBL data is aligned.",
    )
    bool_gate(
        "boe_complete",
        "BOE completeness",
        "Incomplete BOE fields stop customs declaration.",
        "Stop BOE/customs filing until the declaration is complete.",
    )
    bool_gate(
        "fanr_ready",
        "FANR permit",
        "FANR permit must be ready before regulated import moves forward.",
        "Hold arrival approval and BOE submission until FANR is ready.",
    )
    bool_gate(
        "ecas_ready",
        "MOIAT ECAS/EQM",
        "ECAS/EQM readiness is required for regulated electrical cargo.",
        "Do not issue DO or Gate Pass until ECAS/EQM is ready.",
    )
    bool_gate(
        "cicpa_ready",
        "CICPA gate pass",
        "CICPA gate pass is required for port and MOSB access.",
        "Stop port/MOSB access until CICPA is ready.",
    )

    fra_value = record.get("fra_ready")
    if destination in OFFSHORE_SITES:
        if fra_value is None:
            add(
                _gate_result(
                    name="ADNOC FRA",
                    status="not_evaluated",
                    value=None,
                    rule="Offshore loading requires ADNOC FRA readiness.",
                    block_action="Do not start offshore loading until FRA is ready.",
                )
            )
        elif fra_value:
            add(
                _gate_result(
                    name="ADNOC FRA",
                    status="pass",
                    value=True,
                    rule="Offshore loading requires ADNOC FRA readiness.",
                    block_action="Do not start offshore loading until FRA is ready.",
                )
            )
        else:
            add(
                _gate_result(
                    name="ADNOC FRA",
                    status="block",
                    value=False,
                    rule="Offshore loading requires ADNOC FRA readiness.",
                    block_action="Stop LCT loading until FRA is completed.",
                )
            )
    else:
        add(
            _gate_result(
                name="ADNOC FRA",
                status="not_required",
                value=fra_value,
                rule="FRA is only required for offshore loading flows.",
                block_action="Do not start offshore loading until FRA is ready.",
            )
        )

    dot_rule = "DOT permit is required above 90 tons."
    dot_action = "Do not move cargo above 90 tons without DOT approval."
    if weight_tons is None:
        add(_gate_result(name="DOT permit", status="not_evaluated", value=None, rule=dot_rule, block_action=dot_action))
    elif float(weight_tons) <= DOT_THRESHOLD_TONS:
        add(
            _gate_result(
                name="DOT permit",
                status="not_required",
                value=record.get("dot_ready"),
                rule=dot_rule,
                block_action=dot_action,
                reason=f"Weight {weight_tons:.1f}t does not exceed the 90t threshold.",
            )
        )
    elif record.get("dot_ready") is None:
        add(_gate_result(name="DOT permit", status="not_evaluated", value=None, rule=dot_rule, block_action=dot_action))
    elif record.get("dot_ready"):
        add(_gate_result(name="DOT permit", status="pass", value=True, rule=dot_rule, block_action=dot_action))
    else:
        add(
            _gate_result(
                name="DOT permit",
                status="block",
                value=False,
                rule=dot_rule,
                block_action="Stop inland move until DOT approval is issued.",
            )
        )

    weather_rule = "Weather alert holds LCT or barge departure."
    weather_action = "Delay marine departure until the weather warning clears."
    if record.get("weather_alert") is None:
        add(_gate_result(name="Weather alert", status="not_evaluated", value=None, rule=weather_rule, block_action=weather_action))
    elif record.get("weather_alert"):
        add(_gate_result(name="Weather alert", status="block", value=True, rule=weather_rule, block_action=weather_action))
    else:
        add(_gate_result(name="Weather alert", status="pass", value=False, rule=weather_rule, block_action=weather_action))

    mosb_rule = "MOSB intake stops above 100% of capacity."
    mosb_action = "Stop additional intake when MOSB capacity is exceeded."
    if mosb_util is None:
        add(_gate_result(name="MOSB capacity", status="not_evaluated", value=None, rule=mosb_rule, block_action=mosb_action))
    elif float(mosb_util) > MOSB_UTIL_BLOCK_PCT:
        add(_gate_result(name="MOSB capacity", status="block", value=mosb_util, rule=mosb_rule, block_action=mosb_action))
    elif float(mosb_util) > MOSB_UTIL_WARN_PCT:
        add(
            _gate_result(
                name="MOSB capacity",
                status="warn",
                value=mosb_util,
                rule="MOSB forecast utility should stay at or below 85%.",
                block_action=mosb_action,
                reason="MOSB utilization is above the 85% KPI warning threshold.",
            )
        )
    else:
        add(
            _gate_result(
                name="MOSB capacity",
                status="pass",
                value=mosb_util,
                rule="MOSB forecast utility should stay at or below 85%.",
                block_action=mosb_action,
            )
        )

    blocking_actions = [
        details["block_action"]
        for details in gate_results.values()
        if details["status"] == "block"
    ]
    warning_actions = [
        details["block_action"]
        for details in gate_results.values()
        if details["status"] == "warn"
    ]
    return {
        "gate_results": gate_results,
        "blocking_actions": blocking_actions,
        "warning_actions": warning_actions,
        "summary": {
            "blocked": sum(1 for details in gate_results.values() if details["status"] == "block"),
            "warnings": sum(1 for details in gate_results.values() if details["status"] == "warn"),
            "not_evaluated": sum(1 for details in gate_results.values() if details["status"] == "not_evaluated"),
            "not_required": sum(1 for details in gate_results.values() if details["status"] == "not_required"),
        },
    }


def evaluate_kpi_checks(record: dict[str, Any]) -> dict[str, Any]:
    checks: dict[str, Any] = {}
    for name, config in KPI_THRESHOLDS.items():
        checks[name] = {
            "status": "not_evaluated",
            "value": None,
            "threshold": config["threshold"],
            "direction": config["direction"],
            "unit": config["unit"],
        }

    mosb_util = record.get("mosb_utilization_pct")
    if mosb_util is not None:
        checks["wh_forecast_util"] = {
            "status": "breach" if float(mosb_util) > MOSB_UTIL_WARN_PCT else "pass",
            "value": float(mosb_util),
            "threshold": MOSB_UTIL_WARN_PCT,
            "direction": "<=",
            "unit": "%",
        }
    return checks


def _derive_verdict(
    flow_assessment: dict[str, Any],
    zero_gates: dict[str, Any],
    kpi_checks: dict[str, Any],
) -> dict[str, Any]:
    blocked = zero_gates["summary"]["blocked"]
    warnings = zero_gates["summary"]["warnings"]
    evidence_gaps = zero_gates["summary"]["not_evaluated"]
    kpi_breaches = sum(1 for check in kpi_checks.values() if check["status"] == "breach")

    if blocked:
        status = "ZERO"
        reason = "At least one hard gate is blocked."
    elif not flow_assessment["compliant"]:
        status = "WARNING"
        reason = "Flow path does not meet the destination rule."
    elif warnings or kpi_breaches or evidence_gaps:
        status = "WARNING"
        reason = "No hard block was found, but warnings or evidence gaps remain."
    else:
        status = "PASS"
        reason = "All evaluated gates passed."

    return {
        "status": status,
        "reason": reason,
        "blocked_gates": blocked,
        "warnings": warnings + kpi_breaches,
        "evidence_gaps": evidence_gaps,
    }


def assess_shipment_case(record: dict[str, Any]) -> dict[str, Any]:
    flow_assessment = assess_flow(record)
    zero_gates = evaluate_zero_gate_context(record)
    kpi_checks = evaluate_kpi_checks(record)
    verdict = _derive_verdict(flow_assessment, zero_gates, kpi_checks)
    return {
        "normalized_case": _public_record(record),
        "flow_assessment": flow_assessment,
        "zero_gates": zero_gates,
        "kpi_checks": kpi_checks,
        "verdict": verdict,
    }


def _is_backlog_status(status: str) -> bool:
    return status.strip().lower() not in COMPLETED_STATUSES


def _compact_case(case: dict[str, Any]) -> dict[str, Any]:
    normalized_case = case["normalized_case"]
    return {
        "shipment_id": normalized_case.get("shipment_id"),
        "source_row_number": normalized_case.get("source_row_number"),
        "destination": normalized_case.get("destination"),
        "status": normalized_case.get("status"),
        "mode": normalized_case.get("mode"),
        "verdict": case["verdict"]["status"],
        "blocking_actions": case["zero_gates"]["blocking_actions"],
        "observed_flow_code": case["flow_assessment"]["observed_flow_code"],
        "recommended_flow_code": case["flow_assessment"]["recommended_flow_code"],
    }


def analyze_backlog(records: list[dict[str, Any]]) -> dict[str, Any]:
    cases = [assess_shipment_case(record) for record in records]
    by_status = Counter(_status_text(case["normalized_case"].get("status")) or "Unknown" for case in cases)
    by_site = Counter(_status_text(case["normalized_case"].get("destination")) or "Unknown" for case in cases)
    by_mode = Counter(_status_text(case["normalized_case"].get("mode")) or "Unknown" for case in cases)

    hotspots = Counter()
    breaches = Counter()
    zero_candidates: list[dict[str, Any]] = []
    for case in cases:
        normalized_case = case["normalized_case"]
        status = _status_text(normalized_case.get("status")) or "Unknown"
        destination = _status_text(normalized_case.get("destination")) or "Unknown"
        if _is_backlog_status(status):
            hotspots[(destination, status)] += 1

        if case["verdict"]["status"] == "ZERO":
            zero_candidates.append(_compact_case(case))
        if not case["flow_assessment"]["compliant"]:
            breaches["flow_code_non_compliant"] += 1
        if case["zero_gates"]["gate_results"]["DOT permit"]["status"] == "block":
            breaches["dot_missing"] += 1
        if case["zero_gates"]["gate_results"]["MOSB capacity"]["status"] == "block":
            breaches["mosb_capacity_block"] += 1
        if case["kpi_checks"]["wh_forecast_util"]["status"] == "breach":
            breaches["mosb_util_kpi_breach"] += 1
        if case["verdict"]["evidence_gaps"] > 0:
            breaches["evidence_gaps"] += 1

    totals = {
        "total_rows": len(cases),
        "backlog_rows": sum(
            1 for case in cases if _is_backlog_status(_status_text(case["normalized_case"].get("status")))
        ),
        "zero_rows": sum(1 for case in cases if case["verdict"]["status"] == "ZERO"),
        "warning_rows": sum(1 for case in cases if case["verdict"]["status"] == "WARNING"),
        "pass_rows": sum(1 for case in cases if case["verdict"]["status"] == "PASS"),
    }
    hotspot_rows = [
        {"destination": destination, "status": status, "count": count}
        for (destination, status), count in hotspots.most_common(10)
    ]
    breach_rows = [{"code": code, "count": count} for code, count in breaches.items() if count > 0]
    zero_candidates = sorted(
        zero_candidates,
        key=lambda item: (item["destination"] or "", item["status"] or "", item["shipment_id"] or ""),
    )
    return {
        "totals": totals,
        "by_status": dict(sorted(by_status.items())),
        "by_site": dict(sorted(by_site.items())),
        "by_mode": dict(sorted(by_mode.items())),
        "hotspots": hotspot_rows,
        "breaches": breach_rows,
        "zero_candidates": zero_candidates,
        "zero_candidate_ids": [item["shipment_id"] for item in zero_candidates],
    }


def compare_snapshot_summaries(
    baseline_name: str,
    baseline_summary: dict[str, Any],
    candidate_name: str,
    candidate_summary: dict[str, Any],
) -> dict[str, Any]:
    def diff_map(base: dict[str, int], candidate: dict[str, int]) -> dict[str, int]:
        keys = sorted(set(base) | set(candidate))
        return {key: int(candidate.get(key, 0)) - int(base.get(key, 0)) for key in keys}

    baseline_zero = {item["shipment_id"]: item for item in baseline_summary.get("zero_candidates", [])}
    candidate_zero = {item["shipment_id"]: item for item in candidate_summary.get("zero_candidates", [])}

    new_zero_ids = sorted(set(candidate_zero) - set(baseline_zero))
    resolved_zero_ids = sorted(set(baseline_zero) - set(candidate_zero))

    return {
        "baseline_snapshot": baseline_name,
        "candidate_snapshot": candidate_name,
        "delta_totals": diff_map(baseline_summary.get("totals", {}), candidate_summary.get("totals", {})),
        "delta_by_status": diff_map(
            baseline_summary.get("by_status", {}), candidate_summary.get("by_status", {})
        ),
        "delta_by_site": diff_map(baseline_summary.get("by_site", {}), candidate_summary.get("by_site", {})),
        "delta_by_mode": diff_map(baseline_summary.get("by_mode", {}), candidate_summary.get("by_mode", {})),
        "new_zero_candidates": [candidate_zero[item_id] for item_id in new_zero_ids],
        "resolved_zero_candidates": [baseline_zero[item_id] for item_id in resolved_zero_ids],
    }
