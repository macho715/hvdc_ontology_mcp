#!/usr/bin/env python3
"""
Validate canonical Logi ontology core documents.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse


ROOT = Path(__file__).resolve().parent.parent
DOCS_DIR = ROOT / "docs" / "Logi ontol core doc"

CANONICAL_DOCS = [
    "NAMESPACE_REGISTRY.md",
    "CONSOLIDATED-01-core-framework-infra.md",
    "CONSOLIDATED-02-warehouse-flow.md",
    "CONSOLIDATED-03-document-ocr.md",
    "CONSOLIDATED-04-barge-bulk-cargo.md",
    "CONSOLIDATED-05-invoice-cost.md",
    "CONSOLIDATED-06-material-handling.md",
    "CONSOLIDATED-07-port-operations.md",
    "CONSOLIDATED-08-communication.md",
    "CONSOLIDATED-09-operations.md",
    "FLOW_CODE_V35_QUICK_REFERENCE.md",
    "FLOW_CODE_V35_INTEGRATION_REPORT.md",
    "CORE_DOCUMENTATION_MASTER.md",
    "LOGI_ONTOL_CORE_MERGED.md",
]

GENERATED_DOCS = [
    "CORE_DOCUMENTATION_MASTER.md",
    "LOGI_ONTOL_CORE_MERGED.md",
]

BANNED_MOSB_PHRASES = [
    "모든 자재는 mosb를 경유",
    "mosb는 모든 자재의 필수 경유지",
    "all cargo passes",
    "all cargo always passes mosb",
    "all materials pass through mosb",
]

DEPRECATED_NAMESPACES = [
    "http://samsung.com/project-logistics#",
    "http://example.com/ldg#",
    "https://example.com/hvdc#",
]

ALIAS_DOCS = {
    "NAMESPACE_REGISTRY.md",
    "FLOW_CODE_V35_INTEGRATION_REPORT.md",
    "CORE_DOCUMENTATION_MASTER.md",
    "LOGI_ONTOL_CORE_MERGED.md",
}

LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^)]+)\)")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _failures() -> list[str]:
    failures: list[str] = []

    for name in CANONICAL_DOCS:
        path = DOCS_DIR / name
        if not path.exists():
            failures.append(f"Missing canonical document: {name}")

    for name in CANONICAL_DOCS:
        path = DOCS_DIR / name
        if not path.exists():
            continue
        text = _read(path)
        if text.count("```") % 2 != 0:
            failures.append(f"Unbalanced fenced code blocks: {name}")

    for name in ["CONSOLIDATED-01-core-framework-infra.md", "CONSOLIDATED-02-warehouse-flow.md", "CONSOLIDATED-06-material-handling.md"]:
        text = _read(DOCS_DIR / name).lower()
        for phrase in BANNED_MOSB_PHRASES:
            if phrase in text:
                failures.append(f"Banned universal MOSB wording in {name}: {phrase}")

    for name in CANONICAL_DOCS:
        if name in ALIAS_DOCS:
            continue
        text = _read(DOCS_DIR / name)
        for namespace in DEPRECATED_NAMESPACES:
            if namespace in text:
                failures.append(f"Deprecated namespace in {name}: {namespace}")

    flow_doc = _read(DOCS_DIR / "CONSOLIDATED-02-warehouse-flow.md")
    for snippet in [
        "`1`: `wh=0`, `mosb=false`, `site=true`",
        "`2`: `wh>=1`, `mosb=false`, `site=true`",
        "`3`: `wh=0`, `mosb=true`, `site=true`",
        "`4`: `wh>=1`, `mosb=true`, `site=true`",
        "`5`: `(mosb=true and site=false) or (wh>=2 and mosb=false) or timestamp anomaly`",
        "`hvdc:TransportEvent`",
        "`hvdc:hasLogisticsFlowCode`",
    ]:
        if snippet not in flow_doc:
            failures.append(f"Missing canonical Flow Code snippet in CONSOLIDATED-02: {snippet}")

    for name in ["CONSOLIDATED-01-core-framework-infra.md", "CONSOLIDATED-06-material-handling.md", "FLOW_CODE_V35_QUICK_REFERENCE.md"]:
        text = _read(DOCS_DIR / name)
        if "MIR/SHU" not in text:
            failures.append(f"Missing routing canon marker in {name}: MIR/SHU")
        if "AGI/DAS" not in text:
            failures.append(f"Missing routing canon marker in {name}: AGI/DAS")
        if "Flow `3` or `4`" not in text:
            failures.append(f"Missing routing canon marker in {name}: Flow `3` or `4`")
        if "MOSB" not in text:
            failures.append(f"Missing routing canon marker in {name}: MOSB")
        onshore_ok = "Flow `1` and `2`" in text or "Flow `1` or `2`" in text
        if not onshore_ok:
            failures.append(f"Missing routing canon marker in {name}: Flow `1` and `2`")

    ocr_doc = _read(DOCS_DIR / "CONSOLIDATED-03-document-ocr.md")
    for required in [
        "FAIL Example",
        "PASS Example",
        "`MeanConf >= 0.92`",
        "`TableAcc >= 0.98`",
        "`NumericIntegrity = 1.00`",
        "`EntityMatch >= 0.98`",
        "\"ldg:hasResult\": \"FAIL\"",
        "\"ldg:hasResult\": \"PASS\"",
    ]:
        if required not in ocr_doc:
            failures.append(f"Missing OCR canonical marker: {required}")

    cost_doc = _read(DOCS_DIR / "CONSOLIDATED-05-invoice-cost.md")
    for required in [
        "`costGuardBand`",
        "`decision`",
        "AUTO_PASS",
        "HUMAN_REVIEW",
        "AUTO_REJECT",
    ]:
        if required not in cost_doc:
            failures.append(f"Missing cost-guard marker in CONSOLIDATED-05: {required}")

    comm_doc = _read(DOCS_DIR / "CONSOLIDATED-08-communication.md")
    for required in [
        "@prefix lo:",
        "xsd:dateTime",
        "Communication timestamps on the wire use `xsd:dateTime`.",
    ]:
        if required not in comm_doc:
            failures.append(f"Missing communication canonical marker: {required}")
    if "datatype time:Instant minCount 1" in comm_doc:
        failures.append("CONSOLIDATED-08 still uses time:Instant as required wire datatype")

    quick_ref = _read(DOCS_DIR / "FLOW_CODE_V35_QUICK_REFERENCE.md")
    integration = _read(DOCS_DIR / "FLOW_CODE_V35_INTEGRATION_REPORT.md")
    for text, name in [(quick_ref, "FLOW_CODE_V35_QUICK_REFERENCE.md"), (integration, "FLOW_CODE_V35_INTEGRATION_REPORT.md")]:
        for banned in ["755", "9904", "`hvdc:hasFlowCode` is the canonical", "Cases Analyzed: 755"]:
            if banned in text:
                failures.append(f"Stale or deprecated reference in {name}: {banned}")

    for name in GENERATED_DOCS:
        text = _read(DOCS_DIR / name)
        if "triple_count | `unavailable`" not in text or "case_count | `unavailable`" not in text:
            failures.append(f"Generated metadata unavailable markers missing in {name}")

    failures.extend(_check_links())
    failures.extend(_check_generated_drift())
    return failures


def _check_links() -> list[str]:
    failures: list[str] = []
    for name in CANONICAL_DOCS:
        path = DOCS_DIR / name
        text = _read(path)
        for match in LINK_PATTERN.finditer(text):
            target = match.group(1).strip()
            if not target or target.startswith("#"):
                continue
            parsed = urlparse(target)
            if parsed.scheme in {"http", "https", "mailto"}:
                continue
            target_path = unquote(parsed.path)
            resolved = (path.parent / target_path).resolve()
            if not resolved.exists():
                failures.append(f"Broken relative link in {name}: {target}")
    return failures


def _check_generated_drift() -> list[str]:
    result = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "build_logi_master.py"), "--check"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if result.returncode == 0:
        return []
    return [f"Generated master/merged drift detected: {result.stdout.strip() or result.stderr.strip()}"]


def main() -> int:
    failures = _failures()
    if failures:
        print("Logi document validation failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1
    print("Logi document validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
