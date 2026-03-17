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
