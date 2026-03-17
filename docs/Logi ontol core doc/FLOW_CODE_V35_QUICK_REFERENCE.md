# FLOW_CODE_V35_QUICK_REFERENCE

Quick operator reference aligned to the canonical Flow Code v3.5 specification.

Authoritative source:

- [CONSOLIDATED-02-warehouse-flow.md](CONSOLIDATED-02-warehouse-flow.md)

## Flow Code 0-5

| Code | Pattern | Use |
|---|---|---|
| `0` | Pre-arrival | Planning / not yet route-complete |
| `1` | `Port -> Site` | Valid onshore direct path |
| `2` | `Port -> WH -> Site` | Valid onshore warehouse-assisted path |
| `3` | `Port -> MOSB -> Site` | Valid offshore minimum path |
| `4` | `Port -> WH -> MOSB -> Site` | Valid offshore full path |
| `5` | Mixed / incomplete / anomaly | Review queue only |

## Destination Rule

- `MIR/SHU`: Flow `1` and `2` remain valid.
- `AGI/DAS`: Flow `3` or `4` only; MOSB is mandatory.

## Canonical Properties

- `hvdc:hasLogisticsFlowCode` — canonical final Flow Code
- `hvdc:hasFlowCodeOriginal` — preserved pre-upgrade value
- `hvdc:hasFlowOverrideReason` — reason for automatic or policy override

Deprecated alias:

- `hvdc:hasFlowCode` — legacy / derived alias only

## Canonical SPARQL

```sparql
PREFIX hvdc: <https://hvdc-project.com/ontology/core/>

SELECT ?caseCode ?dest ?flow
WHERE {
  ?event a hvdc:TransportEvent ;
         hvdc:hasCase ?caseCode ;
         hvdc:hasFinalLocation ?dest ;
         hvdc:hasLogisticsFlowCode ?flow .
}
ORDER BY ?caseCode
```

## Dataset Measurement Status

- `case_count`: `unavailable`
- `triple_count`: `unavailable`

Counts stay unavailable in the documentation bundle while the authoritative runtime dataset is not present in the repository.
