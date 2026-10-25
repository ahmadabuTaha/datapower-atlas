# DataPower Atlas — Taxonomy Reference

**Purpose:** Canonical classification and semantic mapping for IBM DataPower architectural evidence.

## 1. Overview

The DataPower Atlas taxonomy provides a controlled vocabulary and executable semantic model for interpreting IBM DataPower configuration exports.

It establishes consistent classifications for configuration objects, properties, references, relationships, endpoints, files, and sensitivity.

The taxonomy is a foundational component of the Atlas evidence-processing pipeline.

| Objective | Description |
|---|---|
| Standardization | Establish consistent architectural terminology across tools and generated evidence |
| Classification | Identify the type and meaning of configuration elements |
| Semantic interpretation | Interpret configuration properties in the context of their owning objects |
| Reference extraction | Identify explicit dependencies from configuration evidence |
| Relationship resolution | Map references to valid targets using defined resolution strategies |
| Traceability | Preserve the connection between raw configuration and derived architectural evidence |
| Extensibility | Support additional DataPower object types and semantic mappings |
| Determinism | Reduce inconsistent interpretation between pipeline components |
| Evidence integrity | Prevent unsupported assumptions from becoming confirmed architectural relationships |

### Core principle

**Taxonomies define how evidence is classified and interpreted. They do not replace the evidence itself.**

Raw DataPower configuration remains authoritative.

---

## 2. Taxonomy File Catalog

The taxonomy is organized into eight interconnected YAML files.

| # | File | Classification Scope | Primary Responsibility |
|---|---|---|---|
| 1 | `datapower_objects.yaml` | Object taxonomy | Defines recognized DataPower configuration object types and canonical classifications |
| 2 | `datapower_properties.yaml` | Property taxonomy | Defines property semantics within the context of a source object |
| 3 | `reference_types.yaml` | Reference taxonomy | Defines supported reference classifications |
| 4 | `relationship_types.yaml` | Relationship taxonomy | Defines the semantic meaning of relationships between architectural elements |
| 5 | `endpoint_types.yaml` | Endpoint taxonomy | Classifies network endpoints and their architectural roles |
| 6 | `file_types.yaml` | File taxonomy | Classifies artifacts contained in DataPower exports |
| 7 | `sensitivity.yaml` | Sensitivity taxonomy | Supports classification and handling of sensitive configuration evidence |
| 8 | `cross_taxonomy.yaml` | Cross-taxonomy mappings | Connects object types, properties, references, relationships, endpoints, and resolution strategies |

### Validated taxonomy baseline

The following metrics were reported by the available cross-taxonomy validation record.

| Metric | Validated Count |
|---|---:|
| DataPower object types | 64 |
| Property source types | 18 |
| Reference types | 18 |
| Relationship types | 28 |
| Endpoint types | 11 |
| Cross-taxonomy mappings | 50 |
| File-type buckets | 12 |
| Sensitivity levels | 8 |
| Validation errors | 0 |
| Validation warnings | 0 |
| Validation result | PASS |

These figures represent the recorded validation baseline, not an independently verified count of the current repository revision.

---

## 3. Taxonomy Architecture

The taxonomy separates different architectural concepts rather than combining them into a single classification.

| Layer | Architectural Question | Example |
|---|---|---|
| Object | What configuration entity exists? | `multi_protocol_gateway` |
| Property | What does a configured property represent? | `stylepolicy` |
| Reference | What kind of reference does the property contain? | `datapower_object_reference` |
| Relationship | What is the semantic relationship? | `uses_processing_policy` |
| Endpoint | What kind of network destination is represented? | Backend endpoint |
| File | What kind of referenced artifact exists? | XSLT or GatewayScript |
| Sensitivity | How should evidence be handled? | Sensitive configuration content |
| Cross-taxonomy | How do these classifications connect? | MPGW processing-policy mapping |

### Semantic interpretation sequence

```text
Raw DataPower Configuration
          |
          v
Object Classification
          |
          v
Property Interpretation
          |
          v
Reference Classification
          |
          v
Cross-Taxonomy Mapping
          |
          v
Resolution Strategy
          |
          v
Resolved / Unresolved Evidence
          |
          v
Architectural Relationship
          |
          v
Service & Operation Journeys
```

---

## 4. DataPower Object Taxonomy

**File:** `datapower_objects.yaml`

This taxonomy establishes the canonical identity and classification of DataPower configuration objects.

### Responsibilities

| Responsibility | Description |
|---|---|
| Object recognition | Identify supported configuration object types |
| Canonical naming | Assign stable internal object-type identifiers |
| Object categorization | Group objects according to their technical function |
| Indexing support | Supply object classification to the configuration parser |
| Classification consistency | Prevent multiple tools from independently naming the same object |
| Extension support | Allow new object types to be added through controlled taxonomy changes |

### Representative object classifications

The following object identifiers were observed in the available parser validation evidence.

| Functional Area | Canonical Object Types |
|---|---|
| Gateway services | `multi_protocol_gateway`, `web_service_proxy`, `tcp_proxy` |
| Processing | `style_policy`, `processing_rule`, `processing_action`, `matching_rule` |
| Protocol handlers | `http_source_protocol_handler`, `https_source_protocol_handler`, `mq_source_protocol_handler`, `raw_source_protocol_handler` |
| XML processing | `xml_manager`, `parse_settings` |
| TLS | `tls_client_profile`, `tls_server_profile` |
| Cryptography | `crypto_certificate`, `crypto_key`, `crypto_identification_credentials`, `crypto_validation_credentials` |
| MQ integration | `mq_queue_manager_legacy`, `mq_v9_queue_manager`, `mq_v9_source_handler` |
| API gateway | `api_connect_gateway_service`, `api_rule`, `api_routing_action`, `api_security_action` |
| API assembly | `assembly_function`, `assembly_function_call`, `assembly_rate_limit_action` |
| Routing configuration | `url_map`, `url_rewrite_policy` |
| Operational configuration | `log_target`, `domain_settings`, `deployment_policy` |
| Security configuration | `aaa_policy`, `jwt_generator`, `password_alias` |

This table is representative rather than an exhaustive enumeration of all 64 validated object types.

### Object identity

| Identity Element | Purpose |
|---|---|
| Environment | Identifies the source environment |
| Domain | Establishes DataPower domain scope |
| Canonical type | Identifies the normalized object type |
| Logical name | Identifies the configured object |
| Source provenance | Connects the object to its raw evidence |

Object names alone are insufficient for cross-domain identification.

---

## 5. DataPower Property Taxonomy

**File:** `datapower_properties.yaml`

The property taxonomy defines how a configuration property should be interpreted within its source object.

A property name does not necessarily have the same meaning in every object context.

### Design principles

| Principle | Meaning |
|---|---|
| `context_required` | Property interpretation depends on the source object type |
| `properties_are_not_objects` | A configuration property must not automatically become a separate architectural object |
| `relationships_must_be_property_evidence_backed` | Relationships require explicit supporting property evidence |
| `preserve_raw_property_value` | Original configuration values must remain available for verification |

### Property classification concepts

| Property Kind | Meaning | Illustrative Use |
|---|---|---|
| Object reference | Property refers to another DataPower object | XML Manager reference |
| Endpoint | Property identifies a network destination | Backend URL |
| Compound reference | Property contains multiple semantically distinct references | Policy match declaration |
| File reference | Property identifies an external or local artifact | XSLT or GatewayScript URI |
| Configuration value | Property describes behavior or configuration rather than a target | Processing settings |

The exact executable vocabulary is defined by the YAML files; illustrative descriptions do not introduce additional canonical values.

### Property semantics example

| Source Object | Property | Interpretation | Target |
|---|---|---|---|
| `multi_protocol_gateway` | `stylepolicy` | Object reference | `style_policy` |
| `multi_protocol_gateway` | `xml-manager` | Object reference | `xml_manager` |
| `multi_protocol_gateway` | `ssl-client` | Object reference | `tls_client_profile` |
| `multi_protocol_gateway` | `front-protocol` | Multi-type object reference | Supported front-side protocol handlers |
| `multi_protocol_gateway` | `backend-url` | Endpoint | Backend endpoint |
| `style_policy` | `match` | Compound reference | Matching rule and processing rule |

---

## 6. Reference Type Taxonomy

**File:** `reference_types.yaml`

The reference taxonomy classifies dependencies extracted from configuration properties.

### Reference concepts

| Concept | Description |
|---|---|
| Source | Object containing the reference |
| Reference type | Classification of the referenced target |
| Raw reference | Original value from configuration |
| Target type | Expected target classification |
| Resolution status | Whether the target can be established |
| Provenance | Configuration evidence supporting the reference |

### Observed reference families

| Reference Family | Description | Example |
|---|---|---|
| `object_reference` | Reference to a DataPower configuration object | Processing policy |
| `file_reference` | Reference to an artifact or file | `local:///` XSLT |
| `endpoint_reference` | Reference to a network destination | Backend URL |

These are the observed extraction families, not the complete enumeration of the 18 canonical reference types.

### Reference evidence rules

| Condition | Required Behavior |
|---|---|
| Reference exists and target is found | Preserve reference and resolved target |
| Reference exists and target is missing | Preserve unresolved reference |
| Multiple possible targets exist | Preserve ambiguity |
| Referenced artifact is unavailable | Preserve original file reference |
| Reference is not supported by taxonomy | Record a specific taxonomy or interpretation gap |
| Reference belongs to another domain | Do not silently resolve across domains |

**A reference record is evidence of a configured dependency, not proof of successful resolution or runtime execution.**

---

## 7. Relationship Type Taxonomy

**File:** `relationship_types.yaml`

Relationship types describe the architectural meaning of references after semantic interpretation.

### Representative relationships

| Relationship Type | Source | Target | Meaning |
|---|---|---|---|
| `uses_processing_policy` | MPGW | Style Policy | Gateway references a processing policy |
| `uses_xml_manager` | MPGW | XML Manager | Gateway references an XML Manager |
| `uses_tls_client_profile` | MPGW | TLS Client Profile | Gateway references a TLS client configuration |
| `uses_front_side_handler` | MPGW | Protocol Handler | Gateway references an ingress handler |
| `routes_to_backend` | MPGW | Backend Endpoint | Gateway declares a backend endpoint |
| `uses_matching_rule` | Style Policy | Matching Rule | Policy references a matching rule |
| `contains_processing_rule` | Style Policy | Processing Rule | Policy associates a processing rule with a match |

The relationship catalog must distinguish between a configured association and evidenced operation behavior.

For example, `routes_to_backend` is a configured relationship and does not by itself establish actual operation egress.

---

## 8. Endpoint Type Taxonomy

**File:** `endpoint_types.yaml`

The endpoint taxonomy supports consistent classification of network destinations and their roles.

### Architectural distinctions

| Endpoint Concern | Description |
|---|---|
| Ingress | Where requests enter DataPower |
| Configured backend | Backend configured on a service |
| Dynamically selected destination | Destination determined through processing logic |
| Script-initiated outbound connection | Outbound network operation initiated by a script |
| Messaging destination | Network or messaging destination referenced by an integration configuration |
| Actual operation egress | Outbound destination supported by operation-level evidence |

These are architectural distinctions used in analysis, not a claim that each is a literal key in `endpoint_types.yaml`.

### Endpoint interpretation rules

| Evidence | Permitted Conclusion | Not Automatically Proven |
|---|---|---|
| Configured backend URL | Backend is configured | Operation invokes it |
| Dynamic backend configuration | Backend selection may occur dynamically | Final destination |
| `skip-backside` configuration | Standard backside handling is affected | No outbound communication |
| Resolved GatewayScript outbound call | Script contains outbound behavior | Every operation executes it |
| Missing referenced script | Script dependency exists | Script behavior |
| HTTPS endpoint | HTTPS transport is configured | Mutual TLS |

---

## 9. File Type Taxonomy

**File:** `file_types.yaml`

The file taxonomy classifies artifacts discovered in DataPower exports.

### File classification responsibilities

| Responsibility | Description |
|---|---|
| Inventory classification | Assign recognized file categories |
| Extension interpretation | Classify supported artifact formats |
| File resolution support | Support lookup of referenced artifacts |
| Provenance preservation | Retain original file location |
| Sensitivity integration | Support file-level sensitivity metadata |
| Gap identification | Distinguish unavailable files from unsupported classification |

### Representative artifacts

| Artifact | Architectural Relevance |
|---|---|
| CFG | DataPower configuration source |
| XSLT | Transformation and potentially routing or processing logic |
| GatewayScript | Scripted processing and outbound interaction |
| WSDL | Web-service interface definitions |
| XSD | XML schema definitions |
| Certificate | TLS and cryptographic configuration |
| Key material | Cryptographic dependencies |
| Supporting XML | Policy, transformation, or configuration dependencies |

This is a representative artifact list, not the complete set of 12 validated file-type buckets.

### File resolution rules

| Scenario | Required Interpretation |
|---|---|
| Referenced file is available | Resolved artifact |
| File reference exists but artifact is absent | Unresolved file dependency |
| File scheme is platform-managed | Apply the relevant scheme-specific resolution policy |
| File cannot be classified | Retain original evidence and a specific classification-gap reason |
| File exists in another export | Do not assume it resolves the current export's reference |

**No resolved file does not mean no file reference.**

---

## 10. Sensitivity Taxonomy

**File:** `sensitivity.yaml`

The sensitivity taxonomy supports consistent handling of sensitive configuration data.

### Responsibilities

| Area | Responsibility |
|---|---|
| Detection | Identify configured sensitivity patterns |
| Classification | Assign supported sensitivity classifications |
| Inventory integration | Associate sensitivity findings with files |
| Evidence protection | Support sanitized evidence processing |
| Traceability | Retain sensitivity scan status |
| Reporting | Expose detected sensitivity information without unnecessarily disclosing secrets |

### Required file-inventory runtime fields

| Field | Purpose |
|---|---|
| `sensitivity_scan_status` | Records the sensitivity scan state |
| `contains_sensitive_content` | Indicates whether sensitive content was detected |
| `detected_secret_count` | Records the number of detected secrets |
| `detected_sensitivity_types` | Records the detected sensitivity classifications |
| `sanitized_content_available` | Indicates availability of sanitized evidence |
| `sensitivity_scan_timestamp` | Records when scanning occurred |

The eight validated sensitivity levels should be documented using their exact YAML identifiers rather than reconstructed from assumptions.

---

## 11. Cross-Taxonomy Mapping

**File:** `cross_taxonomy.yaml`

**Status in available source:** `v1_executable_semantic_mapping`

The cross-taxonomy is the executable semantic bridge used by the Reference Extractor and Relationship Resolver.

It connects source object types and properties to reference types, target types, relationships, and resolution strategies.

### Mapping structure

| Field | Responsibility |
|---|---|
| `mapping_id` | Unique identifier for a semantic mapping |
| `source_type` | Canonical source object type |
| `property_name` | Configuration property being interpreted |
| `property_kind` | Semantic property classification |
| `reference_type` | Type of extracted reference |
| `target_type` | Expected canonical target type |
| `target_type_set` | Allowed target types for multi-type references |
| `relationship_type` | Resulting architectural relationship |
| `resolution_strategy` | Strategy used to resolve the reference |
| `argument_position` | Argument index for compound references |
| `semantic_role` | Role of a specific argument within a compound reference |

Not every field is required for every mapping.

### Representative executable mappings

| Mapping ID | Source Type | Property | Target | Relationship |
|---|---|---|---|---|
| `mpgw_stylepolicy` | `multi_protocol_gateway` | `stylepolicy` | `style_policy` | `uses_processing_policy` |
| `mpgw_xml_manager` | `multi_protocol_gateway` | `xml-manager` | `xml_manager` | `uses_xml_manager` |
| `mpgw_tls_client` | `multi_protocol_gateway` | `ssl-client` | `tls_client_profile` | `uses_tls_client_profile` |
| `mpgw_front_protocol` | `multi_protocol_gateway` | `front-protocol` | Protocol handler type set | `uses_front_side_handler` |
| `mpgw_backend_url` | `multi_protocol_gateway` | `backend-url` | Backend endpoint | `routes_to_backend` |
| `stylepolicy_match_matching` | `style_policy` | `match` argument 1 | `matching_rule` | `uses_matching_rule` |
| `stylepolicy_match_rule` | `style_policy` | `match` argument 2 | `processing_rule` | `contains_processing_rule` |

### Resolution strategies

| Strategy | Domain Scope | Behavior |
|---|---|---|
| `same_domain_exact_name` | Same domain | Exact name matching with unique target requirement |
| `same_domain_exact_name_multi_type` | Same domain | Exact name matching against an allowed target-type set |
| `file_inventory_lookup` | Same export | Resolves file references through inventory lookup and DataPower URI normalization |
| `endpoint_parse` | No object-domain scope | Parses explicitly configured endpoint values |

### Example: MPGW processing-policy mapping

```yaml
- mapping_id: mpgw_stylepolicy
  source_type: multi_protocol_gateway
  property_name: stylepolicy
  property_kind: object_reference
  reference_type: datapower_object_reference
  target_type: style_policy
  relationship_type: uses_processing_policy
  resolution_strategy: same_domain_exact_name
```

Interpretation:

| Step | Result |
|---|---|
| 1 | Identify a `multi_protocol_gateway` object |
| 2 | Read its `stylepolicy` property |
| 3 | Classify the property as an object reference |
| 4 | Identify the expected target type as `style_policy` |
| 5 | Apply exact-name resolution within the same domain |
| 6 | Create the supported relationship or preserve unresolved evidence |

---

## 12. Taxonomy Dependencies

| Taxonomy | Depends On | Consumed By |
|---|---|---|
| Objects | Canonical object definitions | CFG parser, relationship resolver |
| Properties | Source-object context | Property interpretation and reference extraction |
| References | Reference classifications | Reference extractor |
| Relationships | Relationship classifications | Relationship resolver and Journey builders |
| Endpoints | Endpoint classifications | Endpoint extractor and architecture analysis |
| Files | Artifact classifications | File inventory and file resolver |
| Sensitivity | Sensitivity definitions | Sensitivity scanner and file inventory |
| Cross-taxonomy | Objects, properties, references, relationships, endpoints, files, sensitivity | Reference extractor and relationship resolver |

The dependency graph must remain consistent: a cross-taxonomy mapping should not refer to undefined canonical types, relationships, or strategies.

---

## 13. Validation

Taxonomy validation is a mandatory prerequisite to generating architectural evidence.

### Validation objectives

| Validation | Expected Outcome |
|---|---|
| YAML structure | Files can be parsed correctly |
| Required definitions | Required taxonomy sections exist |
| Canonical identifiers | Supported identifiers are consistent |
| Cross-taxonomy dependencies | Referenced types and mappings are valid |
| Resolution strategies | Referenced strategies are defined |
| Classification rules | Prohibited generic labels are not used as classifications |
| Sensitivity fields | Required runtime metadata fields are defined |
| Consistency | Conflicting or invalid mappings are reported |

### Validation command

```bash
python tools/validate_taxonomies.py \
  --taxonomy-dir taxonomy
```

The command above follows the available validator's documented interface. Confirm the executable filename against the checked-out repository revision.

### Validation outcomes

| Outcome | Meaning | Pipeline Action |
|---|---|---|
| PASS | Validation completed without errors | Continue |
| Warning | A non-fatal issue was reported | Review before accepting results |
| FAILED | Taxonomy validation error | Stop downstream processing |
| Fatal loading error | Required file or schema could not be loaded | Correct the source before rerunning |

---

## 14. Taxonomy Governance

Taxonomy changes affect the interpretation of architectural evidence and must therefore be controlled.

### Change management

| Change Type | Example | Required Action |
|---|---|---|
| Object extension | Add a newly supported DataPower object | Update object taxonomy and validate |
| Property extension | Add semantics for a supported property | Update property taxonomy |
| Reference extension | Support a new reference type | Update reference definitions |
| Relationship extension | Introduce a new supported relationship | Update relationship definitions and mappings |
| Endpoint extension | Add an endpoint classification | Update endpoint taxonomy |
| File extension | Recognize another artifact type | Update file taxonomy and classification tests |
| Sensitivity extension | Add supported sensitivity rules | Update sensitivity taxonomy |
| Cross-mapping extension | Connect an existing property to a target | Update cross-taxonomy |
| Defect correction | Correct a demonstrably incorrect mapping | Add focused regression evidence |

### Governance principles

| Principle | Requirement |
|---|---|
| Evidence-first | Changes must be supported by actual configuration evidence or a justified semantic contract |
| Additive evolution | Prefer extending the taxonomy without destabilizing validated behavior |
| No generic catch-all labels | Use precise classification or explicit gap reasons |
| Deterministic mappings | Equivalent inputs must produce equivalent classifications |
| Domain isolation | Resolution must not borrow unsupported evidence across environments |
| Provenance | Derived evidence must remain traceable to source artifacts |
| Frozen components | Reopen validated components only for reproducible defects, concrete contradictions, or broken downstream requirements |
| Regression protection | Validate downstream effects before accepting changes |

---

## 15. Classification and Evidence Rules

| Rule | Correct Interpretation | Prohibited Interpretation |
|---|---|---|
| Raw evidence authority | Raw configuration is authoritative | Generated indexes override source evidence |
| Explicit references | Preserve all supported references | Drop references whose targets are unavailable |
| Resolution | Resolve only with supported evidence | Infer targets from naming similarity |
| Domain scope | Respect environment and domain identity | Borrow another environment's evidence |
| Missing artifacts | Preserve unresolved dependency | Assume referenced logic does not exist |
| Backend configuration | Record configured backend | Treat it as proven runtime egress |
| Semantic uncertainty | Preserve certainty and provenance | Upgrade uncertainty without new evidence |
| Classification gaps | Record precise missing-support reasons | Use vague labels such as `Other` or `Unknown` |
| Taxonomy changes | Validate and regression-test | Modify mappings without checking downstream effects |

---

## 16. Relationship to the Atlas Pipeline

| Pipeline Stage | Taxonomy Contribution |
|---|---|
| Taxonomy validation | Ensures semantic definitions are internally consistent |
| File inventory | Classifies discovered export artifacts |
| Sensitivity scanning | Applies sensitivity classifications |
| CFG parsing | Identifies canonical DataPower object types |
| Reference extraction | Interprets properties and creates typed references |
| Relationship resolution | Resolves typed references into architectural relationships |
| Endpoint extraction | Classifies supported network endpoints |
| File reference resolution | Resolves referenced artifacts against available evidence |
| Service Journey building | Aggregates classified service dependencies |
| Operation Journey building | Reconstructs supported operation-level paths |
| Journey quality analysis | Identifies evidence gaps and quality conditions |

### Architectural boundary

The taxonomy supports AS-IS reconstruction.

It does not determine modernization strategy, replacement-product suitability, or target architecture.

Those decisions belong to subsequent Atlas analysis layers and must be grounded in the reconstructed evidence.

---

## 17. Maintenance Checklist

Before accepting a taxonomy change:

- [ ] The classification is specific and justified.
- [ ] Canonical identifiers are consistent.
- [ ] Source-object context is preserved.
- [ ] Cross-taxonomy references are valid.
- [ ] Resolution strategies are explicitly defined.
- [ ] Existing mappings remain compatible unless a defect requires correction.
- [ ] Unresolved evidence remains visible.
- [ ] No unsupported cross-domain resolution is introduced.
- [ ] Raw configuration values and provenance are preserved.
- [ ] Taxonomy validation passes.
- [ ] Focused regression tests pass.
- [ ] Affected generated indexes and journeys are reviewed.
- [ ] Documentation reflects the accepted taxonomy changes.

---

## 18. Summary

The DataPower Atlas taxonomy is not merely a collection of labels. It is an executable classification and semantic interpretation layer.

| Layer | Primary Contribution |
|---|---|
| Object taxonomy | Defines what exists |
| Property taxonomy | Defines what configured properties mean |
| Reference taxonomy | Defines what is referenced |
| Relationship taxonomy | Defines how architectural elements relate |
| Endpoint taxonomy | Defines the role of network destinations |
| File taxonomy | Defines available source artifacts |
| Sensitivity taxonomy | Defines evidence-handling classifications |
| Cross-taxonomy | Defines how the classifications work together |

**Final principle:**

> Classify precisely. Interpret contextually. Resolve deterministically. Preserve unresolved evidence. Never invent architectural facts.
