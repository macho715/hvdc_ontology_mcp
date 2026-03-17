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
