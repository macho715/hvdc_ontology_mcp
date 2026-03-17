from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent
DOMAIN_RULES_PATH = REPO_ROOT / "config" / "domain_rules.yaml"
DOCS_ROOT = REPO_ROOT / "docs" / "Logi ontol core doc"
README_PATH = REPO_ROOT / "README.md"
AGENTS_PATH = REPO_ROOT / "AGENTS.md"
CURSOR_RULE_PATH = REPO_ROOT / ".cursor" / "rules" / "hvdc-domain-background.mdc"
README_GENERATED_START = "<!-- GENERATED_DOMAIN_ONE_PAGER:START -->"
README_GENERATED_END = "<!-- GENERATED_DOMAIN_ONE_PAGER:END -->"
GENERATED_NOTICE = "<!-- generated from config/domain_rules.yaml; do not edit manually -->"

MCP_TOOL_ROWS = [
    ("hvdc_get_domain_summary", "전체 도메인 요약 (세션 시작 시 호출)", "—"),
    ("hvdc_search_docs", ".md 문서 키워드 검색", "keyword, max_results"),
    ("hvdc_read_doc", "특정 문서/섹션 읽기", "filename, section"),
    ("hvdc_list_docs", "사용 가능한 문서 목록", "—"),
    ("hvdc_get_node_info", "8개 노드 상세 정보", "node_name"),
    ("hvdc_get_flow_code", "Flow Code v3.5 조회/검증", "code, destination"),
    ("hvdc_get_kpi", "KPI 임계값 조회", "kpi_name"),
    ("hvdc_get_regulations", "규제 요건 조회", "regulation_name"),
    ("hvdc_hs_code_lookup", "HS Code 조회", "query"),
    ("hvdc_analyze_shipment_case", "단건 shipment 판정", "shipment 또는 file/local_path"),
    ("hvdc_render_backlog_upload_widget", "ChatGPT widget 업로드 준비", "snapshot_name, sheet_name, column_map"),
    ("hvdc_analyze_backlog_batch", "CSV/XLSX backlog 분석 + snapshot 저장", "file/local_path, snapshot_name"),
    ("hvdc_zero_gate_check", "단건 운영 컨텍스트 ZERO gate 판정", "destination, gross_weight_tons, weather_alert, ..."),
    ("hvdc_compare_snapshots", "저장된 backlog snapshot 비교", "baseline_snapshot, candidate_snapshot"),
    ("hvdc_mcp_self_test", "local/public MCP health 및 connector freshness 점검", "target, include_tool_calls"),
]


@lru_cache(maxsize=1)
def load_domain_rules() -> dict[str, Any]:
    return yaml.safe_load(DOMAIN_RULES_PATH.read_text(encoding="utf-8"))


def doc_markdown_files() -> list[str]:
    if not DOCS_ROOT.exists():
        return []
    return sorted(path.name for path in DOCS_ROOT.glob("*.md"))


def _bullet_rows(items: list[str], *, prefix: str = "- ") -> list[str]:
    return [f"{prefix}{item}" for item in items]


def _format_flow_code_rows(rules: dict[str, Any]) -> list[str]:
    return [f"- `{row['code']}`: {row['description']}" for row in rules["flow_codes"]]


def _format_kpi_rows(rules: dict[str, Any]) -> list[str]:
    return [
        f"- `{row['label']} {row['direction']} {row['threshold']}{row['unit']}`"
        for row in rules["kpi_gates"]
    ]


def _format_zero_gate_rows(rules: dict[str, Any]) -> list[str]:
    return [f"- {row['name']} -> {row['action']}" for row in rules["zero_gates"]]


def _python_set_literal(values: list[str]) -> str:
    rendered = ", ".join(repr(value) for value in sorted(values))
    return "{" + rendered + "}"


def render_domain_summary_markdown(
    rules: dict[str, Any] | None = None,
    *,
    docs: list[str] | None = None,
) -> str:
    rules = rules or load_domain_rules()
    docs = docs or doc_markdown_files()
    project = rules["project"]
    overrides = rules["overrides"]
    regulations = rules["regulations"]

    node_rows = ["| Node | Type | Key Info |", "|------|------|----------|"]
    for node in rules["nodes"]:
        info = node["summary"]
        if node.get("customs_code"):
            info = f"{info}, customs {node['customs_code']}"
        node_rows.append(f"| {node['name']} | {node['type']} | {info} |")

    regulation_lines = [
        f"- **{name}**: {details['requirement']}"
        for name, details in regulations.items()
    ]

    return "\n".join(
        [
            "# HVDC Project Domain Summary",
            "## Project",
            f"- **Client**: {project['client']}",
            f"- **Role**: {project['role']}",
            f"- **Scale**: {project['scale']}",
            "",
            "## Node Network (8 nodes)",
            *node_rows,
            "",
            "## Flow Code v3.5",
            "| Code | Description |",
            "|------|-------------|",
            *[
                f"| {row['code']} | {row['description']} |"
                for row in rules["flow_codes"]
            ],
            "",
            f"**Algorithm**: {rules['flow_algorithm']['formula']}",
            f"**AGI/DAS Rule**: Flow Code 0/1/2 -> auto-upgrade to {overrides['minimum_offshore_flow_code']} (MOSB leg mandatory)",
            f"**MOSB Rule**: {overrides['wording']['mosb']} {overrides['wording']['onshore']}",
            f"**DOT Rule**: MIR/SHU require DOT only when gross weight > {overrides['dot_threshold_tons']} tons.",
            "",
            "## KPI Gates",
            "| KPI | Target | Direction |",
            "|-----|--------|-----------|",
            *[
                f"| {row['label']} | {row['threshold']}{row['unit']} | {row['direction']} |"
                for row in rules["kpi_gates"]
            ],
            "",
            "## Key Regulations",
            *regulation_lines,
            "",
            f"## Available Domain Docs ({len(docs)} files)",
            *(_bullet_rows(docs) if docs else ["- docs/ 폴더에 .md 파일을 추가하세요"]),
            "",
            "## Ontology Standards",
            ", ".join(rules["ontology_standards"]),
        ]
    )


def render_readme_one_pager(rules: dict[str, Any] | None = None) -> str:
    rules = rules or load_domain_rules()
    overrides = rules["overrides"]
    regulations = rules["regulations"]
    node_lines = []
    for node in rules["nodes"]:
        label = node["name"]
        if node.get("locode"):
            label = f"{label} (`{node['locode']}`)"
        node_lines.append(f"- {label}: {node['summary']}")

    regulation_lines = [
        f"- `{name}`: {details['requirement']}"
        for name, details in regulations.items()
    ]

    return "\n".join(
        [
            GENERATED_NOTICE,
            "",
            "이 섹션은 Cursor/Agent가 읽을 배경지식과 사람이 구현 규칙을 빠르게 확인하는 용도로 씁니다.",
            "",
            f"- Scope: {rules['project']['role']}",
            f"- Scale: {rules['project']['scale']}",
            "- Sites: MIR, SHU, DAS, AGI plus import ports and MOSB hub",
            "",
            "Core nodes:",
            "",
            *node_lines,
            "",
            "Flow Code v3.5:",
            "",
            *_format_flow_code_rows(rules),
            "",
            "Flow calculation rule:",
            "",
            f"- `{rules['flow_algorithm']['formula']}`",
            f"- `wh_count` means {rules['flow_algorithm']['wh_count_note']}",
            f"- `offshore = {rules['flow_algorithm']['offshore_note']}`",
            "",
            "Mandatory flow overrides:",
            "",
            f"- If destination is `AGI` or `DAS`, Flow Code `0`, `1`, or `2` must be upgraded to `{overrides['minimum_offshore_flow_code']}`",
            f"- For `AGI` and `DAS`, `Flow < {overrides['minimum_offshore_flow_code']}` is invalid",
            "- Valid offshore paths are typically `3` and `4`",
            "",
            "MOSB interpretation:",
            "",
            f"- {overrides['wording']['mosb']}",
            "- Do not hardcode \"all cargo always passes MOSB\" as a universal rule",
            f"- {overrides['wording']['onshore']}",
            "- Enforce MOSB strictly for `AGI` and `DAS`",
            "",
            "Onshore transport rule:",
            "",
            "- `MIR` and `SHU` are onshore SPMT destinations",
            f"- `DOT` approval is required only when cargo weight is greater than `{overrides['dot_threshold_tons']} tons`",
            "- Do not block all MIR/SHU movements by default; block only `> 90t` cases without DOT approval",
            "",
            "Regulatory gates:",
            "",
            *regulation_lines,
            "",
            "ZERO gate triggers:",
            "",
            *_format_zero_gate_rows(rules),
            "",
            "KPI gates:",
            "",
            *_format_kpi_rows(rules),
            "",
            "Coding constants:",
            "",
            f"- Offshore nodes: `{', '.join(overrides['offshore_sites'])}`",
            f"- Onshore nodes: `{', '.join(overrides['onshore_sites'])}`",
            f"- MOSB capacity: `{overrides['mosb_capacity_sqm']:,} sqm`",
            f"- DOT threshold: `{overrides['dot_threshold_tons']} tons`",
            f"- AGI/DAS minimum flow: `{overrides['minimum_offshore_flow_code']}`",
            "",
            "Safe implementation rules:",
            "",
            f"- Never infer DOT requirement unless weight is known and `> {overrides['dot_threshold_tons']}`",
            "- Never allow `AGI` or `DAS` to remain on Flow `0`, `1`, or `2`",
            "- Treat missing regulatory evidence as `not_evaluated` or `blocked`, not implicit pass",
            "- Keep `MOIAT_ECAS` and `MOIAT_EQM` separable in code even if documentation sometimes groups them",
            "- Distinguish summary wording from enforced logic; enforce only explicit rules",
            "",
            "MCP usage pattern:",
            "",
            "- Call `hvdc_get_domain_summary` at session start for baseline context",
            "- Use `hvdc_get_flow_code` for flow validation",
            "- Use `hvdc_get_node_info` for node-specific constraints",
            "- Use `hvdc_get_kpi` for threshold lookup",
            "- Use `hvdc_get_regulations` for permit and block actions",
            "- Use `hvdc_search_docs` or `hvdc_read_doc` for detailed evidence before making abnormality judgments",
            "",
            "Practical decision rule:",
            "",
            "- If a shipment is for `AGI` or `DAS`, first validate MOSB leg and Flow Code",
            "- If a shipment is for `MIR` or `SHU`, first validate gross weight and DOT threshold",
            "- If evidence for permits, BOE, eBL, or weather is missing, do not return a clean pass",
        ]
    )


def render_agents_md(rules: dict[str, Any] | None = None) -> str:
    rules = rules or load_domain_rules()
    project = rules["project"]
    overrides = rules["overrides"]
    docs = doc_markdown_files()

    node_rows = ["| Node | Type | Customs Code | Key Rule |", "|------|------|-------------|----------|"]
    for node in rules["nodes"]:
        code = node.get("customs_code", "—")
        node_rows.append(f"| {node['name']} | {node['type']} | {code} | {node['summary']} |")

    regulation_rows = ["| Regulation | Requirement | Trigger | Block Action |", "|-----------|-------------|---------|-------------|"]
    for name, details in rules["regulations"].items():
        regulation_rows.append(
            f"| {name} | {details['requirement']} | {details['trigger']} | {details['block_action']} |"
        )

    doc_rows = ["| File | Domain |", "|------|--------|"]
    for filename in docs:
        doc_rows.append(f"| {filename} | HVDC logistics domain document |")

    tool_rows = ["| Tool | 용도 | 주요 파라미터 |", "|------|------|--------------|"]
    for name, usage, params in MCP_TOOL_ROWS:
        rendered_params = "—" if params == "—" else f"`{params}`"
        tool_rows.append(f"| `{name}` | {usage} | {rendered_params} |")

    return "\n".join(
        [
            "# GENERATED FROM `config/domain_rules.yaml` — DO NOT EDIT MANUALLY",
            f"> {project['client'].replace(', UAE HVDC Project', '')} | UAE HVDC Project Logistics",
            "> MCP: hvdc_knowledge_mcp",
            "",
            "## Project Overview",
            f"- **Role**: {project['role']}",
            f"- **Scale**: {project['scale']}",
            f"- **Key Partners**: {', '.join(project['key_partners'])}",
            "",
            "## Node Network (8 Nodes)",
            *node_rows,
            "",
            "## Flow Code v3.5 (CRITICAL RULE)",
            "```text",
            *[f"{row['code']} = {row['description']}" for row in rules["flow_codes"]],
            "```",
            f"**Algorithm**: `{rules['flow_algorithm']['formula']}`",
            f"**AGI/DAS Rule**: Flow Code 0/1/2 -> auto-upgrade to {overrides['minimum_offshore_flow_code']} (MOSB leg mandatory)",
            "",
            "## KPI Gates",
            "| KPI | Target | Direction |",
            "|-----|--------|-----------|",
            *[
                f"| {row['label']} | {row['threshold']}{row['unit']} | {row['direction']} |"
                for row in rules["kpi_gates"]
            ],
            "",
            "## Key Regulations (UAE)",
            *regulation_rows,
            "",
            "## MCP Tools (hvdc_knowledge_mcp)",
            *tool_rows,
            "",
            "## Domain Documents (docs/Logi ontol core doc/)",
            *doc_rows,
            "",
            "## Coding Conventions",
            "```python",
            'FLOW_CODES = {0: "Pre Arrival", 1: "Port->Site", 2: "Port->WH->Site",',
            '              3: "Port->MOSB->Site", 4: "Port->WH->MOSB->Site", 5: "Mixed"}',
            "",
            "KPI_THRESHOLDS = {",
            '    "invoice_ocr": 98.0,',
            '    "invoice_audit_delta": 2.0,',
            '    "hs_risk_misclass": 0.5,',
            '    "wh_forecast_util": 85.0,',
            '    "weather_tie_eta_mape": 12.0,',
            "}",
            "",
            f'NODES_OFFSHORE = {_python_set_literal(overrides["offshore_sites"])}',
            f'NODES_ONSHORE = {_python_set_literal(overrides["onshore_sites"])}',
            "```",
            "",
            "## ZERO Gate Triggers",
            "```text",
            *[f"{row['name']:<20} -> {row['action']}" for row in rules["zero_gates"]],
            "```",
            "",
            "*This file is generated from `config/domain_rules.yaml`.*",
        ]
    )


def render_cursor_rule_mdc(rules: dict[str, Any] | None = None) -> str:
    rules = rules or load_domain_rules()
    overrides = rules["overrides"]
    return "\n".join(
        [
            "---",
            "description: HVDC UAE logistics domain background and MCP usage rules for Cursor",
            "alwaysApply: true",
            "---",
            "",
            "<!-- generated from config/domain_rules.yaml; do not edit manually -->",
            "",
            f"- Treat this repository as {rules['project']['client']} logistics software.",
            "- Domain-critical rules must not be invented when the repo docs or MCP can verify them.",
            "- Core flow constraints:",
            f"  - AGI and DAS are offshore destinations and require MOSB. Minimum Flow Code is {overrides['minimum_offshore_flow_code']}.",
            f"  - MIR and SHU are onshore heavy-cargo sites and require DOT approval for cargo above {overrides['dot_threshold_tons']} tons.",
            f"  - MOSB is the central hub and has a {overrides['mosb_capacity_sqm']:,} sqm capacity limit.",
            "- ZERO gate blockers:",
            *[f"  - {row['name']}" for row in rules["zero_gates"]],
            "- When editing or reviewing code related to shipment routing, backlog analysis, KPI checks, regulations, customs, or ZERO logic, use the `hvdc-knowledge` MCP server before changing behavior.",
            "- Prefer these MCP tools by intent:",
            "  - `hvdc_get_domain_summary` for fast domain refresh",
            "  - `hvdc_get_flow_code` and `hvdc_get_node_info` for routing and node rules",
            "  - `hvdc_get_kpi` and `hvdc_get_regulations` for policy thresholds",
            "  - `hvdc_analyze_shipment_case`, `hvdc_analyze_backlog_batch`, `hvdc_zero_gate_check`, and `hvdc_compare_snapshots` for operational reasoning",
            "- Prefer these source documents when MCP needs deeper evidence:",
            "  - `docs/Logi ontol core doc/CONSOLIDATED-01-core-framework-infra.md`",
            "  - `docs/Logi ontol core doc/CONSOLIDATED-02-warehouse-flow.md`",
            "  - `docs/Logi ontol core doc/CONSOLIDATED-09-operations.md`",
            "  - `docs/Logi ontol core doc/FLOW_CODE_V35_QUICK_REFERENCE.md`",
            "  - `AGENTS.md`",
        ]
    )


def replace_readme_generated_section(readme_text: str, generated_section: str) -> str:
    start = readme_text.find(README_GENERATED_START)
    end = readme_text.find(README_GENERATED_END)
    if start == -1 or end == -1 or end < start:
        raise ValueError("README generated section markers are missing.")
    start_content = start + len(README_GENERATED_START)
    return f"{readme_text[:start_content]}\n\n{generated_section}\n\n{readme_text[end:]}"
