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
