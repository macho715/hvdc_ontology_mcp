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
