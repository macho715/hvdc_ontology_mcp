#!/usr/bin/env python3
"""
Generate canonical Logi ontology master documents.

Outputs:
    - docs/Logi ontol core doc/CORE_DOCUMENTATION_MASTER.md
    - docs/Logi ontol core doc/LOGI_ONTOL_CORE_MERGED.md
"""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs" / "Logi ontol core doc"
MASTER_PATH = DOCS_DIR / "CORE_DOCUMENTATION_MASTER.md"
MERGED_PATH = DOCS_DIR / "LOGI_ONTOL_CORE_MERGED.md"
DATASET_PATH = ROOT / "output" / "hvdc_status_v35.ttl"
GENERATED_NOTICE = "<!-- GENERATED FILE: do not edit manually. Rebuild with scripts/build_logi_master.py -->"


@dataclass(frozen=True)
class CuratedDoc:
    filename: str
    title: str
    purpose: str


CURATED_DOCS: list[CuratedDoc] = [
    CuratedDoc("NAMESPACE_REGISTRY.md", "Namespace Registry", "Canonical namespace policy and alias mapping."),
    CuratedDoc("CONSOLIDATED-01-core-framework-infra.md", "Core Framework / Infrastructure", "Node model, routing policy, and core operational constraints."),
    CuratedDoc("CONSOLIDATED-02-warehouse-flow.md", "Warehouse / Flow Code", "Canonical Flow Code v3.5 definitions and validation semantics."),
    CuratedDoc("CONSOLIDATED-03-document-ocr.md", "Document OCR / Guardian", "OCR gate thresholds, SHACL policy, and PASS/FAIL examples."),
    CuratedDoc("CONSOLIDATED-04-barge-bulk-cargo.md", "Barge / Bulk Cargo", "Bulk cargo and LCT-specific flow behavior."),
    CuratedDoc("CONSOLIDATED-05-invoice-cost.md", "Invoice / Cost Guard", "Band-vs-decision policy for invoice cost review."),
    CuratedDoc("CONSOLIDATED-06-material-handling.md", "Material Handling", "Deployable material-handling ontology spec aligned to canonical Flow Code rules."),
    CuratedDoc("CONSOLIDATED-07-port-operations.md", "Port Operations", "Port assignment and port-side logistics control."),
    CuratedDoc("CONSOLIDATED-08-communication.md", "Communication", "Communication ontology examples using canonical timestamp and prefix rules."),
    CuratedDoc("CONSOLIDATED-09-operations.md", "Operations", "Operational reporting, KPI, and analytics model."),
]

REFERENCE_DOCS: list[CuratedDoc] = [
    CuratedDoc("flow-code-v35-schema.ttl", "Flow Code Schema TTL", "Canonical SHACL / OWL flow schema."),
    CuratedDoc("FLOW_CODE_V35_QUICK_REFERENCE.md", "Flow Code Quick Reference", "Operator-oriented reference card aligned to canonical naming."),
    CuratedDoc("FLOW_CODE_V35_INTEGRATION_REPORT.md", "Flow Code Integration Report", "Integration summary without stale dataset counts."),
    CuratedDoc("CONSOLIDATED-06-material-handling-appendix-source-preserved.md", "Material Handling Appendix", "Historical source-preserved appendix excluded from canonical validation."),
]


def _git_commit() -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        commit = result.stdout.strip()
        return commit or "unavailable"
    except OSError:
        return "unavailable"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _line_count(path: Path) -> int:
    return len(path.read_text(encoding="utf-8").splitlines())


def _file_hash(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()


def _measurement_block() -> dict[str, str]:
    if not DATASET_PATH.exists():
        return {
            "measurement_status": "source-dataset-unavailable",
            "triple_count": "unavailable",
            "case_count": "unavailable",
        }
    return {
        "measurement_status": "source-dataset-present-but-not-used-in-doc-build",
        "triple_count": "unavailable",
        "case_count": "unavailable",
    }


def _generated_at(input_paths: list[Path]) -> str:
    try:
        result = subprocess.run(
            ["git", "log", "-1", "--format=%cI", "--", *[str(path.relative_to(ROOT)) for path in input_paths]],
            cwd=str(ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        stamp = result.stdout.strip()
        if stamp:
            return stamp
    except OSError:
        pass

    latest_mtime = max(path.stat().st_mtime for path in input_paths)
    return datetime.fromtimestamp(latest_mtime, tz=UTC).isoformat()


def _metadata_lines(input_paths: list[Path]) -> list[str]:
    measures = _measurement_block()
    return [
        GENERATED_NOTICE,
        "",
        "| Field | Value |",
        "|---|---|",
        f"| generated_at | {_generated_at(input_paths)} |",
        f"| source_commit | `{_git_commit()}` |",
        f"| file_hash | `{_file_hash(input_paths)}` |",
        f"| measurement_status | `{measures['measurement_status']}` |",
        f"| triple_count | `{measures['triple_count']}` |",
        f"| case_count | `{measures['case_count']}` |",
        "",
    ]


def _table_rows(items: list[CuratedDoc]) -> list[str]:
    rows = [
        "| File | Purpose | Lines | SHA256 |",
        "|---|---|---:|---|",
    ]
    for item in items:
        path = DOCS_DIR / item.filename
        rows.append(
            f"| [{item.title}]({item.filename}) | {item.purpose} | {_line_count(path)} | `{_sha256(path)[:12]}` |"
        )
    return rows


def build_master() -> str:
    input_paths = [DOCS_DIR / item.filename for item in CURATED_DOCS + REFERENCE_DOCS]
    lines: list[str] = [
        "# CORE_DOCUMENTATION_MASTER",
        "",
        "Canonical master index for the Logi ontology core document bundle.",
        "This file is generated. It reports canonical sources, namespace policy, and build metadata.",
        "",
        *_metadata_lines(input_paths),
        "## Canonicalization Rules",
        "",
        "- `CONSOLIDATED-02-warehouse-flow.md` is the authoritative Flow Code v3.5 narrative/spec.",
        "- `hvdc:TransportEvent` + `hvdc:hasLogisticsFlowCode` is the canonical event/property pairing.",
        "- `hvdc:hasFlowCode` and `hvdc:LogisticsFlow` are legacy or derived aliases only.",
        "- `MIR/SHU` allow Flow `1` and `2`; `AGI/DAS` require Flow `3` or `4` with MOSB mandatory.",
        "- When the authoritative dataset is not present in the repository, `triple_count` and `case_count` remain `unavailable`.",
        "",
        "## Canonical Documents",
        "",
        *_table_rows(CURATED_DOCS),
        "",
        "## Reference Artifacts",
        "",
        *_table_rows(REFERENCE_DOCS),
        "",
        "## Usage",
        "",
        "- Read the namespace registry first if you need canonical prefixes or alias mappings.",
        "- Read `CONSOLIDATED-02-warehouse-flow.md` before editing any routing or Flow Code logic.",
        "- Treat the material-handling appendix as historical preservation, not as normative specification.",
        "- Rebuild this file and the merged bundle with `python scripts/build_logi_master.py`.",
        "",
    ]
    return "\n".join(lines).strip() + "\n"


def build_merged() -> str:
    merged_items = CURATED_DOCS
    input_paths = [DOCS_DIR / item.filename for item in merged_items]
    lines: list[str] = [
        "# LOGI_ONTOL_CORE_MERGED",
        "",
        "Merged canonical document bundle generated from curated source documents.",
        "",
        *_metadata_lines(input_paths),
        "## Included Sources",
        "",
    ]
    for item in merged_items:
        lines.append(f"- `{item.filename}`")
    lines.append("")

    for item in merged_items:
        path = DOCS_DIR / item.filename
        content = path.read_text(encoding="utf-8").rstrip()
        lines.extend(
            [
                "---",
                "",
                f"## SOURCE: {item.filename}",
                "",
                content,
                "",
            ]
        )
    return "\n".join(lines).rstrip() + "\n"


def _write_if_changed(path: Path, content: str) -> bool:
    if path.exists() and path.read_text(encoding="utf-8") == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Build canonical Logi ontology master documents")
    parser.add_argument("--check", action="store_true", help="Fail if generated outputs are out of date")
    args = parser.parse_args()

    master = build_master()
    merged = build_merged()

    if args.check:
        drift: list[str] = []
        if not MASTER_PATH.exists() or MASTER_PATH.read_text(encoding="utf-8") != master:
            drift.append(str(MASTER_PATH))
        if not MERGED_PATH.exists() or MERGED_PATH.read_text(encoding="utf-8") != merged:
            drift.append(str(MERGED_PATH))
        if drift:
            print("Generated documents are out of date:")
            for path in drift:
                print(f"- {path}")
            return 1
        print("Generated documents are up to date.")
        return 0

    changed: list[str] = []
    if _write_if_changed(MASTER_PATH, master):
        changed.append(str(MASTER_PATH))
    if _write_if_changed(MERGED_PATH, merged):
        changed.append(str(MERGED_PATH))

    if changed:
        print("Updated generated documents:")
        for path in changed:
            print(f"- {path}")
    else:
        print("Generated documents already up to date.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
