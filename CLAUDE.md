# HVDC Project — Claude Code Domain Context
> Samsung C&T x ADNOC x DSV | UAE HVDC Project Logistics
> MACHO-GPT v4.3.2 | MCP: hvdc_knowledge_mcp

---

## Project Overview
- **Role**: SCM/Logistics — Invoice Audit, Customs Clearance, Marine Ops, WH Management
- **Scale**: ~400 TEU / 100 BL per month | 6 construction sites
- **Key Partners**: ADNOC L&S (ALS), DSV, JDN, Mammoet, Hitachi

---

## Node Network (8 Nodes)

| Node | Type | Customs Code | Key Rule |
|------|------|-------------|----------|
| Zayed Port (AEZYD) | Import Port | 47150 | Bulk/Heavy cargo |
| Khalifa Port | Import Port | 47150 | Container cargo |
| Jebel Ali | Import Port | 1485718 | Freezone/ADOPT |
| **MOSB** | **Central Hub** | — | **ALL cargo passes. 20,000sqm. SCT resident.** |
| MIR | Onshore Site | — | 35,006sqm. SPMT. DOT >90t |
| SHU | Onshore Site | — | 10,556sqm. SPMT. DOT >90t |
| DAS | Offshore Site | — | 20h LCT. **MOSB mandatory.** |
| AGI | Offshore Site | — | 10h LCT. **MOSB mandatory.** |

---

## Flow Code v3.5 (CRITICAL RULE)

```
0 = Pre Arrival
1 = Port -> Site (direct, no WH)
2 = Port -> WH -> Site
3 = Port -> MOSB -> Site          <- AGI/DAS: MINIMUM FLOW CODE
4 = Port -> WH -> MOSB -> Site
5 = Mixed / Waiting / Incomplete
```

**Algorithm**: `FLOW = 0 if PreArrival else clip(wh_count + offshore + 1, 1, 4)`
**AGI/DAS Rule**: Flow Code 0/1/2 -> auto-upgrade to 3 (MOSB leg mandatory)

---

## KPI Gates

| KPI | Target | Direction |
|-----|--------|-----------|
| invoice-ocr | 98% | >= |
| invoice-audit delta | 2% | <= |
| cost-guard warn rate | 5% | <= |
| hs-risk misclass | 0.5% | <= |
| cert-chk auto-pass | 90% | >= |
| wh-forecast util | 85% | <= |
| weather-tie ETA MAPE | 12% | <= |

---

## Key Regulations (UAE)

| Regulation | Requirement | Trigger | Block Action |
|-----------|-------------|---------|-------------|
| FANR | 방사선 수입허가 (60일) | 방사선 기자재 | BOE 제출 중단 |
| MOIAT ECAS | 적합성 인증 | 규제 전기제품 | DO/GatePass 발급 금지 |
| DOT | 중량물 운송 허가 | >90톤 | 이송 금지 |
| CICPA | 게이트패스 | 항만/MOSB 출입 | 출입 불가 |
| ADNOC FRA | 리프팅 위험성 평가 | LCT 선적 전 | 선적 중단 |

---

## MCP Tools (hvdc_knowledge_mcp)

| Tool | 용도 | 주요 파라미터 |
|------|------|--------------|
| `hvdc_get_domain_summary` | 전체 도메인 요약 (세션 시작 시 호출) | — |
| `hvdc_search_docs` | .md 문서 키워드 검색 | `keyword`, `max_results` |
| `hvdc_read_doc` | 특정 문서/섹션 읽기 | `filename`, `section` |
| `hvdc_list_docs` | 사용 가능한 문서 목록 | — |
| `hvdc_get_node_info` | 8개 노드 상세 정보 | `node_name` |
| `hvdc_get_flow_code` | Flow Code v3.5 조회/검증 | `code`, `destination` |
| `hvdc_get_kpi` | KPI 임계값 조회 | `kpi_name` |
| `hvdc_get_regulations` | 규제 요건 조회 | `regulation_name` |
| `hvdc_hs_code_lookup` | HS Code 조회 | `query` |

---

## Domain Documents (docs/Logi ontol core doc/)

| File | Domain |
|------|--------|
| CONSOLIDATED-01-core-framework-infra.md | 온톨로지 프레임워크 + 노드 인프라 |
| CONSOLIDATED-02-warehouse-flow.md | 창고 운영 + Flow Code 알고리즘 |
| CONSOLIDATED-03-document-ocr.md | 문서 OCR 처리 |
| CONSOLIDATED-04-barge-bulk-cargo.md | 바지/벌크 화물 |
| CONSOLIDATED-05-invoice-cost.md | 인보이스/비용 관리 |
| CONSOLIDATED-06-material-handling.md | 자재 취급 |
| CONSOLIDATED-07-port-operations.md | 항만 운영 |
| CONSOLIDATED-08-communication.md | 커뮤니케이션 |
| CONSOLIDATED-09-operations.md | 운영 관리 |
| CORE_DOCUMENTATION_MASTER.md | 마스터 문서 |
| FLOW_CODE_V35_*.md | Flow Code v3.5 참조 |
| LOGI_ONTOL_CORE_MERGED.md | 통합 온톨로지 (~469KB) |

---

## Coding Conventions

```python
# HVDC 프로젝트 Python 자동화 규칙
FLOW_CODES = {0: "Pre Arrival", 1: "Port->Site", 2: "Port->WH->Site",
              3: "Port->MOSB->Site", 4: "Port->WH->MOSB->Site", 5: "Mixed"}

KPI_THRESHOLDS = {
    "invoice_ocr": 98.0,      # >=
    "invoice_audit": 2.0,     # <= (delta %)
    "hs_risk": 0.5,           # <= (misclass %)
    "wh_util": 85.0,          # <=
    "eta_mape": 12.0,         # <=
}

NODES_OFFSHORE = {"AGI", "DAS"}   # MOSB 레그 필수
NODES_ONSHORE = {"MIR", "SHU"}    # DOT 허가 필요 (>90톤)
CUSTOMS_CODES = {"ADNOC": "47150", "ADOPT": "1485718", "DUBAI_FZ": "89901"}
```

---

## ZERO Gate Triggers (작업 중단 조건)

```
eBL 비정합          -> Berth 확정 보류
BOE 필드 미충족     -> 통관 신고 중단
FANR Permit 부재   -> 입항 승인 보류
MOSB 용량 초과     -> 추가 입고 중단 (>20,000sqm)
DOT Permit 부재    -> 이송 금지 (>90톤)
기상 경보          -> LCT 출항 연기
```

---

*이 파일은 Claude Code가 세션 시작 시 자동으로 로드합니다.*
*MCP 서버: hvdc_knowledge_mcp (server.py)*
