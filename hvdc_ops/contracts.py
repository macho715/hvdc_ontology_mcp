from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class FlowAssessmentResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_flow_code: int
    recommended_flow_code: int
    minimum_flow_code: int
    auto_upgraded: bool
    compliant: bool
    destination: str | None = None
    path_signature: list[str]
    reasons: list[str]


class GateResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    status: str
    value: Any = None
    rule: str
    block_action: str
    reason: str | None = None


class ZeroGateSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocked: int
    warnings: int
    not_evaluated: int
    not_required: int


class ZeroGateBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_results: dict[str, GateResult]
    blocking_actions: list[str]
    warning_actions: list[str]
    summary: ZeroGateSummary


class KpiCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    value: float | None = None
    threshold: float
    direction: str
    unit: str


class VerdictResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    reason: str | None = None
    blocked_gates: int
    warnings: int
    evidence_gaps: int


class CompactCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shipment_id: str | None = None
    source_row_number: int | None = None
    destination: str | None = None
    status: str | None = None
    mode: str | None = None
    verdict: str
    blocking_actions: list[str]
    observed_flow_code: int
    recommended_flow_code: int


class ExcelExportSheet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    rows: list[dict[str, Any]]


class ExcelExportPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    version: str
    kind: str
    generated_at: str
    workbook_name: str | None = None
    sheets: list[ExcelExportSheet]


class ShipmentCaseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    normalized_case: dict[str, Any]
    flow_assessment: FlowAssessmentResult
    zero_gates: ZeroGateBundle
    kpi_checks: dict[str, KpiCheck]
    verdict: VerdictResult
    input_source: dict[str, Any] = Field(default_factory=dict)
    markdown_summary: str
    excel_export: ExcelExportPayload | None = None


class WidgetDefaults(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_name: str
    sheet_name: str | None = None
    column_map: dict[str, str] = Field(default_factory=dict)


class BacklogUploadWidgetResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    instructions: list[str]
    accepted_extensions: list[str]
    defaults: WidgetDefaults
    tool_name: str
    widget_uri: str


class BacklogTotals(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_rows: int
    backlog_rows: int
    zero_rows: int
    warning_rows: int
    pass_rows: int


class HotspotRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    destination: str
    status: str
    count: int


class BreachRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    count: int


class BacklogBatchResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    snapshot_name: str
    source: dict[str, Any]
    totals: BacklogTotals
    by_status: dict[str, int]
    by_site: dict[str, int]
    by_mode: dict[str, int]
    hotspots: list[HotspotRow]
    breaches: list[BreachRow]
    zero_candidates: list[CompactCase]
    zero_candidate_ids: list[str]
    markdown_report: str
    excel_export: ExcelExportPayload | None = None


class ZeroGateVerdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ZERO", "WARNING", "PASS"]
    blocked_gates: int
    warnings: int
    evidence_gaps: int


class ZeroGateCheckResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    gate_results: dict[str, GateResult]
    blocking_actions: list[str]
    warning_actions: list[str]
    verdict: ZeroGateVerdict
    markdown_summary: str


class SnapshotCompareResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    baseline_snapshot: str
    candidate_snapshot: str
    delta_totals: dict[str, int]
    delta_by_status: dict[str, int]
    delta_by_site: dict[str, int]
    delta_by_mode: dict[str, int]
    new_zero_candidates: list[CompactCase]
    resolved_zero_candidates: list[CompactCase]
    markdown_report: str
    excel_export: ExcelExportPayload | None = None


class SelfTestCheck(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    status: str
    detail: str = ""


class SelfTestResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    connector_url: str | None = None
    public_base_url: str | None = None
    checks: list[SelfTestCheck]
    recommendations: list[str]
    markdown_summary: str
