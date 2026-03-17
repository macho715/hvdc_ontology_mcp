from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = ROOT / ".runtime" / "analysis"
SNAPSHOT_DIR = ANALYSIS_DIR / "snapshots"
MANIFEST_PATH = SNAPSHOT_DIR / "manifest.json"


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-") or "snapshot"


def _ensure_dirs() -> None:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path, fallback: Any) -> Any:
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return fallback


def _write_json(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def _snapshot_paths(snapshot_name: str) -> tuple[Path, Path]:
    slug = _slugify(snapshot_name)
    return SNAPSHOT_DIR / f"{slug}.rows.json", SNAPSHOT_DIR / f"{slug}.summary.json"


def save_snapshot(
    snapshot_name: str,
    *,
    normalized_rows: list[dict[str, Any]],
    aggregate_summary: dict[str, Any],
    source: dict[str, Any],
) -> dict[str, Any]:
    _ensure_dirs()
    rows_path, summary_path = _snapshot_paths(snapshot_name)
    saved_at = _utc_now()
    rows_payload = {
        "snapshot_name": snapshot_name,
        "saved_at": saved_at,
        "source": source,
        "rows": normalized_rows,
    }
    summary_payload = {
        "snapshot_name": snapshot_name,
        "saved_at": saved_at,
        "source": source,
        **aggregate_summary,
    }
    _write_json(rows_path, rows_payload)
    _write_json(summary_path, summary_payload)

    manifest = _read_json(MANIFEST_PATH, {"snapshots": []})
    snapshots = [item for item in manifest.get("snapshots", []) if item.get("snapshot_name") != snapshot_name]
    snapshots.append(
        {
            "snapshot_name": snapshot_name,
            "saved_at": saved_at,
            "rows_path": str(rows_path),
            "summary_path": str(summary_path),
            "row_count": len(normalized_rows),
        }
    )
    snapshots.sort(key=lambda item: item.get("saved_at", ""), reverse=True)
    _write_json(MANIFEST_PATH, {"snapshots": snapshots})
    return summary_payload


def load_snapshot(snapshot_name: str) -> dict[str, Any]:
    rows_path, summary_path = _snapshot_paths(snapshot_name)
    if not rows_path.exists() or not summary_path.exists():
        raise ValueError(f"Snapshot '{snapshot_name}' does not exist.")
    return {
        "rows": _read_json(rows_path, {}),
        "summary": _read_json(summary_path, {}),
    }
