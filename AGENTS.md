# GENERATED FROM `config/domain_rules.yaml` — DO NOT EDIT MANUALLY
> Samsung C&T x ADNOC x DSV | UAE HVDC Project Logistics
> MCP: hvdc_knowledge_mcp

## Project Overview
- **Role**: SCM/Logistics (Invoice Audit, Customs, Marine Ops, WH Management)
- **Scale**: ~400 TEU / 100 BL per month, 6 sites
- **Key Partners**: ADNOC L&S (ALS), DSV, JDN, Mammoet, Hitachi

## Node Network (8 Nodes)
| Node | Type | Customs Code | Key Rule |
|------|------|-------------|----------|
| Zayed Port | Import Port | 47150 | Bulk/Heavy cargo |
| Khalifa Port | Import Port | 47150 | Container cargo |
| Jebel Ali | Import Port | 1485718 | Freezone / ADOPT |
| MOSB | Central Hub | — | Central hub, 20,000 sqm, SCT resident team |
| MIR | Onshore Site | — | SPMT operations, DOT > 90t |
| SHU | Onshore Site | — | SPMT operations, DOT > 90t |
| DAS | Offshore Site | — | 20h LCT, MOSB leg mandatory |
| AGI | Offshore Site | — | 10h LCT, MOSB leg mandatory |

## Flow Code v3.5 (CRITICAL RULE)
```text
0 = Pre Arrival
1 = Port -> Site (direct, no WH)
2 = Port -> WH -> Site
3 = Port -> MOSB -> Site
4 = Port -> WH -> MOSB -> Site
5 = Mixed / Waiting / Incomplete
```
**Algorithm**: `FLOW = 0 if PreArrival else clip(wh_count + offshore + 1, 1, 4)`
**AGI/DAS Rule**: Flow Code 0/1/2 -> auto-upgrade to 3 (MOSB leg mandatory)

## KPI Gates
| KPI | Target | Direction |
|-----|--------|-----------|
| invoice-ocr | 98.0% | >= |
| invoice-audit delta | 2.0% | <= |
| cost-guard warn rate | 5.0% | <= |
| hs-risk misclass | 0.5% | <= |
| cert-chk auto-pass | 90.0% | >= |
| wh-forecast util | 85.0% | <= |
| weather-tie ETA MAPE | 12.0% | <= |

## Key Regulations (UAE)
| Regulation | Requirement | Trigger | Block Action |
|-----------|-------------|---------|-------------|
| FANR | 방사선 수입허가 (60일) | 방사선 기자재 | BOE 제출 중단 |
| MOIAT_ECAS | 적합성 인증 | 규제 전기제품 | DO/GatePass 발급 금지 |
| MOIAT_EQM | 규제 제품 품질 마크 / 관련 인증 | 특정 규제 제품군 | 출고 또는 현장 반입 보류 |
| DOT | 중량물 운송 허가 | >90톤 | 이송 금지 |
| CICPA | 게이트패스 | 항만/MOSB 출입 | 출입 불가 |
| ADNOC_FRA | 리프팅 위험성 평가 | LCT 선적 전 | 선적 중단 |

## MCP Tools (hvdc_knowledge_mcp)
| Tool | 용도 | 주요 파라미터 |
|------|------|--------------|
| `hvdc_get_domain_summary` | 전체 도메인 요약 (세션 시작 시 호출) | — |
| `hvdc_search_docs` | .md 문서 키워드 검색 | `keyword, max_results` |
| `hvdc_read_doc` | 특정 문서/섹션 읽기 | `filename, section` |
| `hvdc_list_docs` | 사용 가능한 문서 목록 | — |
| `hvdc_get_node_info` | 8개 노드 상세 정보 | `node_name` |
| `hvdc_get_flow_code` | Flow Code v3.5 조회/검증 | `code, destination` |
| `hvdc_get_kpi` | KPI 임계값 조회 | `kpi_name` |
| `hvdc_get_regulations` | 규제 요건 조회 | `regulation_name` |
| `hvdc_hs_code_lookup` | HS Code 조회 | `query` |
| `hvdc_analyze_shipment_case` | 단건 shipment 판정 | `shipment 또는 file/local_path` |
| `hvdc_render_backlog_upload_widget` | ChatGPT widget 업로드 준비 | `snapshot_name, sheet_name, column_map` |
| `hvdc_analyze_backlog_batch` | CSV/XLSX backlog 분석 + snapshot 저장 | `file/local_path, snapshot_name` |
| `hvdc_zero_gate_check` | 단건 운영 컨텍스트 ZERO gate 판정 | `destination, gross_weight_tons, weather_alert, ...` |
| `hvdc_compare_snapshots` | 저장된 backlog snapshot 비교 | `baseline_snapshot, candidate_snapshot` |
| `hvdc_mcp_self_test` | local/public MCP health 및 connector freshness 점검 | `target, include_tool_calls` |

## Domain Documents (docs/Logi ontol core doc/)
| File | Domain |
|------|--------|
| AGENTS.md | HVDC logistics domain document |
| CONSOLIDATED-01-core-framework-infra.md | HVDC logistics domain document |
| CONSOLIDATED-02-warehouse-flow.md | HVDC logistics domain document |
| CONSOLIDATED-03-document-ocr.md | HVDC logistics domain document |
| CONSOLIDATED-04-barge-bulk-cargo.md | HVDC logistics domain document |
| CONSOLIDATED-05-invoice-cost.md | HVDC logistics domain document |
| CONSOLIDATED-06-material-handling-appendix-source-preserved.md | HVDC logistics domain document |
| CONSOLIDATED-06-material-handling.md | HVDC logistics domain document |
| CONSOLIDATED-07-port-operations.md | HVDC logistics domain document |
| CONSOLIDATED-08-communication.md | HVDC logistics domain document |
| CONSOLIDATED-09-operations.md | HVDC logistics domain document |
| CORE_DOCUMENTATION_MASTER.md | HVDC logistics domain document |
| FLOW_CODE_V35_INTEGRATION_REPORT.md | HVDC logistics domain document |
| FLOW_CODE_V35_QUICK_REFERENCE.md | HVDC logistics domain document |
| LOGI_ONTOL_CORE_MERGED.md | HVDC logistics domain document |
| NAMESPACE_REGISTRY.md | HVDC logistics domain document |
| agents_template.md | HVDC logistics domain document |

## Coding Conventions
```python
FLOW_CODES = {0: "Pre Arrival", 1: "Port->Site", 2: "Port->WH->Site",
              3: "Port->MOSB->Site", 4: "Port->WH->MOSB->Site", 5: "Mixed"}

KPI_THRESHOLDS = {
    "invoice_ocr": 98.0,
    "invoice_audit_delta": 2.0,
    "hs_risk_misclass": 0.5,
    "wh_forecast_util": 85.0,
    "weather_tie_eta_mape": 12.0,
}

NODES_OFFSHORE = {'AGI', 'DAS'}
NODES_ONSHORE = {'MIR', 'SHU'}
```

## ZERO Gate Triggers
```text
eBL mismatch         -> Hold berth confirmation
BOE field gaps       -> Stop customs filing
FANR permit missing  -> Hold arrival approval
MOSB capacity exceeded -> Stop additional intake (>20,000 sqm)
DOT permit missing   -> Stop inland move (>90t)
Weather alert        -> Delay LCT departure
```

*This file is generated from `config/domain_rules.yaml`.*