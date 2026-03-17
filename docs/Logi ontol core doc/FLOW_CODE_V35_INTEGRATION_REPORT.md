# FLOW_CODE_V35_INTEGRATION_REPORT

Canonical integration summary for Flow Code v3.5 across the curated Logi ontology documents.

## Summary

The canonical Flow Code contract is:

- event class: `hvdc:TransportEvent`
- final flow property: `hvdc:hasLogisticsFlowCode`
- original flow property: `hvdc:hasFlowCodeOriginal`
- offshore destinations `AGI/DAS` require Flow `3` or `4`
- onshore destinations `MIR/SHU` allow Flow `1` and `2`

## Integration Notes

| Domain | Canonical alignment |
|---|---|
| Core framework | References canonical routing policy from `CONSOLIDATED-02` |
| Material handling | Uses `mh:hasLogisticsFlowCode` as a domain-specific equivalent |
| Bulk cargo | Uses `debulk:hasLogisticsFlowCode` as a domain-specific equivalent |
| Port operations | Uses `port:assignedFlowCode` only as initial assignment |
| OCR / document guardian | Uses `ldg:extractedFlowCode` only as extracted value |
| Operations | Consumes canonical final flow and review-state semantics |

## Deprecated / Transitional Names

These may appear in preserved historical material but are not canonical for new examples:

- `hvdc:hasFlowCode`
- `hvdc:LogisticsFlow`
- `http://samsung.com/project-logistics#`

## Canonical References

- [NAMESPACE_REGISTRY.md](NAMESPACE_REGISTRY.md)
- [CONSOLIDATED-02-warehouse-flow.md](CONSOLIDATED-02-warehouse-flow.md)
- [flow-code-v35-schema.ttl](flow-code-v35-schema.ttl)
- [FLOW_CODE_V35_QUICK_REFERENCE.md](FLOW_CODE_V35_QUICK_REFERENCE.md)

## Dataset Measurement Status

- `case_count`: `unavailable`
- `triple_count`: `unavailable`

Stale hard-coded counts are intentionally removed from this integration report until the authoritative source dataset is restored to the repository.
