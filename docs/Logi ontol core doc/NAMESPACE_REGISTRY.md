# NAMESPACE_REGISTRY

Canonical namespace registry for the HVDC Logi ontology bundle.

This file is normative for examples, SHACL snippets, JSON-LD contexts, and SPARQL queries in the curated documentation set.

## Canonical Prefixes

| Prefix | Canonical IRI | Scope |
|---|---|---|
| `hvdc` | `https://hvdc-project.com/ontology/core/` | Core logistics entities, TransportEvent, shared operational properties |
| `mh` | `https://hvdc-project.com/ontology/material-handling/` | Material-handling domain |
| `debulk` | `https://hvdc-project.com/ontology/bulk-cargo/` | Barge / bulk cargo domain |
| `port` | `https://hvdc-project.com/ontology/port-operations/` | Port-operations domain |
| `ldg` | `https://hvdc-project.com/ontology/document-guardian/` | Document guardian / OCR domain |
| `lo` | `https://hvdc-project.com/ontology/communication/` | Communication domain |
| `ops` | `https://hvdc-project.com/ontology/operations/` | Operations reporting / KPI domain |

## Canonical Usage Rules

- Use `hvdc:TransportEvent` as the primary operational event class in canonical examples.
- Use `hvdc:hasLogisticsFlowCode` as the canonical final Flow Code property.
- Use `hvdc:hasFlowCodeOriginal` only to preserve the pre-upgrade Flow Code value.
- Use `xsd:dateTime` for wire/example timestamps in Markdown and SPARQL examples.
- Use domain-specific prefixes such as `mh:`, `debulk:`, `port:`, `ldg:`, `lo:`, and `ops:` only when the example is truly domain-specific.

## Deprecated Aliases

These identifiers may appear in historical documents or preserved appendix material, but they are not canonical for new examples.

| Deprecated Identifier | Replacement | Status |
|---|---|---|
| `http://samsung.com/project-logistics#` | `https://hvdc-project.com/ontology/core/` | Deprecated legacy core namespace |
| `http://example.com/ldg#` | `https://hvdc-project.com/ontology/document-guardian/` | Deprecated sample namespace |
| `https://example.com/hvdc#` | `https://hvdc-project.com/ontology/core/` | Deprecated sample namespace |
| bare `:` communication examples | `lo:` | Deprecated example style |
| `hvdc:hasFlowCode` | `hvdc:hasLogisticsFlowCode` | Deprecated legacy / derived alias |
| `hvdc:LogisticsFlow` | `hvdc:TransportEvent` + flow properties | Deprecated legacy / derived class reference |

## Alias Mapping Notes

- `mh:hasLogisticsFlowCode` is a domain-specific equivalent of `hvdc:hasLogisticsFlowCode`.
- `debulk:hasLogisticsFlowCode` is a domain-specific equivalent of `hvdc:hasLogisticsFlowCode`.
- `port:assignedFlowCode` is the port-stage initial Flow Code assignment and is not the canonical final flow property.
- `ldg:extractedFlowCode` is the OCR-extracted value and is not the canonical final flow property.

## Example Prefix Block

```turtle
@prefix hvdc: <https://hvdc-project.com/ontology/core/> .
@prefix mh: <https://hvdc-project.com/ontology/material-handling/> .
@prefix debulk: <https://hvdc-project.com/ontology/bulk-cargo/> .
@prefix port: <https://hvdc-project.com/ontology/port-operations/> .
@prefix ldg: <https://hvdc-project.com/ontology/document-guardian/> .
@prefix lo: <https://hvdc-project.com/ontology/communication/> .
@prefix ops: <https://hvdc-project.com/ontology/operations/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .
@prefix sh: <http://www.w3.org/ns/shacl#> .
```

## Maintenance Rule

When a namespace or alias policy changes:

1. Update this registry first.
2. Update the curated documents that use the affected prefix.
3. Rebuild `CORE_DOCUMENTATION_MASTER.md` and `LOGI_ONTOL_CORE_MERGED.md`.
4. Run `python scripts/validate_logi_docs.py`.
