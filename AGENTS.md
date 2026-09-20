# DataPower Atlas — AGENTS.md

## 1. Project Mission

DataPower Atlas is an evidence-driven architecture reconstruction system for IBM DataPower environments.

Its purpose is to transform raw DataPower exports into traceable architecture evidence, service journeys, operation journeys, findings, and later modernization requirements.

Official direction:

Raw DataPower Export
→ Structured Architecture Index
→ Service Journeys
→ Operation Journeys
→ Findings
→ Functional Capabilities
→ Modernization / Replacement Analysis

Atlas must reconstruct the implementation faithfully.

It must not silently clean, simplify, normalize, or redesign the source configuration.

---

## 2. Source of Truth

The authoritative source is:

Raw DataPower CFG / Raw Export

All generated indexes, reports, journeys, relationships, unified views, and findings are derived artifacts.

Derived artifacts must always be reproducible from raw evidence.

If a generated artifact conflicts with raw configuration:

Raw configuration wins

unless there is a reproducible parser or extraction defect.

---

## 3. Official Pipeline

Every DataPower domain must follow the same official pipeline:

1. Validate taxonomies
2. Build file inventory
3. Run sensitivity scan
4. Parse DataPower CFG
5. Extract references
6. Resolve relationships
7. Extract endpoints
8. Resolve file references
9. Build service journeys
10. Build operation journeys
11. Analyze journey quality

Official orchestrator:

tools/run_domain_pipeline.sh

Individual tools may be executed during investigation.

Final domain outputs must be reproducible through the official pipeline.

---

## 4. Authoritative Tooling Rule

There must be exactly one authoritative runtime filename for every tool.

Do not create runtime filenames such as:

- *_v1.py
- *_v1_1.py
- *_v2.py
- *_fixed.py
- *_hotfix.py
- *.keep

Version history belongs in Git.

The working tree must contain only authoritative runtime files.

---

## 5. Authoritative Taxonomy Rule

There must be exactly one authoritative taxonomy file for each taxonomy domain.

Expected baseline:

taxonomy/
  cross_taxonomy.yaml
  datapower_objects.yaml
  datapower_properties.yaml
  endpoint_types.yaml
  file_types.yaml
  reference_types.yaml
  relationship_types.yaml
  sensitivity.yaml

Do not create patch taxonomies or versioned runtime copies.

---

## 6. Object Identity

Domain-local object identity must be globally safe.

Use:

environment
+ domain
+ canonical_type
+ logical_name

Never identify an object using logical name alone.

Never merge objects from different domains because their names match.

---

## 7. Domain Isolation

Each domain is an independent evidence boundary.

Resolution is local to:

environment
+ domain
+ target_type
+ target_name

Do not automatically resolve references across:

- STG
- STG-Replica
- DEFAULT
- future domains

Cross-domain relationships belong only to the dedicated Cross-Domain Correlation layer.

---

## 8. Evidence Rules

### Rule 8.1 — Names are hints, not evidence

Never create a relationship because two object names appear related.

Allowed:

explicit property/reference
→ exact target type
→ exact target name
→ resolved relationship

Not allowed:

similar naming
→ inferred relationship

---

### Rule 8.2 — Unresolved does not mean error

Unresolved references must be classified before code changes are considered.

Possible causes include:

- built-in/default object
- shared platform resource
- missing source artifact
- incomplete export
- unsupported semantic mapping
- deployment mechanism outside the export
- stale reference
- investigation required
- parser/resolver defect

Do not modify code merely to reduce unresolved counts.

---

### Rule 8.3 — Missing backend stays missing

Never invent a backend endpoint.

If no backend evidence exists in raw configuration, the journey must expose the absence.

---

### Rule 8.4 — Missing file does not prove deployment failure

A missing referenced file may mean:

- incomplete export
- excluded artifact
- external deployment mechanism
- platform-provided resource
- stale reference

Preserve the evidence gap.

Do not convert it automatically into a deployment defect.

---

### Rule 8.5 — Large graph does not prove traversal defect

Large processing graphs may be real configuration.

Before changing traversal logic:

1. inspect raw configuration;
2. trace processing policy;
3. trace matching rules;
4. trace processing rules;
5. trace processing actions;
6. verify whether the graph actually exists.

---

### Rule 8.6 — Configuration hotspot is not runtime causality

High limits, large caches, large policy graphs, or unusual resource settings may indicate architectural or operational risk.

They do not prove outage causality.

Runtime causality requires evidence such as:

- metrics
- logs
- memory usage
- CPU behavior
- latency
- cache behavior
- incident evidence

---

## 9. Freeze Philosophy

A component that passes agreed validation becomes Frozen.

Do not reopen a frozen component merely because new evidence appears.

A frozen component may only be reopened when one of the following exists:

1. reproducible defect;
2. concrete contradiction with authoritative evidence;
3. broken downstream requirement.

Prefer additive forward fixes such as:

- new taxonomy mapping
- new parser extension
- new resolver
- new correlation rule
- explicit exception
- new reporting layer

over redesigning validated behavior.

---

## 10. Current Frozen Baseline

Current frozen components:

- File Inventory
- Sensitivity Scan
- CFG Parser
- Reference Extractor
- Relationship Resolver
- Endpoint Extractor
- File Reference Resolver
- Service Journey Builder

Operation Journey Builder has passed validation on:

- STG
- STG-Replica

Journey Quality Analyzer becomes frozen after final V1.1 validation is recorded.

---

## 11. Service Journey Rules

### Multi-Protocol Gateway

Expected logical journey:

Ingress
→ MPGW
→ Processing Policy
→ Matching Rule
→ Processing Rule
→ Processing Actions
→ Routing / Backend

---

### Web Service Proxy

Expected logical journey may include:

WSP
→ XML Manager
→ TLS Client Profile
→ WSM Processing Policy
→ Matching Rule
→ WSM Processing Rule
→ Endpoint Rewrite
→ Front Side Handler / Remote Endpoint

Do not infer missing Endpoint Rewrite semantics.

---

### TCP Proxy

TCP Proxy is not modeled as MPGW-style ingress/processing/egress.

Its direct network journey is:

local-address:local-port
→ TCP Proxy
→ destination-address:destination-port

The quality analyzer must treat this as valid ingress/egress evidence.

---

## 12. Operation Journey Rules

Operation journeys must be based on explicit processing evidence.

Typical operation decomposition:

Service
→ Processing Policy
→ Match
→ Matching Rule
→ Processing Rule
→ Processing Actions

Operation identity must not depend on naming alone.

Large operation counts may represent valid Mega Policies.

Do not reduce them without evidence of traversal duplication.

---

## 13. Known Findings That Must Not Be "Fixed"

### SOCPA

Observed:

Endpoint Rewrite object exists
but contains no ingress/backend rules

Classification:

FINDING

Suggested detail:

empty_endpoint_rewrite_policy
partial_missing_ingress_and_egress

Do not invent ingress or backend endpoints.

---

### STG-Replica Mega Policies

Examples:

GetUserEstablishmentsQuery_Service
DeleteLater
GetUserEstablishmentsQuery_Service_V2

Large operation graphs are proven by configuration evidence.

Do not classify them as traversal defects without reproducible proof.

---

### DeleteLater / V2

Observed:

DeleteLater and GetUserEstablishmentsQuery_Service_V2 share the same 79-operation set.

This is a configuration finding.

Do not infer:

- retired
- orphaned
- temporary
- unused

without runtime/deployment evidence.

---

### Replica local:/// References

Missing local:/// artifacts are an open evidence gap.

Do not automatically classify them as broken deployment.

---

### Platform Resources

References such as:

store:///
cert:///
pubcert:///

may represent platform/shared resources.

Do not automatically treat them as parser defects.

---

## 14. Finding Classification

Every anomaly must be classified before code changes are proposed.

Allowed top-level classes:

BUG
GAP
FINDING
EXPECTED_UNRESOLVED
ARCHITECTURAL_HOTSPOT
INVESTIGATION_REQUIRED

Avoid vague classifications such as:

- Other
- Others
- Misc
- Various
- Many
- Unknown

If classification cannot be completed, use a precise reason such as:

unclassified_due_to_missing_source_evidence

unclassified_due_to_parser_gap

unclassified_due_to_missing_extension

Always retain the original evidence.

---

## 15. Provenance Requirements

Important relationships and findings should preserve, where available:

- environment
- domain
- source file
- source line
- raw statement
- owner object
- source object
- target object
- canonical object type
- relationship type
- extraction status
- resolution status

Human-readable reports may summarize evidence.

They must not destroy traceability.

---

## 16. DEFAULT Domain Rules

DEFAULT must be processed as an independent domain.

Potential contents may include:

- shared TLS resources
- shared crypto resources
- shared XML managers
- shared platform resources
- base configuration

Do not make the local resolver jump automatically from STG or STG-Replica into DEFAULT.

Allowed sequence:

domain-local resolution
→ unresolved
→ optional DEFAULT correlation candidate

---

## 17. Cross-Domain Correlation

Cross-domain correlation is a derived analysis layer.

It may identify candidates such as:

- same logical service candidate
- replica variant
- shared configuration
- configuration drift
- domain-specific service
- shared/default dependency

Object name alone is never sufficient evidence.

Domain-local truth remains authoritative.

---

## 18. Unified Atlas Rules

Unified Atlas is derived.

It is not authoritative.

Expected future outputs may include:

unified/
  objects.csv
  relationships.csv
  endpoints.csv
  service_journeys.jsonl
  operation_journeys.jsonl
  domain_comparison.csv
  findings.csv

Every unified record must retain:

- environment
- domain
- provenance
- correlation method

Never remove domain identity during merge.

---

## 19. Codex Responsibilities

Codex may:

- run the official domain pipeline
- validate generated outputs
- inspect pipeline regressions
- trace a service
- trace an operation
- inspect unresolved references
- classify findings
- compare domains
- detect configuration drift
- generate architecture reports
- build derived unified views
- support functional capability analysis

Codex should prefer investigation before modification.

---

## 20. Codex Must Never

Codex must never:

1. infer relationships from object names;
2. treat unresolved references automatically as bugs;
3. auto-resolve across domains;
4. choose old versioned runtime tools;
5. recreate *_v1, *_v2, fixed, hotfix runtime copies;
6. redesign frozen components without reopen evidence;
7. convert every DataPower CLI command into an architecture object;
8. shrink real Mega Policies because they look excessive;
9. model TCP Proxy using MPGW assumptions;
10. invent ingress endpoints;
11. invent backend endpoints;
12. infer runtime outage causality from configuration alone;
13. infer service lifecycle status from naming;
14. silently suppress missing files;
15. automatically resolve to DEFAULT;
16. recommend replacement technologies before capability decomposition.

---

## 21. Required Investigation Workflow

When a new anomaly is discovered:

1. identify environment;
2. identify domain;
3. identify service/object/operation;
4. inspect raw configuration;
5. inspect parsed object representation;
6. inspect extracted references;
7. inspect relationship resolution;
8. inspect endpoint/file extraction if applicable;
9. inspect service journey;
10. inspect operation journey if applicable;
11. inspect quality finding;
12. classify the anomaly;
13. decide whether it is:
   - source configuration behavior
   - evidence gap
   - taxonomy gap
   - parser defect
   - resolver defect
   - journey defect
   - quality-rule defect
   - architecture finding

Only reproducible BUG classifications justify reopening frozen components.

---

## 22. Modification Protocol

Before modifying parser/extractor/resolver logic, Codex must document:

- observed behavior
- expected behavior
- raw evidence
- reproduction method
- affected domain
- affected object/service
- affected pipeline stage
- whether the component is frozen
- reason for reopening
- expected downstream impact

After modification:

1. run focused regression;
2. run affected domain pipeline;
3. compare output counts;
4. inspect new unresolved/resolved differences;
5. verify no unrelated regressions;
6. update findings/freeze documentation if required.

---

## 23. Regression Philosophy

Do not judge regression only by total counts.

A valid change may alter counts.

Regression validation must inspect:

- object identity
- relationship identity
- endpoint identity
- operation identity
- provenance
- new/lost records
- classification changes

Unexpected silent loss of evidence is a failure.

---

## 24. Modernization Boundary

Extraction answers:

What exists?

Modernization answers:

What should exist?

Do not mix them.

Required modernization sequence:

Current DataPower Function
→ Required Functional Capability
→ NFRs
→ Operational Characteristics
→ Replacement Requirement
→ Candidate Technology

Do not jump directly from DataPower objects to products.

---

## 25. Functional Capability Principle

Future modernization analysis must classify required capabilities before technology selection.

Examples:

MPGW may provide:

- HTTP ingress
- routing
- transformation
- GatewayScript execution
- TLS
- AAA
- backend integration

TCP Proxy may provide:

- Layer 4 TCP forwarding

WSP may provide:

- SOAP mediation
- WSDL/service exposure
- endpoint rewriting
- processing rules
- TLS

These are capability observations, not replacement recommendations.

---

## 26. Working Principle

If the DataPower implementation is messy, Atlas must expose that mess as structured evidence.

Atlas must not silently make the architecture appear cleaner than the source implementation.

The purpose of Atlas is faithful reconstruction first.

Modernization decisions come later.