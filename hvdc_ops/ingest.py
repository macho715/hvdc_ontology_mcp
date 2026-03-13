from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import urlparse
from urllib.request import Request, urlopen

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / ".runtime" / "analysis"
UPLOADS_DIR = ANALYSIS_DIR / "uploads"
SUPPORTED_SUFFIXES = {".csv", ".xlsx"}

SEMANTIC_ALIASES: dict[str, tuple[str, ...]] = {
    "shipment_id": ("shipment_id", "shipment id", "id", "bl", "bl_no", "reference", "shipment"),
    "destination": ("destination", "final_location", "final location", "site", "node", "location"),
    "status": ("status", "open_status", "open status", "shipment_status", "current status"),
    "mode": ("mode", "shipment_mode", "transport_mode", "flow_mode"),
    "weight_tons": ("weight_tons", "gross_weight_tons", "gross weight tons", "weight", "gross weight"),
    "port_date": ("port_date", "port date", "ata_port", "at_port", "arrival_port_date"),
    "mosb_date": ("mosb_date", "mosb date", "mosb_in", "mosb arrival", "offshore_hub_date"),
    "site_date": ("site_date", "site date", "delivered_to_site", "delivered date", "site arrival"),
    "eta_date": ("eta_date", "eta date", "eta", "planned_eta"),
    "actual_date": ("actual_date", "actual date", "ata", "actual_delivery_date"),
    "boe_complete": ("boe_complete", "boe complete", "boe_ready", "boe ok"),
    "ebl_match": ("ebl_match", "ebl match", "ebl_ok", "ebl aligned"),
    "fanr_ready": ("fanr_ready", "fanr ready", "fanr permit", "fanr_ok"),
    "ecas_ready": ("ecas_ready", "ecas ready", "ecas_ok", "moiat_ecas"),
    "cicpa_ready": ("cicpa_ready", "cicpa ready", "cicpa_ok", "gatepass_ready"),
    "fra_ready": ("fra_ready", "fra ready", "fra_ok", "adnoc_fra"),
    "dot_ready": ("dot_ready", "dot ready", "dot_ok", "dot permit"),
    "weather_alert": ("weather_alert", "weather alert", "weather_risk", "weather warning"),
    "mosb_utilization_pct": (
        "mosb_utilization_pct",
        "mosb utilization pct",
        "mosb_utilization",
        "mosb util",
        "mosb occupancy",
    ),
}
DATE_FIELDS = {"port_date", "mosb_date", "site_date", "eta_date", "actual_date"}
BOOL_FIELDS = {
    "boe_complete",
    "ebl_match",
    "fanr_ready",
    "ecas_ready",
    "cicpa_ready",
    "fra_ready",
    "dot_ready",
    "weather_alert",
}
FLOAT_FIELDS = {"weight_tons", "mosb_utilization_pct"}
UPPER_FIELDS = {"destination", "mode"}
TRUE_STRINGS = {"true", "t", "yes", "y", "1", "ok", "pass", "ready", "done"}
FALSE_STRINGS = {"false", "f", "no", "n", "0", "fail", "blocked", "hold", "pending"}


@dataclass
class FileSourceMetadata:
    source_kind: str
    display_name: str
    path: str
    sheet_name: str | None
    row_count: int
    columns: list[str]


def ensure_analysis_dirs() -> None:
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _normalize_token(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _is_blank(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and pd.isna(value):
        return True
    if isinstance(value, str):
        return value.strip() == ""
    return False


def _coerce_bool(value: Any) -> bool | None:
    if _is_blank(value):
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        if value == 1:
            return True
        if value == 0:
            return False
    text = str(value).strip().lower()
    if text in TRUE_STRINGS:
        return True
    if text in FALSE_STRINGS:
        return False
    return None


def _coerce_float(value: Any) -> float | None:
    if _is_blank(value):
        return None
    if isinstance(value, (int, float)) and not pd.isna(value):
        return float(value)
    text = str(value).strip().replace(",", "")
    try:
        return float(text)
    except ValueError:
        return None


def _coerce_date(value: Any) -> str | None:
    if _is_blank(value):
        return None
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    return str(value).strip()


def _coerce_text(value: Any, *, upper: bool = False) -> str | None:
    if _is_blank(value):
        return None
    text = str(value).strip()
    return text.upper() if upper else text


def _coerce_value(key: str, value: Any) -> Any:
    if key in BOOL_FIELDS:
        return _coerce_bool(value)
    if key in FLOAT_FIELDS:
        return _coerce_float(value)
    if key in DATE_FIELDS:
        return _coerce_date(value)
    return _coerce_text(value, upper=key in UPPER_FIELDS)


def _match_column(columns: list[str], requested: str) -> str | None:
    requested_token = _normalize_token(requested)
    for column in columns:
        if column == requested or _normalize_token(column) == requested_token:
            return column
    return None


def _build_column_selection(columns: list[str], column_map: dict[str, str] | None) -> dict[str, str]:
    resolved: dict[str, str] = {}
    if column_map:
        for semantic_key, source_column in column_map.items():
            if semantic_key not in SEMANTIC_ALIASES:
                raise ValueError(f"Unknown semantic column '{semantic_key}' in column_map.")
            matched = _match_column(columns, source_column)
            if matched is None:
                raise ValueError(f"Column '{source_column}' not found for semantic key '{semantic_key}'.")
            resolved[semantic_key] = matched

    normalized_columns = {_normalize_token(column): column for column in columns}
    for semantic_key, aliases in SEMANTIC_ALIASES.items():
        if semantic_key in resolved:
            continue
        alias_tokens = {_normalize_token(alias) for alias in aliases}
        for token, column in normalized_columns.items():
            if token in alias_tokens:
                resolved[semantic_key] = column
                break
    return resolved


def _warehouse_leg_count(raw_row: dict[str, Any]) -> int:
    count = 0
    for column, value in raw_row.items():
        token = _normalize_token(str(column))
        if "mosb" in token:
            continue
        if "warehouse" in token or re.search(r"(^|_)wh($|_)", token):
            if not _is_blank(value):
                count += 1
    return count


def _normalize_records(
    rows: list[dict[str, Any]],
    columns: list[str],
    *,
    column_map: dict[str, str] | None,
    source_kind: str,
    display_name: str,
) -> list[dict[str, Any]]:
    selected_columns = _build_column_selection(columns, column_map)
    normalized_records: list[dict[str, Any]] = []
    for index, raw_row in enumerate(rows, start=1):
        normalized: dict[str, Any] = {
            "source_row_number": index,
            "matched_columns": selected_columns,
            "warehouse_leg_count": _warehouse_leg_count(raw_row),
            "_source": {
                "kind": source_kind,
                "display_name": display_name,
            },
        }
        for semantic_key, source_column in selected_columns.items():
            normalized[semantic_key] = _coerce_value(semantic_key, raw_row.get(source_column))

        if not normalized.get("shipment_id"):
            normalized["shipment_id"] = f"ROW-{index}"

        normalized_records.append(normalized)
    return normalized_records


def _validate_suffix(path: Path) -> None:
    if path.suffix.lower() not in SUPPORTED_SUFFIXES:
        supported = ", ".join(sorted(SUPPORTED_SUFFIXES))
        raise ValueError(f"Unsupported file type '{path.suffix}'. Supported: {supported}")


def _download_file(file_param: dict[str, Any]) -> Path:
    ensure_analysis_dirs()
    download_url = str(file_param.get("download_url") or "").strip()
    if not download_url:
        raise ValueError(
            "file.download_url is required for file-based ChatGPT ingestion. "
            "In ChatGPT, use hvdc_render_backlog_upload_widget or another widget flow "
            "that uploads the file and provides a temporary HTTP/HTTPS URL."
        )

    parsed = urlparse(download_url)
    if parsed.scheme not in {"http", "https"}:
        if parsed.scheme == "sandbox":
            raise ValueError(
                "file.download_url uses a sandbox path that the remote MCP server cannot read. "
                "Use hvdc_render_backlog_upload_widget so ChatGPT uploads the file and supplies "
                "a temporary HTTP/HTTPS download_url, or pass an HTTP/HTTPS URL directly."
            )
        raise ValueError(
            "file.download_url must use http or https. "
            "For ChatGPT uploads, use hvdc_render_backlog_upload_widget to obtain a temporary "
            "HTTP/HTTPS download_url before calling the analysis tool."
        )

    extension = Path(parsed.path).suffix.lower() or ".bin"
    target = UPLOADS_DIR / f"upload-{os.getpid()}-{abs(hash(download_url))}{extension}"
    request = Request(download_url, headers={"User-Agent": "hvdc-knowledge-mcp/1.0"})
    with urlopen(request, timeout=30) as response:
        target.write_bytes(response.read())
    _validate_suffix(target)
    return target


def _resolve_local_path(local_path: str, *, allow_local_paths: bool) -> Path:
    if not allow_local_paths:
        raise ValueError("local_path is only allowed when the server is running in stdio mode.")
    path = Path(local_path).expanduser()
    if not path.is_absolute():
        path = (ROOT / path).resolve()
    else:
        path = path.resolve()
    if not path.exists():
        raise ValueError(f"Local file not found: {path}")
    _validate_suffix(path)
    return path


def _read_table(path: Path, *, sheet_name: str | None) -> tuple[list[dict[str, Any]], list[str], str | None]:
    if path.suffix.lower() == ".csv":
        frame = pd.read_csv(path, dtype=object)
        resolved_sheet_name = None
    else:
        frame = pd.read_excel(path, sheet_name=sheet_name if sheet_name else 0, dtype=object)
        resolved_sheet_name = sheet_name or getattr(frame, "name", None)

    frame = frame.where(pd.notna(frame), None)
    rows = frame.to_dict(orient="records")
    return rows, [str(column) for column in frame.columns], resolved_sheet_name


def load_normalized_records(
    *,
    file_param: dict[str, Any] | None,
    local_path: str | None,
    sheet_name: str | None,
    column_map: dict[str, str] | None,
    allow_local_paths: bool,
) -> tuple[list[dict[str, Any]], FileSourceMetadata]:
    provided_sources = int(file_param is not None) + int(bool(local_path))
    if provided_sources != 1:
        raise ValueError("Provide exactly one of file or local_path.")

    if file_param is not None:
        path = _download_file(file_param)
        source_kind = "file_param"
        display_name = file_param.get("file_id") or path.name
    else:
        path = _resolve_local_path(local_path or "", allow_local_paths=allow_local_paths)
        source_kind = "local_path"
        display_name = path.name

    rows, columns, resolved_sheet_name = _read_table(path, sheet_name=sheet_name)
    normalized_records = _normalize_records(
        rows,
        columns,
        column_map=column_map,
        source_kind=source_kind,
        display_name=display_name,
    )
    metadata = FileSourceMetadata(
        source_kind=source_kind,
        display_name=display_name,
        path=str(path),
        sheet_name=resolved_sheet_name,
        row_count=len(normalized_records),
        columns=columns,
    )
    return normalized_records, metadata


def normalize_inline_shipment(
    shipment: dict[str, Any],
    *,
    column_map: dict[str, str] | None = None,
) -> dict[str, Any]:
    columns = [str(column) for column in shipment.keys()]
    normalized = _normalize_records(
        [shipment],
        columns,
        column_map=column_map,
        source_kind="inline",
        display_name="inline_shipment",
    )
    return normalized[0]


def select_record(
    records: list[dict[str, Any]],
    *,
    row_number: int | None,
    shipment_id: str | None,
) -> dict[str, Any]:
    if row_number is None and not shipment_id:
        raise ValueError("Provide row_number or shipment_id when selecting a row from a table.")
    if row_number is not None:
        if row_number < 1 or row_number > len(records):
            raise ValueError(f"row_number must be between 1 and {len(records)}.")
        return records[row_number - 1]

    lookup = (shipment_id or "").strip().upper()
    for record in records:
        if str(record.get("shipment_id") or "").strip().upper() == lookup:
            return record
    raise ValueError(f"shipment_id '{shipment_id}' was not found in the provided table.")
