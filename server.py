"""
HVDC Knowledge MCP Server
Samsung C&T x ADNOC x DSV — HVDC UAE Project
도메인 지식(온톨로지 .md 파일)을 Claude Code/Desktop에 RAG로 제공하는 MCP 서버

MCP Best Practices 적용:
- Path traversal 방지 (resolve + prefix check)
- 인코딩 에러 핸들링 (errors="replace")
- 검색 pagination 지원
- 일관된 에러 응답 포맷
- 포괄적 docstring (입출력 스키마 명시)
"""

import argparse
import asyncio
from collections import deque
import contextlib
import contextvars
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from typing import Any, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlparse
from urllib.request import Request as UrlRequest, urlopen
import uuid

from hvdc_ops import (
    analyze_backlog,
    assess_shipment_case,
    compare_snapshot_summaries,
    evaluate_zero_gate_context,
    load_normalized_records,
    load_snapshot,
    normalize_inline_shipment,
    render_backlog_batch_markdown,
    render_compare_snapshots_markdown,
    render_self_test_markdown,
    render_shipment_case_markdown,
    render_zero_gate_markdown,
    save_snapshot,
    select_record,
)
from hvdc_ops.contracts import (
    BacklogBatchResult,
    BacklogUploadWidgetResult,
    ExcelExportPayload,
    SelfTestResult,
    ShipmentCaseResult,
    SnapshotCompareResult,
    ZeroGateCheckResult,
)
from hvdc_ops.domain_context import doc_markdown_files, load_domain_rules, render_domain_summary_markdown
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from mcp.types import CallToolResult, TextContent
from pydantic import BaseModel, Field, ConfigDict, field_validator
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse

# ───────────────────────────────────────────────
# 로깅 (stderr — stdio transport에서 stdout 오염 방지)
# ───────────────────────────────────────────────
_correlation_id_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "hvdc_correlation_id",
    default="",
)


class JsonLineFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "correlation_id": getattr(record, "correlation_id", None) or _correlation_id_var.get() or None,
        }
        for field in (
            "event",
            "component",
            "path",
            "method",
            "status_code",
            "tool_name",
            "target",
        ):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


_root_handler = logging.StreamHandler(stream=sys.stderr)
_root_handler.setFormatter(JsonLineFormatter())
logging.basicConfig(level=logging.INFO, handlers=[_root_handler], force=True)
logger = logging.getLogger("hvdc_knowledge_mcp")


def _current_correlation_id() -> str:
    return _correlation_id_var.get() or ""


def _new_correlation_id() -> str:
    return uuid.uuid4().hex


@contextlib.contextmanager
def _correlation_scope(correlation_id: str | None = None):
    token = _correlation_id_var.set(correlation_id or _new_correlation_id())
    try:
        yield _correlation_id_var.get()
    finally:
        _correlation_id_var.reset(token)


def _request_correlation_id(request: Request | None = None) -> str:
    if request is not None and hasattr(request, "headers"):
        for header in ("x-correlation-id", "x-request-id"):
            value = str(request.headers.get(header, "")).strip()
            if value:
                return value
    return _current_correlation_id() or _new_correlation_id()


def _log_event(level: int, message: str, **fields: Any) -> None:
    logger.log(level, message, extra=fields)

# ───────────────────────────────────────────────
# 환경 기본값
# ───────────────────────────────────────────────
def _env_default_port() -> int:
    return int(os.getenv("HVDC_MCP_PORT") or os.getenv("PORT") or "8000")


def _env_default_public_base_url() -> str:
    explicit = os.getenv("HVDC_PUBLIC_BASE_URL", "").rstrip("/")
    if explicit:
        return explicit
    railway_domain = os.getenv("RAILWAY_PUBLIC_DOMAIN", "").strip()
    if railway_domain:
        return f"https://{railway_domain}"
    return ""


def _origin_from_url(value: str | None) -> str:
    parsed = urlparse((value or "").strip())
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme}://{parsed.netloc}"
    return ""


# ───────────────────────────────────────────────
# 서버 초기화
# ───────────────────────────────────────────────
APP_INSTRUCTIONS = (
    "Use this app for HVDC UAE logistics knowledge. "
    "Use search and fetch for document retrieval with citations. "
    "Use hvdc_get_flow_code for validated Flow Code v3.5 rules, "
    "hvdc_get_node_info for node constraints, hvdc_get_kpi for KPI gates, "
    "hvdc_get_regulations for UAE compliance, and hvdc_hs_code_lookup for "
    "embedded HS examples. Use hvdc_analyze_shipment_case and "
    "hvdc_analyze_backlog_batch for operational analysis, "
    "hvdc_zero_gate_check for go/no-go validation, hvdc_compare_snapshots "
    "for trend comparison, and hvdc_mcp_self_test for connector diagnostics. "
    "When a ChatGPT user wants to upload a CSV/XLSX for backlog analysis, call "
    "hvdc_render_backlog_upload_widget first so the widget can upload the file "
    "and pass a temporary HTTP download URL to hvdc_analyze_backlog_batch. "
    "The upload widget is optional UI. The authoritative backlog result comes "
    "from hvdc_analyze_backlog_batch, and the authoritative machine-readable "
    "payload is returned in structuredContent. "
    "Always enforce AGI/DAS minimum Flow Code 3 and DOT permits for cargo above 90 tons."
)

mcp = FastMCP(
    "hvdc_knowledge_mcp",
    instructions=APP_INSTRUCTIONS,
    host=os.getenv("HVDC_MCP_HOST", "127.0.0.1"),
    port=_env_default_port(),
    streamable_http_path="/mcp",
    json_response=True,
    stateless_http=True,
)

# 도메인 문서 디렉토리
DOCS_DIR = Path(__file__).parent / "docs"
DOCS_ROUTE_PREFIX = "/docs"
COMPANY_KNOWLEDGE_MAX_BYTES = 250_000
CHATGPT_ALLOWED_ORIGINS = ["https://chatgpt.com", "https://chat.openai.com"]
RUNTIME_DIR = Path(__file__).parent / ".runtime"
WIDGETS_DIR = Path(__file__).parent / "widgets"
REMOTE_STATE_PATH = RUNTIME_DIR / "chatgpt_remote_state.json"
SERVER_STDOUT_LOG = RUNTIME_DIR / "remote-mcp.out.log"
SERVER_STDERR_LOG = RUNTIME_DIR / "remote-mcp.err.log"
TUNNEL_LOG = RUNTIME_DIR / "cloudflared.log"
CURSOR_MCP_CONFIG_PATH = Path(__file__).parent / ".cursor" / "mcp.json"
CURSOR_RULE_PATH = Path(__file__).parent / ".cursor" / "rules" / "hvdc-domain-background.mdc"
CODEX_PROJECT_CONFIG_PATH = Path(__file__).parent / ".codex" / "config.toml"
WINDOWS_FULL_SETUP_PATH = Path(__file__).parent / "SETUP_WINDOWS_FULL.cmd"
HANDOFF_DOC_PATH = Path(__file__).parent / "CHATGPT_CODEX_CURSOR_HANDOFF.md"
DASHBOARD_SNAPSHOT_PATH = RUNTIME_DIR / "dashboard_snapshots.jsonl"
DASHBOARD_SNAPSHOT_LIMIT = 720
DASHBOARD_TREND_LIMIT = 60
DASHBOARD_STALE_AFTER_SECONDS = 30
DASHBOARD_LOG_TAIL_LINES = 40
MCP_APP_RESOURCE_MIME = "text/html;profile=mcp-app"
BACKLOG_UPLOAD_WIDGET_URI = "ui://widget/hvdc-backlog-upload-v1.html"
DASHBOARD_SELF_TEST_PATH = "/dashboard/self-test"
EXCEL_EXPORT_VERSION = "2026-03-17"
EXCEL_EXPORT_SHEETS = ("Summary", "ZERO", "KPI", "Exceptions")

RUNTIME = {
    "transport": os.getenv("HVDC_MCP_TRANSPORT", "stdio"),
    "host": mcp.settings.host,
    "port": mcp.settings.port,
    "public_base_url": _env_default_public_base_url(),
}

# ───────────────────────────────────────────────
# 상수 — HVDC 도메인 핵심 데이터
# ───────────────────────────────────────────────

FLOW_CODES = {
    0: "Pre Arrival (선적 전 단계)",
    1: "Port → Site (직송, 창고 경유 없음)",
    2: "Port → WH → Site (창고 1개 이상 경유)",
    3: "Port → MOSB → Site (해상운송, AGI/DAS 필수)",
    4: "Port → WH → MOSB → Site (창고 + 해상운송)",
    5: "Mixed / Waiting / Incomplete leg (혼합/미완료)",
}

NODES = {
    "Zayed": {"type": "Port", "locode": "AEZYD", "customs_code": "47150", "cargo": "bulk/heavy"},
    "Khalifa": {"type": "Port", "locode": "AEAUH", "customs_code": "47150", "cargo": "container"},
    "JebelAli": {"type": "Port", "locode": "AEJEA", "customs_code": "1485718", "cargo": "freezone"},
    "MOSB": {"type": "Hub", "capacity_sqm": 20000, "operator": "ADNOC L&S", "sct_team": True},
    "MIR": {"type": "OnshoreSite", "laydown_sqm": 35006, "transport": "SPMT", "dot_required": True},
    "SHU": {"type": "OnshoreSite", "laydown_sqm": 10556, "transport": "SPMT", "dot_required": True},
    "DAS": {"type": "OffshoreSite", "voyage_hours": 20, "operator": "ALS", "mosb_mandatory": True},
    "AGI": {"type": "OffshoreSite", "voyage_hours": 10, "operator": "ALS", "mosb_mandatory": True},
}

KPI_GATES = {
    "invoice_ocr": {"threshold": 98.0, "unit": "%", "direction": ">=", "description": "OCR 정확도"},
    "invoice_audit_delta": {"threshold": 2.0, "unit": "%", "direction": "<=", "description": "인보이스 감사 오차"},
    "cost_guard_warn_rate": {"threshold": 5.0, "unit": "%", "direction": "<=", "description": "비용 경고 발생률"},
    "hs_risk_misclass": {"threshold": 0.5, "unit": "%", "direction": "<=", "description": "HS Code 오분류율"},
    "cert_chk_auto_pass": {"threshold": 90.0, "unit": "%", "direction": ">=", "description": "인증 자동통과율"},
    "wh_forecast_util": {"threshold": 85.0, "unit": "%", "direction": "<=", "description": "창고 가동률 예측"},
    "weather_tie_eta_mape": {"threshold": 12.0, "unit": "%", "direction": "<=", "description": "기상연계 ETA 오차"},
}

REGULATIONS = {
    "FANR": {
        "full_name": "Federal Authority for Nuclear Regulation",
        "requirement": "방사선 기자재 수입허가",
        "validity_days": 60,
        "trigger": "방사선 소스, 핵물질 포함 기자재",
        "block_action": "유효 Permit 없으면 BOE 제출 중단",
    },
    "MOIAT_ECAS": {
        "full_name": "Ministry of Industry & Advanced Technology - Emirates Conformity Assessment Scheme",
        "requirement": "규제제품 적합성 인증",
        "trigger": "전기·전자 규제제품",
        "block_action": "CoC 없으면 DO·GatePass 발급 금지",
    },
    "MOIAT_EQM": {
        "full_name": "Emirates Quality Mark",
        "requirement": "장비 품질 마크",
        "trigger": "특정 규제 제품군",
    },
    "DOT": {
        "full_name": "Department of Transport UAE",
        "requirement": "중량물 육상운송 허가",
        "weight_threshold_tons": 90,
        "additional": "SPMT 이송 시 escortVehicle + routeApproval 필수",
        "block_action": "허가 없으면 MIR/SHU 이송 금지",
    },
    "CICPA": {
        "full_name": "Critical Infrastructure & Coastal Protection Authority",
        "requirement": "항만·해상 시설 출입 게이트패스",
        "validity": "현장별 상이 (현장 공지 우선 확인)",
        "block_action": "GatePass 없으면 Port/MOSB 출입 불가",
    },
    "ADNOC_FRA": {
        "full_name": "ADNOC Formal Risk Assessment",
        "requirement": "해상 리프팅 위험성 평가",
        "trigger": "LCT 출항 전, 크레인 리프팅 작업",
        "block_action": "FRA 미완료 시 선적 중단",
    },
}

HS_CODE_EXAMPLES = {
    "850440": "변압기 (Transformers) — HVDC 핵심 품목",
    "854430": "전력케이블 (Power cables)",
    "853690": "전기 개폐 장치 (Switchgear)",
    "854140": "반도체 소자 (Semiconductor devices)",
    "848180": "밸브류 (Valves)",
}


# ───────────────────────────────────────────────
# 헬퍼 함수
# ───────────────────────────────────────────────

def _safe_resolve(filepath: Path) -> Optional[Path]:
    """Path traversal 방지 — docs/ 외부 접근 차단"""
    try:
        resolved = filepath.resolve()
        docs_resolved = DOCS_DIR.resolve()
        if str(resolved).startswith(str(docs_resolved)):
            return resolved
    except (OSError, ValueError):
        pass
    return None


def _read_file_safe(filepath: Path) -> str:
    """안전한 파일 읽기 — 인코딩 에러 대응"""
    safe_path = _safe_resolve(filepath)
    if safe_path is None:
        return "[접근 거부: docs/ 외부 경로]"
    try:
        return safe_path.read_text(encoding="utf-8", errors="replace")
    except OSError as e:
        logger.warning(f"파일 읽기 실패: {filepath} — {e}")
        return f"[파일 읽기 실패: {filepath.name}]"


def _load_doc(filename: str) -> str:
    """docs/ 폴더(하위 포함)에서 .md 파일 로드 (path traversal 방지)"""
    if not DOCS_DIR.exists():
        return "[docs/ 폴더가 존재하지 않습니다]"
    matches = list(DOCS_DIR.rglob(filename))
    if not matches:
        return f"[문서 없음: {filename}]"
    return _read_file_safe(matches[0])


def _slugify(value: str) -> str:
    """문서 경로를 stable id로 바꾸기 위한 slug 생성"""
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "doc"


def _normalize_public_base_url(url: str | None) -> str:
    if not url:
        return ""
    return url.rstrip("/")


def _runtime_base_url() -> str:
    explicit_base_url = _normalize_public_base_url(RUNTIME.get("public_base_url"))
    if explicit_base_url:
        return explicit_base_url

    host = str(RUNTIME.get("host") or "127.0.0.1")
    if host in {"0.0.0.0", "::"}:
        host = "127.0.0.1"
    return f"http://{host}:{RUNTIME.get('port', 8000)}"


def _build_doc_id(filepath: Path) -> str:
    """상대 경로 기반 stable document id 생성"""
    relative = filepath.relative_to(DOCS_DIR).with_suffix("")
    return "--".join(_slugify(part) for part in relative.parts)


def _build_doc_entry(filepath: Path) -> Optional[dict]:
    """문서 메타데이터 생성"""
    safe_path = _safe_resolve(filepath)
    if safe_path is None:
        return None

    doc_id = _build_doc_id(filepath)
    return {
        "id": doc_id,
        "title": filepath.stem,
        "filename": filepath.name,
        "relative_path": filepath.relative_to(DOCS_DIR).as_posix(),
        "url": f"{_runtime_base_url()}{DOCS_ROUTE_PREFIX}/{quote(doc_id, safe='')}",
        "path": safe_path,
    }


def _build_doc_catalog(include_large: bool = True) -> dict[str, dict]:
    """docs/ 하위 markdown 문서 카탈로그 생성"""
    catalog: dict[str, dict] = {}
    if not DOCS_DIR.exists():
        return catalog

    for md_file in sorted(DOCS_DIR.rglob("*.md")):
        if not include_large and md_file.stat().st_size > COMPANY_KNOWLEDGE_MAX_BYTES:
            continue

        entry = _build_doc_entry(md_file)
        if entry is not None:
            catalog[entry["id"]] = entry

    return catalog


def _resolve_doc_entry(identifier: str, include_large: bool = True) -> Optional[dict]:
    """doc id / filename / stem 기준으로 문서 찾기"""
    if not identifier:
        return None

    catalog = _build_doc_catalog(include_large=include_large)
    if identifier in catalog:
        return catalog[identifier]

    normalized = identifier.strip().lower()
    for entry in catalog.values():
        if normalized in {
            entry["id"].lower(),
            entry["filename"].lower(),
            entry["title"].lower(),
        }:
            return entry

    return None


def _match_score(query: str, entry: dict, content: str) -> tuple[int, int]:
    """search tool용 간단한 relevance scoring"""
    normalized_query = query.lower().strip()
    if not normalized_query:
        return 0, 0

    haystack = content.lower()
    title_text = f"{entry['title']} {entry['filename']} {entry['relative_path']}".lower()
    terms = [term for term in re.split(r"\s+", normalized_query) if term]
    if not terms:
        return 0, 0

    score = 0
    match_count = 0

    if normalized_query in title_text:
        score += 60
        match_count += 1
    if normalized_query in haystack:
        score += 20
        match_count += haystack.count(normalized_query)

    for term in terms:
        title_hits = title_text.count(term)
        body_hits = haystack.count(term)
        score += title_hits * 25 + body_hits
        match_count += title_hits + body_hits

    return score, match_count


def _make_text_tool_result(payload: dict) -> CallToolResult:
    """ChatGPT company knowledge/search-fetch 규격 응답 래퍼"""
    return CallToolResult(
        content=[
            TextContent(
                type="text",
                text=json.dumps(payload, ensure_ascii=False),
            )
        ]
    )


def _make_structured_tool_result(
    payload: dict[str, Any] | BaseModel,
    *,
    summary_key: str = "markdown_summary",
) -> CallToolResult:
    """Structured tool output + markdown summary wrapper."""
    if isinstance(payload, BaseModel):
        payload = payload.model_dump(mode="json")
    summary_text = payload.get(summary_key) or payload.get("markdown_report")
    if not isinstance(summary_text, str) or not summary_text.strip():
        summary_text = json.dumps(payload, ensure_ascii=False, indent=2)
    return CallToolResult(
        content=[TextContent(type="text", text=summary_text)],
        structuredContent=payload,
        isError=False,
    )


def _analysis_snapshot_name(prefix: str = "backlog") -> str:
    return f"{prefix}-{datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S')}"


def _allow_local_analysis_paths() -> bool:
    return RUNTIME.get("transport") == "stdio"


def _excel_sheet(name: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {"name": name, "rows": rows}


def _rows_from_mapping(
    mapping: dict[str, Any],
    *,
    key_name: str,
    value_name: str,
    extra: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    base = extra or {}
    return [
        {
            **base,
            key_name: key,
            value_name: value,
        }
        for key, value in mapping.items()
    ]


def _build_excel_export_payload(
    *,
    kind: str,
    workbook_name: str | None,
    sheets: list[dict[str, Any]],
) -> dict[str, Any]:
    normalized_sheets = []
    for default_name in EXCEL_EXPORT_SHEETS:
        sheet = next((item for item in sheets if item["name"] == default_name), None)
        normalized_sheets.append(sheet or _excel_sheet(default_name, []))
    return {
        "version": EXCEL_EXPORT_VERSION,
        "kind": kind,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "workbook_name": workbook_name,
        "sheets": normalized_sheets,
    }


def _shipment_case_excel_export(payload: dict[str, Any]) -> dict[str, Any]:
    normalized_case = payload["normalized_case"]
    flow = payload["flow_assessment"]
    zero = payload["zero_gates"]
    summary_rows = [
        {
            "shipment_id": normalized_case.get("shipment_id"),
            "destination": normalized_case.get("destination"),
            "status": normalized_case.get("status"),
            "mode": normalized_case.get("mode"),
            "verdict": payload["verdict"]["status"],
            "observed_flow_code": flow["observed_flow_code"],
            "recommended_flow_code": flow["recommended_flow_code"],
            "blocking_actions": ", ".join(zero.get("blocking_actions", [])),
            "warning_actions": ", ".join(zero.get("warning_actions", [])),
        }
    ]
    zero_rows = [
        {
            "gate": gate_name,
            "status": details.get("status"),
            "value": details.get("value"),
            "rule": details.get("rule"),
            "block_action": details.get("block_action"),
            "reason": details.get("reason"),
        }
        for gate_name, details in payload["zero_gates"]["gate_results"].items()
    ]
    kpi_rows = [
        {
            "kpi": kpi_name,
            "status": details.get("status"),
            "value": details.get("value"),
            "threshold": details.get("threshold"),
            "direction": details.get("direction"),
            "unit": details.get("unit"),
        }
        for kpi_name, details in payload["kpi_checks"].items()
    ]
    exception_rows = [
        {"type": "flow_reason", "detail": reason}
        for reason in flow.get("reasons", [])
    ] + [
        {"type": "blocking_action", "detail": item}
        for item in zero.get("blocking_actions", [])
    ] + [
        {"type": "warning_action", "detail": item}
        for item in zero.get("warning_actions", [])
    ]
    return _build_excel_export_payload(
        kind="hvdc.shipment_case",
        workbook_name=normalized_case.get("shipment_id"),
        sheets=[
            _excel_sheet("Summary", summary_rows),
            _excel_sheet("ZERO", zero_rows),
            _excel_sheet("KPI", kpi_rows),
            _excel_sheet("Exceptions", exception_rows),
        ],
    )


def _backlog_batch_excel_export(payload: dict[str, Any]) -> dict[str, Any]:
    summary_rows = _rows_from_mapping(
        payload["totals"],
        key_name="metric",
        value_name="value",
        extra={"section": "totals"},
    ) + _rows_from_mapping(
        payload["by_status"],
        key_name="metric",
        value_name="value",
        extra={"section": "by_status"},
    )
    zero_rows = [dict(row) for row in payload.get("zero_candidates", [])]
    kpi_rows = [
        {"kind": "breach", "code": row["code"], "count": row["count"]}
        for row in payload.get("breaches", [])
    ]
    exception_rows = [
        {
            "kind": "hotspot",
            "destination": row["destination"],
            "status": row["status"],
            "count": row["count"],
        }
        for row in payload.get("hotspots", [])
    ] + _rows_from_mapping(
        payload["by_site"],
        key_name="site",
        value_name="count",
        extra={"kind": "site_count"},
    ) + _rows_from_mapping(
        payload["by_mode"],
        key_name="mode",
        value_name="count",
        extra={"kind": "mode_count"},
    )
    return _build_excel_export_payload(
        kind="hvdc.backlog_batch",
        workbook_name=payload.get("snapshot_name"),
        sheets=[
            _excel_sheet("Summary", summary_rows),
            _excel_sheet("ZERO", zero_rows),
            _excel_sheet("KPI", kpi_rows),
            _excel_sheet("Exceptions", exception_rows),
        ],
    )


def _snapshot_compare_excel_export(payload: dict[str, Any]) -> dict[str, Any]:
    summary_rows = _rows_from_mapping(
        payload["delta_totals"],
        key_name="metric",
        value_name="delta",
        extra={"section": "delta_totals"},
    )
    zero_rows = [
        {"change_type": "new", **row}
        for row in payload.get("new_zero_candidates", [])
    ] + [
        {"change_type": "resolved", **row}
        for row in payload.get("resolved_zero_candidates", [])
    ]
    kpi_rows = _rows_from_mapping(
        payload["delta_by_status"],
        key_name="status",
        value_name="delta",
        extra={"section": "delta_by_status"},
    )
    exception_rows = _rows_from_mapping(
        payload["delta_by_site"],
        key_name="site",
        value_name="delta",
        extra={"section": "delta_by_site"},
    ) + _rows_from_mapping(
        payload["delta_by_mode"],
        key_name="mode",
        value_name="delta",
        extra={"section": "delta_by_mode"},
    )
    return _build_excel_export_payload(
        kind="hvdc.snapshot_compare",
        workbook_name=f"{payload.get('baseline_snapshot')}-to-{payload.get('candidate_snapshot')}",
        sheets=[
            _excel_sheet("Summary", summary_rows),
            _excel_sheet("ZERO", zero_rows),
            _excel_sheet("KPI", kpi_rows),
            _excel_sheet("Exceptions", exception_rows),
        ],
    )


def _read_widget_template(filename: str) -> str:
    template_path = (WIDGETS_DIR / filename).resolve()
    return template_path.read_text(encoding="utf-8")


def _widget_resource_meta() -> dict[str, Any]:
    public_origin = _origin_from_url(_env_default_public_base_url())
    widget_domain = (
        os.getenv("HVDC_WIDGET_DOMAIN", "").strip()
        or public_origin
        or "https://hvdc-knowledge-mcp.local"
    )
    connect_domains = [public_origin] if public_origin else []
    resource_domains = ["https://persistent.oaistatic.com"]
    return {
        "openai/widgetDescription": (
            "Upload a CSV or XLSX file, then run HVDC backlog analysis and review ZERO candidates."
        ),
        "openai/widgetPrefersBorder": True,
        "openai/widgetCSP": {
            "connect_domains": connect_domains,
            "resource_domains": resource_domains,
        },
        "openai/widgetDomain": widget_domain,
        "ui": {
            "prefersBorder": True,
            "csp": {
                "connectDomains": connect_domains,
                "resourceDomains": resource_domains,
            },
            "domain": widget_domain,
        },
    }


def _internal_base_url() -> str:
    host = str(RUNTIME["host"]).strip()
    if host in {"", "0.0.0.0"}:
        host = "127.0.0.1"
    elif host == "::":
        host = "[::1]"
    return f"http://{host}:{RUNTIME['port']}"


def _normalize_excel_mcp_url(url: str | None) -> dict[str, str | None]:
    raw = str(url or "").strip().rstrip("/")
    if not raw:
        return {"base_url": None, "mcp_url": None}
    if raw.endswith("/mcp"):
        return {"base_url": raw[:-4], "mcp_url": raw}
    return {"base_url": raw, "mcp_url": f"{raw}/mcp"}


def _http_json(
    url: str,
    *,
    method: str = "GET",
    body: dict[str, Any] | None = None,
    expected_statuses: set[int] | None = None,
    timeout_sec: int = 10,
) -> dict[str, Any]:
    data = None
    headers = {"Accept": "application/json, text/event-stream"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = UrlRequest(url, data=data, headers=headers, method=method)
    try:
        with urlopen(request, timeout=timeout_sec) as response:
            status = getattr(response, "status", 200)
            if expected_statuses and status not in expected_statuses:
                raise ValueError(f"Unexpected status {status} for {url}")
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        status = exc.code
        raw = exc.read().decode("utf-8", errors="replace")
        if expected_statuses and status in expected_statuses:
            return {"status": status, "body": raw}
        raise ValueError(f"{method} {url} failed with HTTP {status}: {raw}") from exc
    except URLError as exc:
        raise ValueError(f"{method} {url} failed: {exc.reason}") from exc

    try:
        payload = json.loads(raw) if raw else {}
    except json.JSONDecodeError:
        payload = {"raw": raw}
    payload.setdefault("status", status)
    return payload


async def _run_self_test(target: str, include_tool_calls: bool) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    recommendations: list[str] = []
    public_base_url = _normalize_public_base_url(RUNTIME.get("public_base_url"))
    local_base_url = _internal_base_url()
    state = _read_json_file_safe(REMOTE_STATE_PATH)
    state_public_base_url = _normalize_public_base_url(state.get("public_base_url"))
    if public_base_url and state_public_base_url and state_public_base_url != public_base_url:
        connector_url = f"{public_base_url}/mcp"
    else:
        connector_url = state.get("mcp_url") or (f"{public_base_url}/mcp" if public_base_url else None)

    def add_check(name: str, status: str, detail: str = "") -> None:
        checks.append({"name": name, "status": status, "detail": detail})

    async def fetch_json(
        url: str,
        *,
        method: str = "GET",
        body: dict[str, Any] | None = None,
        expected_statuses: set[int] | None = None,
    ) -> dict[str, Any]:
        return await asyncio.to_thread(
            _http_json,
            url,
            method=method,
            body=body,
            expected_statuses=expected_statuses,
        )

    async def check_base(label: str, base_url: str | None) -> None:
        if not base_url:
            add_check(f"{label} base url", "skipped", "No base URL configured.")
            return
        try:
            root = await fetch_json(f"{base_url}/", expected_statuses={200})
            add_check(f"{label} health", "pass", f"transport={root.get('transport')}")
            dashboard = await fetch_json(f"{base_url}/dashboard/status", expected_statuses={200})
            dashboard_summary = dashboard.get("summary") if isinstance(dashboard.get("summary"), dict) else {}
            add_check(
                f"{label} dashboard",
                "pass",
                f"health_score={dashboard_summary.get('health_score')}",
            )
        except Exception as exc:
            add_check(f"{label} health", "fail", str(exc))
            recommendations.append(f"Restore {label} HTTP health before using the connector.")
            return

        if include_tool_calls:
            mcp_url = f"{base_url}{mcp.settings.streamable_http_path}"
            initialize_body = {
                "jsonrpc": "2.0",
                "id": "initialize",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "hvdc-self-test", "version": "1.0"},
                },
            }
            tools_list_body = {
                "jsonrpc": "2.0",
                "id": "tools-list",
                "method": "tools/list",
                "params": {},
            }
            tool_call_body = {
                "jsonrpc": "2.0",
                "id": "tool-call",
                "method": "tools/call",
                "params": {"name": "hvdc_get_domain_summary", "arguments": {}},
            }
            try:
                initialize = await fetch_json(
                    mcp_url,
                    method="POST",
                    body=initialize_body,
                    expected_statuses={200},
                )
                server_info = ((initialize.get("result") or {}).get("serverInfo") or {})
                add_check(f"{label} mcp initialize", "pass", server_info.get("name", "ok"))
            except Exception as exc:
                add_check(f"{label} mcp initialize", "fail", str(exc))
                recommendations.append(f"Fix {label} /mcp initialize before relying on ChatGPT.")
                return

            try:
                tools_list = await fetch_json(
                    mcp_url,
                    method="POST",
                    body=tools_list_body,
                    expected_statuses={200},
                )
                tools = ((tools_list.get("result") or {}).get("tools") or [])
                add_check(f"{label} tools/list", "pass", f"{len(tools)} tools")
            except Exception as exc:
                add_check(f"{label} tools/list", "fail", str(exc))
                recommendations.append(f"Fix {label} tools/list before relying on analysis tools.")

            try:
                tool_call = await fetch_json(
                    mcp_url,
                    method="POST",
                    body=tool_call_body,
                    expected_statuses={200},
                )
                is_error = bool((tool_call.get("result") or {}).get("isError"))
                add_check(f"{label} sample tool call", "fail" if is_error else "pass", "hvdc_get_domain_summary")
            except Exception as exc:
                add_check(f"{label} sample tool call", "fail", str(exc))
                recommendations.append(f"Fix representative tool calls on {label} before using this server.")

    if target in {"local", "both"}:
        if RUNTIME.get("transport") != "streamable-http":
            add_check("local health", "skipped", "HTTP transport is not active in stdio mode.")
        else:
            await check_base("local", local_base_url)

    if target in {"public", "both"}:
        if public_base_url:
            await check_base("public", public_base_url)
        else:
            add_check("public health", "skipped", "No public_base_url configured.")
            recommendations.append("Set HVDC_PUBLIC_BASE_URL for stable connector checks.")

    live_host = urlparse(public_base_url or local_base_url).netloc
    state_host = urlparse(str(connector_url or "")).netloc
    if connector_url and state_host and live_host and state_host != live_host:
        add_check(
            "connector freshness",
            "warning",
            f"State connector host {state_host} differs from live host {live_host}.",
        )
        recommendations.append("Refresh or recreate the ChatGPT connector to use the live /mcp URL.")
    elif connector_url:
        add_check("connector freshness", "pass", "Connector URL matches the live host.")
    else:
        add_check("connector freshness", "warning", "No connector URL found in state.")
        recommendations.append("Create or refresh the ChatGPT connector after the server starts.")

    if public_base_url.endswith(".trycloudflare.com"):
        add_check("quick tunnel mode", "warning", "Connector URL is using a quick tunnel.")
        recommendations.append("Move to a stable HTTPS host for durable ChatGPT connector URLs.")
    elif public_base_url:
        add_check("quick tunnel mode", "pass", "Stable public base URL detected.")
    else:
        add_check("quick tunnel mode", "skipped", "No public base URL configured.")

    failed = any(check["status"] == "fail" for check in checks)
    warnings = any(check["status"] == "warning" for check in checks)
    status = "fail" if failed else "warning" if warnings else "pass"
    return {
        "checks": checks,
        "connector_url": connector_url,
        "public_base_url": public_base_url or None,
        "status": status,
        "recommendations": recommendations,
    }


def _build_transport_security(public_base_url: str | None) -> TransportSecuritySettings:
    """streamable-http용 Host/Origin 보안 정책 생성"""
    normalized_base_url = _normalize_public_base_url(public_base_url)
    if not normalized_base_url:
        logger.warning(
            "HVDC_PUBLIC_BASE_URL not set. Streamable HTTP will run in dev mode "
            "without DNS rebinding protection, and search/fetch URLs will point to localhost."
        )
        return TransportSecuritySettings(enable_dns_rebinding_protection=False)

    parsed = urlparse(normalized_base_url)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(
            "public base URL must include scheme and host, for example https://abc123.ngrok.app"
        )

    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=["127.0.0.1:*", "localhost:*", "[::1]:*", parsed.netloc],
        allowed_origins=[
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://[::1]:*",
            f"{parsed.scheme}://{parsed.netloc}",
            *CHATGPT_ALLOWED_ORIGINS,
        ],
    )


def _configure_runtime(
    transport: str,
    host: str,
    port: int,
    public_base_url: str | None,
) -> None:
    """CLI/env 기반 런타임 설정 반영"""
    normalized_public_base_url = _normalize_public_base_url(public_base_url)
    RUNTIME.update(
        {
            "transport": transport,
            "host": host,
            "port": port,
            "public_base_url": normalized_public_base_url,
        }
    )

    mcp.settings.host = host
    mcp.settings.port = port
    mcp.settings.json_response = True
    mcp.settings.stateless_http = True

    if transport == "streamable-http":
        mcp.settings.transport_security = _build_transport_security(normalized_public_base_url)


def _build_root_status_payload() -> dict:
    indexed_docs = len(_build_doc_catalog(include_large=False))
    total_docs = len(_build_doc_catalog(include_large=True))
    public_base_url = _normalize_public_base_url(RUNTIME.get("public_base_url"))
    runtime_base_url = _runtime_base_url()
    widget_meta = _widget_resource_meta()
    widget_ui_meta = widget_meta.get("ui") if isinstance(widget_meta.get("ui"), dict) else {}
    widget_csp = widget_ui_meta.get("csp") if isinstance(widget_ui_meta.get("csp"), dict) else {}
    tools = [
        "search",
        "fetch",
        "hvdc_get_domain_summary",
        "hvdc_search_docs",
        "hvdc_read_doc",
        "hvdc_list_docs",
        "hvdc_get_node_info",
        "hvdc_get_flow_code",
        "hvdc_get_kpi",
        "hvdc_get_regulations",
        "hvdc_hs_code_lookup",
        "hvdc_analyze_shipment_case",
        "hvdc_render_backlog_upload_widget",
        "hvdc_analyze_backlog_batch",
        "hvdc_zero_gate_check",
        "hvdc_compare_snapshots",
        "hvdc_mcp_self_test",
    ]
    widget_template_path = WIDGETS_DIR / "hvdc_backlog_upload_v1.html"
    chatgpt_upload = {
        "supported": widget_template_path.exists(),
        "widget_tool_name": "hvdc_render_backlog_upload_widget",
        "widget_tool_available": "hvdc_render_backlog_upload_widget" in tools,
        "analysis_tool_name": "hvdc_analyze_backlog_batch",
        "analysis_tool_available": "hvdc_analyze_backlog_batch" in tools,
        "resource_uri": BACKLOG_UPLOAD_WIDGET_URI,
        "resource_available": widget_template_path.exists(),
        "template_path": str(widget_template_path),
        "template_exists": widget_template_path.exists(),
        "widget_domain": widget_ui_meta.get("domain"),
        "widget_domain_configured": bool(widget_ui_meta.get("domain")),
        "widget_csp": widget_csp,
        "widget_csp_configured": bool(widget_csp.get("connectDomains") is not None and widget_csp.get("resourceDomains") is not None),
        "submission_ready": bool(widget_template_path.exists() and widget_ui_meta.get("domain") and widget_csp),
        "accepted_extensions": [".csv", ".xlsx"],
        "remote_download_url_schemes": ["http", "https"],
        "direct_sandbox_paths_supported": False,
        "local_path_stdio_only": True,
        "recommended_prompt": "Backlog upload widget을 열어서 XLSX를 올리고 ZERO 후보를 분석해줘",
        "instructions": [
            "ChatGPT remote uploads must be converted into a temporary HTTP/HTTPS download URL.",
            "Use hvdc_render_backlog_upload_widget before hvdc_analyze_backlog_batch for CSV/XLSX uploads.",
            "sandbox:/mnt/... paths are not readable by Railway or other remote MCP hosts.",
        ],
    }
    return {
        "name": "hvdc_knowledge_mcp",
        "transport": RUNTIME["transport"],
        "mcp_path": mcp.settings.streamable_http_path,
        "docs_path": DOCS_ROUTE_PREFIX,
        "dashboard_path": "/dashboard",
        "dashboard_status_path": "/dashboard/status",
        "dashboard_self_test_path": DASHBOARD_SELF_TEST_PATH,
        "host": RUNTIME["host"],
        "port": RUNTIME["port"],
        "runtime_base_url": runtime_base_url,
        "public_base_url": public_base_url or None,
        "dashboard_url": f"{runtime_base_url}/dashboard",
        "dashboard_self_test_url": f"{runtime_base_url}{DASHBOARD_SELF_TEST_PATH}",
        "indexed_docs": indexed_docs,
        "total_docs": total_docs,
        "tools": tools,
        "resources": [
            {
                "name": "hvdc-backlog-upload-widget",
                "uri": BACKLOG_UPLOAD_WIDGET_URI,
                "mime_type": MCP_APP_RESOURCE_MIME,
                "meta": widget_meta,
            }
        ],
        "chatgpt_upload": chatgpt_upload,
    }


async def _build_health_payload(request: Request | None = None) -> dict[str, Any]:
    root_payload = _build_root_status_payload()
    state = _read_json_file_safe(REMOTE_STATE_PATH)
    correlation_id = _request_correlation_id(request)
    request_host = str(request.headers.get("host", "")).strip() if request is not None else ""
    public_base_url = _normalize_public_base_url(root_payload.get("public_base_url"))
    public_host = urlparse(public_base_url).netloc if public_base_url else ""

    docs_ready = bool(DOCS_DIR.exists() and root_payload.get("indexed_docs", 0) > 0)
    mcp_ready = bool(root_payload.get("mcp_path") and root_payload.get("tools"))
    if public_host and request_host:
        public_probe_ok: bool | None = request_host == public_host
    elif public_base_url:
        probe_value = state.get("last_health_probe_ok")
        public_probe_ok = probe_value if isinstance(probe_value, bool) else None
    else:
        public_probe_ok = None

    checks = [
        {"name": "docs", "ok": docs_ready, "detail": f"indexed_docs={root_payload.get('indexed_docs', 0)}"},
        {"name": "mcp", "ok": mcp_ready, "detail": f"tools={len(root_payload.get('tools', []))}"},
        {
            "name": "public_probe",
            "ok": public_probe_ok,
            "detail": public_base_url or "not configured",
        },
    ]
    status = "healthy"
    if not docs_ready or not mcp_ready or public_probe_ok is False:
        status = "degraded"

    return {
        **root_payload,
        "status": status,
        "checks": checks,
        "docs_ready": docs_ready,
        "mcp_ready": mcp_ready,
        "public_probe_ok": public_probe_ok,
        "correlation_id": correlation_id,
    }


async def _build_excel_subservice_payload() -> dict[str, Any]:
    urls = _normalize_excel_mcp_url(os.getenv("HVDC_EXCEL_MCP_URL"))
    base_url = urls["base_url"]
    mcp_url = urls["mcp_url"]
    payload: dict[str, Any] = {
        "configured": bool(base_url),
        "status": "not_configured",
        "base_url": base_url,
        "mcp_url": mcp_url,
        "health": {"url": f"{base_url}/health" if base_url else None, "ok": None, "status_code": None, "latency_ms": None, "error": None},
        "initialize": {"url": mcp_url, "ok": None, "server_name": None, "status_code": None, "error": None},
        "local_ready": bool(base_url and urlparse(base_url).hostname in {"127.0.0.1", "localhost"}),
        "export_contract_version": EXCEL_EXPORT_VERSION,
        "sheet_defaults": list(EXCEL_EXPORT_SHEETS),
    }
    if not base_url or not mcp_url:
        return payload

    payload["health"] = await _probe_http_endpoint(f"{base_url}/health", timeout_sec=3)
    initialize_body = {
        "jsonrpc": "2.0",
        "id": "excel-initialize",
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "hvdc-dashboard", "version": "1.0"},
        },
    }
    started_at = time.perf_counter()
    try:
        initialize = await asyncio.to_thread(
            _http_json,
            mcp_url,
            method="POST",
            body=initialize_body,
            expected_statuses={200},
            timeout_sec=5,
        )
        server_info = ((initialize.get("result") or {}).get("serverInfo") or {})
        payload["initialize"] = {
            "url": mcp_url,
            "ok": True,
            "server_name": server_info.get("name"),
            "status_code": initialize.get("status", 200),
            "latency_ms": int((time.perf_counter() - started_at) * 1000),
            "error": None,
        }
    except Exception as exc:
        payload["initialize"] = {
            "url": mcp_url,
            "ok": False,
            "server_name": None,
            "status_code": None,
            "latency_ms": int((time.perf_counter() - started_at) * 1000),
            "error": str(exc),
        }

    if payload["health"].get("ok") and payload["initialize"].get("ok"):
        payload["status"] = "ready"
    else:
        payload["status"] = "degraded"
    return payload


def _connector_freshness_payload(
    connector_url: str | None,
    live_mcp_url: str | None,
) -> dict[str, Any]:
    if not connector_url:
        return {
            "status": "missing",
            "detail": "No connector URL is recorded in runtime state.",
            "connector_url": None,
        }

    connector_host = urlparse(connector_url).netloc
    live_host = urlparse(live_mcp_url or "").netloc
    if connector_host and live_host and connector_host == live_host:
        return {
            "status": "fresh",
            "detail": "Connector host matches the live MCP host.",
            "connector_url": connector_url,
        }

    if connector_host and live_host:
        return {
            "status": "stale",
            "detail": f"Connector host {connector_host} differs from live host {live_host}.",
            "connector_url": connector_url,
        }

    return {
        "status": "unknown",
        "detail": "Connector URL is present but host comparison is incomplete.",
        "connector_url": connector_url,
    }


def _surface_entry(
    *,
    surface_id: str,
    label: str,
    status: str,
    mode: str,
    primary: str,
    checks: list[str],
    next_action: str,
    verification: str,
    link: str | None = None,
) -> dict[str, Any]:
    status_label = {
        "ready": "Ready",
        "degraded": "Degraded",
        "action_needed": "Action Needed",
    }.get(status, "Unknown")
    return {
        "id": surface_id,
        "label": label,
        "status": status,
        "status_label": status_label,
        "mode": mode,
        "primary": primary,
        "checks": checks,
        "next_action": next_action,
        "verification": verification,
        "link": link,
    }


def _build_surface_readiness_payload(
    state: dict[str, Any],
    runtime: dict[str, Any],
    root_payload: dict[str, Any],
) -> dict[str, Any]:
    live_public_base_url = runtime.get("public_base_url") or root_payload.get("public_base_url")
    live_mcp_url = runtime.get("mcp_url") or (
        f"{live_public_base_url}{mcp.settings.streamable_http_path}" if live_public_base_url else None
    )
    chatgpt_upload = root_payload.get("chatgpt_upload") if isinstance(root_payload.get("chatgpt_upload"), dict) else {}
    connector = _connector_freshness_payload(state.get("mcp_url"), live_mcp_url)
    quick_tunnel = bool(
        runtime.get("mode") == "quick"
        or (isinstance(live_public_base_url, str) and live_public_base_url.endswith(".trycloudflare.com"))
    )

    chatgpt_status = "ready"
    if not live_public_base_url or not chatgpt_upload.get("submission_ready"):
        chatgpt_status = "action_needed"
    elif connector["status"] in {"missing", "stale"}:
        chatgpt_status = "action_needed"
    elif quick_tunnel:
        chatgpt_status = "degraded"

    chatgpt_checks = [
        f"Public base: {live_public_base_url or 'not configured'}",
        f"Widget submission: {'ready' if chatgpt_upload.get('submission_ready') else 'needs metadata'}",
        f"Connector freshness: {connector['status']}",
        f"Host stability: {'quick tunnel' if quick_tunnel else 'stable public host'}",
    ]
    if connector["detail"]:
        chatgpt_checks.append(connector["detail"])
    chatgpt_next_action = "Refresh the ChatGPT connector with the live /mcp URL."
    if not live_public_base_url:
        chatgpt_next_action = "Deploy the server behind a public HTTPS host before creating a connector."
    elif not chatgpt_upload.get("submission_ready"):
        chatgpt_next_action = "Restore widget metadata so ChatGPT file upload flows remain submission-ready."
    elif quick_tunnel:
        chatgpt_next_action = "Prefer Railway, Tailscale Funnel, or another stable host to avoid hostname rotation."

    cursor_ready = CURSOR_MCP_CONFIG_PATH.exists() and CURSOR_RULE_PATH.exists() and WINDOWS_FULL_SETUP_PATH.exists()
    codex_ready = CODEX_PROJECT_CONFIG_PATH.exists() and WINDOWS_FULL_SETUP_PATH.exists()

    items = [
        _surface_entry(
            surface_id="chatgpt",
            label="ChatGPT",
            status=chatgpt_status,
            mode="Remote MCP",
            primary=live_mcp_url or "Public /mcp not configured",
            checks=chatgpt_checks,
            next_action=chatgpt_next_action,
            verification="Create or refresh the connector, then run hvdc_mcp_self_test if the app still fails.",
            link=live_mcp_url,
        ),
        _surface_entry(
            surface_id="cursor",
            label="Cursor",
            status="ready" if cursor_ready else "action_needed",
            mode="Repo-local stdio MCP",
            primary="Reload Window after opening the trusted repo.",
            checks=[
                f".cursor/mcp.json: {'present' if CURSOR_MCP_CONFIG_PATH.exists() else 'missing'}",
                f"alwaysApply rule: {'present' if CURSOR_RULE_PATH.exists() else 'missing'}",
                f"Windows full setup: {'present' if WINDOWS_FULL_SETUP_PATH.exists() else 'missing'}",
            ],
            next_action="Run SETUP_WINDOWS_FULL.cmd on a new PC, then reload Cursor.",
            verification="Prompt: hvdc_get_domain_summary 먼저 호출해줘.",
            link=None,
        ),
        _surface_entry(
            surface_id="codex",
            label="Codex",
            status="ready" if codex_ready else "action_needed",
            mode="Repo-scoped stdio MCP",
            primary="Open the trusted repo so .codex/config.toml is loaded.",
            checks=[
                f".codex/config.toml: {'present' if CODEX_PROJECT_CONFIG_PATH.exists() else 'missing'}",
                f"Windows full setup: {'present' if WINDOWS_FULL_SETUP_PATH.exists() else 'missing'}",
                f"Handoff doc: {'present' if HANDOFF_DOC_PATH.exists() else 'missing'}",
            ],
            next_action="Run SETUP_WINDOWS_FULL.cmd, open the repo in Codex, and approve trust.",
            verification='Command: codex exec --skip-git-repo-check "Call hvdc_get_domain_summary and return only 3 bullets."',
            link=None,
        ),
    ]

    summary = {
        "total": len(items),
        "ready": sum(1 for item in items if item["status"] == "ready"),
        "degraded": sum(1 for item in items if item["status"] == "degraded"),
        "action_needed": sum(1 for item in items if item["status"] == "action_needed"),
    }
    return {"summary": summary, "items": items}


def _read_json_file_safe(filepath: Path) -> dict:
    try:
        if not filepath.exists():
            return {}
        return json.loads(filepath.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to read JSON file %s: %s", filepath, exc)
        return {}


def _isoformat_file_mtime(filepath: Path) -> Optional[str]:
    with contextlib.suppress(OSError):
        return datetime.fromtimestamp(filepath.stat().st_mtime, tz=timezone.utc).isoformat()
    return None


def _parse_iso_datetime(value: object) -> Optional[datetime]:
    if not isinstance(value, str) or not value:
        return None

    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _seconds_since(value: object) -> Optional[int]:
    parsed = _parse_iso_datetime(value)
    if parsed is None:
        return None
    return max(0, int((datetime.now(timezone.utc) - parsed).total_seconds()))


def _pid_from_value(value: object) -> Optional[int]:
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None


def _process_is_running(pid: Optional[int]) -> bool:
    if not pid:
        return False

    if os.name == "nt":
        try:
            completed = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return f'"{pid}"' in completed.stdout
        except OSError as exc:
            logger.warning("Failed to query PID %s on Windows: %s", pid, exc)
            return False

    with contextlib.suppress(OSError):
        os.kill(pid, 0)
        return True
    return False


def _tail_log(filepath: Path, max_lines: int = 20) -> list[str]:
    try:
        if not filepath.exists():
            return []
        lines: deque[str] = deque(maxlen=max_lines)
        with filepath.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                lines.append(line.rstrip())
        return list(lines)
    except OSError as exc:
        logger.warning("Failed to read log file %s: %s", filepath, exc)
        return []


def _runtime_log_paths(state: dict) -> dict[str, Path]:
    log_state = state.get("logs") if isinstance(state.get("logs"), dict) else {}
    defaults = {
        "server_stdout": SERVER_STDOUT_LOG,
        "server_stderr": SERVER_STDERR_LOG,
        "tunnel_log": TUNNEL_LOG,
    }

    log_paths: dict[str, Path] = {}
    for key, fallback in defaults.items():
        raw_path = log_state.get(key)
        log_paths[key] = Path(raw_path) if raw_path else fallback

    tunnel_stderr = log_state.get("tunnel_stderr")
    if tunnel_stderr:
        log_paths["tunnel_stderr"] = Path(tunnel_stderr)

    return log_paths


def _read_jsonl_file_safe(filepath: Path) -> list[dict[str, Any]]:
    if not filepath.exists():
        return []

    rows: list[dict[str, Any]] = []
    try:
        with filepath.open("r", encoding="utf-8", errors="replace") as handle:
            for line in handle:
                stripped = line.strip()
                if not stripped:
                    continue
                with contextlib.suppress(json.JSONDecodeError):
                    payload = json.loads(stripped)
                    if isinstance(payload, dict):
                        rows.append(payload)
    except OSError as exc:
        logger.warning("Failed to read JSONL file %s: %s", filepath, exc)
    return rows


def _write_jsonl_file_safe(filepath: Path, rows: list[dict[str, Any]]) -> None:
    try:
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(
            "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""),
            encoding="utf-8",
        )
    except OSError as exc:
        logger.warning("Failed to write JSONL file %s: %s", filepath, exc)


def _average(values: list[object]) -> Optional[float]:
    numbers = [float(value) for value in values if isinstance(value, (int, float))]
    if not numbers:
        return None
    return round(sum(numbers) / len(numbers), 1)


def _default_internal_base_url(host: str, port: int) -> str:
    internal_host = host or "127.0.0.1"
    if internal_host in {"0.0.0.0", "::"}:
        internal_host = "127.0.0.1"
    return f"http://{internal_host}:{port}"


def _normalize_probe(probe: object, fallback_url: Optional[str] = None) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "url": fallback_url,
        "ok": None,
        "status_code": None,
        "latency_ms": None,
        "error": None,
    }
    if isinstance(probe, dict):
        for key in ("url", "ok", "status_code", "latency_ms", "error"):
            if key in probe:
                payload[key] = probe.get(key)
    return payload


def _build_connectivity_payload(
    state: dict[str, Any],
    root_payload: dict[str, Any],
    runtime: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    live_status = state.get("live_status") if isinstance(state.get("live_status"), dict) else {}
    probes = live_status.get("probes") if isinstance(live_status.get("probes"), dict) else {}
    internal_base_url = _default_internal_base_url(str(root_payload["host"]), int(root_payload["port"]))

    return {
        "local_status": _normalize_probe(probes.get("local_status"), f"{internal_base_url}/"),
        "local_health": _normalize_probe(probes.get("local_health"), f"{internal_base_url}/health"),
        "local_docs": _normalize_probe(probes.get("local_docs"), f"{internal_base_url}{DOCS_ROUTE_PREFIX}"),
        "public_health": _normalize_probe(
            probes.get("public_health"),
            f"{runtime['public_base_url']}/health" if runtime.get("public_base_url") else None,
        ),
    }


async def _probe_http_endpoint(url: str, *, timeout_sec: int = 5) -> dict[str, Any]:
    started_at = time.perf_counter()
    try:
        payload = await asyncio.to_thread(
            _http_json,
            url,
            expected_statuses={200},
            timeout_sec=timeout_sec,
        )
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        return {
            "url": url,
            "ok": True,
            "status_code": payload.get("status", 200),
            "latency_ms": latency_ms,
            "error": None,
        }
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started_at) * 1000)
        match = re.search(r"\bHTTP (\d{3})\b", str(exc))
        return {
            "url": url,
            "ok": False,
            "status_code": int(match.group(1)) if match else None,
            "latency_ms": latency_ms,
            "error": str(exc),
        }


async def _refresh_connectivity_payload(
    connectivity: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    async def refresh_one(name: str, probe: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        url = probe.get("url")
        if not isinstance(url, str) or not url:
            return name, probe
        refreshed = await _probe_http_endpoint(url)
        return name, {**probe, **refreshed}

    refreshed = await asyncio.gather(
        *(refresh_one(name, probe) for name, probe in connectivity.items())
    )
    return {name: probe for name, probe in refreshed}


def _build_deployment_payload(runtime: dict[str, Any]) -> dict[str, Any]:
    public_base_url = str(runtime.get("public_base_url") or "")
    provider = "local"
    provider_label = "Local"

    if os.getenv("RAILWAY_PROJECT_ID") or os.getenv("RAILWAY_PUBLIC_DOMAIN"):
        provider = "railway"
        provider_label = "Railway"
    elif runtime.get("mode") == "tailscale-funnel" or public_base_url.endswith(".ts.net"):
        provider = "tailscale"
        provider_label = "Tailscale Funnel"
    elif public_base_url.endswith(".trycloudflare.com"):
        provider = "cloudflare-quick"
        provider_label = "Cloudflare Quick Tunnel"
    elif public_base_url:
        provider = "external"
        provider_label = "External HTTPS"

    return {
        "provider": provider,
        "provider_label": provider_label,
        "railway_project_name": os.getenv("RAILWAY_PROJECT_NAME") or None,
        "railway_project_id": os.getenv("RAILWAY_PROJECT_ID") or None,
        "railway_service_name": os.getenv("RAILWAY_SERVICE_NAME") or None,
        "railway_service_id": os.getenv("RAILWAY_SERVICE_ID") or None,
        "railway_environment_name": os.getenv("RAILWAY_ENVIRONMENT_NAME") or None,
        "railway_environment_id": os.getenv("RAILWAY_ENVIRONMENT_ID") or None,
        "railway_public_domain": os.getenv("RAILWAY_PUBLIC_DOMAIN") or None,
        "railway_private_domain": os.getenv("RAILWAY_PRIVATE_DOMAIN") or None,
    }


def _severity_rank(severity: str) -> int:
    return {"critical": 0, "warning": 1, "info": 2}.get(severity, 3)


def _collect_dashboard_alerts(
    state: dict[str, Any],
    runtime: dict[str, Any],
    root_payload: dict[str, Any],
    processes: dict[str, dict[str, Any]],
    connectivity: dict[str, dict[str, Any]],
    subservices: dict[str, Any],
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    managed = runtime["managed"]
    state_server_status = (
        state.get("server_status") if isinstance(state.get("server_status"), dict) else {}
    )
    recent_restarts = (
        list(state.get("recent_restarts", []))
        if isinstance(state.get("recent_restarts"), list)
        else []
    )
    latest_restart = recent_restarts[-1] if recent_restarts else {}

    if not processes["server"]["running"]:
        alerts.append(
            {
                "severity": "critical",
                "code": "server_down",
                "title": "Server process is down",
                "detail": "The MCP server PID is not responding.",
            }
        )

    if processes["supervisor"]["expected"] and not processes["supervisor"]["running"]:
        alerts.append(
            {
                "severity": "warning",
                "code": "supervisor_down",
                "title": "Supervisor process is down",
                "detail": "Auto-heal and periodic health probes are not running.",
            }
        )

    if processes["tunnel"]["expected"] and not processes["tunnel"]["running"]:
        alerts.append(
            {
                "severity": "critical",
                "code": "tunnel_down",
                "title": "Tunnel process is down",
                "detail": "The public HTTPS endpoint is unavailable until cloudflared is back.",
            }
        )

    if managed and isinstance(runtime.get("state_age_seconds"), int) and runtime["state_age_seconds"] > DASHBOARD_STALE_AFTER_SECONDS:
        alerts.append(
            {
                "severity": "warning",
                "code": "state_stale",
                "title": "Managed state file is stale",
                "detail": f"Last state update was {runtime['state_age_seconds']} seconds ago.",
            }
        )

    if managed and isinstance(runtime.get("probe_age_seconds"), int) and runtime["probe_age_seconds"] > DASHBOARD_STALE_AFTER_SECONDS:
        alerts.append(
            {
                "severity": "warning",
                "code": "probe_stale",
                "title": "Health probe is stale",
                "detail": f"Last supervisor probe was {runtime['probe_age_seconds']} seconds ago.",
            }
        )

    if managed and runtime.get("last_health_probe_ok") is False:
        alerts.append(
            {
                "severity": "critical",
                "code": "probe_failed",
                "title": "Latest health probe failed",
                "detail": "Supervisor could not validate the MCP HTTP surface on the latest check.",
            }
        )

    if runtime.get("public_base_url") and connectivity["public_health"].get("ok") is False:
        alerts.append(
            {
                "severity": "critical",
                "code": "public_health_failed",
                "title": "Public health endpoint failed",
                "detail": "The external HTTPS /health probe did not succeed.",
            }
        )

    if managed and connectivity["local_docs"].get("ok") is False:
        alerts.append(
            {
                "severity": "warning",
                "code": "docs_probe_failed",
                "title": "Docs endpoint probe failed",
                "detail": "The supervisor could not validate the /docs index.",
            }
        )

    indexed_docs = state_server_status.get("indexed_docs")
    total_docs = state_server_status.get("total_docs")
    chatgpt_upload = root_payload.get("chatgpt_upload") if isinstance(root_payload.get("chatgpt_upload"), dict) else {}
    if isinstance(indexed_docs, int) and indexed_docs != root_payload["indexed_docs"]:
        alerts.append(
            {
                "severity": "warning",
                "code": "indexed_docs_mismatch",
                "title": "Indexed document count changed",
                "detail": f"State reports {indexed_docs}, runtime reports {root_payload['indexed_docs']}.",
            }
        )
    if isinstance(total_docs, int) and total_docs != root_payload["total_docs"]:
        alerts.append(
            {
                "severity": "warning",
                "code": "total_docs_mismatch",
                "title": "Total document count changed",
                "detail": f"State reports {total_docs}, runtime reports {root_payload['total_docs']}.",
            }
        )

    if not chatgpt_upload.get("template_exists"):
        alerts.append(
            {
                "severity": "warning",
                "code": "upload_widget_missing",
                "title": "ChatGPT upload widget template is missing",
                "detail": "CSV/XLSX remote upload analysis will fail until the widget template is restored.",
            }
        )
    if not chatgpt_upload.get("widget_csp_configured"):
        alerts.append(
            {
                "severity": "warning",
                "code": "upload_widget_csp_missing",
                "title": "ChatGPT upload widget CSP is not configured",
                "detail": "App submission and broad distribution require _meta.ui.csp on the widget resource.",
            }
        )
    if not chatgpt_upload.get("widget_domain_configured"):
        alerts.append(
            {
                "severity": "warning",
                "code": "upload_widget_domain_missing",
                "title": "ChatGPT upload widget domain is not configured",
                "detail": "App submission requires _meta.ui.domain on the widget resource.",
            }
        )

    if latest_restart and latest_restart.get("public_url_changed"):
        alerts.append(
            {
                "severity": "warning",
                "code": "public_url_changed",
                "title": "Public URL changed on the latest restart",
                "detail": "Quick tunnel mode rotated the published hostname.",
            }
        )

    if runtime["mode"] == "quick":
        alerts.append(
            {
                "severity": "info",
                "code": "quick_tunnel",
                "title": "Quick tunnel mode",
                "detail": "The public hostname can change on restart.",
            }
        )

    if not runtime.get("public_base_url"):
        alerts.append(
            {
                "severity": "info",
                "code": "local_only",
                "title": "Public base URL is not configured",
                "detail": "Dashboard is running in local-only mode without a public HTTPS host.",
            }
        )

    excel_mcp = subservices.get("excel_mcp") if isinstance(subservices.get("excel_mcp"), dict) else {}
    if excel_mcp.get("configured") and excel_mcp.get("health", {}).get("ok") is False:
        alerts.append(
            {
                "severity": "warning",
                "code": "excel_health_failed",
                "title": "Excel MCP health probe failed",
                "detail": "Configured Excel MCP /health did not respond successfully.",
            }
        )
    if excel_mcp.get("configured") and excel_mcp.get("initialize", {}).get("ok") is False:
        alerts.append(
            {
                "severity": "warning",
                "code": "excel_initialize_failed",
                "title": "Excel MCP initialize failed",
                "detail": "Configured Excel MCP /mcp initialize call failed.",
            }
        )

    alerts.sort(key=lambda item: (_severity_rank(item["severity"]), item["code"]))
    return alerts


def _summarize_health(
    alerts: list[dict[str, str]],
    processes: dict[str, dict[str, Any]],
    runtime: dict[str, Any],
    connectivity: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    score = 100
    for alert in alerts:
        severity = alert["severity"]
        if severity == "critical":
            score -= 28
        elif severity == "warning":
            score -= 12
        elif severity == "info":
            score -= 3

    if not processes["server"]["running"]:
        score = 0
    elif connectivity["public_health"].get("ok") is False:
        score = min(score, 45)
    elif runtime.get("last_health_probe_ok") is False:
        score = min(score, 55)

    score = max(0, min(score, 100))
    health_state = "healthy"
    if score < 60 or not processes["server"]["running"]:
        health_state = "down"
    elif score < 90:
        health_state = "degraded"

    severity_counts = {
        "critical": sum(1 for alert in alerts if alert["severity"] == "critical"),
        "warning": sum(1 for alert in alerts if alert["severity"] == "warning"),
        "info": sum(1 for alert in alerts if alert["severity"] == "info"),
    }
    tracked_processes = [
        process for process in processes.values() if process["expected"] or process["required"]
    ]
    if not tracked_processes:
        tracked_processes = list(processes.values())
    processes_up = sum(1 for process in tracked_processes if process["running"])
    process_total = len(tracked_processes)

    return {
        "health_score": score,
        "health_state": health_state,
        "status_label": {"healthy": "Healthy", "degraded": "Degraded", "down": "Down"}[health_state],
        "alert_count": len(alerts),
        "severity_counts": severity_counts,
        "processes_up": processes_up,
        "process_total": process_total,
        "stale": bool(
            runtime["managed"]
            and (
                (isinstance(runtime.get("state_age_seconds"), int) and runtime["state_age_seconds"] > DASHBOARD_STALE_AFTER_SECONDS)
                or (isinstance(runtime.get("probe_age_seconds"), int) and runtime["probe_age_seconds"] > DASHBOARD_STALE_AFTER_SECONDS)
            )
        ),
        "restart_count": runtime.get("restart_count", 0),
    }


def _append_dashboard_snapshot(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    history = _read_jsonl_file_safe(DASHBOARD_SNAPSHOT_PATH)
    last_entry = history[-1] if history else None
    should_append = True

    current_ts = _parse_iso_datetime(snapshot.get("ts"))
    last_ts = _parse_iso_datetime(last_entry.get("ts")) if isinstance(last_entry, dict) else None
    if last_entry and current_ts and last_ts:
        same_runtime = all(
            last_entry.get(key) == snapshot.get(key)
            for key in ("started_at", "server_pid", "tunnel_pid", "supervisor_pid", "health_score", "health_state", "alert_count")
        )
        if same_runtime and (current_ts - last_ts).total_seconds() < 3:
            should_append = False

    if should_append:
        history.append(snapshot)
        history = history[-DASHBOARD_SNAPSHOT_LIMIT:]
        _write_jsonl_file_safe(DASHBOARD_SNAPSHOT_PATH, history)

    return history


def _build_history_payload(
    history: list[dict[str, Any]],
    runtime: dict[str, Any],
    recent_restarts: list[dict[str, Any]],
) -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    last_hour = []
    for entry in history:
        ts = _parse_iso_datetime(entry.get("ts"))
        if ts and (now - ts).total_seconds() <= 3600:
            last_hour.append(entry)

    trend_source = last_hour or history
    trend = trend_source[-DASHBOARD_TREND_LIMIT:]
    recent_restart_list = list(reversed(recent_restarts[-6:]))

    return {
        "sample_count": len(history),
        "last_hour_sample_count": len(last_hour),
        "avg_health_score": _average([entry.get("health_score") for entry in last_hour]),
        "avg_latency_ms": _average([entry.get("probe_latency_ms") for entry in last_hour]),
        "trend": trend,
        "restart_count": runtime.get("restart_count", 0),
        "recent_restarts": recent_restart_list,
        "latest_restart": recent_restart_list[0] if recent_restart_list else None,
    }


async def _build_dashboard_payload() -> dict:
    root_payload = _build_root_status_payload()
    state = _read_json_file_safe(REMOTE_STATE_PATH)
    if not state:
        state = {
            "mode": "public" if root_payload.get("public_base_url") else "local",
            "server_pid": os.getpid(),
            "status_url": f"{root_payload['runtime_base_url']}/",
            "health_url": f"{root_payload['runtime_base_url']}/health",
            "docs_url": f"{root_payload['runtime_base_url']}{DOCS_ROUTE_PREFIX}",
            "mcp_url": f"{root_payload['runtime_base_url']}{mcp.settings.streamable_http_path}",
            "dashboard_url": root_payload["dashboard_url"],
            "server_status": root_payload,
            "recent_restarts": [],
            "restart_count": 0,
        }

    log_paths = _runtime_log_paths(state)
    started_at = state.get("started_at") if isinstance(state.get("started_at"), str) else None
    started_dt = _parse_iso_datetime(started_at)
    uptime_seconds = max(0, int((datetime.now(timezone.utc) - started_dt).total_seconds())) if started_dt else None
    state_file_updated_at = _isoformat_file_mtime(REMOTE_STATE_PATH)
    last_health_probe_at = (
        state.get("last_health_probe_at")
        if isinstance(state.get("last_health_probe_at"), str)
        else (
            state["live_status"].get("health_probe_at")
            if isinstance(state.get("live_status"), dict) and isinstance(state["live_status"].get("health_probe_at"), str)
            else None
        )
    )
    restart_count = state.get("restart_count") if isinstance(state.get("restart_count"), int) else 0
    recent_restarts = (
        list(state.get("recent_restarts", []))
        if isinstance(state.get("recent_restarts"), list)
        else []
    )

    process_config = {
        "supervisor": {
            "pid": _pid_from_value(state.get("supervisor_pid")),
            "expected": bool(_pid_from_value(state.get("supervisor_pid"))),
            "required": False,
        },
        "server": {
            "pid": _pid_from_value(state.get("server_pid")) or os.getpid(),
            "expected": True,
            "required": True,
        },
        "tunnel": {
            "pid": _pid_from_value(state.get("tunnel_pid")),
            "expected": (state.get("mode") == "quick"),
            "required": (state.get("mode") == "quick"),
        },
    }
    processes: dict[str, dict[str, Any]] = {}
    for name, config in process_config.items():
        pid = config["pid"]
        processes[name] = {
            "pid": pid,
            "running": _process_is_running(pid),
            "expected": config["expected"],
            "required": config["required"],
        }

    runtime = {
        "managed": REMOTE_STATE_PATH.exists(),
        "mode": state.get("mode") or ("public" if root_payload.get("public_base_url") else "local"),
        "started_at": started_at,
        "uptime_seconds": uptime_seconds,
        "state_file": str(REMOTE_STATE_PATH),
        "state_file_updated_at": state_file_updated_at,
        "state_age_seconds": _seconds_since(state_file_updated_at),
        "last_health_probe_at": last_health_probe_at,
        "last_health_probe_ok": state.get("last_health_probe_ok"),
        "last_health_probe_latency_ms": state.get("last_health_probe_latency_ms"),
        "probe_age_seconds": _seconds_since(last_health_probe_at),
        "status_url": state.get("status_url") or f"{root_payload['runtime_base_url']}/",
        "health_url": state.get("health_url") or f"{root_payload['runtime_base_url']}/health",
        "docs_url": state.get("docs_url") or f"{root_payload['runtime_base_url']}{DOCS_ROUTE_PREFIX}",
        "mcp_url": state.get("mcp_url") or f"{root_payload['runtime_base_url']}{mcp.settings.streamable_http_path}",
        "dashboard_url": state.get("dashboard_url")
        or (
            f"{state.get('public_base_url')}/dashboard"
            if state.get("public_base_url")
            else root_payload["dashboard_url"]
        ),
        "public_base_url": state.get("public_base_url") or root_payload.get("public_base_url"),
        "cloudflared_path": state.get("cloudflared_path"),
        "restart_count": restart_count,
    }
    runtime["deployment"] = _build_deployment_payload(runtime)

    connectivity = await _refresh_connectivity_payload(
        _build_connectivity_payload(state, root_payload, runtime)
    )
    preferred_probe = connectivity.get("public_health") or connectivity.get("local_health") or {}
    if preferred_probe.get("ok") is not None:
        runtime["last_health_probe_at"] = datetime.now(timezone.utc).isoformat()
        runtime["last_health_probe_ok"] = preferred_probe.get("ok")
        runtime["last_health_probe_latency_ms"] = preferred_probe.get("latency_ms")
        runtime["probe_age_seconds"] = 0

    subservices = {
        "excel_mcp": await _build_excel_subservice_payload(),
    }
    alerts = _collect_dashboard_alerts(state, runtime, root_payload, processes, connectivity, subservices)
    summary = _summarize_health(alerts, processes, runtime, connectivity)

    snapshot = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "health_score": summary["health_score"],
        "health_state": summary["health_state"],
        "alert_count": summary["alert_count"],
        "processes_up": summary["processes_up"],
        "process_total": summary["process_total"],
        "probe_latency_ms": runtime.get("last_health_probe_latency_ms"),
        "state_age_seconds": runtime.get("state_age_seconds"),
        "probe_age_seconds": runtime.get("probe_age_seconds"),
        "started_at": runtime.get("started_at"),
        "supervisor_pid": processes["supervisor"]["pid"],
        "server_pid": processes["server"]["pid"],
        "tunnel_pid": processes["tunnel"]["pid"],
        "public_base_url": runtime.get("public_base_url"),
    }
    history_rows = _append_dashboard_snapshot(snapshot)
    history = _build_history_payload(history_rows, runtime, recent_restarts)
    surfaces = _build_surface_readiness_payload(state, runtime, root_payload)

    logs = {}
    for name, path in log_paths.items():
        logs[name] = {
            "path": str(path),
            "exists": path.exists(),
            "updated_at": _isoformat_file_mtime(path),
            "tail": _tail_log(path, max_lines=DASHBOARD_LOG_TAIL_LINES),
        }

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "runtime": runtime,
        "server": root_payload,
        "connectivity": connectivity,
        "subservices": subservices,
        "surfaces": surfaces,
        "processes": processes,
        "alerts": alerts,
        "history": history,
        "logs": logs,
    }


def _search_in_docs(keyword: str, max_results: int = 10) -> list[dict]:
    """모든 .md 파일에서 키워드 검색, 컨텍스트 반환 (pagination 지원)"""
    results = []
    if not DOCS_DIR.exists():
        return results

    for md_file in sorted(DOCS_DIR.rglob("*.md")):
        entry = _build_doc_entry(md_file)
        if entry is None:
            continue
        content = _read_file_safe(md_file)
        if content.startswith("["):  # 에러 메시지면 스킵
            continue
        lines = content.split("\n")
        matches = []
        for i, line in enumerate(lines):
            if keyword.lower() in line.lower():
                start = max(0, i - 2)
                end = min(len(lines), i + 5)
                snippet = "\n".join(lines[start:end])
                matches.append({"line": i + 1, "snippet": snippet})
        if matches:
            results.append({
                "doc_id": entry["id"],
                "file": md_file.name,
                "url": entry["url"],
                "match_count": len(matches),
                "matches": matches[:3],  # 파일당 최대 3개 스니펫
            })
        if len(results) >= max_results:
            break

    return results


def _count_lines(filepath: Path) -> int:
    """파일 줄 수만 세기 (전체 내용 메모리 로드 대신)"""
    try:
        safe_path = _safe_resolve(filepath)
        if safe_path is None:
            return 0
        count = 0
        with open(safe_path, "r", encoding="utf-8", errors="replace") as f:
            for _ in f:
                count += 1
        return count
    except OSError:
        return 0


def _make_error(message: str, hint: str = "", available: list = None) -> str:
    """일관된 에러 JSON 응답 생성"""
    result = {"error": message}
    if hint:
        result["hint"] = hint
    if available:
        result["available"] = available
    return json.dumps(result, ensure_ascii=False, indent=2)


# ───────────────────────────────────────────────
# 입력 모델 (Pydantic v2)
# ───────────────────────────────────────────────

class SearchInput(BaseModel):
    """키워드 검색 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    keyword: str = Field(
        ...,
        description="검색할 키워드 (예: 'MOSB', 'Flow Code', 'DOT permit')",
        min_length=1,
        max_length=200,
    )
    max_results: int = Field(
        default=10,
        description="최대 반환 파일 수 (1~50)",
        ge=1,
        le=50,
    )


class NodeQueryInput(BaseModel):
    """노드 조회 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    node_name: Optional[str] = Field(
        default=None,
        description="조회할 노드명 (예: 'MOSB', 'DAS', 'MIR'). 미입력 시 전체 반환.",
    )


class FlowCodeInput(BaseModel):
    """Flow Code 조회 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    code: Optional[int] = Field(
        default=None,
        description="조회할 Flow Code 번호 (0~5). 미입력 시 전체 반환.",
        ge=0,
        le=5,
    )
    destination: Optional[str] = Field(
        default=None,
        description="최종 목적지 (예: 'AGI', 'DAS', 'MIR', 'SHU'). AGI/DAS는 자동으로 Flow>=3 적용.",
    )


class DocQueryInput(BaseModel):
    """문서 읽기 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    filename: str = Field(
        ...,
        description="읽을 문서 파일명 (예: 'CONSOLIDATED-01-core-framework-infra.md')",
        min_length=1,
    )
    section: Optional[str] = Field(
        default=None,
        description="특정 섹션만 추출할 경우 헤더명 입력 (예: 'Flow Code', 'SHACL')",
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        """위험한 경로 패턴 차단"""
        if ".." in v or "/" in v or "\\" in v:
            raise ValueError("파일명에 경로 구분자를 포함할 수 없습니다. 파일명만 입력하세요.")
        return v


class KPIInput(BaseModel):
    """KPI 조회 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    kpi_name: Optional[str] = Field(
        default=None,
        description="조회할 KPI명 (예: 'invoice_ocr', 'wh_forecast_util'). 미입력 시 전체.",
    )


class RegulationInput(BaseModel):
    """규제 조회 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    regulation_name: Optional[str] = Field(
        default=None,
        description="조회할 규제명 (예: 'FANR', 'DOT', 'CICPA'). 미입력 시 전체.",
    )


class HSCodeInput(BaseModel):
    """HS Code 조회 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(
        ...,
        description="HS Code 번호 또는 품목명 (예: '850440', '변압기', 'transformer')",
        min_length=1,
    )


class CompanyKnowledgeSearchInput(BaseModel):
    """ChatGPT company knowledge/search tool 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    query: str = Field(
        ...,
        description="Search query for the HVDC logistics knowledge base",
        min_length=1,
        max_length=500,
    )


class CompanyKnowledgeFetchInput(BaseModel):
    """ChatGPT company knowledge/fetch tool 입력"""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    id: str = Field(
        ...,
        description="Document id returned from the search tool",
        min_length=1,
        max_length=500,
    )


class FileParam(BaseModel):
    """ChatGPT file input descriptor."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    download_url: Optional[str] = Field(
        default=None,
        description="Temporary HTTPS/HTTP download URL for the uploaded file.",
    )
    file_id: Optional[str] = Field(
        default=None,
        description="ChatGPT file id for traceability.",
    )


class ShipmentCaseInput(BaseModel):
    """Shipment case analysis input."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    shipment: Optional[dict[str, Any]] = Field(
        default=None,
        description="Structured shipment object using semantic keys or source column names.",
    )
    file: Optional[FileParam] = Field(
        default=None,
        description="ChatGPT file parameter with download_url and file_id.",
    )
    local_path: Optional[str] = Field(
        default=None,
        description="CSV/XLSX local path. Only allowed in stdio mode.",
    )
    row_number: Optional[int] = Field(
        default=None,
        description="1-based row number when selecting a shipment from a table source.",
        ge=1,
    )
    shipment_id: Optional[str] = Field(
        default=None,
        description="Shipment identifier when selecting a shipment from a table source.",
    )
    sheet_name: Optional[str] = Field(
        default=None,
        description="Worksheet name for XLSX input. Defaults to the first sheet.",
    )
    column_map: Optional[dict[str, str]] = Field(
        default=None,
        description="Semantic key to source column mapping override.",
    )


class BacklogBatchInput(BaseModel):
    """Backlog batch analysis input."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    file: Optional[FileParam] = Field(
        default=None,
        description="ChatGPT file parameter with download_url and file_id.",
    )
    local_path: Optional[str] = Field(
        default=None,
        description="CSV/XLSX local path. Only allowed in stdio mode.",
    )
    sheet_name: Optional[str] = Field(
        default=None,
        description="Worksheet name for XLSX input. Defaults to the first sheet.",
    )
    column_map: Optional[dict[str, str]] = Field(
        default=None,
        description="Semantic key to source column mapping override.",
    )
    snapshot_name: Optional[str] = Field(
        default=None,
        description="Optional snapshot name. Reused names overwrite prior snapshots.",
    )


class BacklogUploadWidgetInput(BaseModel):
    """Render tool input for the ChatGPT backlog upload widget."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    snapshot_name: Optional[str] = Field(
        default=None,
        description="Optional snapshot name to prefill in the upload widget.",
    )
    sheet_name: Optional[str] = Field(
        default=None,
        description="Optional worksheet name to prefill for XLSX analysis.",
    )
    column_map: Optional[dict[str, str]] = Field(
        default=None,
        description="Optional semantic key to source column mapping override.",
    )


class ZeroGateContextInput(BaseModel):
    """ZERO gate context input."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    destination: str = Field(..., description="Destination node, for example AGI, DAS, MIR, or SHU.")
    gross_weight_tons: Optional[float] = Field(default=None, description="Gross weight in metric tons.")
    weather_alert: Optional[bool] = Field(default=None, description="Whether a weather alert is active.")
    boe_complete: Optional[bool] = Field(default=None, description="Whether BOE fields are complete.")
    ebl_match: Optional[bool] = Field(default=None, description="Whether the eBL matches the shipment data.")
    fanr_ready: Optional[bool] = Field(default=None, description="Whether FANR readiness is confirmed.")
    ecas_ready: Optional[bool] = Field(default=None, description="Whether ECAS/EQM readiness is confirmed.")
    cicpa_ready: Optional[bool] = Field(default=None, description="Whether CICPA gate pass readiness is confirmed.")
    fra_ready: Optional[bool] = Field(default=None, description="Whether ADNOC FRA readiness is confirmed.")
    dot_ready: Optional[bool] = Field(default=None, description="Whether DOT approval is ready.")
    mosb_utilization_pct: Optional[float] = Field(
        default=None,
        description="MOSB utilization as a percentage of capacity.",
    )


class SnapshotCompareInput(BaseModel):
    """Snapshot compare input."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    baseline_snapshot: str = Field(..., min_length=1, description="Baseline snapshot name.")
    candidate_snapshot: str = Field(..., min_length=1, description="Candidate snapshot name.")


class SelfTestInput(BaseModel):
    """MCP self-test input."""
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")
    target: str = Field(
        default="both",
        description="Target scope: local, public, or both.",
    )
    include_tool_calls: bool = Field(
        default=True,
        description="Whether initialize, tools/list, and sample tool calls are executed.",
    )

    @field_validator("target")
    @classmethod
    def validate_target(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"local", "public", "both"}:
            raise ValueError("target must be one of: local, public, both.")
        return normalized


# ───────────────────────────────────────────────
# MCP Tools
# ───────────────────────────────────────────────

@mcp.resource(
    BACKLOG_UPLOAD_WIDGET_URI,
    name="hvdc-backlog-upload-widget",
    title="HVDC Backlog Upload Widget",
    description="ChatGPT widget for CSV/XLSX upload and backlog batch analysis.",
    mime_type=MCP_APP_RESOURCE_MIME,
    meta=_widget_resource_meta(),
)
def backlog_upload_widget_resource() -> str:
    """Widget template used for ChatGPT file uploads."""
    return _read_widget_template("hvdc_backlog_upload_v1.html")


@mcp.tool(
    name="hvdc_get_domain_summary",
    annotations={
        "title": "HVDC 전체 도메인 요약 (컨텍스트 주입용)",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hvdc_get_domain_summary() -> str:
    """HVDC 프로젝트 전체 도메인 지식을 압축 요약하여 반환합니다.

    새 대화 시작 시 또는 복잡한 작업 전에 호출하여 컨텍스트를 빠르게 주입합니다.
    Python 자동화, 이메일 초안, KPI 분석 등 모든 작업의 시작점으로 활용하세요.

    Returns:
        str: Markdown 형식 — 프로젝트 개요, 노드 8개, Flow Code v3.5, KPI 7개, 규제 5개, 문서 목록
    """
    return render_domain_summary_markdown(load_domain_rules(), docs=doc_markdown_files())


@mcp.tool(
    name="hvdc_search_docs",
    annotations={
        "title": "HVDC 도메인 문서 키워드 검색",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hvdc_search_docs(params: SearchInput) -> str:
    """HVDC 온톨로지 .md 문서 전체에서 키워드를 검색하고 관련 컨텍스트를 반환합니다.

    코드 작성, 문서 작성, 데이터 분석 시 도메인 용어/규칙/제약 조건을 빠르게 찾을 때 사용합니다.

    Args:
        params.keyword (str): 검색 키워드 (예: 'MOSB', 'Flow Code 3', 'DOT permit')
        params.max_results (int): 최대 반환 파일 수 (기본 10, 최대 50)

    Returns:
        str: JSON — {keyword, total_files_matched, total_matches, results: [{file, match_count, matches}]}
             매칭 없으면 {keyword, total_files: 0, message, hint}
    """
    results = _search_in_docs(params.keyword, params.max_results)
    if not results:
        return json.dumps({
            "keyword": params.keyword,
            "total_files": 0,
            "message": f"'{params.keyword}' 관련 내용을 docs/ 폴더에서 찾지 못했습니다.",
            "hint": "hvdc_list_docs로 사용 가능한 문서를 먼저 확인하세요.",
        }, ensure_ascii=False, indent=2)

    total_matches = sum(r["match_count"] for r in results)
    return json.dumps({
        "keyword": params.keyword,
        "total_files_matched": len(results),
        "total_matches": total_matches,
        "results": results,
    }, ensure_ascii=False, indent=2)


@mcp.tool(
    name="hvdc_get_node_info",
    annotations={
        "title": "HVDC 물류 노드 정보 조회",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hvdc_get_node_info(params: NodeQueryInput) -> str:
    """HVDC 프로젝트 8개 물류 노드(Port/Hub/Site)의 상세 정보를 반환합니다.

    노드별 타입, 용량, 운영자, 통관코드, 운송수단, 규제 요건 등을 확인합니다.
    AGI/DAS는 flow_code_rule, MIR/SHU는 dot_rule이 자동 추가됩니다.

    Args:
        params.node_name (Optional[str]): 노드명 (예: 'MOSB', 'DAS'). 미입력 시 전체 반환.

    Returns:
        str: JSON — {node_name: {type, locode, ...}} 또는 에러
    """
    if params.node_name:
        key = params.node_name.strip().upper().replace(" ", "")
        matched = {k: v for k, v in NODES.items() if k.upper() == key or key in k.upper()}
        if not matched:
            return _make_error(
                f"'{params.node_name}' 노드 없음",
                hint="대소문자 무관, 부분 매칭 지원",
                available=list(NODES.keys()),
            )
        data = matched
    else:
        data = NODES

    enriched = {}
    for name, info in data.items():
        node = dict(info)
        if info.get("mosb_mandatory"):
            node["flow_code_rule"] = "AGI/DAS -> Flow Code >= 3 필수 (MOSB 레그 mandatory)"
        if info.get("dot_required"):
            node["dot_rule"] = "화물 >90톤 시 DOT 허가 필수"
        enriched[name] = node

    return json.dumps(enriched, ensure_ascii=False, indent=2)


@mcp.tool(
    name="hvdc_get_flow_code",
    annotations={
        "title": "HVDC Flow Code v3.5 조회 및 검증",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hvdc_get_flow_code(params: FlowCodeInput) -> str:
    """HVDC Flow Code v3.5 시스템을 조회하고, 목적지별 적합한 Flow Code를 안내합니다.

    AGI/DAS 목적지는 자동으로 Flow Code >= 3 규칙을 적용합니다.
    Python 코드 작성 시 flow code 로직 참조용으로 활용하세요.

    Args:
        params.code (Optional[int]): 0~5 Flow Code 번호
        params.destination (Optional[str]): 목적지명 (AGI/DAS -> 자동 검증)

    Returns:
        str: JSON — {flow_codes_v35, algorithm, wh_handling_mapping, [queried_code], [destination_validation]}
    """
    result = {
        "flow_codes_v35": FLOW_CODES,
        "algorithm": {
            "formula": "FLOW_CODE = 0 if Pre_Arrival else clip(wh_count + offshore + 1, 1, 4)",
            "variables": {
                "wh_count": "MOSB 제외 창고 컬럼 중 날짜가 있는 개수",
                "offshore": "MOSB 컬럼에 날짜 있으면 1, 없으면 0",
                "base_step": "1 (Port->Site 기본)",
            },
            "domain_rules": {
                "AGI_DAS": "Final_Location이 AGI 또는 DAS -> Flow Code 0/1/2는 3으로 강제 승급",
                "Flow5_conditions": [
                    "MOSB 있으나 Site 없음",
                    "WH 2개 이상 + MOSB 없음",
                ],
            },
        },
        "wh_handling_mapping": {
            "0": "WH 경유 0회 (Flow 0, 1)",
            "1": "WH 경유 1회 (Flow 2, 3)",
            "2": "WH 경유 2회 (Flow 4)",
            "3": "WH 경유 3회 (Flow 4 max)",
        },
    }

    if params.code is not None:
        result["queried_code"] = {
            "code": params.code,
            "description": FLOW_CODES.get(params.code, "Unknown"),
        }

    if params.destination:
        dest = params.destination.upper()
        if dest in ("AGI", "DAS"):
            result["destination_validation"] = {
                "destination": dest,
                "minimum_flow_code": 3,
                "rule": "AGI/DAS는 MOSB 레그 필수 -> Flow Code < 3 사용 불가",
                "recommended": "Flow 3 (Port -> MOSB -> Site) 또는 Flow 4 (Port -> WH -> MOSB -> Site)",
            }
        else:
            result["destination_validation"] = {
                "destination": dest,
                "minimum_flow_code": 1,
                "rule": "육상 현장은 Flow 1~4 모두 가능",
            }

    return json.dumps(result, ensure_ascii=False, indent=2)


@mcp.tool(
    name="hvdc_read_doc",
    annotations={
        "title": "HVDC 온톨로지 문서 읽기",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hvdc_read_doc(params: DocQueryInput) -> str:
    """HVDC 온톨로지 .md 문서를 읽어 전체 또는 특정 섹션을 반환합니다.

    SHACL 규칙, JSON-LD 예시, Roadmap 등 특정 섹션만 추출도 가능합니다.

    Args:
        params.filename (str): 파일명 (예: 'CONSOLIDATED-01-core-framework-infra.md')
        params.section (Optional[str]): 추출할 섹션 헤더 키워드

    Returns:
        str: 문서 전체 텍스트 또는 해당 섹션. 섹션 없으면 사용 가능한 헤더 목록 반환.
    """
    content = _load_doc(params.filename)
    if content.startswith("["):
        return content  # 에러 메시지 그대로 반환

    if params.section:
        lines = content.split("\n")
        section_kw = params.section.lower()
        capturing = False
        section_lines = []
        header_level = 0

        for line in lines:
            if line.startswith("#"):
                level = len(line) - len(line.lstrip("#"))
                if section_kw in line.lower():
                    capturing = True
                    header_level = level
                    section_lines = [line]
                elif capturing and level <= header_level:
                    break
            elif capturing:
                section_lines.append(line)

        if section_lines:
            return "\n".join(section_lines)

        # 섹션 못 찾으면 사용 가능한 헤더 목록 반환
        headers = [line for line in lines if line.startswith("#")][:30]
        return json.dumps({
            "error": f"섹션 '{params.section}'을 '{params.filename}'에서 찾지 못했습니다.",
            "available_headers": headers,
            "hint": "위 헤더 중 하나를 section 파라미터에 입력하세요.",
        }, ensure_ascii=False, indent=2)

    return content


@mcp.tool(
    name="search",
    title="Search HVDC Knowledge",
    description=(
        "Use this when you need to search the indexed HVDC logistics knowledge base "
        "for documents related to a site, rule, regulation, KPI, or process."
    ),
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def search(params: CompanyKnowledgeSearchInput) -> CallToolResult:
    """ChatGPT company knowledge / deep research 호환 search tool."""
    results = []
    for entry in _build_doc_catalog(include_large=False).values():
        content = _read_file_safe(entry["path"])
        if content.startswith("["):
            continue

        score, match_count = _match_score(params.query, entry, content)
        if score <= 0:
            continue

        results.append(
            {
                "id": entry["id"],
                "title": entry["title"],
                "url": entry["url"],
                "_score": score,
                "_match_count": match_count,
            }
        )

    results.sort(key=lambda item: (-item["_score"], -item["_match_count"], item["title"]))
    payload = {
        "results": [
            {
                "id": item["id"],
                "title": item["title"],
                "url": item["url"],
            }
            for item in results[:8]
        ]
    }
    return _make_text_tool_result(payload)


@mcp.tool(
    name="fetch",
    title="Fetch HVDC Document",
    description=(
        "Use this when you need the full text of a document returned by the "
        "search tool for citation, summarization, or deep analysis."
    ),
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def fetch(params: CompanyKnowledgeFetchInput) -> CallToolResult:
    """ChatGPT company knowledge / deep research 호환 fetch tool."""
    entry = _resolve_doc_entry(params.id, include_large=False)
    if entry is None:
        raise ValueError(
            f"Unknown document id '{params.id}'. Call search first and pass one of its result ids."
        )

    content = _read_file_safe(entry["path"])
    if content.startswith("["):
        raise ValueError(content)

    payload = {
        "id": entry["id"],
        "title": entry["title"],
        "text": content,
        "url": entry["url"],
        "metadata": {
            "filename": entry["filename"],
            "relative_path": entry["relative_path"],
            "size_kb": round(entry["path"].stat().st_size / 1024, 1),
            "line_count": _count_lines(entry["path"]),
        },
    }
    return _make_text_tool_result(payload)


@mcp.tool(
    name="hvdc_list_docs",
    annotations={
        "title": "HVDC 도메인 문서 목록 조회",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hvdc_list_docs() -> str:
    """docs/ 폴더에 있는 HVDC 온톨로지 문서 목록을 반환합니다.

    어떤 도메인 문서가 사용 가능한지 먼저 확인할 때 사용합니다.

    Returns:
        str: JSON — {docs_directory, total_files, files: [{filename, size_kb, lines}]}
    """
    if not DOCS_DIR.exists():
        return _make_error(
            "docs/ 폴더가 없습니다.",
            hint=f"docs/ 폴더를 생성하고 .md 파일을 넣으세요: {DOCS_DIR}",
        )

    files = []
    for md_file in sorted(DOCS_DIR.rglob("*.md")):
        safe = _safe_resolve(md_file)
        if safe is None:
            continue
        entry = _build_doc_entry(md_file)
        files.append({
            "doc_id": entry["id"] if entry else "",
            "filename": md_file.name,
            "url": entry["url"] if entry else "",
            "size_kb": round(md_file.stat().st_size / 1024, 1),
            "lines": _count_lines(md_file),
        })

    return json.dumps({
        "docs_directory": str(DOCS_DIR),
        "total_files": len(files),
        "files": files,
    }, ensure_ascii=False, indent=2)


@mcp.tool(
    name="hvdc_get_kpi",
    annotations={
        "title": "HVDC KPI 게이트 기준값 조회",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hvdc_get_kpi(params: KPIInput) -> str:
    """HVDC 프로젝트 KPI 게이트 기준값을 반환합니다.

    인보이스 OCR 정확도, 창고 가동률, 날씨 연계 ETA 오차 등 운영 임계값을 확인합니다.
    Python 자동화 스크립트에서 KPI 임계값 상수로 활용하세요.

    Args:
        params.kpi_name (Optional[str]): KPI명 (예: 'invoice_ocr', 'wh_forecast_util')

    Returns:
        str: JSON — {kpi_name: {threshold, unit, direction, description}} 또는 전체 KPI
    """
    if params.kpi_name:
        kpi = KPI_GATES.get(params.kpi_name)
        if not kpi:
            return _make_error(
                f"KPI '{params.kpi_name}' 없음",
                available=list(KPI_GATES.keys()),
            )
        return json.dumps({params.kpi_name: kpi}, ensure_ascii=False, indent=2)

    return json.dumps({
        "kpi_gates": KPI_GATES,
        "usage_note": "threshold + direction으로 PASS/FAIL 판정. 예: invoice_ocr >= 98%",
    }, ensure_ascii=False, indent=2)


@mcp.tool(
    name="hvdc_get_regulations",
    annotations={
        "title": "HVDC UAE 규정/인증 요건 조회",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hvdc_get_regulations(params: RegulationInput) -> str:
    """UAE HVDC 프로젝트에 적용되는 주요 규제/인증/허가 요건을 반환합니다.

    FANR, MOIAT, DOT, CICPA 등 통관/현장 작업에 필요한 규정을 확인합니다.
    이메일/보고서 작성 시 규정 근거로 활용하세요.

    Args:
        params.regulation_name (Optional[str]): 규제명 (예: 'FANR', 'DOT'). 미입력 시 전체.

    Returns:
        str: JSON — {regulations: {...}, key_principle} 또는 특정 규제 상세
    """
    if params.regulation_name:
        key = params.regulation_name.upper().replace(" ", "_")
        reg = REGULATIONS.get(key)
        if not reg:
            return _make_error(
                f"규제 '{params.regulation_name}' 없음",
                available=list(REGULATIONS.keys()),
            )
        return json.dumps({key: reg}, ensure_ascii=False, indent=2)

    return json.dumps({
        "regulations": REGULATIONS,
        "key_principle": "규제 위반 시 ZERO 모드 발동 — 작업 즉시 중단 후 요건 충족 시 재개",
    }, ensure_ascii=False, indent=2)


@mcp.tool(
    name="hvdc_hs_code_lookup",
    annotations={
        "title": "HVDC HS Code 조회",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
)
async def hvdc_hs_code_lookup(params: HSCodeInput) -> str:
    """HVDC 프로젝트 주요 품목의 HS Code를 조회합니다.

    인보이스 작성, BOE(통관신고서) 검증, HS Risk 분석에 활용합니다.
    현재 5개 핵심 품목 내장. 미매칭 시 전체 목록 + WCO 확인 안내 반환.

    Args:
        params.query (str): HS Code 번호 또는 품목명 (예: '850440', '변압기', 'cable')

    Returns:
        str: JSON — {query, matched: {code: desc}} 또는 {query, result: '직접 매칭 없음', all_hvdc_hs_codes}
    """
    query = params.query.lower()
    matched = {}

    for code, desc in HS_CODE_EXAMPLES.items():
        if query in code or query in desc.lower():
            matched[code] = desc

    if not matched:
        return json.dumps({
            "query": params.query,
            "result": "직접 매칭 없음",
            "all_hvdc_hs_codes": HS_CODE_EXAMPLES,
            "hint": "WCO HS 2022 기준. 정확한 분류는 관세사 확인 필요.",
        }, ensure_ascii=False, indent=2)

    return json.dumps({
        "query": params.query,
        "matched": matched,
        "risk_note": "HS Risk Score = f(HS, Origin, DG, Cert요구, 과거검사빈도). 목표: misclass <= 0.5%",
    }, ensure_ascii=False, indent=2)


@mcp.tool(
    name="hvdc_analyze_shipment_case",
    title="Analyze HVDC Shipment Case",
    description="Analyze one shipment case against Flow Code, ZERO gates, and KPI evidence.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    meta={"openai/fileParams": ["file"]},
    structured_output=True,
)
async def hvdc_analyze_shipment_case(params: ShipmentCaseInput) -> CallToolResult:
    """Analyze a single shipment from inline data or a CSV/XLSX source."""
    if params.shipment is not None:
        if params.file is not None or params.local_path:
            raise ValueError("Use shipment or file/local_path, not both.")
        record = normalize_inline_shipment(params.shipment, column_map=params.column_map)
        source = {"source_kind": "inline", "display_name": "inline_shipment"}
    else:
        records, metadata = load_normalized_records(
            file_param=params.file.model_dump(exclude_none=True) if params.file is not None else None,
            local_path=params.local_path,
            sheet_name=params.sheet_name,
            column_map=params.column_map,
            allow_local_paths=_allow_local_analysis_paths(),
        )
        record = select_record(records, row_number=params.row_number, shipment_id=params.shipment_id)
        source = metadata.__dict__

    missing = [field for field in ("destination", "status") if not record.get(field)]
    if missing:
        raise ValueError(f"Shipment case is missing required semantic fields: {', '.join(missing)}")

    payload = assess_shipment_case(record)
    payload["input_source"] = source
    payload["markdown_summary"] = render_shipment_case_markdown(payload)
    payload["excel_export"] = ExcelExportPayload.model_validate(
        _shipment_case_excel_export(payload)
    ).model_dump(mode="json")
    return _make_structured_tool_result(ShipmentCaseResult.model_validate(payload))


@mcp.tool(
    name="hvdc_render_backlog_upload_widget",
    title="Open HVDC Backlog Upload Widget",
    description="Render a ChatGPT upload widget that uploads a CSV/XLSX file and runs backlog analysis.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    meta={
        "ui": {
            "resourceUri": BACKLOG_UPLOAD_WIDGET_URI,
            "visibility": ["model", "app"],
        },
        "openai/outputTemplate": BACKLOG_UPLOAD_WIDGET_URI,
        "openai/toolInvocation/invoking": "Preparing upload widget...",
        "openai/toolInvocation/invoked": "Upload widget ready",
    },
    structured_output=True,
)
async def hvdc_render_backlog_upload_widget(params: BacklogUploadWidgetInput) -> CallToolResult:
    """Render the ChatGPT widget used for file upload and backlog analysis."""
    # The widget only prepares the temporary upload/download handoff for ChatGPT.
    payload = {
        "title": "HVDC backlog upload widget ready",
        "instructions": [
            "Upload one CSV or XLSX shipment file from ChatGPT.",
            "The widget will obtain a temporary HTTP download URL and call hvdc_analyze_backlog_batch.",
            "Use column_map only when source column names differ from the standard semantic aliases.",
        ],
        "accepted_extensions": [".csv", ".xlsx"],
        "defaults": {
            "snapshot_name": params.snapshot_name or _analysis_snapshot_name(),
            "sheet_name": params.sheet_name,
            "column_map": params.column_map or {},
        },
        "tool_name": "hvdc_analyze_backlog_batch",
        "widget_uri": BACKLOG_UPLOAD_WIDGET_URI,
    }
    return _make_structured_tool_result(BacklogUploadWidgetResult.model_validate(payload))


@mcp.tool(
    name="hvdc_analyze_backlog_batch",
    title="Analyze HVDC Backlog Batch",
    description="Analyze a shipment batch from CSV/XLSX and persist a named backlog snapshot.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    meta={
        "ui": {
            "visibility": ["model", "app"],
        },
        "openai/fileParams": ["file"],
        "openai/widgetAccessible": True,
    },
    structured_output=True,
)
async def hvdc_analyze_backlog_batch(params: BacklogBatchInput) -> CallToolResult:
    """Analyze a backlog batch from CSV/XLSX and persist a named snapshot."""
    # This tool is the authority for the structured result payload and snapshot persistence.
    records, metadata = load_normalized_records(
        file_param=params.file.model_dump(exclude_none=True) if params.file is not None else None,
        local_path=params.local_path,
        sheet_name=params.sheet_name,
        column_map=params.column_map,
        allow_local_paths=_allow_local_analysis_paths(),
    )
    if not records:
        raise ValueError("The provided table has no shipment rows.")

    missing_rows = [
        record["source_row_number"]
        for record in records
        if not record.get("destination") or not record.get("status")
    ]
    if missing_rows:
        raise ValueError(
            "Backlog batch rows are missing required semantic fields destination/status "
            f"at rows: {', '.join(str(row) for row in missing_rows[:10])}"
        )

    snapshot_name = params.snapshot_name or _analysis_snapshot_name()
    analysis = analyze_backlog(records)
    payload = {
        "snapshot_name": snapshot_name,
        "source": metadata.__dict__,
        **analysis,
    }
    save_snapshot(
        snapshot_name,
        normalized_rows=records,
        aggregate_summary=payload,
        source=metadata.__dict__,
    )
    payload["markdown_report"] = render_backlog_batch_markdown(payload)
    payload["excel_export"] = ExcelExportPayload.model_validate(
        _backlog_batch_excel_export(payload)
    ).model_dump(mode="json")
    return _make_structured_tool_result(
        BacklogBatchResult.model_validate(payload),
        summary_key="markdown_report",
    )


@mcp.tool(
    name="hvdc_zero_gate_check",
    title="Check HVDC ZERO Gates",
    description="Evaluate one operation context against ZERO gate blockers and warnings.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    structured_output=True,
)
async def hvdc_zero_gate_check(params: ZeroGateContextInput) -> CallToolResult:
    """Evaluate structured ZERO-gate context."""
    record = {
        "destination": params.destination.strip().upper(),
        "weight_tons": params.gross_weight_tons,
        "weather_alert": params.weather_alert,
        "boe_complete": params.boe_complete,
        "ebl_match": params.ebl_match,
        "fanr_ready": params.fanr_ready,
        "ecas_ready": params.ecas_ready,
        "cicpa_ready": params.cicpa_ready,
        "fra_ready": params.fra_ready,
        "dot_ready": params.dot_ready,
        "mosb_utilization_pct": params.mosb_utilization_pct,
    }
    zero_gates = evaluate_zero_gate_context(record)
    summary = zero_gates["summary"]
    if summary["blocked"]:
        verdict_status = "ZERO"
    elif summary["warnings"] or summary["not_evaluated"]:
        verdict_status = "WARNING"
    else:
        verdict_status = "PASS"
    payload = {
        "gate_results": zero_gates["gate_results"],
        "blocking_actions": zero_gates["blocking_actions"],
        "warning_actions": zero_gates["warning_actions"],
        "verdict": {
            "status": verdict_status,
            "blocked_gates": summary["blocked"],
            "warnings": summary["warnings"],
            "evidence_gaps": summary["not_evaluated"],
        },
    }
    payload["markdown_summary"] = render_zero_gate_markdown(payload)
    return _make_structured_tool_result(ZeroGateCheckResult.model_validate(payload))


@mcp.tool(
    name="hvdc_compare_snapshots",
    title="Compare HVDC Backlog Snapshots",
    description="Compare two persisted backlog snapshots and summarize deltas.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    structured_output=True,
)
async def hvdc_compare_snapshots(params: SnapshotCompareInput) -> CallToolResult:
    """Compare two saved backlog snapshots."""
    baseline = load_snapshot(params.baseline_snapshot)
    candidate = load_snapshot(params.candidate_snapshot)
    payload = compare_snapshot_summaries(
        params.baseline_snapshot,
        baseline["summary"],
        params.candidate_snapshot,
        candidate["summary"],
    )
    payload["markdown_report"] = render_compare_snapshots_markdown(payload)
    payload["excel_export"] = ExcelExportPayload.model_validate(
        _snapshot_compare_excel_export(payload)
    ).model_dump(mode="json")
    return _make_structured_tool_result(
        SnapshotCompareResult.model_validate(payload),
        summary_key="markdown_report",
    )


@mcp.tool(
    name="hvdc_mcp_self_test",
    title="Run HVDC MCP Self Test",
    description="Probe local/public MCP health, tool calls, and connector freshness.",
    annotations={
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False,
    },
    structured_output=True,
)
async def hvdc_mcp_self_test(params: SelfTestInput) -> CallToolResult:
    """Run MCP connectivity and connector freshness checks."""
    payload = await _run_self_test(params.target, params.include_tool_calls)
    payload["markdown_summary"] = render_self_test_markdown(payload)
    return _make_structured_tool_result(SelfTestResult.model_validate(payload))


# ───────────────────────────────────────────────
# Custom HTTP Routes (ChatGPT / browser friendly)
# ───────────────────────────────────────────────

@mcp.custom_route("/", methods=["GET"], include_in_schema=False)
async def root_status(request: Request) -> JSONResponse:
    with _correlation_scope(_request_correlation_id(request)) as correlation_id:
        payload = _build_root_status_payload()
        payload["correlation_id"] = correlation_id
        _log_event(
            logging.INFO,
            "root status requested",
            event="root_status",
            component="http",
            path="/",
            method="GET",
            status_code=200,
            correlation_id=correlation_id,
        )
        return JSONResponse(payload)


@mcp.custom_route("/health", methods=["GET"], include_in_schema=False)
async def healthcheck(request: Request) -> JSONResponse:
    with _correlation_scope(_request_correlation_id(request)) as correlation_id:
        payload = await _build_health_payload(request)
        status_code = 200
        _log_event(
            logging.INFO,
            "health requested",
            event="healthcheck",
            component="http",
            path="/health",
            method="GET",
            status_code=status_code,
            correlation_id=correlation_id,
        )
        return JSONResponse(payload, status_code=status_code)


@mcp.custom_route("/favicon.ico", methods=["GET"], include_in_schema=False)
async def favicon(_: Request) -> PlainTextResponse:
    return PlainTextResponse("", status_code=204)


@mcp.custom_route(DOCS_ROUTE_PREFIX, methods=["GET"], include_in_schema=False)
async def list_docs_http(_: Request) -> JSONResponse:
    catalog = _build_doc_catalog(include_large=True)
    return JSONResponse(
        {
            "total_files": len(catalog),
            "files": [
                {
                    "id": entry["id"],
                    "title": entry["title"],
                    "filename": entry["filename"],
                    "url": entry["url"],
                }
                for entry in catalog.values()
            ],
        }
    )


@mcp.custom_route(f"{DOCS_ROUTE_PREFIX}/{{doc_id:path}}", methods=["GET"], include_in_schema=False)
async def read_doc_http(request: Request) -> PlainTextResponse:
    doc_id = request.path_params["doc_id"]
    entry = _resolve_doc_entry(doc_id, include_large=True)
    if entry is None:
        return PlainTextResponse("Document not found", status_code=404)

    return PlainTextResponse(
        _read_file_safe(entry["path"]),
        media_type="text/markdown",
    )


@mcp.custom_route("/dashboard/status", methods=["GET"], include_in_schema=False)
async def dashboard_status(request: Request) -> JSONResponse:
    with _correlation_scope(_request_correlation_id(request)) as correlation_id:
        payload = await _build_dashboard_payload()
        payload["correlation_id"] = correlation_id
        _log_event(
            logging.INFO,
            "dashboard status requested",
            event="dashboard_status",
            component="http",
            path="/dashboard/status",
            method="GET",
            status_code=200,
            correlation_id=correlation_id,
        )
        return JSONResponse(payload)


@mcp.custom_route(DASHBOARD_SELF_TEST_PATH, methods=["GET"], include_in_schema=False)
async def dashboard_self_test(request: Request) -> JSONResponse:
    with _correlation_scope(_request_correlation_id(request)) as correlation_id:
        target = str(request.query_params.get("target", "both")).strip().lower()
        if target not in {"local", "public", "both"}:
            target = "both"
        include_tool_calls = str(request.query_params.get("include_tool_calls", "true")).strip().lower() not in {
            "0",
            "false",
            "no",
            "off",
        }
        payload = await _run_self_test(target, include_tool_calls)
        payload["markdown_summary"] = render_self_test_markdown(payload)
        payload["correlation_id"] = correlation_id
        _log_event(
            logging.INFO,
            "dashboard self test requested",
            event="dashboard_self_test",
            component="http",
            path=DASHBOARD_SELF_TEST_PATH,
            method="GET",
            status_code=200,
            target=target,
            correlation_id=correlation_id,
        )
        return JSONResponse(payload)


@mcp.custom_route("/dashboard", methods=["GET"], include_in_schema=False)
async def dashboard(_: Request) -> HTMLResponse:
    return HTMLResponse(
        """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>HVDC MCP Dashboard</title>
  <style>
    :root {
      color-scheme: light;
      --bg: #f4f1e8;
      --panel: rgba(255, 255, 255, 0.82);
      --panel-strong: rgba(255, 255, 255, 0.96);
      --text: #182229;
      --muted: #58656e;
      --line: rgba(24, 34, 41, 0.12);
      --ok: #0f766e;
      --warn: #b45309;
      --bad: #b91c1c;
      --accent: #154a7d;
      --shadow: 0 22px 44px rgba(20, 37, 55, 0.12);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: "Segoe UI", "Helvetica Neue", sans-serif;
      color: var(--text);
      background:
        radial-gradient(circle at top left, rgba(21, 74, 125, 0.18), transparent 28%),
        radial-gradient(circle at top right, rgba(15, 118, 110, 0.16), transparent 26%),
        linear-gradient(180deg, #f8f4ea 0%, var(--bg) 100%);
    }

    .shell {
      width: min(1200px, calc(100vw - 32px));
      margin: 24px auto 56px;
    }

    .hero {
      padding: 28px;
      border: 1px solid var(--line);
      border-radius: 24px;
      background: linear-gradient(135deg, rgba(255,255,255,0.95), rgba(255,255,255,0.72));
      box-shadow: var(--shadow);
      backdrop-filter: blur(16px);
    }

    .hero h1 {
      margin: 0 0 8px;
      font-size: clamp(30px, 4vw, 44px);
      letter-spacing: -0.04em;
    }

    .hero p {
      margin: 0;
      color: var(--muted);
      font-size: 15px;
    }

    .hero-top {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      flex-wrap: wrap;
    }

    .toolbar {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }

    .toolbar label {
      font-size: 12px;
      color: var(--muted);
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .toolbar select,
    .toolbar button,
    .toolbar input {
      border: 1px solid var(--line);
      border-radius: 999px;
      background: rgba(255,255,255,0.86);
      color: var(--text);
      padding: 10px 14px;
      font: inherit;
    }

    .toolbar button {
      background: var(--accent);
      color: #fff;
      cursor: pointer;
    }

    .meta {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      margin-top: 18px;
    }

    .pill {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      background: rgba(21, 74, 125, 0.08);
      border: 1px solid rgba(21, 74, 125, 0.12);
      font-size: 13px;
    }

    .status-band {
      display: grid;
      grid-template-columns: minmax(180px, 220px) 1fr;
      gap: 18px;
      margin-top: 20px;
      padding: 18px;
      border-radius: 20px;
      border: 1px solid var(--line);
      background: rgba(255, 255, 255, 0.72);
    }

    .score {
      padding: 18px;
      border-radius: 20px;
      color: #fff;
      display: grid;
      place-items: center;
      min-height: 150px;
      text-align: center;
    }

    .score strong {
      display: block;
      font-size: clamp(40px, 6vw, 62px);
      line-height: 1;
      letter-spacing: -0.06em;
    }

    .score span {
      display: block;
      margin-top: 8px;
      font-size: 13px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      opacity: 0.84;
    }

    .score.healthy { background: linear-gradient(135deg, #0f766e, #14b8a6); }
    .score.degraded { background: linear-gradient(135deg, #b45309, #f59e0b); }
    .score.down { background: linear-gradient(135deg, #991b1b, #ef4444); }

    .status-copy {
      display: flex;
      flex-direction: column;
      justify-content: center;
      gap: 10px;
    }

    .status-copy h2 {
      margin: 0;
      font-size: clamp(24px, 3vw, 36px);
      letter-spacing: -0.05em;
    }

    .status-copy p {
      margin: 0;
      color: var(--muted);
      font-size: 15px;
    }

    .state-pill {
      display: inline-flex;
      align-items: center;
      width: fit-content;
      padding: 8px 12px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .state-pill.healthy { background: rgba(15, 118, 110, 0.12); color: var(--ok); }
    .state-pill.degraded { background: rgba(180, 83, 9, 0.12); color: var(--warn); }
    .state-pill.down { background: rgba(185, 28, 28, 0.12); color: var(--bad); }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      margin-top: 18px;
    }

    .card {
      border: 1px solid var(--line);
      border-radius: 22px;
      background: var(--panel);
      box-shadow: var(--shadow);
      padding: 20px;
      backdrop-filter: blur(10px);
    }

    .card h2 {
      margin: 0 0 14px;
      font-size: 15px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
      color: var(--muted);
    }

    .stats {
      display: grid;
      gap: 10px;
    }

    .stat {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 10px 0;
      border-bottom: 1px solid var(--line);
      font-size: 14px;
    }

    .stat:last-child { border-bottom: 0; }
    .stat.compact { padding: 8px 0; }
    .label { color: var(--muted); }
    .value {
      text-align: right;
      word-break: break-word;
      font-weight: 600;
    }

    .process-list {
      display: grid;
      gap: 12px;
    }

    .process {
      border: 1px solid var(--line);
      border-radius: 16px;
      padding: 14px;
      background: var(--panel-strong);
    }

    .process-meta {
      color: var(--muted);
      font-size: 13px;
    }

    .process-head {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 6px;
    }

    .process-name {
      font-weight: 700;
      text-transform: capitalize;
    }

    .badge {
      display: inline-flex;
      align-items: center;
      padding: 5px 10px;
      border-radius: 999px;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }

    .badge.ok { color: var(--ok); background: rgba(15, 118, 110, 0.12); }
    .badge.bad { color: var(--bad); background: rgba(185, 28, 28, 0.12); }
    .badge.warn { color: var(--warn); background: rgba(180, 83, 9, 0.12); }
    .badge.info { color: var(--accent); background: rgba(21, 74, 125, 0.12); }

    .links {
      display: grid;
      gap: 10px;
    }

    a {
      color: var(--accent);
      text-decoration: none;
    }

    a:hover { text-decoration: underline; }

    .list {
      display: grid;
      gap: 12px;
    }

    .list-item {
      border: 1px solid var(--line);
      border-radius: 18px;
      padding: 14px 16px;
      background: var(--panel-strong);
    }

    .list-item header {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: flex-start;
      margin-bottom: 8px;
    }

    .list-item h3 {
      margin: 0;
      font-size: 15px;
    }

    .list-item p {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }

    .empty {
      color: var(--muted);
      font-size: 14px;
      padding: 8px 0;
    }

    code {
      font-family: Consolas, "Courier New", monospace;
      background: rgba(21, 74, 125, 0.08);
      border-radius: 8px;
      padding: 2px 6px;
      word-break: break-word;
    }

    .section-head {
      display: flex;
      justify-content: space-between;
      align-items: center;
      gap: 12px;
      margin-bottom: 14px;
      flex-wrap: wrap;
    }

    .section-copy {
      margin: 0;
      color: var(--muted);
      font-size: 13px;
      line-height: 1.5;
    }

    .surface-primary {
      margin: 0 0 8px;
      color: var(--text);
      font-size: 13px;
      line-height: 1.5;
    }

    .toggle {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      color: var(--muted);
      font-size: 13px;
    }

    .trend {
      display: grid;
      gap: 14px;
    }

    .trend-summary {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
    }

    .mini-stat {
      padding: 10px 12px;
      border-radius: 16px;
      background: rgba(21, 74, 125, 0.08);
      border: 1px solid rgba(21, 74, 125, 0.08);
      min-width: 108px;
    }

    .mini-stat strong {
      display: block;
      font-size: 20px;
      letter-spacing: -0.05em;
    }

    .mini-stat span {
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: 0.08em;
    }

    .trend-bars {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(8px, 1fr));
      gap: 5px;
      align-items: end;
      min-height: 180px;
      padding-top: 12px;
    }

    .trend-bar {
      border-radius: 999px 999px 4px 4px;
      min-height: 10px;
      opacity: 0.95;
    }

    .trend-bar.healthy { background: linear-gradient(180deg, #34d399, #0f766e); }
    .trend-bar.degraded { background: linear-gradient(180deg, #fbbf24, #b45309); }
    .trend-bar.down { background: linear-gradient(180deg, #f87171, #b91c1c); }

    .log-shell {
      margin-top: 18px;
    }

    .log-toolbar {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 14px;
    }

    .log-tabs {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
    }

    .log-tab {
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.88);
      color: var(--text);
      border-radius: 999px;
      padding: 8px 12px;
      cursor: pointer;
      font: inherit;
    }

    .log-tab.active {
      background: var(--accent);
      color: #fff;
      border-color: transparent;
    }

    .log-view {
      border: 1px solid var(--line);
      border-radius: 20px;
      overflow: hidden;
      background: rgba(16, 24, 32, 0.96);
      color: #d4dde4;
      box-shadow: var(--shadow);
    }

    .log-head {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 12px 14px;
      background: rgba(255, 255, 255, 0.08);
      border-bottom: 1px solid rgba(255,255,255,0.08);
      font-size: 13px;
    }

    .log-view pre {
      margin: 0;
      padding: 14px;
      min-height: 300px;
      max-height: 420px;
      overflow: auto;
      font: 12px/1.5 Consolas, "Courier New", monospace;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .log-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
      gap: 16px;
      margin-top: 18px;
    }

    .log-box {
      border: 1px solid var(--line);
      border-radius: 18px;
      overflow: hidden;
      background: rgba(16, 24, 32, 0.96);
      color: #d4dde4;
      box-shadow: var(--shadow);
    }

    .log-box header {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      padding: 12px 14px;
      background: rgba(255, 255, 255, 0.08);
      border-bottom: 1px solid rgba(255,255,255,0.08);
      font-size: 13px;
    }

    .log-box pre {
      margin: 0;
      padding: 14px;
      min-height: 260px;
      max-height: 360px;
      overflow: auto;
      font: 12px/1.5 Consolas, "Courier New", monospace;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .footer {
      margin-top: 16px;
      color: var(--muted);
      font-size: 13px;
      text-align: right;
    }

    @media (max-width: 720px) {
      .shell { width: min(100vw - 20px, 100%); margin: 12px auto 40px; }
      .hero, .card { border-radius: 18px; }
      .status-band { grid-template-columns: 1fr; }
      .log-box pre { min-height: 220px; }
      .log-view pre { min-height: 220px; }
    }
  </style>
</head>
<body>
  <main class="shell">
    <section class="hero">
      <div class="hero-top">
        <div>
          <h1>HVDC MCP Dashboard</h1>
          <p>Operational view for the streamable HTTP server, public connector health, restart history, and log activity.</p>
        </div>
        <div class="toolbar">
          <label for="refreshInterval">Refresh</label>
          <select id="refreshInterval">
            <option value="5000">5 sec</option>
            <option value="15000">15 sec</option>
            <option value="30000">30 sec</option>
            <option value="0">Off</option>
          </select>
          <button id="refreshNow" type="button">Refresh Now</button>
        </div>
      </div>
      <div class="meta" id="meta"></div>
      <div class="status-band" id="statusBand"></div>
    </section>

    <section class="grid">
      <article class="card">
        <h2>Runtime</h2>
        <div class="stats" id="runtime"></div>
      </article>
      <article class="card">
        <h2>Deployment</h2>
        <div class="stats" id="deployment"></div>
      </article>
      <article class="card">
        <h2>Server</h2>
        <div class="stats" id="server"></div>
      </article>
      <article class="card">
        <h2>Connectivity</h2>
        <div class="stats" id="connectivity"></div>
      </article>
      <article class="card">
        <h2>ChatGPT Upload</h2>
        <div class="stats" id="chatgptUpload"></div>
      </article>
      <article class="card">
        <h2>Excel Integration</h2>
        <div class="stats" id="excelIntegration"></div>
      </article>
      <article class="card">
        <h2>Client Surfaces</h2>
        <div class="list" id="surfaces"></div>
      </article>
      <article class="card">
        <h2>Processes</h2>
        <div class="process-list" id="processes"></div>
      </article>
      <article class="card">
        <h2>Alerts</h2>
        <div class="list" id="alerts"></div>
      </article>
      <article class="card">
        <h2>Recent Restarts</h2>
        <div class="list" id="restarts"></div>
      </article>
      <article class="card">
        <h2>Health Trend</h2>
        <div class="trend" id="trend"></div>
      </article>
      <article class="card">
        <h2>Links</h2>
        <div class="links" id="links"></div>
      </article>
    </section>

    <section class="card">
      <div class="section-head">
        <div>
          <h2>Self Test</h2>
          <p class="section-copy">Run the same MCP checks used during connector diagnostics without leaving the dashboard.</p>
        </div>
        <div class="toolbar">
          <label for="selfTestTarget">Target</label>
          <select id="selfTestTarget">
            <option value="both">both</option>
            <option value="public">public</option>
            <option value="local">local</option>
          </select>
          <label class="toggle" for="selfTestDeep">
            <input id="selfTestDeep" type="checkbox" checked>
            Deep checks
          </label>
          <button id="runSelfTest" type="button">Run Self Test</button>
        </div>
      </div>
      <div class="stats" id="selfTestMeta"></div>
      <div class="list" id="selfTestChecks"></div>
      <div class="list" id="selfTestRecommendations"></div>
    </section>

    <section class="card log-shell">
      <h2>Logs</h2>
      <div class="log-toolbar">
        <div class="log-tabs" id="logTabs"></div>
        <div class="toolbar">
          <input id="logFilter" type="search" placeholder="Filter log lines">
        </div>
      </div>
      <div class="log-view">
        <div class="log-head" id="logMeta"></div>
        <pre id="logOutput"></pre>
      </div>
    </section>
    <div class="footer" id="footer"></div>
  </main>

  <script>
    const appState = {
      refreshMs: 5000,
      timer: null,
      activeLog: null,
      logFilter: "",
      selfTest: null,
      selfTestLoaded: false,
      selfTestBusy: false,
    };

    const el = {
      meta: document.getElementById("meta"),
      statusBand: document.getElementById("statusBand"),
      runtime: document.getElementById("runtime"),
      deployment: document.getElementById("deployment"),
      server: document.getElementById("server"),
      connectivity: document.getElementById("connectivity"),
      chatgptUpload: document.getElementById("chatgptUpload"),
      excelIntegration: document.getElementById("excelIntegration"),
      surfaces: document.getElementById("surfaces"),
      processes: document.getElementById("processes"),
      alerts: document.getElementById("alerts"),
      restarts: document.getElementById("restarts"),
      trend: document.getElementById("trend"),
      links: document.getElementById("links"),
      selfTestTarget: document.getElementById("selfTestTarget"),
      selfTestDeep: document.getElementById("selfTestDeep"),
      runSelfTest: document.getElementById("runSelfTest"),
      selfTestMeta: document.getElementById("selfTestMeta"),
      selfTestChecks: document.getElementById("selfTestChecks"),
      selfTestRecommendations: document.getElementById("selfTestRecommendations"),
      logTabs: document.getElementById("logTabs"),
      logMeta: document.getElementById("logMeta"),
      logOutput: document.getElementById("logOutput"),
      refreshInterval: document.getElementById("refreshInterval"),
      refreshNow: document.getElementById("refreshNow"),
      logFilter: document.getElementById("logFilter"),
      footer: document.getElementById("footer"),
    };

    function fmtDuration(totalSeconds) {
      if (typeof totalSeconds !== "number") return "n/a";
      const days = Math.floor(totalSeconds / 86400);
      const hours = Math.floor((totalSeconds % 86400) / 3600);
      const mins = Math.floor((totalSeconds % 3600) / 60);
      const secs = totalSeconds % 60;
      const parts = [];
      if (days) parts.push(`${days}d`);
      if (hours || days) parts.push(`${hours}h`);
      if (mins || hours || days) parts.push(`${mins}m`);
      parts.push(`${secs}s`);
      return parts.join(" ");
    }

    function fmtDate(value) {
      if (!value) return "n/a";
      const date = new Date(value);
      if (Number.isNaN(date.getTime())) return value;
      return date.toLocaleString();
    }

    function fmtNumber(value, suffix = "") {
      if (typeof value !== "number") return "n/a";
      return `${value}${suffix}`;
    }

    function fmtLatency(value) {
      return typeof value === "number" ? `${value} ms` : "n/a";
    }

    function statRow(label, value) {
      return `<div class="stat"><span class="label">${label}</span><span class="value">${value ?? "n/a"}</span></div>`;
    }

    function linkRow(label, href) {
      if (!href) return statRow(label, "n/a");
      return `<div class="stat"><span class="label">${label}</span><span class="value"><a href="${href}" target="_blank" rel="noreferrer">${href}</a></span></div>`;
    }

    function escapeHtml(value) {
      return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;");
    }

    function severityBadge(severity) {
      const normalized = severity || "info";
      return `<span class="badge ${normalized === "critical" ? "bad" : normalized === "warning" ? "warn" : "info"}">${normalized}</span>`;
    }

    function readinessBadge(status, label) {
      const normalized = status || "action_needed";
      const css = ["ready", "pass"].includes(normalized)
        ? "ok"
        : ["degraded", "warning"].includes(normalized)
          ? "warn"
          : normalized === "skipped"
            ? "info"
            : "bad";
      return `<span class="badge ${css}">${label || normalized}</span>`;
    }

    function endpointRow(label, probe) {
      if (!probe) return statRow(label, "n/a");
      const statusText = probe.ok === true
        ? `OK ${probe.status_code ?? ""}`.trim()
        : probe.ok === false
          ? `Fail ${probe.status_code ?? ""}`.trim()
          : "n/a";
      return `
        <div class="stat">
          <span class="label">${label}</span>
          <span class="value">
            ${statusText}<br>
            <span class="process-meta">${fmtLatency(probe.latency_ms)}</span>
          </span>
        </div>
      `;
    }

    function renderList(node, items, emptyText, formatter) {
      if (!items.length) {
        node.innerHTML = `<div class="empty">${emptyText}</div>`;
        return;
      }
      node.innerHTML = items.map(formatter).join("");
    }

    function renderLogs(logs) {
      const names = Object.keys(logs || {});
      if (!names.length) {
        el.logTabs.innerHTML = "";
        el.logMeta.textContent = "No log sources";
        el.logOutput.textContent = "[no log output]";
        return;
      }

      if (!appState.activeLog || !logs[appState.activeLog]) {
        appState.activeLog = names[0];
      }

      el.logTabs.innerHTML = names.map((name) => `
        <button type="button" class="log-tab ${name === appState.activeLog ? "active" : ""}" data-log-name="${name}">
          ${name}
        </button>
      `).join("");

      const selected = logs[appState.activeLog];
      const rawLines = Array.isArray(selected.tail) ? selected.tail : [];
      const filteredLines = appState.logFilter
        ? rawLines.filter((line) => String(line).toLowerCase().includes(appState.logFilter.toLowerCase()))
        : rawLines;

      el.logMeta.innerHTML = `
        <strong>${appState.activeLog}</strong>
        <span>${fmtDate(selected.updated_at)} | ${escapeHtml(selected.path || "")}</span>
      `;
      el.logOutput.textContent = filteredLines.length ? filteredLines.join("\\n") : "[no matching log lines]";
    }

    function renderSelfTest(payload) {
      if (!payload) {
        el.selfTestMeta.innerHTML = [
          statRow("Status", "not run"),
          statRow("Target", el.selfTestTarget.value || "both"),
          statRow("Deep checks", el.selfTestDeep.checked ? "yes" : "no"),
        ].join("");
        el.selfTestChecks.innerHTML = `<div class="empty">Run the self-test to verify health, dashboard, MCP initialize, tools/list, and sample tool calls.</div>`;
        el.selfTestRecommendations.innerHTML = "";
        return;
      }

      const checks = Array.isArray(payload.checks) ? payload.checks : [];
      const recommendations = Array.isArray(payload.recommendations) ? payload.recommendations : [];
      el.selfTestMeta.innerHTML = [
        statRow("Status", payload.status || "n/a"),
        statRow("Connector", payload.connector_url || "n/a"),
        statRow("Public base", payload.public_base_url || "n/a"),
        statRow("Deep checks", el.selfTestDeep.checked ? "yes" : "no"),
      ].join("");

      renderList(
        el.selfTestChecks,
        checks,
        "No self-test checks returned.",
        (check) => `
          <article class="list-item">
            <header>
              <h3>${escapeHtml(check.name || "check")}</h3>
              ${readinessBadge(check.status, check.status)}
            </header>
            <p>${escapeHtml(check.detail || "No detail.")}</p>
          </article>
        `
      );

      renderList(
        el.selfTestRecommendations,
        recommendations,
        "No follow-up actions required.",
        (item) => `
          <article class="list-item">
            <header>
              <h3>Recommended Action</h3>
              ${readinessBadge("ready", "info")}
            </header>
            <p>${escapeHtml(item)}</p>
          </article>
        `
      );
    }

    async function runSelfTest() {
      if (appState.selfTestBusy) return;
      appState.selfTestBusy = true;
      el.runSelfTest.disabled = true;
      el.runSelfTest.textContent = "Running...";
      try {
        const target = el.selfTestTarget.value || "both";
        const includeToolCalls = el.selfTestDeep.checked ? "true" : "false";
        const response = await fetch(`/dashboard/self-test?target=${encodeURIComponent(target)}&include_tool_calls=${includeToolCalls}`, {
          cache: "no-store",
        });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        appState.selfTest = await response.json();
        appState.selfTestLoaded = true;
        renderSelfTest(appState.selfTest);
      } catch (error) {
        appState.selfTest = {
          status: "fail",
          checks: [{ name: "dashboard self-test", status: "fail", detail: error.message }],
          recommendations: ["Retry the self-test after confirming /health and /mcp are reachable."],
        };
        renderSelfTest(appState.selfTest);
      } finally {
        appState.selfTestBusy = false;
        el.runSelfTest.disabled = false;
        el.runSelfTest.textContent = "Run Self Test";
      }
    }

    function render(data) {
      const summary = data.summary || {};
      const runtime = data.runtime || {};
      const deployment = runtime.deployment || {};
      const server = data.server || {};
      const connectivity = data.connectivity || {};
      const subservices = data.subservices || {};
      const surfaces = data.surfaces || {};
      const chatgptUpload = server.chatgpt_upload || {};
      const excelIntegration = subservices.excel_mcp || {};
      const processes = data.processes || {};
      const alerts = Array.isArray(data.alerts) ? data.alerts : [];
      const history = data.history || {};
      const logs = data.logs || {};
      const surfaceSummary = surfaces.summary || {};
      const surfaceItems = Array.isArray(surfaces.items) ? surfaces.items : [];

      el.meta.innerHTML = `
        <span class="pill">Updated ${fmtDate(data.generated_at)}</span>
        <span class="pill">Mode ${runtime.mode || "n/a"}</span>
        <span class="pill">Deploy ${deployment.provider_label || "n/a"}</span>
        <span class="pill">${summary.processes_up ?? 0}/${summary.process_total ?? 0} processes up</span>
        <span class="pill">Transport ${server.transport || "n/a"}</span>
        <span class="pill">Probe ${fmtLatency(runtime.last_health_probe_latency_ms)}</span>
        <span class="pill">Upload ${chatgptUpload.supported ? "widget ready" : "action needed"}</span>
        <span class="pill">Excel ${excelIntegration.status || "not configured"}</span>
        <span class="pill">Surfaces ${surfaceSummary.ready ?? 0}/${surfaceSummary.total ?? 0} ready</span>
        <span class="pill">Restarts ${history.restart_count ?? 0}</span>
      `;

      el.statusBand.innerHTML = `
        <div class="score ${summary.health_state || "degraded"}">
          <div>
            <strong>${summary.health_score ?? "n/a"}</strong>
            <span>Health Score</span>
          </div>
        </div>
        <div class="status-copy">
          <span class="state-pill ${summary.health_state || "degraded"}">${summary.status_label || "Unknown"}</span>
          <h2>${summary.alert_count ? `${summary.alert_count} active alerts` : "No active alerts"}</h2>
          <p>State age ${fmtNumber(runtime.state_age_seconds, "s")} | Probe age ${fmtNumber(runtime.probe_age_seconds, "s")} | Restart count ${history.restart_count ?? 0}</p>
          <p>Public base ${runtime.public_base_url || "not configured"}.</p>
        </div>
      `;

      el.runtime.innerHTML = [
        statRow("Started", fmtDate(runtime.started_at)),
        statRow("Uptime", fmtDuration(runtime.uptime_seconds)),
        statRow("Managed", runtime.managed ? "yes" : "no"),
        statRow("Host", `${server.host || "n/a"}:${server.port || "n/a"}`),
        statRow("Public base", runtime.public_base_url || "not configured"),
        statRow("Last probe", fmtDate(runtime.last_health_probe_at)),
        statRow("Probe latency", fmtLatency(runtime.last_health_probe_latency_ms)),
        statRow("State file", runtime.state_file || "n/a"),
        statRow("State updated", fmtDate(runtime.state_file_updated_at)),
      ].join("");

      el.deployment.innerHTML = [
        statRow("Provider", deployment.provider_label || "n/a"),
        statRow("Environment", deployment.railway_environment_name || runtime.mode || "n/a"),
        statRow("Project", deployment.railway_project_name || "n/a"),
        statRow("Service", deployment.railway_service_name || "n/a"),
        statRow("Public domain", deployment.railway_public_domain || runtime.public_base_url || "n/a"),
        statRow("Private domain", deployment.railway_private_domain || "n/a"),
      ].join("");

      el.server.innerHTML = [
        statRow("Name", server.name),
        statRow("Indexed docs", `${server.indexed_docs ?? "n/a"} / ${server.total_docs ?? "n/a"}`),
        statRow("Tools", Array.isArray(server.tools) ? server.tools.length : "n/a"),
        statRow("MCP path", server.mcp_path),
        statRow("Docs path", server.docs_path),
        statRow("Dashboard path", server.dashboard_path),
      ].join("");

      el.connectivity.innerHTML = [
        endpointRow("Local status", connectivity.local_status),
        endpointRow("Local health", connectivity.local_health),
        endpointRow("Local docs", connectivity.local_docs),
        endpointRow("Public health", connectivity.public_health),
      ].join("");

      el.chatgptUpload.innerHTML = [
        statRow("Status", chatgptUpload.supported ? "ready" : "action needed"),
        statRow("Submission", chatgptUpload.submission_ready ? "ready" : "needs metadata"),
        statRow("Widget tool", chatgptUpload.widget_tool_name || "n/a"),
        statRow("Resource URI", chatgptUpload.resource_uri || "n/a"),
        statRow("Template", chatgptUpload.template_exists ? "present" : "missing"),
        statRow("Widget domain", chatgptUpload.widget_domain || "n/a"),
        statRow("CSP", chatgptUpload.widget_csp_configured ? "configured" : "missing"),
        statRow("Files", Array.isArray(chatgptUpload.accepted_extensions) ? chatgptUpload.accepted_extensions.join(", ") : "n/a"),
        statRow("Remote URL", Array.isArray(chatgptUpload.remote_download_url_schemes) ? chatgptUpload.remote_download_url_schemes.join(", ") : "n/a"),
        statRow("sandbox:/ read", chatgptUpload.direct_sandbox_paths_supported ? "yes" : "no"),
        statRow("Prompt", chatgptUpload.recommended_prompt || "n/a"),
      ].join("");

      el.excelIntegration.innerHTML = [
        statRow("Status", excelIntegration.status || "not configured"),
        statRow("Configured", excelIntegration.configured ? "yes" : "no"),
        statRow("Base URL", excelIntegration.base_url || "n/a"),
        statRow("MCP URL", excelIntegration.mcp_url || "n/a"),
        statRow("Health", excelIntegration.health?.ok === true ? "pass" : excelIntegration.health?.ok === false ? "fail" : "n/a"),
        statRow("Initialize", excelIntegration.initialize?.ok === true ? "pass" : excelIntegration.initialize?.ok === false ? "fail" : "n/a"),
        statRow("Server", excelIntegration.initialize?.server_name || "n/a"),
        statRow("Local Ready", excelIntegration.local_ready ? "yes" : "no"),
        statRow("Export Version", excelIntegration.export_contract_version || "n/a"),
        statRow("Sheets", Array.isArray(excelIntegration.sheet_defaults) ? excelIntegration.sheet_defaults.join(", ") : "n/a"),
      ].join("");

      renderList(
        el.surfaces,
        surfaceItems,
        "No client surface data available.",
        (surface) => `
          <article class="list-item">
            <header>
              <h3>${escapeHtml(surface.label || surface.id || "surface")}</h3>
              ${readinessBadge(surface.status, surface.status_label)}
            </header>
            <p class="surface-primary"><strong>${escapeHtml(surface.mode || "n/a")}</strong> | ${escapeHtml(surface.primary || "n/a")}</p>
            <p>${escapeHtml((surface.checks || []).join(" | "))}</p>
            <p>Next: ${escapeHtml(surface.next_action || "n/a")}</p>
            <p>Verify: <code>${escapeHtml(surface.verification || "n/a")}</code></p>
          </article>
        `
      );

      el.processes.innerHTML = Object.entries(processes).map(([name, proc]) => {
        const statusClass = proc.running ? "ok" : (proc.expected ? "bad" : "warn");
        const statusText = proc.running ? "running" : (proc.expected ? "down" : "idle");
        return `
          <div class="process">
            <div class="process-head">
              <div class="process-name">${name}</div>
              <span class="badge ${statusClass}">${statusText}</span>
            </div>
            <div class="stat compact"><span class="label">PID</span><span class="value">${proc.pid ?? "n/a"}</span></div>
            <div class="process-meta">Expected: ${proc.expected ? "yes" : "no"} | Required: ${proc.required ? "yes" : "no"}</div>
          </div>
        `;
      }).join("");

      renderList(
        el.alerts,
        alerts,
        "No active alerts.",
        (alert) => `
          <article class="list-item">
            <header>
              <h3>${alert.title}</h3>
              ${severityBadge(alert.severity)}
            </header>
            <p>${alert.detail}</p>
          </article>
        `
      );

      renderList(
        el.restarts,
        Array.isArray(history.recent_restarts) ? history.recent_restarts : [],
        "No restart history recorded yet.",
        (restart) => `
          <article class="list-item">
            <header>
              <h3>${restart.reason || "restart"}</h3>
              ${restart.public_url_changed ? '<span class="badge warn">url changed</span>' : '<span class="badge info">tracked</span>'}
            </header>
            <p>${fmtDate(restart.at)} | previous server PID ${restart.previous_server_pid ?? "n/a"} | previous URL ${restart.previous_public_base_url || "n/a"}</p>
          </article>
        `
      );

      const trend = Array.isArray(history.trend) ? history.trend : [];
      if (!trend.length) {
        el.trend.innerHTML = `<div class="empty">No health samples yet.</div>`;
      } else {
        el.trend.innerHTML = `
          <div class="trend-summary">
            <div class="mini-stat"><strong>${history.avg_health_score ?? "n/a"}</strong><span>Avg score</span></div>
            <div class="mini-stat"><strong>${history.avg_latency_ms ?? "n/a"}</strong><span>Avg ms</span></div>
            <div class="mini-stat"><strong>${history.last_hour_sample_count ?? 0}</strong><span>1h samples</span></div>
          </div>
          <div class="trend-bars">
            ${trend.map((entry) => `
              <div
                class="trend-bar ${entry.health_state || "degraded"}"
                style="height:${Math.max(10, Number(entry.health_score || 0))}%"
                title="${escapeHtml(`${fmtDate(entry.ts)} | score ${entry.health_score ?? "n/a"} | alerts ${entry.alert_count ?? 0} | latency ${fmtLatency(entry.probe_latency_ms)}`)}"
              ></div>
            `).join("")}
          </div>
        `;
      }

      el.links.innerHTML = [
        linkRow("Dashboard", runtime.dashboard_url),
        linkRow("Self Test", server.dashboard_self_test_url),
        linkRow("Status", runtime.status_url),
        linkRow("Health", runtime.health_url),
        linkRow("Docs", runtime.docs_url),
        linkRow("MCP", runtime.mcp_url),
        linkRow("Excel MCP", excelIntegration.mcp_url),
        linkRow("Excel Health", excelIntegration.health?.url),
      ].join("");

      renderLogs(logs);
      renderSelfTest(appState.selfTest);
      el.footer.textContent = `Auto refresh ${appState.refreshMs ? `every ${Math.round(appState.refreshMs / 1000)} seconds` : "disabled"}. Runtime base URL: ${server.runtime_base_url || "n/a"}`;
    }

    async function refresh() {
      try {
        const response = await fetch("/dashboard/status", { cache: "no-store" });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        render(await response.json());
      } catch (error) {
        el.footer.textContent = `Dashboard refresh failed: ${error.message}`;
      }
    }

    function setRefreshTimer() {
      if (appState.timer) {
        clearInterval(appState.timer);
        appState.timer = null;
      }
      if (appState.refreshMs > 0) {
        appState.timer = setInterval(refresh, appState.refreshMs);
      }
    }

    el.refreshInterval.addEventListener("change", (event) => {
      appState.refreshMs = Number(event.target.value);
      setRefreshTimer();
    });

    el.refreshNow.addEventListener("click", () => {
      refresh();
    });

    el.runSelfTest.addEventListener("click", () => {
      runSelfTest();
    });

    el.logTabs.addEventListener("click", (event) => {
      const button = event.target.closest("[data-log-name]");
      if (!button) return;
      appState.activeLog = button.getAttribute("data-log-name");
      refresh();
    });

    el.logFilter.addEventListener("input", (event) => {
      appState.logFilter = event.target.value || "";
      refresh();
    });

    renderSelfTest(null);
    refresh().then(() => {
      if (!appState.selfTestLoaded) {
        runSelfTest();
      }
    });
    setRefreshTimer();
  </script>
</body>
</html>"""
    )


# ───────────────────────────────────────────────
# 서버 실행
# ───────────────────────────────────────────────
def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="HVDC Knowledge MCP server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "sse", "streamable-http"],
        default=os.getenv("HVDC_MCP_TRANSPORT", "stdio"),
        help="Transport mode (default: stdio)",
    )
    parser.add_argument(
        "--host",
        default=os.getenv("HVDC_MCP_HOST", "127.0.0.1"),
        help="HTTP host for streamable-http / sse transports",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=_env_default_port(),
        help="HTTP port for streamable-http / sse transports",
    )
    parser.add_argument(
        "--public-base-url",
        default=_env_default_public_base_url(),
        help="Public HTTPS base URL used for document citations, e.g. https://abc123.ngrok.app",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = _parse_args()
    _configure_runtime(args.transport, args.host, args.port, args.public_base_url)

    logger.info("HVDC Knowledge MCP Server starting...")
    logger.info(f"Docs directory: {DOCS_DIR}")
    if DOCS_DIR.exists():
        md_count = len(list(DOCS_DIR.rglob("*.md")))
        logger.info(f"Found {md_count} .md files")
    else:
        logger.warning("docs/ directory not found!")
    logger.info(
        "Transport=%s host=%s port=%s mcp_path=%s",
        args.transport,
        args.host,
        args.port,
        mcp.settings.streamable_http_path,
    )
    if args.transport == "streamable-http":
        logger.info("Status URL: http://%s:%s/", args.host, args.port)
        logger.info("Health URL: http://%s:%s/health", args.host, args.port)
        logger.info("MCP URL: http://%s:%s%s", args.host, args.port, mcp.settings.streamable_http_path)
        if RUNTIME["public_base_url"]:
            logger.info("Public base URL: %s", RUNTIME["public_base_url"])
        else:
            logger.warning(
                "No public base URL configured. search/fetch citations will use localhost URLs."
            )
    mcp.run(transport=args.transport)
