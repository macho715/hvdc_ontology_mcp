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
