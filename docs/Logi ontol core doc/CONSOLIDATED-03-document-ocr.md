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
