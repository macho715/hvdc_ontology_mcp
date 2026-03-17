# LOGI_ONTOL_CORE_MERGED

Merged canonical document bundle generated from curated source documents.

<!-- GENERATED FILE: do not edit manually. Rebuild with scripts/build_logi_master.py -->

| Field | Value |
|---|---|
| generated_at | 2026-03-13T20:15:57.222499+00:00 |
| source_commit | `da7b1a3` |
| file_hash | `470525d8f19eb922c2a7bda66907e7ccd4f2d8c2445b2ac23ce1c3408464361b` |
| measurement_status | `source-dataset-unavailable` |
| triple_count | `unavailable` |
| case_count | `unavailable` |

## Included Sources

- `NAMESPACE_REGISTRY.md`
- `CONSOLIDATED-01-core-framework-infra.md`
- `CONSOLIDATED-02-warehouse-flow.md`
- `CONSOLIDATED-03-document-ocr.md`
- `CONSOLIDATED-04-barge-bulk-cargo.md`
- `CONSOLIDATED-05-invoice-cost.md`
- `CONSOLIDATED-06-material-handling.md`
- `CONSOLIDATED-07-port-operations.md`
- `CONSOLIDATED-08-communication.md`
- `CONSOLIDATED-09-operations.md`

---

## SOURCE: NAMESPACE_REGISTRY.md

# NAMESPACE_REGISTRY

Canonical namespace registry for the HVDC Logi ontology bundle.

This file is normative for examples, SHACL snippets, JSON-LD contexts, and SPARQL queries in the curated documentation set.

## Canonical Prefixes

| Prefix | Canonical IRI | Scope |
|---|---|---|
| `hvdc` | `https://hvdc-project.com/ontology/core/` | Core logistics entities, TransportEvent, shared operational properties |
| `mh` | `https://hvdc-project.com/ontology/material-handling/` | Material-handling domain |
| `debulk` | `https://hvdc-project.com/ontology/bulk-cargo/` | Barge / bulk cargo domain |
| `port` | `https://hvdc-project.com/ontology/port-operations/` | Port-operations domain |
| `ldg` | `https://hvdc-project.com/ontology/document-guardian/` | Document guardian / OCR domain |
| `lo` | `https://hvdc-project.com/ontology/communication/` | Communication domain |
| `ops` | `https://hvdc-project.com/ontology/operations/` | Operations reporting / KPI domain |

## Canonical Usage Rules

- Use `hvdc:TransportEvent` as the primary operational event class in canonical examples.
- Use `hvdc:hasLogisticsFlowCode` as the canonical final Flow Code property.
- Use `hvdc:hasFlowCodeOriginal` only to preserve the pre-upgrade Flow Code value.
- Use `xsd:dateTime` for wire/example timestamps in Markdown and SPARQL examples.
- Use domain-specific prefixes such as `mh:`, `debulk:`, `port:`, `ldg:`, `lo:`, and `ops:` only when the example is truly domain-specific.

## Deprecated Aliases

These identifiers may appear in historical documents or preserved appendix material, but they are not canonical for new examples.

| Deprecated Identifier | Replacement | Status |
|---|---|---|
| `http://samsung.com/project-logistics#` | `https://hvdc-project.com/ontology/core/` | Deprecated legacy core namespace |
| `http://example.com/ldg#` | `https://hvdc-project.com/ontology/document-guardian/` | Deprecated sample namespace |
| `https://example.com/hvdc#` | `https://hvdc-project.com/ontology/core/` | Deprecated sample namespace |
| bare `:` communication examples | `lo:` | Deprecated example style |
| `hvdc:hasFlowCode` | `hvdc:hasLogisticsFlowCode` | Deprecated legacy / derived alias |
| `hvdc:LogisticsFlow` | `hvdc:TransportEvent` + flow properties | Deprecated legacy / derived class reference |

## Alias Mapping Notes

- `mh:hasLogisticsFlowCode` is a domain-specific equivalent of `hvdc:hasLogisticsFlowCode`.
- `debulk:hasLogisticsFlowCode` is a domain-specific equivalent of `hvdc:hasLogisticsFlowCode`.
- `port:assignedFlowCode` is the port-stage initial Flow Code assignment and is not the canonical final flow property.
- `ldg:extractedFlowCode` is the OCR-extracted value and is not the canonical final flow property.

## Example Prefix Block

```turtle
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .
@prefix mh: <https://hvdc-project.com/ontology/material-handling/> .
@prefix debulk: <https://hvdc-project.com/ontology/bulk-cargo/> .
@prefix port: <https://hvdc-project.com/ontology/port-operations/> .
@prefix ldg: <https://hvdc-project.com/ontology/document-guardian/> .
@prefix lo: <https://hvdc-project.com/ontology/communication/> .
@prefix ops: <https://hvdc-project.com/ontology/operations/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
```

## Maintenance Rule

When a namespace or alias policy changes:

1. Update this registry first.
2. Update the curated documents that use the affected prefix.
3. Rebuild `CORE_DOCUMENTATION_MASTER.md` and `LOGI_ONTOL_CORE_MERGED.md`.
4. Run `python scripts/validate_logi_docs.py`.

---

## SOURCE: CONSOLIDATED-01-core-framework-infra.md

# CONSOLIDATED-01 — Core Framework / Infrastructure

Canonical infrastructure and routing policy for the HVDC logistics ontology bundle.

See also:
- [NAMESPACE_REGISTRY.md](NAMESPACE_REGISTRY.md)
- [CONSOLIDATED-02-warehouse-flow.md](CONSOLIDATED-02-warehouse-flow.md)
- [flow-code-v35-schema.ttl](flow-code-v35-schema.ttl)

## 1. Scope

This document defines the canonical node network, routing policy, and core operational constraints for the Samsung C&T x ADNOC x DSV HVDC UAE logistics program.

The objective is to keep the infrastructure narrative aligned with the executable Flow Code and validation rules.

## 2. Canonical Node Network

| Node | Type | Code | Notes |
|---|---|---|---|
| Zayed Port | Import Port | `AEZYD` / customs `47150` | Bulk and heavy cargo entry |
| Khalifa Port | Import Port | `AEAUH` / customs `47150` | Container cargo entry |
| Jebel Ali | Import Port | `AEJEA` / customs `1485718` | Freezone / ADOPT path |
| MOSB | Central Hub | - | Central hub, 20,000 sqm, SCT resident team |
| MIR | Onshore Site | - | Onshore site, SPMT, DOT required only if `>90t` |
| SHU | Onshore Site | - | Onshore site, SPMT, DOT required only if `>90t` |
| DAS | Offshore Site | - | LCT route, MOSB mandatory |
| AGI | Offshore Site | - | LCT route, MOSB mandatory |

## 3. Canonical Routing Policy

### 3.1 Core rule

- MOSB is the central hub and has a `20,000 sqm` capacity limit.
- MOSB is mandatory for offshore destinations `AGI` and `DAS`.
- Direct and non-MOSB flows remain valid for onshore cases unless another rule blocks them.

### 3.2 Allowed destination patterns

| Destination group | Allowed patterns | Flow expectation |
|---|---|---|
| `MIR`, `SHU` | `Port -> Site`, `Port -> WH -> Site`, `Port -> MOSB -> Site`, `Port -> WH -> MOSB -> Site` | Flow `1`, `2`, `3`, or `4` depending on actual legs |
| `AGI`, `DAS` | `Port -> MOSB -> Site`, `Port -> WH -> MOSB -> Site` | Flow `3` or `4` only |

### 3.3 Operational guardrails

- `AGI/DAS`: a MOSB leg is non-optional because offshore transport requires LCT dispatch from MOSB.
- `MIR/SHU`: a MOSB leg may exist, but it is not mandatory by default.
- `DOT`: apply only when `gross_weight_tons > 90`.
- `MOSB capacity`: if current MOSB utilization exceeds `20,000 sqm`, hold additional intake and re-sequence dispatch.

## 4. Core Regulatory Constraints

| Regulation | Trigger | Block Action |
|---|---|---|
| `FANR` | Radiation-related cargo | Hold BOE filing / arrival approval |
| `MOIAT_ECAS` | Regulated electrical products | Hold DO / GatePass issuance |
| `MOIAT_EQM` | Specific regulated product classes | Hold release to site |
| `DOT` | Cargo `>90t` | Stop inland movement |
| `CICPA` | Port / MOSB access | Deny entry |
| `ADNOC_FRA` | LCT lifting / offshore load-out | Stop loading |

## 5. Canonical Flow Alignment

This document does not define Flow Code independently. The authoritative Flow Code source is:

- [CONSOLIDATED-02-warehouse-flow.md](CONSOLIDATED-02-warehouse-flow.md)

Infrastructure documents must stay aligned with these business outcomes:

- `MIR/SHU` allow Flow `1` and `2`.
- `AGI/DAS` require Flow `3` or `4`.
- `Flow 5` is a review state for mixed, incomplete, or anomalous routing.

## 6. Canonical Ontology Model

### 6.1 Core class / property pairing

- Primary operational event class: `hvdc:TransportEvent`
- Canonical final Flow property: `hvdc:hasLogisticsFlowCode`
- Original/pre-upgrade property: `hvdc:hasFlowCodeOriginal`

### 6.2 Deprecated references

- `hvdc:hasFlowCode` is a deprecated legacy / derived alias.
- `hvdc:LogisticsFlow` is a deprecated legacy / derived class reference.
- New canonical examples in this bundle must use `hvdc:TransportEvent` + `hvdc:hasLogisticsFlowCode`.

## 7. JSON-LD Infrastructure Example

```json
{
  "@context": {
    "hvdc": "https://hvdc-project.com/ontology/core/",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
  },
  "@id": "hvdc:event-agi-0001",
  "@type": "hvdc:TransportEvent",
  "hvdc:hasCase": "HE-208221",
  "hvdc:hasDate": {
    "@value": "2025-05-13T08:00:00+04:00",
    "@type": "xsd:dateTime"
  },
  "hvdc:hasOriginPort": "Khalifa Port",
  "hvdc:hasFinalLocation": "AGI",
  "hvdc:hasWarehouseCount": 0,
  "hvdc:hasMOSBLeg": true,
  "hvdc:hasSiteArrival": true,
  "hvdc:hasLogisticsFlowCode": 3,
  "hvdc:requiresMOSBLeg": true,
  "hvdc:hasFlowDescription": "Port -> MOSB -> Site"
}
```

## 8. SHACL Snippets

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .

hvdc:CoreTransportEventShape a sh:NodeShape ;
  sh:targetClass hvdc:TransportEvent ;
  sh:property [
    sh:path hvdc:hasLogisticsFlowCode ;
    sh:datatype xsd:integer ;
    sh:minInclusive 0 ;
    sh:maxInclusive 5 ;
    sh:minCount 1 ;
    sh:message "TransportEvent must carry Flow Code 0..5."
  ] ;
  sh:property [
    sh:path hvdc:hasFinalLocation ;
    sh:datatype xsd:string ;
    sh:minCount 1 ;
    sh:message "TransportEvent must declare the final destination."
  ] .

hvdc:OffshoreMOSBConstraint a sh:NodeShape ;
  sh:targetClass hvdc:TransportEvent ;
  sh:sparql [
    sh:message "AGI/DAS destinations require MOSB and Flow 3 or 4." ;
    sh:select """
      PREFIX hvdc: <https://hvdc-project.com/ontology/core/>
      SELECT $this
      WHERE {
        $this hvdc:hasFinalLocation ?dest ;
              hvdc:hasLogisticsFlowCode ?flow ;
              hvdc:hasMOSBLeg ?mosb .
        FILTER(?dest IN ("AGI", "DAS"))
        FILTER(?flow < 3 || ?mosb = false)
      }
    """
  ] .
```

## 9. Infrastructure QA Checklist

- Confirm the node network still distinguishes `onshore` and `offshore` delivery models.
- Confirm MOSB wording does not imply universal mandatory routing.
- Confirm `DOT` is described only for `>90t`.
- Confirm all examples use canonical namespaces from [NAMESPACE_REGISTRY.md](NAMESPACE_REGISTRY.md).

## 10. Canonical Conclusion

The core infrastructure model is:

- `MOSB` is central, but not universally mandatory.
- `AGI/DAS` are offshore destinations with required MOSB staging.
- `MIR/SHU` remain valid onshore destinations for direct and warehouse-assisted delivery paths.
- Routing semantics must be implemented through the canonical Flow Code definitions in [CONSOLIDATED-02-warehouse-flow.md](CONSOLIDATED-02-warehouse-flow.md).

---

## SOURCE: CONSOLIDATED-02-warehouse-flow.md

# CONSOLIDATED-02 — Warehouse / Flow Code

Canonical Flow Code v3.5 specification for the HVDC logistics ontology bundle.

This is the authoritative narrative/spec source for routing semantics. Other documents may summarize Flow Code behavior, but they must not redefine it independently.

See also:
- [NAMESPACE_REGISTRY.md](NAMESPACE_REGISTRY.md)
- [flow-code-v35-schema.ttl](flow-code-v35-schema.ttl)
- [FLOW_CODE_V35_QUICK_REFERENCE.md](FLOW_CODE_V35_QUICK_REFERENCE.md)

## 1. Canonical Event / Property Model

- Primary operational class: `hvdc:TransportEvent`
- Primary final Flow property: `hvdc:hasLogisticsFlowCode`
- Original/pre-upgrade property: `hvdc:hasFlowCodeOriginal`

Deprecated aliases:

- `hvdc:hasFlowCode` is a deprecated legacy / derived alias.
- `hvdc:LogisticsFlow` is a deprecated legacy / derived class reference.

## 2. Canonical Routing Outcomes

- `MIR/SHU` allow Flow `1` and `2`.
- `AGI/DAS` require Flow `3` or `4`.
- `AGI/DAS` with input Flow `0`, `1`, or `2` must be upgraded to `3`.
- `Flow 5` is a review state and must never be used as a substitute for a valid completed offshore route.

## 3. Canonical Flow Code Definitions

### 3.1 Business labels

| Code | Label | Canonical pattern |
|---|---|---|
| `0` | Pre Arrival | Planning state, site arrival not yet valid |
| `1` | Direct | `Port -> Site` |
| `2` | WH | `Port -> WH -> Site` |
| `3` | MOSB | `Port -> MOSB -> Site` |
| `4` | Full | `Port -> WH -> MOSB -> Site` |
| `5` | Mixed / Review | Incomplete, mixed, or anomalous route state |

### 3.2 Canonical state model

- `0`: pre-arrival
- `1`: `wh=0`, `mosb=false`, `site=true`
- `2`: `wh>=1`, `mosb=false`, `site=true`
- `3`: `wh=0`, `mosb=true`, `site=true`
- `4`: `wh>=1`, `mosb=true`, `site=true`
- `5`: `(mosb=true and site=false) or (wh>=2 and mosb=false) or timestamp anomaly`

## 4. Canonical Algorithm

### 4.1 Base formula

`FLOW = 0 if PreArrival else clip(wh_count + offshore + 1, 1, 4)`

Where:

- `wh_count` = warehouse legs excluding MOSB
- `offshore` = `1` if a MOSB leg exists, otherwise `0`

### 4.2 Canonical decision procedure

```python
def classify_flow(*, pre_arrival: bool, wh_count: int, mosb: bool, site: bool, destination: str, timestamp_anomaly: bool) -> int:
    if pre_arrival:
        flow = 0
    elif timestamp_anomaly:
        flow = 5
    elif mosb and not site:
        flow = 5
    elif wh_count >= 2 and not mosb:
        flow = 5
    else:
        if wh_count == 0 and not mosb and site:
            flow = 1
        elif wh_count >= 1 and not mosb and site:
            flow = 2
        elif wh_count == 0 and mosb and site:
            flow = 3
        elif wh_count >= 1 and mosb and site:
            flow = 4
        else:
            flow = 5

    if destination in {"AGI", "DAS"} and flow in {0, 1, 2}:
        return 3
    return flow
```

### 4.3 Mandatory offshore override

- If destination is `AGI` or `DAS`, Flow `<3` is invalid as a final state.
- Preserve the original value in `hvdc:hasFlowCodeOriginal`.
- Record the reason in `hvdc:hasFlowOverrideReason`.

## 5. Canonical JSON-LD Example

```json
{
  "@context": {
    "hvdc": "https://hvdc-project.com/ontology/core/",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
  },
  "@id": "hvdc:event-mir-0007",
  "@type": "hvdc:TransportEvent",
  "hvdc:hasCase": "MIR-2025-0007",
  "hvdc:hasDate": {
    "@value": "2025-10-31T14:23:00+04:00",
    "@type": "xsd:dateTime"
  },
  "hvdc:hasFinalLocation": "MIR",
  "hvdc:hasWarehouseCount": 1,
  "hvdc:hasMOSBLeg": false,
  "hvdc:hasSiteArrival": true,
  "hvdc:hasLogisticsFlowCode": 2
}
```

## 6. Canonical SHACL Rules

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .

hvdc:TransportEventShape a sh:NodeShape ;
  sh:targetClass hvdc:TransportEvent ;
  sh:property [
    sh:path hvdc:hasLogisticsFlowCode ;
    sh:datatype xsd:integer ;
    sh:minInclusive 0 ;
    sh:maxInclusive 5 ;
    sh:minCount 1 ;
    sh:message "Flow Code must be 0..5."
  ] ;
  sh:property [
    sh:path hvdc:hasWarehouseCount ;
    sh:datatype xsd:integer ;
    sh:minInclusive 0 ;
    sh:message "Warehouse count must be non-negative."
  ] .

hvdc:AGIDASConstraint a sh:NodeShape ;
  sh:targetClass hvdc:TransportEvent ;
  sh:sparql [
    sh:message "AGI/DAS must use Flow 3 or 4." ;
    sh:select """
      PREFIX hvdc: <https://hvdc-project.com/ontology/core/>
      SELECT $this
      WHERE {
        $this hvdc:hasFinalLocation ?dest ;
              hvdc:hasLogisticsFlowCode ?flow .
        FILTER(?dest IN ("AGI", "DAS") && ?flow < 3)
      }
    """
  ] .

hvdc:Flow5ReviewConstraint a sh:NodeShape ;
  sh:targetClass hvdc:TransportEvent ;
  sh:sparql [
    sh:message "Flow 5 cases must carry an explicit review reason." ;
    sh:select """
      PREFIX hvdc: <https://hvdc-project.com/ontology/core/>
      SELECT $this
      WHERE {
        $this hvdc:hasLogisticsFlowCode 5 .
        FILTER NOT EXISTS { $this hvdc:requiresReview ?flag }
      }
    """
  ] .

hvdc:OverrideReasonConstraint a sh:NodeShape ;
  sh:targetClass hvdc:TransportEvent ;
  sh:sparql [
    sh:message "When the original Flow Code is changed, an override reason is required." ;
    sh:select """
      PREFIX hvdc: <https://hvdc-project.com/ontology/core/>
      SELECT $this
      WHERE {
        $this hvdc:hasFlowCodeOriginal ?original ;
              hvdc:hasLogisticsFlowCode ?final .
        FILTER(?original != ?final)
        FILTER NOT EXISTS { $this hvdc:hasFlowOverrideReason ?reason }
      }
    """
  ] .
```

## 7. Canonical SPARQL Examples

### 7.1 AGI/DAS compliance

```sparql
PREFIX hvdc: <https://hvdc-project.com/ontology/core/>

SELECT ?event ?caseCode ?dest ?flow
WHERE {
  ?event a hvdc:TransportEvent ;
         hvdc:hasCase ?caseCode ;
         hvdc:hasFinalLocation ?dest ;
         hvdc:hasLogisticsFlowCode ?flow .
  FILTER(?dest IN ("AGI", "DAS") && ?flow < 3)
}
ORDER BY ?caseCode
```

### 7.2 Flow 5 review queue

```sparql
PREFIX hvdc: <https://hvdc-project.com/ontology/core/>

SELECT ?event ?caseCode
WHERE {
  ?event a hvdc:TransportEvent ;
         hvdc:hasCase ?caseCode ;
         hvdc:hasLogisticsFlowCode 5 .
}
ORDER BY ?caseCode
```

## 8. Cross-Domain Mapping Notes

- `mh:hasLogisticsFlowCode` is a material-handling equivalent of `hvdc:hasLogisticsFlowCode`.
- `debulk:hasLogisticsFlowCode` is a bulk-cargo equivalent of `hvdc:hasLogisticsFlowCode`.
- `port:assignedFlowCode` is the initial port classification, not the authoritative final Flow Code.
- `ldg:extractedFlowCode` is an OCR extraction field, not the authoritative final Flow Code.

## 9. QA Checklist

- Confirm all new examples use `https://hvdc-project.com/ontology/core/`.
- Confirm no canonical example uses `hvdc:hasFlowCode` as the primary property.
- Confirm `Flow 5` is reserved for mixed, incomplete, or anomalous states.
- Confirm `AGI/DAS` language always states `Flow 3 or 4`.

## 10. Canonical Conclusion

Flow Code v3.5 is canonical only when the following are simultaneously true:

- the event is modeled as `hvdc:TransportEvent`
- the final flow is recorded in `hvdc:hasLogisticsFlowCode`
- `AGI/DAS` constraints are enforced
- legacy aliases are treated as transitional references, not as the canonical contract

---

## SOURCE: CONSOLIDATED-03-document-ocr.md

# CONSOLIDATED-03 — Document OCR / Guardian

Canonical OCR, validation, and trust-gate policy for HVDC logistics documents.

See also:
- [NAMESPACE_REGISTRY.md](NAMESPACE_REGISTRY.md)
- [CONSOLIDATED-05-invoice-cost.md](CONSOLIDATED-05-invoice-cost.md)

## 1. Scope

This document standardizes OCR quality gates, validation shapes, and PASS/FAIL examples for the document guardian pipeline.

The policy is intentionally strict because OCR quality directly affects customs, invoice audit, and downstream zero-gate decisions.

## 2. Canonical Namespaces

```turtle
@prefix ldg: <https://hvdc-project.com/ontology/document-guardian/> .
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
```

## 3. OCR KPI Gates

| KPI | Threshold | Action on failure |
|---|---|---|
| `MeanConf` | `>= 0.92` | ZERO-fail-safe + manual review |
| `TableAcc` | `>= 0.98` | ZERO-fail-safe + manual review |
| `NumericIntegrity` | `= 1.00` | ZERO-fail-safe + manual review |
| `EntityMatch` | `>= 0.98` | ZERO-fail-safe + manual review |

Canonical statement:

- `MeanConf >= 0.92`
- `TableAcc >= 0.98`
- `NumericIntegrity = 1.00`
- `EntityMatch >= 0.98`

## 4. Canonical SHACL

```turtle
@prefix ldg: <https://hvdc-project.com/ontology/document-guardian/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ldg:ValidationShape a sh:NodeShape ;
  sh:targetClass ldg:Validation ;
  sh:property [
    sh:path ldg:hasStage ;
    sh:minCount 1 ;
    sh:message "Validation must have stage."
  ] ;
  sh:property [
    sh:path ldg:hasResult ;
    sh:in ("PASS" "FAIL" "WARN") ;
    sh:message "Validation result must be PASS, FAIL, or WARN."
  ] .

ldg:MetricShape a sh:NodeShape ;
  sh:targetClass ldg:Metric ;
  sh:property [
    sh:path ldg:hasMeanConf ;
    sh:minInclusive 0.0 ;
    sh:maxInclusive 1.0
  ] ;
  sh:property [
    sh:path ldg:hasTableAcc ;
    sh:minInclusive 0.0 ;
    sh:maxInclusive 1.0
  ] ;
  sh:property [
    sh:path ldg:hasNumericIntegrity ;
    sh:minInclusive 0.0 ;
    sh:maxInclusive 1.0
  ] ;
  sh:property [
    sh:path ldg:hasEntityMatch ;
    sh:minInclusive 0.0 ;
    sh:maxInclusive 1.0
  ] .

ldg:OCRKPIGateShape a sh:NodeShape ;
  sh:targetClass ldg:Metric ;
  sh:sparql [
    sh:severity sh:Violation ;
    sh:message "OCR KPI Gate failure: MeanConf>=0.92, TableAcc>=0.98, NumericIntegrity=1.00, EntityMatch>=0.98 are mandatory." ;
    sh:select """
      PREFIX ldg: <https://hvdc-project.com/ontology/document-guardian/>
      SELECT $this
      WHERE {
        $this ldg:hasMeanConf ?meanConf ;
              ldg:hasTableAcc ?tableAcc ;
              ldg:hasNumericIntegrity ?numInt ;
              ldg:hasEntityMatch ?entityMatch .
        FILTER(
          ?meanConf < 0.92 ||
          ?tableAcc < 0.98 ||
          ?numInt != 1.00 ||
          ?entityMatch < 0.98
        )
      }
    """
  ] .

ldg:AuditShape a sh:NodeShape ;
  sh:targetClass ldg:Audit ;
  sh:property [
    sh:path ldg:hasSelfCheck ;
    sh:in ("PASS" "FAIL")
  ] ;
  sh:property [
    sh:path ldg:hasTotalsCheck ;
    sh:in ("PASS" "FAIL")
  ] ;
  sh:property [
    sh:path ldg:hasCrossDocCheck ;
    sh:in ("PASS" "FAIL")
  ] ;
  sh:property [
    sh:path ldg:hasHashConsistency ;
    sh:in ("PASS" "FAIL")
  ] .

ldg:CostGuardCheckShape a sh:NodeShape ;
  sh:targetClass ldg:CostGuardCheck ;
  sh:property [
    sh:path ldg:hasVerdict ;
    sh:in ("PASS" "WARN" "HIGH" "CRITICAL")
  ] .
```

## 5. FAIL Example

This is an explicit FAIL example. It must not be interpreted as a passing sample because `TableAcc` and `EntityMatch` are below gate.

```json
{
  "@context": {
    "ldg": "https://hvdc-project.com/ontology/document-guardian/"
  },
  "@id": "ldg:document-ocr-fail-001",
  "@type": "ldg:Document",
  "ldg:hasValidation": {
    "@type": "ldg:Validation",
    "ldg:hasStage": "Auto-Validation",
    "ldg:hasResult": "FAIL",
    "ldg:hasPercentage": 91.0
  },
  "ldg:hasMetric": {
    "@type": "ldg:Metric",
    "ldg:hasMeanConf": 0.97,
    "ldg:hasTableAcc": 0.95,
    "ldg:hasNumericIntegrity": 1.0,
    "ldg:hasEntityMatch": 0.92
  },
  "ldg:hasAudit": {
    "@type": "ldg:Audit",
    "ldg:hasSelfCheck": "PASS",
    "ldg:hasTotalsCheck": "PASS",
    "ldg:hasCrossDocCheck": "PASS",
    "ldg:hasHashConsistency": "PASS"
  }
}
```

## 6. PASS Example

This is a gate-compliant PASS example.

```json
{
  "@context": {
    "ldg": "https://hvdc-project.com/ontology/document-guardian/"
  },
  "@id": "ldg:document-ocr-pass-001",
  "@type": "ldg:Document",
  "ldg:hasValidation": {
    "@type": "ldg:Validation",
    "ldg:hasStage": "Auto-Validation",
    "ldg:hasResult": "PASS",
    "ldg:hasPercentage": 99.2
  },
  "ldg:hasMetric": {
    "@type": "ldg:Metric",
    "ldg:hasMeanConf": 0.99,
    "ldg:hasTableAcc": 0.99,
    "ldg:hasNumericIntegrity": 1.0,
    "ldg:hasEntityMatch": 0.99
  },
  "ldg:hasAudit": {
    "@type": "ldg:Audit",
    "ldg:hasSelfCheck": "PASS",
    "ldg:hasTotalsCheck": "PASS",
    "ldg:hasCrossDocCheck": "PASS",
    "ldg:hasHashConsistency": "PASS"
  }
}
```

## 7. SPARQL Query

```sparql
PREFIX ldg: <https://hvdc-project.com/ontology/document-guardian/>

SELECT ?document ?meanConf ?tableAcc ?numericIntegrity ?entityMatch
WHERE {
  ?document a ldg:Document ;
            ldg:hasMetric ?metric .
  ?metric ldg:hasMeanConf ?meanConf ;
          ldg:hasTableAcc ?tableAcc ;
          ldg:hasNumericIntegrity ?numericIntegrity ;
          ldg:hasEntityMatch ?entityMatch .
  FILTER(
    ?meanConf < 0.92 ||
    ?tableAcc < 0.98 ||
    ?numericIntegrity != 1.00 ||
    ?entityMatch < 0.98
  )
}
ORDER BY ?document
```

## 8. Operating Interpretation

- A FAIL gate is a document-readiness failure, not merely a “low confidence warning”.
- OCR failure should block automated downstream trust decisions.
- Cost-guard and invoice-review stages must consume the same PASS/FAIL semantics.

## 9. QA Checklist

- Confirm all fenced code blocks render correctly.
- Confirm no FAIL sample is labeled PASS.
- Confirm all KPI thresholds match the SHACL gate and the prose.
- Confirm examples use canonical `ldg:` namespace only.

---

## SOURCE: CONSOLIDATED-04-barge-bulk-cargo.md

---
title: "HVDC Barge Operations & Bulk Cargo Ontology"
type: "ontology-design"
domain: "bulk-cargo-operations"
sub-domains: ["bulk-cargo-operations", "seafastening", "stability-control", "barge-operations", "lifting-rigging", "flow-code"]
version: "consolidated-1.1"
date: "2025-11-01"
tags: ["ontology", "hvdc", "bulk-cargo", "barge", "lashing", "stability", "flow-code", "flow-code-v35", "mosb", "lct", "consolidated"]
standards: ["RDF", "OWL", "SHACL", "SPARQL", "JSON-LD", "Turtle", "XSD", "IMSBC", "SOLAS"]
status: "active"
source_files: ["1_CORE-05-hvdc-bulk-cargo-ops.md", "docs/flow_code_v35/FLOW_CODE_V35_ALGORITHM.md"]
---

# hvdc-barge-bulk-cargo · CONSOLIDATED-04

## Bulk Cargo Operations

### Source
- **Original File**: `1_CORE-05-hvdc-bulk-cargo-ops.md`
- **Version**: unified-1.0
- **Date**: 2025-01-23

## Executive Summary

**Bulk/Project 화물 해상 운송(적재·양하·고박·안정성·인양) 전 과정**을 **온톨로지(지식 그래프)**로 모델링하여 데이터 일관성, 추적성, 자동화 가능성을 높인다.

### Flow Code v3.5 in Barge & Bulk Cargo Operations

Barge and bulk cargo operations in the HVDC project primarily utilize **Flow Code 3 and 4**, as most bulk materials require **MOSB transit** for offshore delivery to AGI/DAS sites. The barge/LCT transport model inherently follows the **Port → MOSB → Site** pattern, making MOSB the critical staging and consolidation point for all offshore bulk cargo.

**Key Flow Patterns:**
- **Flow 3**: Port → MOSB → AGI/DAS (Direct bulk cargo to offshore)
- **Flow 4**: Port → Warehouse → MOSB → AGI/DAS (Bulk cargo with interim storage)
- **MOSB Mandatory**: All AGI/DAS bulk shipments enforce MOSB leg (domain rule)

---

**적용 범위**: 철강 구조물, OOG, 프리캐스트(Hollow Core Slab), Breakbulk 전반
**목표 산출물**: 클래스/속성 정의, 제약, 예시 인스턴스, 검증(SHACL), 교환 스키마(CSV), 쿼리(SPARQL) 샘플
**단위**: 길이(m), 중량(t), 각도(deg), 좌표계: 선박 데크 로컬 좌표 (X fwd, Y port→stbd, Z keel→up)
**책임 경계**: 본 모델은 **데이터 표현/검증용**. 공학적 최종 판단(예: Stability 승인, 구조 검토)은 전문 SW/엔지니어 권한

**상위 개념 계층(Top Taxonomy)**:
```
Maritime Logistics
└── Cargo Operation
    ├── Bulk Cargo Operation (BULK)
    │   ├── Planning Phase
    │   ├── Loading Operation
    │   ├── Discharging Operation
    │   ├── Stowage & Lashing
    │   ├── Stability Control
    │   ├── Lifting & Transport Handling
    │   └── Post-Operation (Survey, Handover)
    ├── Documentation (Vessel Loading Plan, Lashing Plan, Stability Report, Rigging Plan)
    ├── Resources (Vessel, Equipment, Manpower)
    ├── Locations (Port, Berth, Jetty, Yard)
    └── Constraints (Safety, Compliance, Environment, Contract)
```

**Visual — 핵심 클래스/관계(요약)**

| Class | 핵심 속성 | 관계 | 근거/조인 소스 | 결과 |
|-------|-----------|------|----------------|------|
| debulk:Cargo | cargoId, cargoType, weight(t), dimL/W/H(m), cogX/Y/Z(m), stackable(boolean), hazmatClass? | placedOn→DeckArea, securedBy→LashingAssembly, handledBy→Equipment | OCR/Table Parser | 상태, 정합성 |
| debulk:Vessel | vesselName, imo?, deckStrength(t/m²), coordinateOrigin | hasDeck→DeckArea, carries→Cargo, operatedBy→Crew | Vessel Registry | 운항 상태 |
| debulk:DeckArea | areaId, usableL/W/H, maxPointLoad, maxUniformLoad | partOf→Vessel, hosts→Cargo | Deck Layout | 적재 용량 |
| debulk:LashingAssembly | requiredCapacity(t), calcTension(t), safetyFactor | appliedTo→Cargo, uses→LashingElement, verifiedBy→Engineer | Lashing Calc | 고박 강도 |
| debulk:LashingElement | wll(t), angleDeg, count, length(m) | partOf→LashingAssembly | Equipment Spec | 유효 용량 |
| debulk:StabilityCase | disp(t), vcg(m), gm(m), rollAngle(deg) | evaluates→Vessel, considers→Cargo | Stability Calc | 안정성 상태 |
| debulk:LiftingPlan | liftId, method, slingAngleDeg, estLoadShare(t) | for→Cargo, uses→RiggingGear, verifiedBy→Engineer | Rigging Design | 인양 계획 |
| debulk:RiggingGear | gearId, type, wll(t), length(m) | partOf→LiftingPlan | Gear Spec | 장비 용량 |
| debulk:Equipment | equipId, type, swl(t), radius(m)? | allocatedTo→OperationTask | Equipment List | 작업 배정 |
| debulk:Manpower | personId, role, certificateId?, contact | assignedTo→OperationTask | Crew Roster | 인력 배정 |
| debulk:OperationTask | taskId, status, start/end(DateTime), sequence | relatesCargo→Cargo, uses→Equipment | Task Planning | 작업 상태 |
| debulk:Port/Jetty/Berth | code, draught, restriction | hosts→OperationTask | Port Database | 위치 정보 |
| debulk:Environment | wind(m/s), seaState, temp, accel_g | affects→LashingAssembly/StabilityCase | Weather API | 환경 영향 |
| debulk:Document | docId, type, version, fileRef | documents→(Plan/Report), about→(Vessel/Cargo) | Document Store | 문서 관리 |

자료: Load Plan, Stability Calculator, Equipment Spec, Crew Roster

**How it works (flow)**

1. **Planning Phase**: 데이터 수집·제약 정의 → Draft → Reviewed → Approved (Loading Plan, Stowage Layout, Lashing Calc Sheet)
2. **Pre-Operation**: 자원 배정·브리핑 → Ready → Mobilized (Equipment & Workforce Plan, JSA)
3. **Execution**: 적재/고박/검사 → In-Progress → Paused/Resumed → Completed (QC Checklist, Photos, Survey Report)
4. **Post-Operation**: 서류/인계 → Completed → Archived (B/L, COA Evidence, Final Report)

---

## Flow Code v3.5 Integration in Barge & Bulk Cargo Operations

### Bulk Cargo Flow Code Patterns

Bulk and project cargo in the HVDC logistics network predominantly follow **Flow Code 3 and 4** due to the inherent requirements of offshore transportation via MOSB.

| Flow Code | Bulk Cargo Pattern | Typical Cargo | Routing |
|-----------|-------------------|---------------|---------|
| **Flow 3** | Direct MOSB Transit | Heavy machinery, transformers, pre-assembled structures | Zayed Port → MOSB → LCT → AGI/DAS |
| **Flow 4** | Warehouse + MOSB | Bulk materials requiring consolidation | Zayed Port → AAA Storage → MOSB → LCT → AGI/DAS |
| **Flow 5** | Incomplete/Awaiting | Bulk cargo at MOSB pending site assignment | MOSB staging area (temporary) |

### Barge/LCT Operations and Flow Code

#### LCT Transport Model

Landing Craft Tank (LCT) and barge operations are the **exclusive mode** for bulk cargo delivery to AGI/DAS offshore platforms. This transport model enforces the following Flow Code characteristics:

```
LCT Operation Flow:
1. Port Arrival (Flow 0) → Pre-customs clearance
2. Port Clearance → MOSB Transit (Flow 3/4 initiated)
3. MOSB Staging → Bulk cargo consolidation, lashing preparation
4. LCT Loading → Seafastening, stability verification
5. Sea Passage → MOSB → AGI/DAS (8-12 hour transit)
6. Offshore Discharge → Final delivery (Flow 3/4 completed)

Flow Code Determination:
- If cargo went directly from Port to MOSB: Flow 3
- If cargo stopped at warehouse before MOSB: Flow 4
```

#### MOSB as Flow Code Anchor

MOSB (Mussafah Offshore Supply Base) is the **mandatory transit point** for all AGI/DAS bulk cargo, making it the **Flow Code anchor** for offshore logistics:

```
MOSB Functional Role:
- Consolidation: Aggregate bulk cargo from multiple ports/warehouses
- Staging: Prepare cargo for LCT loading (lashing, seafastening)
- Quality Control: Inspect cargo condition before offshore transport
- Compliance: Verify FANR (nuclear), ADNOC permits, gate passes

Flow Code Impact:
- MOSB presence = Flow Code ≥ 3 (automatic)
- AGI/DAS destination + MOSB = Flow 3 or 4 (enforced)
- Non-MOSB bulk cargo = Invalid for AGI/DAS (domain rule violation)
```

### RDF/OWL Implementation

#### Flow Code Properties for Bulk Cargo

```turtle
@prefix debulk: <https://hvdc-project.com/ontology/bulk-cargo/> .
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Flow Code for Bulk Cargo
debulk:hasLogisticsFlowCode a owl:DatatypeProperty ;
    rdfs:label "Bulk Cargo Flow Code" ;
    rdfs:comment "Flow Code (3-5) for bulk cargo operations" ;
    rdfs:domain debulk:Cargo ;
    rdfs:range xsd:integer ;
    sh:minInclusive 3 ;
    sh:maxInclusive 5 ;
    sh:message "Bulk cargo to AGI/DAS must have Flow Code 3-5" .

debulk:requiresMOSBStaging a owl:DatatypeProperty ;
    rdfs:label "Requires MOSB Staging" ;
    rdfs:comment "Boolean flag for MOSB staging requirement" ;
    rdfs:domain debulk:Cargo ;
    rdfs:range xsd:boolean ;
    sh:minCount 1 .

debulk:hasLCTTransport a owl:ObjectProperty ;
    rdfs:label "Has LCT Transport" ;
    rdfs:comment "Links bulk cargo to LCT/barge transport event" ;
    rdfs:domain debulk:Cargo ;
    rdfs:range debulk:TransportEvent .

debulk:mosbArrivalDate a owl:DatatypeProperty ;
    rdfs:label "MOSB Arrival Date" ;
    rdfs:comment "Date cargo arrived at MOSB for staging" ;
    rdfs:domain debulk:Cargo ;
    rdfs:range xsd:date .

debulk:mosbDepartureDate a owl:DatatypeProperty ;
    rdfs:label "MOSB Departure Date" ;
    rdfs:comment "Date LCT departed MOSB with cargo" ;
    rdfs:domain debulk:Cargo ;
    rdfs:range xsd:date .

# SHACL Constraint: AGI/DAS Bulk Cargo Must Use MOSB
debulk:AGIDASBulkConstraint a sh:NodeShape ;
    sh:targetClass debulk:Cargo ;
    sh:sparql [
        sh:message "AGI/DAS bulk cargo must transit through MOSB (Flow >= 3)" ;
        sh:select """
            PREFIX debulk: <https://hvdc-project.com/ontology/bulk-cargo/>
            SELECT $this
            WHERE {
                $this debulk:finalDestination ?dest ;
                      debulk:hasLogisticsFlowCode ?flowCode .
                FILTER(?dest IN ("AGI", "DAS") && ?flowCode < 3)
            }
        """ ;
    ] .
```

#### Instance Example: Transformer to AGI via LCT

```turtle
# Bulk Cargo: 85-ton Transformer
debulk:cargo/TRANSFORMER-AGI-T1 a debulk:Cargo ;
    debulk:cargoId "TRANSFORMER-AGI-T1" ;
    debulk:cargoType "Power Transformer" ;
    debulk:weight 85000 ;  # kg
    debulk:dimensions "12.5m × 4.2m × 5.8m" ;
    debulk:finalDestination "AGI" ;
    debulk:hasLogisticsFlowCode 3 ;
    debulk:hasFlowDescription "Port → MOSB → AGI (LCT direct)" ;
    debulk:requiresMOSBStaging true ;
    debulk:mosbArrivalDate "2024-11-10"^^xsd:date ;
    debulk:mosbDepartureDate "2024-11-12"^^xsd:date ;
    debulk:hasLCTTransport debulk:transport/LCT-AGI-2024-11 .

# LCT Transport Event
debulk:transport/LCT-AGI-2024-11 a debulk:TransportEvent ;
    debulk:transportId "LCT-AGI-2024-11" ;
    debulk:vesselName "LCT-ADNOC-05" ;
    debulk:origin debulk:location/MOSB ;
    debulk:destination debulk:site/AGI ;
    debulk:departureDate "2024-11-12T06:00:00"^^xsd:dateTime ;
    debulk:arrivalDate "2024-11-12T18:00:00"^^xsd:dateTime ;
    debulk:seaState "Calm (1-2m)" ;
    debulk:cargoManifest ( debulk:cargo/TRANSFORMER-AGI-T1 ) .

# MOSB Staging Operation
debulk:operation/MOSB-STAGING-T1 a debulk:OperationTask ;
    debulk:taskId "MOSB-STAGING-T1" ;
    debulk:taskType "MOSB Staging & Lashing Preparation" ;
    debulk:relatesCargo debulk:cargo/TRANSFORMER-AGI-T1 ;
    debulk:location debulk:location/MOSB ;
    debulk:startDate "2024-11-10T08:00:00"^^xsd:dateTime ;
    debulk:endDate "2024-11-11T17:00:00"^^xsd:dateTime ;
    debulk:status "Completed" ;
    debulk:lashingVerified true ;
    debulk:seafasteningApproved true .
```

### SPARQL Queries for Bulk Cargo Flow Code

#### 1. Bulk Cargo Flow Code Distribution

```sparql
PREFIX debulk: <https://hvdc-project.com/ontology/bulk-cargo/>

SELECT ?flowCode (COUNT(?cargo) AS ?count) (SUM(?weight) AS ?totalWeight)
WHERE {
    ?cargo a debulk:Cargo ;
           debulk:hasLogisticsFlowCode ?flowCode ;
           debulk:weight ?weight .
}
GROUP BY ?flowCode
ORDER BY ?flowCode
```

#### 2. MOSB Staging Duration Analysis

```sparql
PREFIX debulk: <https://hvdc-project.com/ontology/bulk-cargo/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?cargo ?cargoId ?arrivalDate ?departureDate
       ((?departureDate - ?arrivalDate) AS ?stagingDays)
WHERE {
    ?cargo a debulk:Cargo ;
           debulk:cargoId ?cargoId ;
           debulk:mosbArrivalDate ?arrivalDate ;
           debulk:mosbDepartureDate ?departureDate .
}
ORDER BY DESC(?stagingDays)
```

#### 3. AGI/DAS Compliance Check

```sparql
PREFIX debulk: <https://hvdc-project.com/ontology/bulk-cargo/>

SELECT ?cargo ?destination ?flowCode ?mosbStaging ?compliant
WHERE {
    ?cargo a debulk:Cargo ;
           debulk:finalDestination ?destination ;
           debulk:hasLogisticsFlowCode ?flowCode ;
           debulk:requiresMOSBStaging ?mosbStaging .
    FILTER(?destination IN ("AGI", "DAS"))
    BIND(IF(?flowCode >= 3 && ?mosbStaging = true, "PASS", "FAIL") AS ?compliant)
}
ORDER BY ?compliant ?destination
```

#### 4. LCT Transport Efficiency

```sparql
PREFIX debulk: <https://hvdc-project.com/ontology/bulk-cargo/>

SELECT ?lct ?origin ?destination (COUNT(?cargo) AS ?cargoCount)
       ?departureDate ?arrivalDate
WHERE {
    ?lct a debulk:TransportEvent ;
         debulk:origin ?origin ;
         debulk:destination ?destination ;
         debulk:departureDate ?departureDate ;
         debulk:arrivalDate ?arrivalDate .
    ?cargo debulk:hasLCTTransport ?lct .
}
GROUP BY ?lct ?origin ?destination ?departureDate ?arrivalDate
ORDER BY DESC(?cargoCount)
```

### Bulk Cargo KPIs with Flow Code

| KPI Metric | Target | Calculation | Flow Code Relevance |
|------------|--------|-------------|---------------------|
| **MOSB Throughput** | 90-95% | (Flow 3 + Flow 4) / Total Bulk Cargo | MOSB staging efficiency |
| **Flow 3 Ratio** | 60-70% | Flow 3 / (Flow 3 + Flow 4) | Direct MOSB transit rate |
| **Flow 4 Ratio** | 30-40% | Flow 4 / (Flow 3 + Flow 4) | Warehouse consolidation rate |
| **MOSB Staging Time** | <48 hours | Avg(Departure - Arrival) at MOSB | Staging efficiency |
| **AGI/DAS Compliance** | 100% | AGI/DAS with Flow ≥3 / Total AGI/DAS | Mandatory MOSB rule |
| **LCT Utilization** | 80-85% | LCT trips with cargo / Total LCT trips | Transport efficiency |
| **Flow 5 Resolution** | <3 days | Avg(Site Assignment - MOSB Arrival) | Incomplete routing resolution |

### Integration with Bulk Cargo Operations

#### Stowage & Lashing (Flow 3, 4)
- MOSB staging area stowage planning
- Seafastening calculations for LCT transport
- Flow Code determines stowage priority (Flow 3 = urgent offshore)

#### Stability Control (Flow 3, 4)
- LCT stability verification before departure
- Cargo COG (Center of Gravity) adjustments at MOSB
- Flow Code impacts stability calculations (Flow 4 may have multiple items)

#### Lifting & Transport Handling (Flow 3, 4)
- MOSB crane operations for LCT loading
- Rigging plans specific to offshore transport
- Flow Code defines handling sequence (Flow 3 loads first)

---

**Options (설계 선택지)**

1. **OWL/SHACL 엄격형**: 모든 클래스/속성/제약을 OWL/SHACL로 엄격하게 모델링. *Pros* 의미적 추론↑ / *Cons* 초기 모델링 복잡도↑
2. **하이브리드형(권장)**: OWL + CSV 교환 + SHACL 제약, 부족 구간은 유사 패턴 추천. *Pros* 실용성↑ / *Cons* 온톨로지 일관성 유지 필요
3. **실무 간소형**: 핵심 클래스만 모델링하고 나머지는 확장 가능한 구조. *Pros* 빠른 적용↑ / *Cons* 확장성 제한

**Roadmap (P→Pi→B→O→S + KPI)**

- **Prepare**: 클래스 스키마 정의, SHACL 제약 규칙 작성, CSV 템플릿 준비
- **Pilot**: /switch_mode LATTICE + /logi-master bulk-cargo-planning --deep --stability-check로 샘플 화물 1회전. KPI: 검증정확도 ≥97%, 안전성 ≥95%
- **Build**: 라싱 계산, 안정성 검증, 인양 계획 자동화 시스템 구축
- **Operate**: 실시간 모니터링, 이상 상황 즉시 알림 + 대안 제시
- **Scale**: 3D 좌표 연동, CAD/BIM 링크, 가속도 스펙트럼 분석 추가

**Automation notes**

- **입력 감지 →** /switch_mode LATTICE + /logi-master bulk-cargo-planning (화물→적재→고박→안정성→인양 계획)
- **표준 근거**: IMSBC, SOLAS, Port Notice 등 규정 기반 제약 검증
- **감사 포맷**: SHACL Validation 결과 + Stability Report + Lashing Calculation

**QA / Gap 체크**

- Cargo CSV에 **COG/중량/치수** 누락 없음?
- DeckArea에 **허용하중(균등/점하중)** 입력 완료?
- LashingElements **WLL·각도** 기입 및 세트 매핑 완료?
- StabilityCase에 **GM/VCG/조건** 기록?
- Equipment/Manpower **작업별 배정** 완료?

가정: (i) 모든 화물은 정확한 치수/중량 정보를 보유, (ii) 선박 데크 강도 데이터가 최신으로 유지됨, (iii) 환경 조건은 실시간으로 업데이트됨.

---

# Part 2: Detailed Class Specifications

## 속성 도메인/레인지(OWL 스타일 요약)

* `securedBy (Cargo → LashingAssembly)` [0..*]
* `appliedTo (LashingAssembly → Cargo)` [1..*]
* `uses (LashingAssembly → LashingElement)` [1..*]
* `placedOn (Cargo → DeckArea)` [1]
* `hosts (DeckArea → Cargo)` [0..*]
* `relatesCargo (OperationTask → Cargo)` [0..*]
* `allocatedTo (Equipment → OperationTask)` [0..*]
* `assignedTo (Manpower → OperationTask)` [0..*]
* `evaluates (StabilityCase → Vessel)` [1]
* `considers (StabilityCase → Cargo)` [0..*]
* `documents (Document → Plan/Report/Task)` [1..*]

## 제약(Constraints) 예시

* **Deck Strength**: `sum(load_i / footprint_i) ≤ deckStrength` (균등하중·점하중 모두 고려)
* **Lashing WLL**: `Σ(WLL_effective) ≥ requiredCapacity × SF` (SF≥2.0 예시)
* **Sling Angle**: 각도 작아질수록 다리장력 증가: `T_leg = W / (2 × sin(angle))`
* **Stability Gate**: `GM ≥ GM_min`, `VCG ≤ limitVCG`, `heel ≤ 5°` (예시 기준)

---

# Part 3: Validation & Verification

## SHACL 검증 규칙(요지)

데이터 일관성/안전 최소 기준을 자동 검출

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix debulk: <http://example.com/bulk#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

debulk:CargoShape a sh:NodeShape ;
  sh:targetClass debulk:Cargo ;
  sh:property [ sh:path debulk:weight ; sh:datatype xsd:decimal ; sh:minInclusive 0.1 ] ;
  sh:property [ sh:path debulk:dimL ; sh:datatype xsd:decimal ; sh:minInclusive 0.1 ] ;
  sh:property [ sh:path debulk:placedOn ; sh:minCount 1 ; sh:class debulk:DeckArea ] .

debulk:LashingAssemblyShape a sh:NodeShape ;
  sh:targetClass debulk:LashingAssembly ;
  sh:property [ sh:path debulk:uses ; sh:minCount 2 ; sh:class debulk:LashingElement ] ;
  sh:rule [ a sh:SPARQLRule ;
    sh:prefixes ( ) ;
    sh:construct """
      CONSTRUCT { ?this debulk:status "UNDER_CAPACITY" }
      WHERE {
        ?this debulk:requiredCapacity ?req .
        {
          SELECT ?this (SUM(?effWll) AS ?sumWll)
          WHERE { ?this debulk:uses ?e . ?e debulk:wll ?w . ?e debulk:angleDeg ?a .
                  BIND( (?w) * sin(?a * 3.14159/180) AS ?effWll ) }
          GROUP BY ?this
        }
        FILTER (?sumWll < (?req * 2.0))
      }
    """ ] .
```

*해석*: 라싱 요소의 유효 WLL(각도 보정 합계)이 요구능력×안전율(2.0) 미만이면 `UNDER_CAPACITY` 플래그.

## SPARQL 질의 예시

```sparql
# Q1: Cargo별 라싱 유효용량 합계 추출
PREFIX debulk: <http://example.com/bulk#>
SELECT ?cargo (SUM(?wll*sin(?a*pi()/180)) AS ?sumEffWll)
WHERE {
  ?cargo a debulk:Cargo ; debulk:securedBy ?ls .
  ?ls debulk:uses ?e . ?e debulk:wll ?wll ; debulk:angleDeg ?a .
}
GROUP BY ?cargo
```

```sparql
# Q2: 데크 허용균등하중 대비 점검
PREFIX debulk: <http://example.com/bulk#>
SELECT ?deck ?sumWeight ?area ?uniformLoad ?maxUL
WHERE {
  ?deck a debulk:DeckArea ; debulk:usableL ?L ; debulk:usableW ?W ; debulk:maxUniformLoad ?maxUL .
  BIND((?L*?W) AS ?area)
  { SELECT ?deck (SUM(?w) AS ?sumWeight)
    WHERE { ?cargo debulk:placedOn ?deck ; debulk:weight ?w } GROUP BY ?deck }
  BIND(?sumWeight / ?area AS ?uniformLoad)
}
```

## 컴피턴시 질문(Competency Questions)

모델이 답해야 할 질의 정의(요구사항 유도용):

1. 특정 `Cargo`의 **총 라싱 유효용량**은 요구능력 대비 충분한가?
2. `DeckArea` A1에 적재된 화물들의 **평균/최대 접지하중**은 허용치 이내인가?
3. 주어진 `StabilityCase`에서 **총중량/VCG/GM 변화**는 기준을 만족하는가?
4. 반경 R에서 크레인의 **SWL ≥ 예상 훅하중**인가? 불충분 시 대체안은?
5. 야간조 작업에 필요한 **인력/자격증/연락망**은 배정되었는가?

---

# Part 4: Implementation Guide

## 교환 스키마(Operational CSV/Excel 템플릿)

### Cargo.csv

| cargoId | type | weight_t | dimL_m | dimW_m | dimH_m | cogX_m | cogY_m | cogZ_m | stackable | placedOn |
|---------|------|---------:|-------:|-------:|-------:|-------:|-------:|-------:|:---------:|----------|
| C001 | SteelStructure | 42.5 | 12.0 | 3.2 | 3.5 | 5.8 | 0.0 | 1.4 | FALSE | A1 |

### LashingElements.csv

| lashId | type | wll_t | angle_deg | length_m | assemblyId |
|--------|------|------:|----------:|---------:|------------|
| LE01 | Chain10mm | 6.0 | 45 | 8.0 | LS01 |

### DeckAreas.csv

| areaId | vessel | usableL_m | usableW_m | maxUniform_tpm2 | maxPoint_t |
|--------|--------|----------:|----------:|----------------:|-----------:|
| A1 | Vessel_ABC | 20 | 10 | 15 | 60 |

### Tasks.csv (스케줄·자원 배정)

| taskId | phase | relatesCargo | start_utc | end_utc | eq_alloc | manpower |
|--------|-------|--------------|-----------|---------|----------|----------|
| T001 | Loading | C001 | 2025-11-02T06:00 | 2025-11-02T10:00 | Crane_M80 | Rigger3,Banksman2 |

## 문서 매핑(Plans ↔ Ontology)

| 문서 | 온톨로지 매핑 | 자동 생성 포인트 |
|------|---------------|------------------|
| Vessel Loading Plan | `OperationTask`, `DeckArea`, `Cargo` | Gantt/테이블, COG 리스트, Layout 주석 |
| Seafastening/Lashing Plan | `LashingAssembly`, `LashingElement`, `Environment` | 각도·장력 표, 부족 용량 플래그 |
| Stability Report | `StabilityCase`, `Vessel`, `Cargo` | 중량/VCG 집계 표, 한계 비교 |
| Lifting/Rigging Plan | `LiftingPlan`, `RiggingGear`, `Equipment` | 다리장력 계산 표, WLL 매칭 체크 |
| Logistics Execution Plan | `OperationTask`, `Manpower`, `Equipment` | 교대별 배정표, 연락처 리스트 |

## 예시 인스턴스(직관용 Turtle)

```turtle
@prefix debulk: <http://example.com/bulk#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

debulk:Cargo_001 a debulk:Cargo ;
  debulk:cargoType "SteelStructure" ;
  debulk:weight "42.5"^^xsd:decimal ;
  debulk:dimL "12.0"^^xsd:decimal ; debulk:dimW "3.2"^^xsd:decimal ; debulk:dimH "3.5"^^xsd:decimal ;
  debulk:cogX "5.8"^^xsd:decimal ; debulk:cogY "0.0"^^xsd:decimal ; debulk:cogZ "1.4"^^xsd:decimal ;
  debulk:placedOn debulk:Deck_A1 ;
  debulk:securedBy debulk:LashSet_01 .

debulk:Deck_A1 a debulk:DeckArea ;
  debulk:areaId "A1" ; debulk:usableL "20.0"^^xsd:decimal ; debulk:usableW "10.0"^^xsd:decimal ;
  debulk:maxUniformLoad "15.0"^^xsd:decimal .

debulk:LashSet_01 a debulk:LashingAssembly ;
  debulk:requiredCapacity "1.2"^^xsd:decimal ;  # g·W / μ 등으로 산정된 필요 능력(예)
  debulk:uses debulk:Chain_10mm_1, debulk:Chain_10mm_2 .

debulk:Chain_10mm_1 a debulk:LashingElement ; debulk:wll "6.0"^^xsd:decimal ; debulk:angleDeg "45"^^xsd:decimal .
debulk:Chain_10mm_2 a debulk:LashingElement ; debulk:wll "6.0"^^xsd:decimal ; debulk:angleDeg "45"^^xsd:decimal .

debulk:Stab_LoadedCalm a debulk:StabilityCase ;
  debulk:gm "1.8"^^xsd:decimal ; debulk:vcg "4.2"^^xsd:decimal ; debulk:rollAngle "2.0"^^xsd:decimal ;
  debulk:evaluates debulk:Vessel_ABC ; debulk:considers debulk:Cargo_001 .
```

## OWL 스키마(발췌)

```turtle
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix debulk: <http://example.com/bulk#> .

debulk:Cargo a owl:Class ; rdfs:label "Cargo" .
debulk:LashingAssembly a owl:Class .
debulk:LashingElement a owl:Class .
debulk:DeckArea a owl:Class .

debulk:securedBy a owl:ObjectProperty ;
  rdfs:domain debulk:Cargo ; rdfs:range debulk:LashingAssembly .
debulk:placedOn a owl:ObjectProperty ;
  rdfs:domain debulk:Cargo ; rdfs:range debulk:DeckArea .
debulk:uses a owl:ObjectProperty ;
  rdfs:domain debulk:LashingAssembly ; rdfs:range debulk:LashingElement .

debulk:weight a owl:DatatypeProperty .
debulk:dimL a owl:DatatypeProperty .
debulk:cogX a owl:DatatypeProperty .
```

---

# Part 5: Governance & Extension

## 지배 규칙(정책·규정) 표현 패턴

* `ComplianceRule` 클래스로 규정 항목 정의(예: IMSBC, SOLAS, Port Notice)
* `appliesTo`(Rule→Class/Property), `threshold`(수치), `reference`(문헌식별), `jurisdiction`
* 규정 점검은 **추론 규칙** 또는 **SHACL/SPARQL**로 구현

## 버전·추적성(Traceability)

* 모든 엔티티에 `version`, `createdAt`, `createdBy`, `sourceDoc` 부여
* 변경 기록: `supersedes`(구버전), `wasDerivedFrom`(원데이터), `approvalStatus`
* 파일 링크는 `Document.fileRef`(URI)로 관리

## 차후 확장 포인트

* 3D 좌표(모델 ID) 연동, CAD/BIM 링크 속성(`modelRef`)
* 가속도 스펙트럼/항해 구간별 `Environment` 타임시리즈
* 비용/계약(`CostItem`, `LaytimeEvent`) 추가
* 포장/방수/내식(`Packaging`, `Protection`) 속성 추가

### 결론

이 온톨로지는 **계획↔실행↔검증**을 하나의 그래프로 잇는다.
동일 데이터를 문서, 체크리스트, 계산, 리포트로 **재사용**할 수 있게 해준다.
CSV/OWL/SHACL 샘플을 기반으로 바로 파일화를 진행하면 현장 적용 속도가 빨라진다.

---

## SOURCE: CONSOLIDATED-05-invoice-cost.md

# CONSOLIDATED-05 — Invoice / Cost Guard

Canonical cost-guard semantics for invoice audit in the HVDC logistics ontology bundle.

See also:
- [NAMESPACE_REGISTRY.md](NAMESPACE_REGISTRY.md)
- [CONSOLIDATED-03-document-ocr.md](CONSOLIDATED-03-document-ocr.md)

## 1. Purpose

This document separates risk classification from operational decision-making.

The canonical model uses two axes:

- `costGuardBand`: risk band derived from delta analysis
- `decision`: workflow decision for automation or human review

## 2. Canonical Enums

### 2.1 costGuardBand

| Value | Meaning |
|---|---|
| `PASS` | Within tolerance |
| `WARN` | Mild variance requiring attention |
| `HIGH` | Material variance requiring human review |
| `CRITICAL` | Severe variance requiring rejection path |

### 2.2 decision

| Value | Meaning |
|---|---|
| `AUTO_PASS` | Safe to accept automatically |
| `HUMAN_REVIEW` | Requires analyst review / approval |
| `AUTO_REJECT` | Should be rejected automatically or escalated immediately |

## 3. Canonical Mapping Rule

| costGuardBand | Canonical decision |
|---|---|
| `PASS` | `AUTO_PASS` |
| `WARN` | `HUMAN_REVIEW` |
| `HIGH` | `HUMAN_REVIEW` |
| `CRITICAL` | `AUTO_REJECT` |

Illustrative band thresholds for the examples below:

- `PASS`: `abs(delta_pct) <= 3.0`
- `WARN`: `3.0 < abs(delta_pct) <= 5.0`
- `HIGH`: `5.0 < abs(delta_pct) <= 10.0`
- `CRITICAL`: `abs(delta_pct) > 10.0`

## 4. Canonical JSON Example — PASS

```json
{
  "invoiceId": "INV-2025-001",
  "vendor": "DSV Logistics",
  "currency": "USD",
  "riskResult": {
    "deltaPercent": 2.1,
    "costGuardBand": "PASS",
    "decision": "AUTO_PASS"
  },
  "proof": {
    "lane": "MOSB -> MIR Site",
    "rateSource": "Contract",
    "rateReferenceUSD": 7350.0,
    "draftRateUSD": 7500.0
  }
}
```

## 5. Canonical JSON Example — WARN

```json
{
  "invoiceId": "INV-2025-002",
  "vendor": "ALS Logistics",
  "currency": "USD",
  "riskResult": {
    "deltaPercent": 4.8,
    "costGuardBand": "WARN",
    "decision": "HUMAN_REVIEW"
  },
  "proof": {
    "lane": "Zayed Port -> DSV Indoor -> MIR Site",
    "rateSource": "Contract",
    "rateReferenceUSD": 6200.0,
    "draftRateUSD": 6500.0
  }
}
```

## 6. Canonical JSON Example — HIGH

```json
{
  "invoiceId": "INV-2025-002B",
  "vendor": "ALS Logistics",
  "currency": "USD",
  "riskResult": {
    "deltaPercent": 7.2,
    "costGuardBand": "HIGH",
    "decision": "HUMAN_REVIEW"
  },
  "proof": {
    "lane": "Khalifa Port -> MOSB -> SHU",
    "rateSource": "Contract",
    "rateReferenceUSD": 7100.0,
    "draftRateUSD": 7611.2
  }
}
```

## 7. Canonical JSON Example — CRITICAL

```json
{
  "invoiceId": "INV-2025-003",
  "vendor": "Vendor XYZ",
  "currency": "USD",
  "riskResult": {
    "deltaPercent": 12.5,
    "costGuardBand": "CRITICAL",
    "decision": "AUTO_REJECT"
  },
  "proof": {
    "lane": "Khalifa Port -> MOSB -> AGI",
    "rateSource": "Contract",
    "rateReferenceUSD": 7550.0,
    "draftRateUSD": 8500.0
  }
}
```

## 8. Canonical Reporting Rule

- Reports may show `PASS`, `WARN`, `HIGH`, or `CRITICAL` to describe risk.
- Workflow engines and approval automation must use `AUTO_PASS`, `HUMAN_REVIEW`, or `AUTO_REJECT`.
- Do not overload a single `verdict` field to mean both band and workflow decision.

## 9. PRISM.KERNEL Recommendation

For audit traces:

- Keep `costGuardBand` in the recap for quick risk scanning.
- Keep `decision` in the machine-readable artifact for orchestration.

Example recap line:

`INV-2025-003 | Vendor XYZ | USD 85,000.00 | Delta 12.5% | Band CRITICAL | Decision AUTO_REJECT`

## 10. QA Checklist

- Confirm every example contains both `costGuardBand` and `decision`.
- Confirm `CRITICAL` examples do not use `REJECT`; use `AUTO_REJECT`.
- Confirm `PASS` examples do not use vague labels such as `ACCEPTABLE`; use `AUTO_PASS`.

---

## SOURCE: CONSOLIDATED-06-material-handling.md

# CONSOLIDATED-06 — Material Handling

Deployable material-handling ontology specification aligned to the canonical HVDC Flow Code model.

Historical raw/source-preserved material now lives in:

- [CONSOLIDATED-06-material-handling-appendix-source-preserved.md](CONSOLIDATED-06-material-handling-appendix-source-preserved.md)

See also:
- [NAMESPACE_REGISTRY.md](NAMESPACE_REGISTRY.md)
- [CONSOLIDATED-02-warehouse-flow.md](CONSOLIDATED-02-warehouse-flow.md)
- [flow-code-v35-schema.ttl](flow-code-v35-schema.ttl)

## 1. Scope

This document defines the clean, deployable material-handling view of the HVDC routing model.

It keeps only:

- canonical routing prose
- valid namespace usage
- valid TTL / JSON-LD / SPARQL examples
- material-handling specific constraints that do not contradict the canonical Flow Code model

## 2. Canonical Material-Handling Rules

- `MIR/SHU` are onshore destinations and may use Flow `1` or `2`.
- `AGI/DAS` are offshore destinations and must use Flow `3` or `4`.
- MOSB is the central hub. It is mandatory for offshore routing and optional/default for valid onshore routing.
- DOT is required only when gross weight is greater than `90 tons`.

## 3. Canonical Namespace Mapping

```turtle
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .
@prefix mh: <https://hvdc-project.com/ontology/material-handling/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
```

Canonical mapping notes:

- `mh:hasLogisticsFlowCode` is a material-handling equivalent of `hvdc:hasLogisticsFlowCode`.
- `mh:hasFlowCodeOriginal` may preserve the pre-upgrade value for audit.
- Canonical business meaning still comes from [CONSOLIDATED-02-warehouse-flow.md](CONSOLIDATED-02-warehouse-flow.md).

## 4. Routing by Site Type

| Destination | Material-handling expectation | Final flow |
|---|---|---|
| `MIR`, `SHU` | Direct or warehouse-assisted inland route | Flow `1` or `2` |
| `AGI`, `DAS` | MOSB staging plus offshore LCT dispatch | Flow `3` or `4` |

## 5. Canonical Turtle Example

```turtle
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .
@prefix mh: <https://hvdc-project.com/ontology/material-handling/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

mh:cargo-agi-001 a mh:Cargo ;
  mh:hasDestinationSite "AGI" ;
  mh:hasGrossWeightTons "125.0"^^xsd:decimal ;
  mh:hasLogisticsFlowCode 3 ;
  mh:hasFlowCodeOriginal 1 ;
  hvdc:hasFlowOverrideReason "AGI/DAS requires MOSB leg" ;
  hvdc:requiresMOSBLeg true .

hvdc:event-agi-001 a hvdc:TransportEvent ;
  hvdc:hasCase "AGI-2025-001" ;
  hvdc:hasFinalLocation "AGI" ;
  hvdc:hasWarehouseCount 0 ;
  hvdc:hasMOSBLeg true ;
  hvdc:hasSiteArrival true ;
  hvdc:hasLogisticsFlowCode 3 ;
  hvdc:hasFlowCodeOriginal 1 ;
  hvdc:hasFlowOverrideReason "AGI/DAS requires MOSB leg" .
```

## 6. Canonical JSON-LD Example

```json
{
  "@context": {
    "hvdc": "https://hvdc-project.com/ontology/core/",
    "mh": "https://hvdc-project.com/ontology/material-handling/",
    "xsd": "http://www.w3.org/2001/XMLSchema#"
  },
  "@id": "mh:cargo-mir-001",
  "@type": "mh:Cargo",
  "mh:hasDestinationSite": "MIR",
  "mh:hasGrossWeightTons": {
    "@value": 45.0,
    "@type": "xsd:decimal"
  },
  "mh:hasLogisticsFlowCode": 2,
  "hvdc:requiresMOSBLeg": false
}
```

## 7. Canonical SPARQL Examples

### 7.1 Offshore compliance

```sparql
PREFIX mh: <https://hvdc-project.com/ontology/material-handling/>

SELECT ?cargo ?dest ?flow
WHERE {
  ?cargo a mh:Cargo ;
         mh:hasDestinationSite ?dest ;
         mh:hasLogisticsFlowCode ?flow .
  FILTER(?dest IN ("AGI", "DAS") && ?flow < 3)
}
ORDER BY ?cargo
```

### 7.2 Heavy inland DOT check

```sparql
PREFIX mh: <https://hvdc-project.com/ontology/material-handling/>

SELECT ?cargo ?dest ?tons
WHERE {
  ?cargo a mh:Cargo ;
         mh:hasDestinationSite ?dest ;
         mh:hasGrossWeightTons ?tons .
  FILTER(?dest IN ("MIR", "SHU") && ?tons > 90)
}
ORDER BY DESC(?tons)
```

## 8. Material-Handling SHACL Snippet

```turtle
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix mh: <https://hvdc-project.com/ontology/material-handling/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

mh:CargoFlowShape a sh:NodeShape ;
  sh:targetClass mh:Cargo ;
  sh:property [
    sh:path mh:hasLogisticsFlowCode ;
    sh:datatype xsd:integer ;
    sh:minInclusive 0 ;
    sh:maxInclusive 5
  ] ;
  sh:sparql [
    sh:message "AGI/DAS cargo must use Flow 3 or 4." ;
    sh:select """
      PREFIX mh: <https://hvdc-project.com/ontology/material-handling/>
      SELECT $this
      WHERE {
        $this mh:hasDestinationSite ?dest ;
              mh:hasLogisticsFlowCode ?flow .
        FILTER(?dest IN ("AGI", "DAS") && ?flow < 3)
      }
    """
  ] .
```

## 9. Appendix Boundary

The appendix preserves historical content and malformed legacy examples for audit/reference purposes only.

It is out of scope for canonical validation and must not be treated as the normative source for:

- namespace policy
- Flow Code semantics
- SHACL syntax
- JSON-LD example structure

## 10. Canonical Conclusion

The deployable material-handling spec is intentionally narrow:

- use `mh:` for material-handling specifics
- use `hvdc:` for canonical cross-domain Flow Code semantics
- rely on [CONSOLIDATED-02-warehouse-flow.md](CONSOLIDATED-02-warehouse-flow.md) for the authoritative final routing model

---

## SOURCE: CONSOLIDATED-07-port-operations.md

---
title: "HVDC Port Operations - Consolidated"
type: "ontology-design"
domain: "port-operations"
sub-domains: ["ofco-system", "port-agency", "bilingual", "flow-code"]
version: "consolidated-1.1"
date: "2025-11-01"
tags: ["ontology", "hvdc", "port-operations", "flow-code", "flow-code-v35", "khalifa-port", "zayed-port", "consolidated", "ofco", "invoice", "bilingual"]
standards: ["RDF", "OWL", "SHACL", "SPARQL", "JSON-LD"]
status: "active"
source_files: [
  "2_EXT-01-hvdc-ofco-port-ops-en.md",
  "2_EXT-02-hvdc-ofco-port-ops-ko.md",
  "docs/flow_code_v35/FLOW_CODE_V35_ALGORITHM.md"
]
---

# hvdc-port-operations · CONSOLIDATED-07

## Executive Summary

**핵심 한 줄**: OFCO는 '항만 대행(Agency)·항만요금·장비/인력·수배(수자원/게이트패스) 서비스를 묶는 온톨로지 기반 Port Ops & Invoice 허브이며, 문서(Invoice)↔운영(PortCall/ServiceEvent)↔요율(Tariff/PriceCenter)을 Multi-Key Identity Graph로 한 번에 해석합니다. (EN-KR: Any-key in → Resolve → PortCall & Services → Rate & Cost mapping.)
0) Executive Summary (3–5)
• Multi‑Key Identity Graph: 입력 키는 OFCO/SAFEEN/ADP 인보이스번호, Rotation#, Samsung Ref,
hvdc_code 등 아무 키든 OK → 동일 실체(PortCall·Shipment·Invoice) 클러스터로 귀결.
• Ontology‑First: Invoice, InvoiceLine, ServiceEvent(채널크로싱/접안/예인/조종/PHC/장비/인력/수배/게
이트패스/문서수수료), PortCall, Rotation, TariffRef, PriceCenter, CostCenter(A/B/C) 클래스로 정규화.
• 검증 표준: LDG v8.2 ↔ OCR v2.4 연동, KPI(MeanConf≥0.92, TableAcc≥0.98,
NumericIntegrity=1.00), ZERO failsafe.
• 매핑 규칙: Cost Center v2.5 17‑Regex + Subject 패턴("SAFEEN"→Channel Transit, "ADP INV + Port
Dues"→Port Dues, "Cargo Clearance/Arranging FW/BA/5000 IG FW" 등) → Price Center 3‑Way(A/
B/C) 분개.
• 회계 일관성: EA×Rate 합=Amount(±0.01), Σ라인=Invoice Total(±2.00%), 통화/VAT 100.00% 일치,
[EXT] 메타 금액 집계 제외.

---

## Flow Code v3.5 Integration in Port Operations

### Port as Flow Code Origin Point

Port operations represent the **starting point** of the Flow Code classification system. Upon vessel arrival and cargo clearance at **Khalifa Port, Zayed Port, or Jebel Ali Port**, the initial Flow Code determination begins based on the **Final Destination** and **routing plan**.

**Key Flow Code Decision Points at Port:**
1. **Pre Arrival (Flow 0)**: Cargo still on vessel, awaiting port clearance
2. **Post-Clearance Classification**: Port operations team assigns initial Flow Code based on:
   - Final destination (MIR/SHU vs AGI/DAS)
   - Cargo type (container vs bulk)
   - Storage requirements (direct vs warehouse consolidation)
   - MOSB leg necessity (offshore delivery requirement)

### Port-Specific Flow Code Patterns

| Port | Primary Cargo Type | Typical Flow Code | Routing Pattern |
|------|-------------------|-------------------|-----------------|
| **Khalifa Port** | Containers | Flow 1, 2 | Direct or warehouse → Onshore sites |
| **Zayed Port** | Bulk/Heavy | Flow 3, 4 | MOSB staging → Offshore delivery |
| **Jebel Ali** | Mixed (Freezone) | Flow 1, 2, 4 | Varies by customs clearance |

### Flow Code Assignment Process at Port

#### Stage 1: Vessel Arrival (Flow 0)

```
Pre-Arrival Status:
- PortCall initiated with Rotation Number
- Cargo manifest reviewed
- Final destination extracted from Samsung Ref / HVDC Code
- Preliminary Flow Code assessment

Port Operations:
- Channel crossing (SAFEEN service)
- Berthing at designated terminal
- Pilotage and tug services
- Port dues calculation (ADP)

Flow Code = 0 (Pre Arrival) until customs clearance completed
```

#### Stage 2: Customs Clearance & Flow Code Determination

```
Clearance Process:
1. MOIAT customs documentation verified
2. FANR certification (if nuclear materials)
3. Gate pass issued (CICPA)
4. Final destination confirmed

Flow Code Assignment Logic:
IF Final_Location IN ["MIR", "SHU"]:
    IF Requires_Warehouse_Storage:
        Flow Code = 2 (Port → WH → Site)
    ELSE:
        Flow Code = 1 (Port → Site direct)

ELIF Final_Location IN ["AGI", "DAS"]:
    # AGI/DAS offshore → MOSB mandatory
    IF Requires_Warehouse_Storage:
        Flow Code = 4 (Port → WH → MOSB → Site)
    ELSE:
        Flow Code = 3 (Port → MOSB → Site)

ELSE:
    Flow Code = 5 (Awaiting destination assignment)
```

#### Stage 3: Port Departure & Initial Transport

```
Departure from Port:
- Cargo loaded onto trucks/transport
- Port handling charges finalized (OFCO invoice)
- Initial Flow Code recorded in HVDC tracking system
- Next location determined (Warehouse, MOSB, or direct to Site)

Port Operations Complete:
- PortCall status updated to "Departed"
- Flow Code locked for this cargo
- Transit tracking initiated
```

### RDF/OWL Implementation

#### Flow Code Properties for Port Operations

```turtle
@prefix port: <https://hvdc-project.com/ontology/port-operations/> .
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .
@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

# Port-assigned Flow Code
port:assignedFlowCode a owl:DatatypeProperty ;
    rdfs:label "Port-Assigned Flow Code" ;
    rdfs:comment "Initial Flow Code determined at port clearance" ;
    rdfs:domain port:PortCall ;
    rdfs:range xsd:integer ;
    sh:minInclusive 0 ;
    sh:maxInclusive 5 .

port:flowCodeAssignmentDate a owl:DatatypeProperty ;
    rdfs:label "Flow Code Assignment Date" ;
    rdfs:comment "Date when Flow Code was determined at port" ;
    rdfs:domain port:PortCall ;
    rdfs:range xsd:dateTime .

port:finalDestinationDeclared a owl:DatatypeProperty ;
    rdfs:label "Final Destination Declared" ;
    rdfs:comment "Destination declared at port (MIR/SHU/AGI/DAS)" ;
    rdfs:domain port:PortCall ;
    rdfs:range xsd:string .

port:requiresMOSBTransit a owl:DatatypeProperty ;
    rdfs:label "Requires MOSB Transit" ;
    rdfs:comment "Boolean flag set at port for MOSB requirement" ;
    rdfs:domain port:PortCall ;
    rdfs:range xsd:boolean .

port:portOfEntry a owl:ObjectProperty ;
    rdfs:label "Port of Entry" ;
    rdfs:comment "Entry port (Khalifa/Zayed/Jebel Ali)" ;
    rdfs:domain port:PortCall ;
    rdfs:range port:Port .

# SHACL Constraint: Flow Code Assignment Must Match Destination
port:FlowCodeDestinationConstraint a sh:NodeShape ;
    sh:targetClass port:PortCall ;
    sh:sparql [
        sh:message "AGI/DAS destination must have Flow Code ≥ 3 at port assignment" ;
        sh:select """
            PREFIX port: <https://hvdc-project.com/ontology/port-operations/>
            SELECT $this
            WHERE {
                $this port:finalDestinationDeclared ?dest ;
                      port:assignedFlowCode ?flowCode .
                FILTER(?dest IN ("AGI", "DAS") && ?flowCode < 3)
            }
        """ ;
    ] .
```

#### Instance Example: Port Clearance with Flow Code

```turtle
# Port Call: Container cargo to AGI
port:portcall/ROT-2504053298 a port:PortCall ;
    port:rotationNumber "2504053298" ;
    port:vesselName "MSC MAGNOLIA" ;
    port:portOfEntry port:port/KHALIFA ;
    port:arrivalDate "2024-11-10T08:00:00"^^xsd:dateTime ;
    port:clearanceDate "2024-11-11T14:00:00"^^xsd:dateTime ;
    port:departureDate "2024-11-12T06:00:00"^^xsd:dateTime ;
    port:finalDestinationDeclared "AGI" ;
    port:requiresMOSBTransit true ;
    port:assignedFlowCode 3 ;
    port:flowCodeAssignmentDate "2024-11-11T14:30:00"^^xsd:dateTime ;
    port:flowCodeRationale "AGI offshore destination - MOSB leg mandatory" .

# Port Services (OFCO Invoice Lines)
port:service/CHANNEL-CROSSING-ROT2504053298 a port:ServiceEvent ;
    port:serviceType "Channel Crossing" ;
    port:relatesToPortCall port:portcall/ROT-2504053298 ;
    port:provider "SAFEEN" ;
    port:cost "6621.52"^^xsd:decimal ;
    port:currency "AED" .

port:service/BERTHING-ROT2504053298 a port:ServiceEvent ;
    port:serviceType "Berthing" ;
    port:relatesToPortCall port:portcall/ROT-2504053298 ;
    port:provider "ADP" ;
    port:berth "Khalifa Container Terminal - Berth 3" ;
    port:cost "3500.00"^^xsd:decimal ;
    port:currency "AED" .
```

### SPARQL Queries for Port Operations Flow Code

#### 1. Flow Code Distribution by Port of Entry

```sparql
PREFIX port: <https://hvdc-project.com/ontology/port-operations/>

SELECT ?port ?flowCode (COUNT(?portCall) AS ?count)
WHERE {
    ?portCall a port:PortCall ;
              port:portOfEntry ?portObj ;
              port:assignedFlowCode ?flowCode .
    ?portObj port:portName ?port .
}
GROUP BY ?port ?flowCode
ORDER BY ?port ?flowCode
```

#### 2. AGI/DAS Port Clearance Compliance

```sparql
PREFIX port: <https://hvdc-project.com/ontology/port-operations/>

SELECT ?portCall ?rotationNumber ?destination ?flowCode ?compliant
WHERE {
    ?portCall a port:PortCall ;
              port:rotationNumber ?rotationNumber ;
              port:finalDestinationDeclared ?destination ;
              port:assignedFlowCode ?flowCode .
    FILTER(?destination IN ("AGI", "DAS"))
    BIND(IF(?flowCode >= 3, "PASS", "FAIL") AS ?compliant)
}
ORDER BY ?compliant ?destination
```

#### 3. Port Clearance Time by Flow Code

```sparql
PREFIX port: <https://hvdc-project.com/ontology/port-operations/>

SELECT ?flowCode (AVG(?clearanceTime) AS ?avgClearanceHours)
WHERE {
    ?portCall a port:PortCall ;
              port:assignedFlowCode ?flowCode ;
              port:arrivalDate ?arrival ;
              port:clearanceDate ?clearance .
    BIND((xsd:decimal(?clearance - ?arrival) / 3600) AS ?clearanceTime)
}
GROUP BY ?flowCode
ORDER BY ?flowCode
```

#### 4. MOSB Requirement Accuracy at Port

```sparql
PREFIX port: <https://hvdc-project.com/ontology/port-operations/>

SELECT ?destination (COUNT(?portCall) AS ?total)
       (SUM(?mosbRequired) AS ?mosbCount)
       (100.0 * SUM(?mosbRequired) / COUNT(?portCall) AS ?mosbPercentage)
WHERE {
    ?portCall a port:PortCall ;
              port:finalDestinationDeclared ?destination ;
              port:requiresMOSBTransit ?mosbFlag .
    BIND(IF(?mosbFlag = true, 1, 0) AS ?mosbRequired)
}
GROUP BY ?destination
ORDER BY ?destination
```

### Port Operations KPIs with Flow Code

| KPI Metric | Target | Calculation | Flow Code Relevance |
|------------|--------|-------------|---------------------|
| **Flow Code Assignment Accuracy** | 100% | Correct Flow assignments / Total | Initial classification correctness |
| **AGI/DAS MOSB Flag Accuracy** | 100% | AGI/DAS with MOSB flag / Total AGI/DAS | Offshore routing accuracy |
| **Khalifa Port Flow 1+2 Ratio** | 70-80% | (Flow 1 + Flow 2) / Total Khalifa | Container direct/warehouse routing |
| **Zayed Port Flow 3+4 Ratio** | 80-90% | (Flow 3 + Flow 4) / Total Zayed | Bulk cargo MOSB routing |
| **Average Clearance Time** | <48 hours | Avg(Clearance - Arrival) | Port efficiency |
| **Flow 5 (Unassigned) Rate** | <2% | Flow 5 / Total | Incomplete destination rate |

### Integration with Port Operations Workflow

#### Port Call Lifecycle with Flow Code

```
1. Pre-Arrival (Flow 0)
   - Vessel approaching UAE waters
   - Cargo manifest prepared
   - Samsung Ref / HVDC Code extracted

2. Channel Crossing & Berthing (Flow 0)
   - SAFEEN channel crossing service
   - ADP berthing at terminal
   - Awaiting customs clearance

3. Customs Clearance (Flow Code Assignment)
   - MOIAT documentation verified
   - Final destination confirmed
   - Flow Code assigned (1-5)
   - MOSB requirement flagged (if AGI/DAS)

4. Port Departure (Flow Code Active)
   - Cargo loaded on transport
   - OFCO invoice finalized
   - Flow Code tracked in system
   - Next waypoint determined

5. Post-Port Tracking
   - Flow Code guides routing decisions
   - Warehouse, MOSB, or Site dispatch
   - Flow Code remains fixed through journey
```

---

1) Ontology Core (RDF/OWL)
1.1 주요 클래스
• org:Organization ⟶ ofco:OFCO, adports:ADPorts, safeen:SAFEEN, sct:SCT
• vsl:Vessel / vsl:Voyage / port:PortCall(RotationNo 포함)
• fin:Invoice(source=OFCO), fin:InvoiceLine(최대 4 RatePair)
• ops:ServiceEvent ⟶ ops:ChannelCrossing, ops:Berthing, ops:Pilotage, ops:PilotLaunch,
ops:PHC_BulkHandling, ops:PortDues, ops:Waste, ops:FW_Supply, ops:EquipmentHire,
ops:Manpower, ops:GatePass, ops:DocProcessing
• rate:TariffRef / rate:RatePair(EA,Rate,Amount)
• cost:CostCenterA/B, cost:PriceCenter(A/B/C 3‑Way)
• id:Key ⟶ id:OFCOInvNo, id:SAFEENInvNo, id:ADPInvNo, id:RotationNo, id:SamsungRef,
id:HVDCCode
1.2 핵심 프로퍼티(요지)
• ops:relatesToPortCall(InvoiceLine→PortCall), ops:hasRotationNo, fin:belongsToInvoice,
fin:lineNo(NO.), fin:subject(SUBJECT), fin:currency(AED), fin:vat(0.00/5.00), rate:hasEA_i /
hasRate_i / lineAmount, cost:hasCostCenterA/B / hasPriceCenter,
prov:hasEvidence(file,page,line or ref‑row), id:hasSamsungRef / hasOFCOInvNo /
hasRotationNo / hasHVDCCode.
1

1.3 예시 IRI 정책(요지)
• ofco:invoice/OFCO-INV-0000181
• ofco:line/OFCO-INV-0000181#2015 (NO.=2015)
• ops:portcall/ROT-2504053298 (RotationNo)
• id:samsung/HVDC-AGI-GRM-J71-50
1.4 Mini‑TTL 예시
ofco:invoice/OFCO‑INV‑0000181afin:Invoice;
fin:currency"AED"; fin:total "2799.99"^^xsd:decimal .
ofco:line/OFCO‑INV‑0000181#2002afin:InvoiceLine;
fin:belongsToInvoiceofco:invoice/OFCO‑INV‑0000181;
fin:lineNo2002; fin:subject "SAFEEN … Channel Crossing – Rot# 2503123133" ;
rate:hasEA_12.00; rate:hasRate_1 3091.25 ;
rate:hasEA_22.00; rate:hasRate_2 100.00 ;
rate:hasEA_31.00; rate:hasRate_3 239.00 ;
fin:lineAmount6621.52;
ops:relatesToPortCallops:portcall/ROT‑2503123133;
cost:hasCostCenterAcost:PORT_HANDLING_CHARGE;
cost:hasCostCenterBcost:CHANNEL_TRANSIT_CHARGES;
cost:hasPriceCenter cost:CHANNEL_TRANSIT_CHARGES.
2) Multi‑Key Identity Graph
문제: 단일 키 의존 시 연쇄조인 실패·누락 위험.
해법: id:Key 슈퍼클래스 아래 모든 키를 동등 1급 엔터티로 수집하고, Same‑As/LinkSet으로 실체를 클러스터링.
링크 소스(예) ‑ InvoiceNo(OFCO/SAFEEN/ADP), RotationNo, SamsungRef(HVDC‑AGI‑…), HVDCCode,
Vessel+ETA.
클러스터링 규칙(요지) 1) RotationNo 같고, 날짜 창(±7d)·항만 동일 → 같은 PortCall 후보. 2) SamsungRef
동일 + Subject 패턴 일치 → 같은 Operation Batch. 3) InvoiceNo 묶음 Σ(lineAmount) = Invoice
Total(±2.00%) → 같은 Invoice.
3) SHACL 검증(요약)
• InvoiceLineShape
• rate:hasEA_* × rate:hasRate_* 의 합 = fin:lineAmount ±0.01
• RatePair 최대 4, 결측 시 0.00 채움
• fin:currency = "AED" , fin:vat ∈ {0.00, 5.00}
• prov:hasEvidence 필수
• InvoiceShape
• Σ(InvoiceLine.fin:lineAmount) = fin:total ±2.00%
• [EXT] 라벨 행 금액 집계 제외
2

• PortCallLinkShape
• Subject에 Rot# 있으면 ops:relatesToPortCall 필수
4) Cost/Price Center 매핑 규칙(OFCO 전용)
• Regex v2.5 + Subject 패턴(요지)
• "SAFEEN" → PORT HANDLING CHARGE / CHANNEL TRANSIT CHARGES
• "ADP INV" + "Port Dues" → PORT HANDLING CHARGE / PORT DUES & SERVICES
CHARGES
• "Cargo Clearance" → CONTRACT / AF FOR CC
• "Arranging FW Supply"|"FW Supply" → CONTRACT / AF FOR FW SA
• "Berthing Arrangement" → CONTRACT / AF FOR BA
• "5000 IG FW" → AT COST / AT COST(WATER SUPPLY)
• PRICE CENTER 3‑Way
• A/B: Tariff·키워드 기반(예: Channel Crossing/Port Dues/PHC/Equipment/Manpower)
• C: 수수료/Pass/Document(예: Gate Pass, Doc Processing)
• 규칙: C=0 의심 재검토, A>B 또는 B<0 시 일부 C로 이동, A+B+C=Original_TOTAL, Diff=0.00
5) 파이프라인(운영·검증)
1) Pre‑Prep: 회전/데스큐/샤프닝(DPI<300 경고) 2) OCR v2.4: 레이아웃·토큰 conf 수집 3) Smart Table Parser
2.1: 병합셀 해제·세로표 가로화·단위/통화 분리 4) NLP Refine: NULL/단위 보정, 추정 금지 5) Field Tagger:
Parties/IDs/Incoterms/Rotation/Subject 6) LDG Payload Build: 해시·CrossLinks·Evidence 7) Mapping &
QC: EA×Rate 분해, Cost/Price Center 적용, VAT·통화·합계 검증 8) COST‑GUARD: 기준요율 대비 Δ% 밴드
(PASS/WARN/HIGH/CRITICAL) 9) Report(7+2): Discrepancy Table, Compliance Matrix, DEM/DET Forecast
등
KPI 게이트: MeanConf≥0.92, TableAcc≥0.98, NumericIntegrity=1.00 → 미달 시 ZERO 중단 로그.
6) 데이터 맵(Excel/JSON → Ontology)
Source Field Ontology Property Note
NO. fin:lineNo Row key
SUBJECT fin:subject 패턴 매핑 트리거
SAMSUNG REF id:hasSamsungRef 클러스터 anchor
Channel Crossing fin:lineAmount 또는 금액→Line, EA/
Charges… 등 금액열 rate:hasRate_i / rate:hasEA_i Rate 분해
EA_1..4 rate:hasEA_i 최대 4 쌍
3

Source Field Ontology Property Note
Rate_1..4 rate:hasRate_i 금액=Σ(EA×Rate)
Amount (AED) fin:lineAmount 2 decimals
INVOICE NUMBER (OFCO) id:hasOFCOInvNo Invoice join
Rotation# (Subject 내) ops:hasRotationNo PortCall link
7) Report 표준(7+2)
1) Auto Guard Summary
1.5) Risk Assessment(등급/동인/신뢰도)
2) Discrepancy Table(Δ·허용오차·상태)
3) Compliance Matrix(UAE·근거 링크)
4) Auto‑Fill(Freight/Insurance)
5) Auto Action Hooks(명령·가이드)
6) DEM/DET & Gate‑Out Forecast
7) Evidence & Citations
8) Weak Spot & Improvements
9) Changelog
8) 운영 명령 & 자동화 훅
• 인식/검증: /ocr_basic {file} mode:LDG+ → KPI Pass 확인 → /ocr_table / /ocr_retry
• 코스트가드: /switch_mode COST-GUARD + /logi-master invoice-audit --AEDonly
• 매핑: /mapping run → /run pricecenter map → /mapping update pricecenter
• 규제 체크: /logi-master cert-chk (MOIAT/FANR/TRA)
• 배치: /workflow bulk … → /export excel
9) 운영 규칙(정합성)
• Σ(BB:BI)=BJ ±2.00% / EA 결측 시 EA=1.00 & Rate=Amount 규칙 허용(내 ±2.00%)
• VAT=0.00% 또는 5.00% 외 [MISMATCH]
• [EXT] 메타는 금액 집계 제외, 근거(M열) 필수
• 증거(Evidence): 파일명/페이지/라인 또는 참조시트(Row) 필수 기록
10) 로드맵 (P→Pi→B→O→S + KPI)
• Prepare(2주): 스키마/네임스페이스/IRI 설계, SHACL 초안, 키‑링크 룰 정의
KPI: 스키마 커버리지 ≥90.00%
• Pilot(3주): 1개 인보이스 묶음(예: OFCO‑INV‑0000181) E2E, Δ오차≤2.00%
KPI: ZERO 트리거=0, Evidence 100.00%
4

• Build(4주): CostCenter v2.5·3‑Way 분개·COST‑GUARD 통합
KPI: Pass율≥95.00%
• Operate(지속): 배치 처리 및 리포트(7+2) 자동 발행
KPI: TAT ≤ 0.50h/건
• Scale(지속): SAFEEN/ADP 직조인, PortCall API, DEM/DET 2.0 연계
KPI: 오탐율 ≤ 2.00%
11) 리스크 & 완화
• 키 불일치/누락: Multi‑Key 흡수 + 휴리스틱 윈도우(±7d)
• OCR 품질 저하: KPI 게이트 + /ocr_lowres_fix + ZERO 중단
• 요율 변동: TariffRef 버전드(유효일) + COST‑GUARD Δ% 밴드
12) 부록 — Subject→Cost/PriceCenter 예시(발췌)
Subject 큐 Cost A Cost B PriceCenter
SAFEEN … Channel PORT HANDLING CHANNEL TRANSIT CHANNEL TRANSIT
Crossing CHARGE CHARGES CHARGES
ADP INV … Port PORT HANDLING PORT DUES &
PORT DUES
Dues CHARGE SERVICES CHARGES
Agency fee: Cargo AGENCY FEE FOR CARGO
CONTRACT AF FOR CC
Clearance CLEARANCE
Arranging FW
CONTRACT AF FOR FW SA SUPPLY WATER 5000IG
Supply
Berthing CONTRACT(AF FOR AGENCY FEE FOR BERTHING
CONTRACT
Arrangement BA) ARRANGEMENT
AT COST(WATER
5000 IG FW AT COST SUPPLY WATER 5000IG
SUPPLY)
13) 구현 노트
• 코드베이스: logiontology/ (mapping/validation/reasoning/rdfio/report/pipeline)
• SHACL Runner 옵션, JSON‑LD 컨텍스트 제공, RDFLib + DuckDB로 라인‑레벨 집계 검증.
• 외부 연계: PortCall(AD Ports)·SAFEEN 청구 스냅샷 → TariffRef Evidence로 보관.
끝. (숫자 2 decimals, ISO 날짜 사용, NDA/PII 마스킹 준수)
5

---

## Part 2: OFCO 시스템 (한국어)

### Source

- **Original File**: 2_EXT-02-hvdc-ofco-port-ops-ko.md
- **Version**: 4.1
- **Date**: 2025-01-19
- **Language**: Korean

---

> 핵심 한 줄: **OFCO는 '항만 대행(Agency)·항만요금·장비/인력·수배(수자원/게이트패스) 서비스**를 묶는 **온톨로지 기반 Port Ops & Invoice 허브**이며, 문서(Invoice)↔운영(PortCall/ServiceEvent)↔요율(Tariff/PriceCenter)을 **Multi-Key Identity Graph**로 한 번에 해석합니다. (EN-KR: Any-key in → Resolve → PortCall & Services → Rate & Cost mapping.)

---

## 0) Executive Summary (3–5)
- **Multi‑Key Identity Graph**: 입력 키는 *OFCO/SAFEEN/ADP 인보이스번호, Rotation#, Samsung Ref, hvdc_code* 등 아무 키든 OK → **동일 실체(PortCall·Shipment·Invoice) 클러스터**로 귀결.
- **Ontology‑First**: *Invoice, InvoiceLine, ServiceEvent(채널크로싱/접안/예인/조종/PHC/장비/인력/수배/게이트패스/문서수수료), PortCall, Rotation, TariffRef, PriceCenter, CostCenter(A/B/C)* 클래스로 정규화.
- **검증 표준**: **LDG v8.2 ↔ OCR v2.4** 연동, KPI(MeanConf≥0.92, TableAcc≥0.98, NumericIntegrity=1.00), **ZERO failsafe**.
- **매핑 규칙**: Cost Center v2.5 **17‑Regex** + Subject 패턴("SAFEEN"→Channel Transit, "ADP INV + Port Dues"→Port Dues, "Cargo Clearance/Arranging FW/BA/5000 IG FW" 등) → **Price Center 3‑Way(A/B/C)** 분개.
- **회계 일관성**: EA×Rate 합=Amount(±0.01), Σ라인=Invoice Total(±2.00%), 통화/VAT 100.00% 일치, **[EXT] 메타 금액 집계 제외**.

---

## 1) Ontology Core (RDF/OWL)
### 1.1 주요 클래스
- **org:Organization** ⟶ *ofco:OFCO, adports:ADPorts, safeen:SAFEEN, sct:SCT*
- **vsl:Vessel / vsl:Voyage / port:PortCall** *(RotationNo 포함)*
- **fin:Invoice** *(source=OFCO)*, **fin:InvoiceLine** *(최대 4 RatePair)*
- **ops:ServiceEvent** ⟶ *ops:ChannelCrossing, ops:Berthing, ops:Pilotage, ops:PilotLaunch, ops:PHC_BulkHandling, ops:PortDues, ops:Waste, ops:FW_Supply, ops:EquipmentHire, ops:Manpower, ops:GatePass, ops:DocProcessing*
- **rate:TariffRef / rate:RatePair(EA,Rate,Amount)**
- **cost:CostCenterA/B, cost:PriceCenter** *(A/B/C 3‑Way)*
- **id:Key** ⟶ *id:OFCOInvNo, id:SAFEENInvNo, id:ADPInvNo, id:RotationNo, id:SamsungRef, id:HVDCCode*

### 1.2 핵심 프로퍼티(요지)
- **ops:relatesToPortCall**(InvoiceLine→PortCall), **ops:hasRotationNo**, **fin:belongsToInvoice**, **fin:lineNo**(NO.), **fin:subject**(SUBJECT), **fin:currency**(AED), **fin:vat**(0.00/5.00), **rate:hasEA_i / hasRate_i / lineAmount**, **cost:hasCostCenterA/B / hasPriceCenter**, **prov:hasEvidence**(file,page,line or ref‑row), **id:hasSamsungRef / hasOFCOInvNo / hasRotationNo / hasHVDCCode**.

### 1.3 예시 IRI 정책(요지)
- `ofco:invoice/OFCO-INV-0000181`
- `ofco:line/OFCO-INV-0000181#2015` *(NO.=2015)*
- `ops:portcall/ROT-2504053298` *(RotationNo)*
- `id:samsung/HVDC-AGI-GRM-J71-50`

### 1.4 Mini‑TTL 예시
```ttl
ofco:invoice/OFCO-INV-0000181 a fin:Invoice ;
  fin:currency "AED" ; fin:total "2799.99"^^xsd:decimal .

ofco:line/OFCO-INV-0000181#2002 a fin:InvoiceLine ;
  fin:belongsToInvoice ofco:invoice/OFCO-INV-0000181 ;
  fin:lineNo 2002 ; fin:subject "SAFEEN … Channel Crossing – Rot# 2503123133" ;
  rate:hasEA_1 2.00 ; rate:hasRate_1 3091.25 ;
  rate:hasEA_2 2.00 ; rate:hasRate_2 100.00 ;
  rate:hasEA_3 1.00 ; rate:hasRate_3 239.00 ;
  fin:lineAmount 6621.52 ;
  ops:relatesToPortCall ops:portcall/ROT-2503123133 ;
  cost:hasCostCenterA cost:PORT_HANDLING_CHARGE ;
  cost:hasCostCenterB cost:CHANNEL_TRANSIT_CHARGES ;
  cost:hasPriceCenter  cost:CHANNEL_TRANSIT_CHARGES .
```

---

## 2) Multi‑Key Identity Graph
**문제**: 단일 키 의존 시 연쇄조인 실패·누락 위험.
**해법**: **id:Key** 슈퍼클래스 아래 모든 키를 동등 1급 엔터티로 수집하고, **Same‑As/LinkSet**으로 실체를 클러스터링.

**링크 소스(예)**
- *InvoiceNo(OFCO/SAFEEN/ADP)*, *RotationNo*, *SamsungRef(HVDC‑AGI‑…)*, *HVDCCode*, *Vessel+ETA*.

**클러스터링 규칙(요지)**
1) `RotationNo` 같고, 날짜 창(±7d)·항만 동일 → 같은 **PortCall** 후보.
2) `SamsungRef` 동일 + Subject 패턴 일치 → 같은 **Operation Batch**.
3) `InvoiceNo` 묶음 Σ(lineAmount) = Invoice Total(±2.00%) → 같은 **Invoice**.

---

## 3) SHACL 검증(요약)
- **InvoiceLineShape**
  - `rate:hasEA_* × rate:hasRate_*`의 합 = `fin:lineAmount` ±0.01
  - RatePair 최대 4, 결측 시 0.00 채움
  - `fin:currency = "AED"`, `fin:vat ∈ {0.00, 5.00}`
  - `prov:hasEvidence` **필수**
- **InvoiceShape**
  - Σ(InvoiceLine.fin:lineAmount) = `fin:total` ±2.00%
  - `[EXT]` 라벨 행 금액 **집계 제외**
- **PortCallLinkShape**
  - Subject에 `Rot#` 있으면 `ops:relatesToPortCall` **필수**

---

## 4) Cost/Price Center 매핑 규칙(OFCO 전용)
- **Regex v2.5 + Subject 패턴**(요지)
  - `"SAFEEN"` → `PORT HANDLING CHARGE / CHANNEL TRANSIT CHARGES`
  - `"ADP INV"`+`"Port Dues"` → `PORT HANDLING CHARGE / PORT DUES & SERVICES CHARGES`
  - `"Cargo Clearance"` → `CONTRACT / AF FOR CC`
  - `"Arranging FW Supply"|"FW Supply"` → `CONTRACT / AF FOR FW SA`
  - `"Berthing Arrangement"` → `CONTRACT / AF FOR BA`
  - `"5000 IG FW"` → `AT COST / AT COST(WATER SUPPLY)`

- **PRICE CENTER 3‑Way**
  - **A/B**: Tariff·키워드 기반(예: Channel Crossing/Port Dues/PHC/Equipment/Manpower)
  - **C**: 수수료/Pass/Document(예: Gate Pass, Doc Processing)
  - **규칙**: *C=0 의심 재검토*, *A>B 또는 B<0 시 일부 C로 이동*, *A+B+C=Original_TOTAL, Diff=0.00*

---

## 5) 파이프라인(운영·검증)
1) **Pre‑Prep**: 회전/데스큐/샤프닝(DPI<300 경고)
2) **OCR v2.4**: 레이아웃·토큰 conf 수집
3) **Smart Table Parser 2.1**: 병합셀 해제·세로표 가로화·단위/통화 분리
4) **NLP Refine**: NULL/단위 보정, 추정 금지
5) **Field Tagger**: Parties/IDs/Incoterms/Rotation/Subject
6) **LDG Payload Build**: 해시·CrossLinks·Evidence
7) **Mapping & QC**: EA×Rate 분해, Cost/Price Center 적용, VAT·통화·합계 검증
8) **COST‑GUARD**: 기준요율 대비 Δ% 밴드(PASS/WARN/HIGH/CRITICAL)
9) **Report(7+2)**: Discrepancy Table, Compliance Matrix, DEM/DET Forecast 등

**KPI 게이트**: MeanConf≥0.92, TableAcc≥0.98, NumericIntegrity=1.00 → 미달 시 **ZERO** 중단 로그.

---

## 6) 데이터 맵(Excel/JSON → Ontology)
| Source Field | Ontology Property | Note |
|---|---|---|
| `NO.` | `fin:lineNo` | Row key |
| `SUBJECT` | `fin:subject` | 패턴 매핑 트리거 |
| `SAMSUNG REF` | `id:hasSamsungRef` | 클러스터 anchor |
| `Channel Crossing Charges…` 등 금액열 | `fin:lineAmount` 또는 `rate:hasRate_i`/`rate:hasEA_i` | 금액→Line, EA/Rate 분해 |
| `EA_1..4` | `rate:hasEA_i` | 최대 4 쌍 |
| `Rate_1..4` | `rate:hasRate_i` | 금액=Σ(EA×Rate) |
| `Amount (AED)` | `fin:lineAmount` | 2 decimals |
| `INVOICE NUMBER (OFCO)` | `id:hasOFCOInvNo` | Invoice join |
| `Rotation#`(Subject 내) | `ops:hasRotationNo` | PortCall link |

---

## 7) Report 표준(7+2)
1) **Auto Guard Summary**
1.5) **Risk Assessment**(등급/동인/신뢰도)
2) **Discrepancy Table**(Δ·허용오차·상태)
3) **Compliance Matrix**(UAE·근거 링크)
4) **Auto‑Fill**(Freight/Insurance)
5) **Auto Action Hooks**(명령·가이드)
6) **DEM/DET & Gate‑Out Forecast**
7) **Evidence & Citations**
8) **Weak Spot & Improvements**
9) **Changelog**

---

## 8) 운영 명령 & 자동화 훅
- **인식/검증**: `/ocr_basic {file} mode:LDG+` → KPI Pass 확인 → `/ocr_table`/`/ocr_retry`
- **코스트가드**: `/switch_mode COST-GUARD + /logi-master invoice-audit --AEDonly`
- **매핑**: `/mapping run` → `/run pricecenter map` → `/mapping update pricecenter`
- **규제 체크**: `/logi-master cert-chk`(MOIAT/FANR/TRA)
- **배치**: `/workflow bulk …` → `/export excel`

---

## 9) 운영 규칙(정합성)
- `Σ(BB:BI)=BJ` ±2.00% / EA 결측 시 EA=1.00 & Rate=Amount 규칙 허용(내 ±2.00%)
- VAT=0.00% 또는 5.00% 외 **[MISMATCH]**
- `[EXT]` 메타는 **금액 집계 제외**, 근거(M열) 필수
- **증거(Evidence)**: 파일명/페이지/라인 또는 참조시트(Row) **필수 기록**

---

## 10) 로드맵 (P→Pi→B→O→S + KPI)
- **Prepare(2주)**: 스키마/네임스페이스/IRI 설계, SHACL 초안, 키‑링크 룰 정의
  KPI: 스키마 커버리지 ≥90.00%
- **Pilot(3주)**: 1개 인보이스 묶음(예: OFCO‑INV‑0000181) E2E, Δ오차≤2.00%
  KPI: ZERO 트리거=0, Evidence 100.00%
- **Build(4주)**: CostCenter v2.5·3‑Way 분개·COST‑GUARD 통합
  KPI: Pass율≥95.00%
- **Operate(지속)**: 배치 처리 및 리포트(7+2) 자동 발행
  KPI: TAT ≤ 0.50h/건
- **Scale(지속)**: SAFEEN/ADP 직조인, PortCall API, DEM/DET 2.0 연계
  KPI: 오탐율 ≤ 2.00%

---

## 11) 리스크 & 완화
- **키 불일치/누락**: Multi‑Key 흡수 + 휴리스틱 윈도우(±7d)
- **OCR 품질 저하**: KPI 게이트 + `/ocr_lowres_fix` + ZERO 중단
- **요율 변동**: TariffRef 버전드(유효일) + COST‑GUARD Δ% 밴드

---

## 12) 부록 — Subject→Cost/PriceCenter 예시(발췌)
| Subject 큐 | Cost A | Cost B | PriceCenter |
|---|---|---|
| SAFEEN … Channel Crossing | PORT HANDLING CHARGE | CHANNEL TRANSIT CHARGES | CHANNEL TRANSIT CHARGES |
| ADP INV … Port Dues | PORT HANDLING CHARGE | PORT DUES & SERVICES CHARGES | PORT DUES |
| Agency fee: Cargo Clearance | CONTRACT | AF FOR CC | AGENCY FEE FOR CARGO CLEARANCE |
| Arranging FW Supply | CONTRACT | AF FOR FW SA | SUPPLY WATER 5000IG |
| Berthing Arrangement | CONTRACT(AF FOR BA) | CONTRACT | AGENCY FEE FOR BERTHING ARRANGEMENT |
| 5000 IG FW | AT COST | AT COST(WATER SUPPLY) | SUPPLY WATER 5000IG |

---

## 13) 구현 노트
- 코드베이스: `logiontology/`(mapping/validation/reasoning/rdfio/report/pipeline)
- SHACL Runner 옵션, JSON‑LD 컨텍스트 제공, RDFLib + DuckDB로 라인‑레벨 집계 검증.
- 외부 연계: PortCall(AD Ports)·SAFEEN 청구 스냅샷 → `TariffRef` Evidence로 보관.

---

### 끝. (숫자 2 decimals, ISO 날짜 사용, NDA/PII 마스킹 준수)

---

## SOURCE: CONSOLIDATED-08-communication.md

# CONSOLIDATED-08 — Communication

Canonical communication ontology notes for logistics coordination, auditability, and timestamp handling.

See also:
- [NAMESPACE_REGISTRY.md](NAMESPACE_REGISTRY.md)
- [CONSOLIDATED-09-operations.md](CONSOLIDATED-09-operations.md)

## 1. Scope

This document standardizes communication examples used for email, message, and command traces.

Communication timestamps on the wire use `xsd:dateTime`.

## 2. Canonical Prefix Block

```turtle
@prefix lo: <https://hvdc-project.com/ontology/communication/> .
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix prov: <http://www.w3.org/ns/prov#> .
```

## 3. Canonical Model

| Class / Property | Meaning |
|---|---|
| `lo:EmailMessage` | Email or email-like communication entity |
| `lo:hasIntent` | Intent such as request, inform, confirm, reply |
| `lo:aboutProcess` | Related logistics process |
| `lo:refersTo` | Related BL / DO / invoice / case / shipment object |
| `lo:eventTime` | Canonical communication timestamp using `xsd:dateTime` |
| `lo:projectTag` | Project or workflow tag |

Optional modeling note:

- `time:Instant` may be introduced in future OWL modeling, but curated Markdown examples and operational wire examples must use `xsd:dateTime`.

## 4. Turtle Example

```turtle
@prefix lo: <https://hvdc-project.com/ontology/communication/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

lo:msg-001 a lo:EmailMessage ;
  lo:projectTag "HVDC-001" ;
  lo:eventTime "2025-10-19T09:00:00+04:00"^^xsd:dateTime ;
  lo:hasIntent lo:intent-request ;
  lo:refersTo lo:doc-bl-8899 ;
  lo:aboutProcess lo:process-shipment-a .

lo:msg-002 a lo:EmailMessage ;
  lo:projectTag "HVDC-001" ;
  lo:eventTime "2025-10-19T09:24:00+04:00"^^xsd:dateTime ;
  lo:hasIntent lo:intent-inform ;
  lo:refersTo lo:doc-bl-8899 ;
  lo:aboutProcess lo:process-shipment-a .
```

## 5. SHACL Example

```turtle
@prefix lo: <https://hvdc-project.com/ontology/communication/> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

lo:EmailMessageShape a sh:NodeShape ;
  sh:targetClass lo:EmailMessage ;
  sh:property [
    sh:path lo:projectTag ;
    sh:datatype xsd:string ;
    sh:minCount 1
  ] ;
  sh:property [
    sh:path lo:eventTime ;
    sh:datatype xsd:dateTime ;
    sh:minCount 1
  ] ;
  sh:property [
    sh:path lo:hasIntent ;
    sh:minCount 1
  ] .
```

## 6. SPARQL Example — TAT

```sparql
PREFIX lo: <https://hvdc-project.com/ontology/communication/>
PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

SELECT ?project (AVG(?minutes) AS ?avgTatMin)
WHERE {
  ?request a lo:EmailMessage ;
           lo:projectTag ?project ;
           lo:eventTime ?t1 ;
           lo:hasIntent lo:intent-request .

  ?reply a lo:EmailMessage ;
         lo:projectTag ?project ;
         lo:eventTime ?t2 ;
         lo:hasIntent lo:intent-inform .

  FILTER(?t2 > ?t1)
  BIND((xsd:dateTime(?t2) - xsd:dateTime(?t1)) AS ?delta)
  BIND((?delta / 60000) AS ?minutes)
}
GROUP BY ?project
```

## 7. Canonical Rules

- Use `lo:` explicitly; do not rely on bare `:` examples.
- Use `xsd:dateTime` in prose, TTL, JSON-LD, and SPARQL.
- Keep communication examples consistent with Dubai offset notation where timestamps are concrete.

## 8. QA Checklist

- Confirm every example declares `@prefix lo:`.
- Confirm no canonical SHACL example requires `time:Instant`.
- Confirm timestamps retain explicit timezone offsets in examples.

---

## SOURCE: CONSOLIDATED-09-operations.md

# CONSOLIDATED-09 — Operations

Canonical operations document for KPI reporting, routing analytics, backlog review, and zero-gate decision support.

See also:
- [CONSOLIDATED-02-warehouse-flow.md](CONSOLIDATED-02-warehouse-flow.md)
- [CONSOLIDATED-05-invoice-cost.md](CONSOLIDATED-05-invoice-cost.md)
- [NAMESPACE_REGISTRY.md](NAMESPACE_REGISTRY.md)

## 1. Scope

This document defines the operational reporting layer that consumes canonical routing, OCR, customs, and invoice-audit signals.

## 2. Canonical Prefixes

```turtle
@prefix ops: <https://hvdc-project.com/ontology/operations/> .
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
```

## 3. Canonical Operational Metrics

| Metric | Definition |
|---|---|
| `ops:totalBacklog` | Total non-complete operational cases |
| `ops:siteBacklog` | Backlog by final destination |
| `ops:flowDistribution` | Distribution by `hvdc:hasLogisticsFlowCode` |
| `ops:zeroCandidates` | Cases failing zero-gate or trust-gate checks |
| `ops:costGuardBand` | Risk band from invoice cost review |
| `ops:decision` | Automation decision (`AUTO_PASS`, `HUMAN_REVIEW`, `AUTO_REJECT`) |

## 4. Flow-Aware Operations Policy

- Flow metrics must use `hvdc:hasLogisticsFlowCode` and allow Flow `0` through `5`.
- `AGI/DAS` cases with Flow `<3` are operational violations.
- `MIR/SHU` direct and warehouse-assisted paths remain valid unless another rule blocks them.
- `Flow 5` is a review state that must be visible in dashboards and reports.

## 5. KPI Gates

| KPI | Threshold |
|---|---|
| `invoice-ocr` | `>= 98%` |
| `invoice-audit delta` | `<= 2%` |
| `cost-guard warn rate` | `<= 5%` |
| `hs-risk misclass` | `<= 0.5%` |
| `cert-chk auto-pass` | `>= 90%` |
| `wh-forecast util` | `<= 85%` |
| `weather-tie ETA MAPE` | `<= 12%` |

## 6. Turtle Example

```turtle
@prefix ops: <https://hvdc-project.com/ontology/operations/> .
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

ops:ops-snapshot-2025-10 a ops:OperationSnapshot ;
  ops:reportMonth "2025-10" ;
  ops:totalBacklog 114 ;
  ops:zeroCandidates 12 ;
  ops:generatedAt "2025-10-31T17:00:00+04:00"^^xsd:dateTime .

hvdc:event-ops-agi-001 a hvdc:TransportEvent ;
  hvdc:hasCase "AGI-2025-001" ;
  hvdc:hasFinalLocation "AGI" ;
  hvdc:hasLogisticsFlowCode 3 ;
  hvdc:hasFlowCodeOriginal 1 .
```

## 7. SPARQL Examples

### 7.1 Flow distribution

```sparql
PREFIX hvdc: <https://hvdc-project.com/ontology/core/>

SELECT ?flow (COUNT(?event) AS ?count)
WHERE {
  ?event a hvdc:TransportEvent ;
         hvdc:hasLogisticsFlowCode ?flow .
}
GROUP BY ?flow
ORDER BY ?flow
```

### 7.2 Offshore routing violations

```sparql
PREFIX hvdc: <https://hvdc-project.com/ontology/core/>

SELECT ?caseCode ?dest ?flow
WHERE {
  ?event a hvdc:TransportEvent ;
         hvdc:hasCase ?caseCode ;
         hvdc:hasFinalLocation ?dest ;
         hvdc:hasLogisticsFlowCode ?flow .
  FILTER(?dest IN ("AGI", "DAS") && ?flow < 3)
}
ORDER BY ?caseCode
```

## 8. Dashboard / Report Interpretation

- `healthy`: no offshore routing violations and KPI gates within target
- `degraded`: warnings or review queue accumulation
- `off-track`: KPI breaches or zero-gate blockers requiring action

## 9. Cost Guard Consumption Rule

Operations reports may show:

- `costGuardBand`
- `decision`

They must not collapse those into a single ambiguous verdict field.

## 10. Canonical Conclusion

Operational analytics in this bundle are valid only when they consume:

- canonical Flow Code values (`0` through `5`)
- canonical event/property naming (`hvdc:TransportEvent`, `hvdc:hasLogisticsFlowCode`)
- canonical band/decision semantics from [CONSOLIDATED-05-invoice-cost.md](CONSOLIDATED-05-invoice-cost.md)
