# CORE_DOCUMENTATION_MASTER

Canonical master index for the Logi ontology core document bundle.
This file is generated. It reports canonical sources, namespace policy, and build metadata.

<!-- GENERATED FILE: do not edit manually. Rebuild with scripts/build_logi_master.py -->

| Field | Value |
|---|---|
| generated_at | 2026-03-17T23:42:23+04:00 |
| source_commit | `cc410b6` |
| file_hash | `db14a18ea56f23eb2d0bb16e07edb73d6ab58713259e5a4ff728b192442919a8` |
| measurement_status | `source-dataset-unavailable` |
| triple_count | `unavailable` |
| case_count | `unavailable` |

## Canonicalization Rules

- `CONSOLIDATED-02-warehouse-flow.md` is the authoritative Flow Code v3.5 narrative/spec.
- `hvdc:TransportEvent` + `hvdc:hasLogisticsFlowCode` is the canonical event/property pairing.
- `hvdc:hasFlowCode` and `hvdc:LogisticsFlow` are legacy or derived aliases only.
- `MIR/SHU` allow Flow `1` and `2`; `AGI/DAS` require Flow `3` or `4` with MOSB mandatory.
- When the authoritative dataset is not present in the repository, `triple_count` and `case_count` remain `unavailable`.

## Canonical Documents

| File | Purpose | Lines | SHA256 |
|---|---|---:|---|
| [Namespace Registry](NAMESPACE_REGISTRY.md) | Canonical namespace policy and alias mapping. | 68 | `28b48f4cfe32` |
| [Core Framework / Infrastructure](CONSOLIDATED-01-core-framework-infra.md) | Node model, routing policy, and core operational constraints. | 170 | `8c4edaf32445` |
| [Warehouse / Flow Code](CONSOLIDATED-02-warehouse-flow.md) | Canonical Flow Code v3.5 definitions and validation semantics. | 244 | `ba3ee524fbb2` |
| [Document OCR / Guardian](CONSOLIDATED-03-document-ocr.md) | OCR gate thresholds, SHACL policy, and PASS/FAIL examples. | 235 | `a503387eee14` |
| [Barge / Bulk Cargo](CONSOLIDATED-04-barge-bulk-cargo.md) | Bulk cargo and LCT-specific flow behavior. | 597 | `68b97ebbd36c` |
| [Invoice / Cost Guard](CONSOLIDATED-05-invoice-cost.md) | Band-vs-decision policy for invoice cost review. | 158 | `e92689ecdc01` |
| [Material Handling](CONSOLIDATED-06-material-handling.md) | Deployable material-handling ontology spec aligned to canonical Flow Code rules. | 178 | `dee90d43513f` |
| [Port Operations](CONSOLIDATED-07-port-operations.md) | Port assignment and port-side logistics control. | 704 | `3bef5286c376` |
| [Communication](CONSOLIDATED-08-communication.md) | Communication ontology examples using canonical timestamp and prefix rules. | 120 | `39dfddf5c67d` |
| [Operations](CONSOLIDATED-09-operations.md) | Operational reporting, KPI, and analytics model. | 125 | `cbb440fd7432` |

## Reference Artifacts

| File | Purpose | Lines | SHA256 |
|---|---|---:|---|
| [Flow Code Schema TTL](flow-code-v35-schema.ttl) | Canonical SHACL / OWL flow schema. | 490 | `46ee82d6c23a` |
| [Flow Code Quick Reference](FLOW_CODE_V35_QUICK_REFERENCE.md) | Operator-oriented reference card aligned to canonical naming. | 55 | `162aeeb0b9ed` |
| [Flow Code Integration Report](FLOW_CODE_V35_INTEGRATION_REPORT.md) | Integration summary without stale dataset counts. | 46 | `99539b4b5c4f` |
| [Material Handling Appendix](CONSOLIDATED-06-material-handling-appendix-source-preserved.md) | Historical source-preserved appendix excluded from canonical validation. | 3485 | `3ab51aa2379e` |

## Usage

- Read the namespace registry first if you need canonical prefixes or alias mappings.
- Read `CONSOLIDATED-02-warehouse-flow.md` before editing any routing or Flow Code logic.
- Treat the material-handling appendix as historical preservation, not as normative specification.
- Rebuild this file and the merged bundle with `python scripts/build_logi_master.py`.
