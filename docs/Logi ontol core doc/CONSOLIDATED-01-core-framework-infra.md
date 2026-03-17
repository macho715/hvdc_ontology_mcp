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
