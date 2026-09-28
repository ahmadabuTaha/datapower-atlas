# DataPower Atlas — AGENTS.md

## 1. Project Mission

DataPower Atlas is an evidence-driven architecture reconstruction system for IBM DataPower environments.

Its purpose is to transform raw DataPower exports into traceable architecture evidence, service journeys, operation journeys, findings, functional capabilities, and later modernization requirements.

Official direction:

```text
Raw DataPower Export
→ Structured Architecture Index
→ Service Journeys
→ Operation Journeys
→ Findings
→ Functional Capabilities
→ Modernization / Replacement Analysis
```

Atlas must reconstruct the implementation faithfully.

It must not silently clean, simplify, normalize, or redesign the source configuration.

Codex operates as an:

```text
Architecture Investigation Engine
```

Its primary objectives are:

1. reconstruct evidence-based AS-IS architecture;
2. derive functional capabilities from validated behavior;
3. support evidence-based replacement requirements;
4. minimize unnecessary retrieval and token consumption.

Codex must not act as a generic DataPower encyclopedia.

---

## 2. Source of Truth

The authoritative source is:

```text
Raw DataPower CFG / Raw Export / Referenced Source Artifact
```

All generated indexes, reports, journeys, relationships, unified views, findings, and downstream analysis are derived artifacts.

Derived artifacts must always be reproducible from raw evidence.

Authority order:

```text
Raw CFG / Raw Export / Source Artifact
        ↓
Validated Atlas Indexes
        ↓
Journey Evidence Bundles
        ↓
Skill Outputs
        ↓
Capability / Replacement / Diagram Outputs
```

If a generated artifact conflicts with raw configuration:

```text
Raw configuration wins
```

unless there is a reproducible parser, extraction, resolver, aggregation, or journey defect.

---

## 3. Required Contracts

Codex must follow:

```text
docs/skill-contract.md
docs/journey-evidence-contract.md
```

`docs/skill-contract.md` defines:

- skill execution chain;
- shared terminology;
- input/output contracts;
- evidence certainty propagation;
- finding classifications;
- token-efficiency rules;
- integration reasoning patterns.

`docs/journey-evidence-contract.md` defines:

- Service Architectural Evidence Bundle;
- Operation Architectural Evidence Bundle;
- dependency semantics;
- file reference and resolution states;
- routing and egress semantics;
- evidence certainty;
- provenance;
- aggregation rules.

Skills must not redefine these contracts locally.

If a skill-specific instruction conflicts with one of these contracts, the shared contract wins unless the contract itself is being intentionally revised.

---

## 4. Official Pipeline

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

```text
tools/run_domain_pipeline.sh
```

Individual tools may be executed during focused investigation.

Final domain outputs must be reproducible through the official pipeline.

---

## 5. Authoritative Tooling Rule

There must be exactly one authoritative runtime filename for every tool.

Do not create runtime filenames such as:

```text
*_v1.py
*_v1_1.py
*_v2.py
*_fixed.py
*_hotfix.py
*.keep
```

Version history belongs in Git.

The working tree must contain only authoritative runtime files.

---

## 6. Authoritative Taxonomy Rule

There must be exactly one authoritative taxonomy file for each taxonomy domain.

Expected baseline:

```text
taxonomy/
  cross_taxonomy.yaml
  datapower_objects.yaml
  datapower_properties.yaml
  endpoint_types.yaml
  file_types.yaml
  reference_types.yaml
  relationship_types.yaml
  sensitivity.yaml
```

Do not create patch taxonomies or versioned runtime copies.

---

## 7. Object Identity

Domain-local object identity must be globally safe.

Use:

```text
environment
+ domain
+ canonical_type
+ logical_name
```

Never identify an object using logical name alone.

Never merge objects from different domains because their names match.

---

## 8. Domain Isolation

Each domain is an independent evidence boundary.

Resolution is local to:

```text
environment
+ domain
+ target_type
+ target_name
```

Do not automatically resolve references across:

- STG
- STG-Replica
- DEFAULT
- future domains

Cross-domain relationships belong only to the dedicated Cross-Domain Correlation layer.

Do not borrow:

- files;
- relationships;
- endpoints;
- artifacts;
- findings;

from another domain to complete missing local evidence.

Cross-domain evidence is allowed only during explicit:

- `compare-domains`;
- shared dependency analysis;
- replica correlation;
- DEFAULT correlation.

Cross-domain evidence must remain explicitly identified as correlation or candidate evidence unless confirmed.

---

## 9. Evidence Rules

### Rule 9.1 — Names are hints, not evidence

Never create a relationship because two object names appear related.

Allowed:

```text
explicit property/reference
→ exact target type
→ exact target name
→ resolved relationship
```

Not allowed:

```text
similar naming
→ inferred relationship
```

---

### Rule 9.2 — Unresolved does not mean error

Unresolved references must be classified before code changes are considered.

Possible causes include:

- built-in/default object;
- shared platform resource;
- missing source artifact;
- incomplete export;
- unsupported semantic mapping;
- deployment mechanism outside the export;
- stale reference;
- investigation required;
- parser/resolver defect.

Do not modify code merely to reduce unresolved counts.

---

### Rule 9.3 — Unresolved does not mean absent

Preserve these distinctions:

```text
unresolved dependency
!=
missing dependency

no resolved file
!=
no file reference

unresolved egress
!=
no egress evidence path
```

An explicit reference remains evidence even when its target cannot be resolved.

---

### Rule 9.4 — Missing backend stays missing

Never invent a backend endpoint.

If no backend evidence exists, the journey must expose the absence or unresolved state.

---

### Rule 9.5 — Configured backend is not actual egress

Never collapse all routing information into one generic `backend` conclusion.

Distinguish:

```text
Configured Backend
Actual Evidenced Egress
Candidate Egress
Unresolved Egress
Remote System Identity
Remote Topology
```

A configured backend must not automatically be interpreted as the actual operation runtime path.

---

### Rule 9.6 — Dynamic backend does not identify a destination

Dynamic routing means the destination is selected dynamically.

It does not prove a specific target.

Do not infer a remote endpoint from:

```text
dynamic-backend
service name
artifact filename
related domain configuration
```

without supporting evidence.

---

### Rule 9.7 — Missing file does not prove deployment failure

A missing referenced file may mean:

- incomplete export;
- excluded artifact;
- external deployment mechanism;
- platform-provided resource;
- stale reference.

Preserve the evidence gap.

Do not convert it automatically into a deployment defect.

---

### Rule 9.8 — Missing artifact does not permit semantic inference

If a referenced XSLT, GatewayScript, or other source artifact is unavailable:

```text
preserve the reference
preserve the unresolved resolution state
do not infer the artifact contents
```

If actual routing depends on that artifact:

```text
actual egress remains unresolved
```

unless another independent evidence source proves it.

---

### Rule 9.9 — Large graph does not prove traversal defect

Large processing graphs may be real configuration.

Before changing traversal logic:

1. inspect raw configuration;
2. trace processing policy;
3. trace matching rules;
4. trace processing rules;
5. trace processing actions;
6. verify whether the graph actually exists.

---

### Rule 9.10 — Configuration hotspot is not runtime causality

High limits, large caches, large policy graphs, or unusual resource settings may indicate architectural or operational risk.

They do not prove outage causality.

Runtime causality requires evidence such as:

- metrics;
- logs;
- memory usage;
- CPU behavior;
- latency;
- cache behavior;
- incident evidence.

---

### Rule 9.11 — HTTPS does not imply mTLS

mTLS requires appropriate evidence, such as:

```text
outbound TLS usage
client identification credentials
client certificate/private key
validation credentials/trust
```

Do not infer mTLS from HTTPS alone.

---

## 10. Freeze Philosophy

A component that passes agreed validation becomes Frozen.

Do not reopen a frozen component merely because new evidence appears.

A frozen component may only be reopened when one of the following exists:

1. reproducible defect;
2. concrete contradiction with authoritative evidence;
3. broken downstream requirement.

Prefer additive forward fixes such as:

- new taxonomy mapping;
- new parser extension;
- new resolver;
- new semantic support;
- new aggregation layer;
- new correlation rule;
- explicit exception;
- new reporting layer;

over redesigning validated behavior.

---

## 11. Current Frozen Baseline

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

Journey Quality Analyzer is frozen after the STG end-to-end regression validated
the TCP direct-path representation, domain-safe operation counting, and pipeline
journey input on 2026-09-28.

The STG AS-IS user-journey aggregation outputs produced from that validated
evidence are frozen at the same baseline. Reopen only under the freeze criteria
defined above.

Do not reopen these components for Journey enrichment alone.

Journey enrichment should be implemented forward through aggregation/materialization unless a focused investigation proves an upstream defect.

---

## 12. Default Retrieval Strategy

Codex must use generated Atlas evidence as the primary retrieval layer.

Default architecture investigation order:

```text
Question
→ Exact Environment / Domain
→ Exact Service
→ Service Journey / Service Evidence Bundle
→ Relevant Known Findings
→ Operation Journey / Operation Evidence Bundle when required
→ Supporting Index only when required
→ Raw CFG / Source Artifact only when required
```

Do not start by scanning the whole repository.

Do not load all findings, relationships, files, objects, operations, or raw configuration unless the task explicitly requires broad analysis.

Indexes are retrieval aids.

Raw configuration remains the final authority.

---

## 13. Journey-First Rule

For service analysis:

```text
Service Journey / Service Architectural Evidence Bundle
```

is the default entry point.

For operation analysis:

```text
Operation Journey / Operation Architectural Evidence Bundle
```

is the default operation-level entry point.

Reuse evidence already materialized in the Journey before retrieving supporting indexes.

If the Journey already contains:

- dependency state;
- file resolution state;
- route-control evidence;
- known finding;
- configured backend;
- actual egress status;
- certainty;
- provenance;

do not rediscover it unless:

```text
verification is required
evidence is contradictory
evidence is incomplete
new evidence is explicitly required
```

---

## 14. Service Journey Rules

### Multi-Protocol Gateway

Expected logical journey:

```text
Ingress
→ MPGW
→ Processing Policy
→ Matching Rule
→ Processing Rule
→ Processing Actions
→ Routing / Egress
```

Routing/evidence interpretation must still follow the Journey Evidence Contract.

A configured backside must not automatically become actual egress.

---

### Web Service Proxy

Expected logical journey may include:

```text
WSP
→ XML Manager
→ TLS Client Profile
→ WSM Processing Policy
→ Matching Rule
→ WSM Processing Rule
→ Endpoint Rewrite
→ Front Side Handler / Remote Endpoint
```

Do not infer missing Endpoint Rewrite semantics.

---

### TCP Proxy

TCP Proxy is not modeled as MPGW-style ingress/processing/egress.

Its direct network journey is:

```text
local-address:local-port
→ TCP Proxy
→ destination-address:destination-port
```

The quality analyzer must treat this as valid ingress/egress evidence.

---

## 15. Operation Journey Rules

Operation journeys must be based on explicit processing evidence.

Typical operation decomposition:

```text
Service
→ Processing Policy
→ Match
→ Matching Rule
→ Processing Rule
→ Processing Actions
```

Operation identity must not depend on naming alone.

Large operation counts may represent valid Mega Policies.

Do not reduce them without evidence of traversal duplication.

For service-level analysis:

```text
retrieve operation summaries first
```

For operation-level analysis:

```text
retrieve only the selected operation
```

Load the full operation set only when the task requires:

- policy-wide comparison;
- operation concentration;
- shared behavior analysis;
- pattern analysis;
- coverage analysis.

---

## 16. Routing and Egress Rules

Routing must follow the canonical model defined in:

```text
docs/journey-evidence-contract.md
```

Codex must distinguish:

```text
backend mode
configured backend
route-control evidence
actual egress
remote system identity
remote topology
```

If normal backside routing is bypassed:

```text
configured backend
must not automatically become
actual egress
```

If routing behavior depends on an unresolved XSLT or GatewayScript:

```text
Actual Egress = unresolved
```

unless other direct evidence proves otherwise.

If a resolved script performs outbound communication:

```text
script-mediated egress
```

may be recorded when supported by explicit source evidence.

Do not create multiple runtime calls merely because both configured backend and script-mediated outbound evidence exist.

---

## 17. Evidence Certainty

Use only:

```text
confirmed
candidate
unresolved
not_evidenced
```

A downstream step must not strengthen certainty without new evidence.

Default propagation:

```text
confirmed    → confirmed
candidate    → candidate
unresolved   → unresolved
not_evidenced → not_evidenced
```

The following are prohibited without new evidence:

```text
candidate → confirmed
unresolved → confirmed
not_evidenced → candidate
not_evidenced → confirmed
```

If new evidence changes certainty:

- preserve the new evidence source;
- preserve provenance;
- record the reason for the certainty change.

Certainty is local to each fact.

A service may legitimately contain:

```text
Ingress                confirmed
Processing             confirmed
Configured Backend     confirmed
Actual Egress          unresolved
Remote System Identity not_evidenced
```

---

## 18. Known Findings Reuse

Known findings relevant to the current:

- domain;
- service;
- object;
- dependency;
- artifact;
- operation;

must be reused before opening a new investigation.

If a finding is already materialized in the Journey Evidence Bundle:

```text
treat it as existing context
```

Do not repeatedly rediscover known evidence.

Only reopen investigation when:

```text
verification is required
new contradictory evidence appears
the finding impacts a new downstream requirement
```

Known findings should be retrieved narrowly.

Do not load the entire findings corpus for a single service question.

---

## 19. Known Findings That Must Not Be "Fixed"

### SOCPA

Observed:

```text
Endpoint Rewrite object exists
but contains no ingress/backend rules
```

Classification:

```text
FINDING
```

Suggested detail:

```text
empty_endpoint_rewrite_policy
partial_missing_ingress_and_egress
```

Do not invent ingress or backend endpoints.

---

### STG-Replica Mega Policies

Examples:

```text
GetUserEstablishmentsQuery_Service
DeleteLater
GetUserEstablishmentsQuery_Service_V2
```

Large operation graphs are proven by configuration evidence.

Do not classify them as traversal defects without reproducible proof.

---

### DeleteLater / V2

Observed:

```text
DeleteLater and GetUserEstablishmentsQuery_Service_V2
share the same 79-operation set.
```

This is a configuration finding.

Do not infer:

- retired;
- orphaned;
- temporary;
- unused;

without runtime/deployment evidence.

---

### Replica local:/// References

Missing `local:///` artifacts are an open evidence gap.

Do not automatically classify them as broken deployment.

Preserve each explicit reference even when the target file is unresolved.

---

### Platform Resources

References such as:

```text
store:///
cert:///
pubcert:///
```

may represent platform/shared resources.

Do not automatically treat them as parser defects.

---

## 20. Finding Classification

Every anomaly must be classified before code changes are proposed.

Allowed top-level classes:

```text
BUG
GAP
FINDING
EXPECTED_UNRESOLVED
ARCHITECTURAL_HOTSPOT
INVESTIGATION_REQUIRED
```

Avoid vague classifications such as:

- Other
- Others
- Misc
- Various
- Many
- Unknown

If classification cannot be completed, use a precise reason such as:

```text
unclassified_due_to_missing_source_evidence
unclassified_due_to_parser_gap
unclassified_due_to_missing_extension
```

Always retain the original evidence.

Classification and remediation are separate.

Permitted remediation actions:

```text
NO_CHANGE
ADD_TAXONOMY
ADD_MAPPING
ADD_SEMANTIC_SUPPORT
FIX_LOGIC
COLLECT_MORE_EVIDENCE
RECORD_FINDING
```

Use the smallest action that addresses the proven issue.

---

## 21. Provenance Requirements

Important relationships, semantic facts, and findings should preserve, where available:

- environment;
- domain;
- source file;
- source line;
- raw statement;
- owner object;
- source object;
- target object;
- canonical object type;
- relationship type;
- extraction status;
- resolution status;
- artifact path;
- evidence hash / source pointer.

Human-readable reports may summarize evidence.

They must not destroy traceability.

The following must remain consistent unless explicitly documented otherwise:

```text
Journey top-level domain
service identity domain
operation identity domain
source object domain
source path domain
relationship domain
```

A reproducible mismatch is:

```text
INVESTIGATION_REQUIRED
```

until isolated and classified.

---

## 22. DEFAULT Domain Rules

DEFAULT must be processed as an independent domain.

Potential contents may include:

- shared TLS resources;
- shared crypto resources;
- shared XML managers;
- shared platform resources;
- base configuration;
- management/security/network foundation.

Do not make the local resolver jump automatically from STG or STG-Replica into DEFAULT.

Allowed sequence:

```text
domain-local resolution
→ unresolved
→ optional DEFAULT correlation candidate
```

---

## 23. Cross-Domain Correlation

Cross-domain correlation is a derived analysis layer.

It may identify candidates such as:

- same logical service candidate;
- replica variant;
- shared configuration;
- configuration drift;
- domain-specific service;
- shared/default dependency.

Object name alone is never sufficient evidence.

Domain-local truth remains authoritative.

Cross-domain correlation must not rewrite local resolution state.

---

## 24. Unified Atlas Rules

Unified Atlas is derived.

It is not authoritative.

Expected future outputs may include:

```text
unified/
  objects.csv
  relationships.csv
  endpoints.csv
  service_journeys.jsonl
  operation_journeys.jsonl
  domain_comparison.csv
  findings.csv
```

Every unified record must retain:

- environment;
- domain;
- provenance;
- correlation method.

Never remove domain identity during merge.

---

## 25. Codex Responsibilities

Codex may:

- run the official domain pipeline;
- validate generated outputs;
- inspect pipeline regressions;
- trace a service;
- trace an operation;
- inspect unresolved references;
- classify findings;
- compare domains;
- detect configuration drift;
- generate architecture reports;
- build derived unified views;
- support functional capability analysis;
- support replacement requirement analysis;
- generate evidence-based diagrams.

Codex should prefer investigation before modification.

---

## 26. Codex Must Never

Codex must never:

1. infer relationships from object names;
2. treat unresolved references automatically as bugs;
3. auto-resolve across domains;
4. choose old versioned runtime tools;
5. recreate `*_v1`, `*_v2`, `fixed`, `hotfix` runtime copies;
6. redesign frozen components without reopen evidence;
7. convert every DataPower CLI command into an architecture object;
8. shrink real Mega Policies because they look excessive;
9. model TCP Proxy using MPGW assumptions;
10. invent ingress endpoints;
11. invent backend endpoints;
12. treat configured backend as actual egress without evidence;
13. infer a specific destination from dynamic routing alone;
14. infer runtime outage causality from configuration alone;
15. infer service lifecycle status from naming;
16. silently suppress missing files;
17. interpret unresolved file as absent reference;
18. automatically resolve to DEFAULT;
19. borrow evidence from another domain to complete local uncertainty;
20. strengthen evidence certainty without new evidence;
21. recommend replacement technologies before capability decomposition.

---

## 27. Required Investigation Workflow

When a new anomaly is discovered:

1. identify environment;
2. identify domain;
3. identify service/object/operation;
4. inspect existing Journey Evidence Bundle;
5. inspect relevant known findings;
6. inspect supporting index evidence only when required;
7. inspect raw configuration/source only when required;
8. reproduce the issue;
9. isolate the failing stage;
10. compare derived output with raw evidence;
11. classify the anomaly;
12. determine downstream impact;
13. select the minimum corrective action.

Possible classifications include:

```text
source configuration behavior
evidence gap
taxonomy gap
semantic mapping gap
parser defect
resolver defect
journey defect
aggregation defect
provenance defect
quality-rule defect
architecture finding
```

Only reproducible BUG classifications justify reopening frozen components.

---

## 28. Modification Protocol

Before modifying parser/extractor/resolver/builder logic, Codex must document:

- observed behavior;
- expected behavior;
- raw evidence;
- reproduction method;
- affected environment/domain;
- affected object/service/operation;
- affected pipeline stage;
- whether the component is frozen;
- reason for reopening;
- expected downstream impact.

After modification:

1. run focused regression;
2. run affected domain pipeline;
3. compare output counts where useful;
4. inspect new unresolved/resolved differences;
5. inspect identity/provenance changes;
6. verify no unrelated regressions;
7. update findings/freeze documentation if required.

---

## 29. Regression Philosophy

Do not judge regression only by total counts.

A valid change may alter counts.

Regression validation must inspect:

- object identity;
- relationship identity;
- endpoint identity;
- operation identity;
- file references;
- routing state;
- egress state;
- evidence certainty;
- provenance;
- new/lost records;
- classification changes.

Unexpected silent loss of evidence is a failure.

---

## 30. Raw Source Access

Open raw CFG or source artifacts only when:

- aggregated evidence is insufficient;
- verification is required;
- evidence is contradictory;
- operation semantics require source inspection;
- a suspected Atlas defect must be confirmed.

Do not read raw source merely because it exists.

For resolved source artifacts, extract only architecture-relevant semantics required by the investigation.

---

## 31. Smoke-Test Guidance

Smoke tests may use generated Atlas directories available in the local workspace.

Smoke-test inputs and outputs intentionally ignored by Git remain local validation material.

Do not copy ignored smoke-test artifacts into:

- committed contracts;
- permanent skills;
- taxonomy;
- schemas;
- permanent examples;
- long-lived project facts.

When performing a smoke test:

1. select a representative service or operation from available generated outputs;
2. start from Journey evidence;
3. reuse known findings already available for that graph;
4. retrieve only targeted supporting evidence;
5. inspect raw source only when required;
6. verify conclusions against available source evidence;
7. evaluate retrieval/token efficiency;
8. generalize only the reasoning rule or contract improvement.

Do not encode service-specific or domain-specific smoke-test facts as permanent rules.

Smoke testing should verify that:

- known evidence is reused rather than rediscovered;
- unresolved references remain unresolved;
- missing artifacts are not treated as absent references;
- configured backend is not automatically treated as actual egress;
- evidence is not borrowed from another domain;
- evidence certainty is not strengthened without new evidence;
- raw source is opened only when aggregated evidence is insufficient.

---

## 32. Skill Integration Contract

Skills form a staged evidence pipeline.

A downstream skill should consume the smallest validated output from the upstream skill instead of repeating upstream investigation.

Primary flow:

```text
run-domain-analysis
        ↓
trace-service
        ↓
trace-operation          when required
        ↓
investigate-gap          when required
        ↓
datapower-semantics      supporting lookup
        ↓
capability-analysis
        ↓
replacement-analysis
        ↓
generate-architecture-diagrams
```

Cross-domain flow:

```text
validated domain outputs
        ↓
default-domain-analysis  when required
        ↓
compare-domains
        ↓
capability-analysis
        ↓
replacement-analysis
        ↓
generate-architecture-diagrams
```

No downstream skill may strengthen evidence certainty without new evidence.

Detailed skill behavior is defined in:

```text
docs/skill-contract.md
```

---

## 33. Token-Efficiency Requirement

Optimize for:

```text
minimum evidence required
+
maximum architectural correctness
```

Prefer:

```text
compact indexes
Journey Evidence Bundles
operation summaries
relevant known findings
targeted source inspection
```

Avoid:

```text
whole-domain scans
entire findings-register retrieval
entire CFG retrieval
all-operation retrieval
duplicate evidence loading
broad semantic documentation
```

Default principle:

```text
Index First
→ Journey First
→ Exact Target Retrieval
→ Supporting Evidence Only When Needed
→ Raw CFG / Source Only When Needed
```

If evidence already exists in the current Journey bundle, reuse it.

---

## 34. Modernization Boundary

Extraction answers:

```text
What exists?
```

Modernization answers:

```text
What should exist?
```

Do not mix them.

Required modernization sequence:

```text
Current DataPower Function
→ Required Functional Capability
→ NFRs
→ Operational Characteristics
→ Replacement Requirement
→ Solution Role
→ Candidate Technology
```

Do not jump directly from DataPower objects to products.

---

## 35. Functional Capability Principle

Modernization analysis must classify required capabilities before technology selection.

Capabilities describe observed behavior, not object names.

Examples:

MPGW may provide:

- HTTP ingress;
- routing;
- transformation;
- GatewayScript execution;
- TLS;
- AAA;
- backend integration.

TCP Proxy may provide:

- Layer 4 TCP forwarding.

WSP may provide:

- SOAP mediation;
- WSDL/service exposure;
- endpoint rewriting;
- processing rules;
- TLS.

These are capability observations, not replacement recommendations.

Do not assume every instance of an object type exercises every possible capability.

---

## 36. Replacement Analysis Guardrail

Do not map DataPower objects directly to replacement products.

Required reasoning:

```text
Current Function
→ Capability
→ NFR / Constraint
→ Replacement Requirement
→ Solution Role
→ Candidate Technology
```

Replacement analysis must preserve:

- unresolved capabilities;
- evidence gaps;
- domain-specific constraints;
- operational characteristics.

---

## 37. Diagram Guardrail

Architecture diagrams are renderers of evidence.

They must never introduce architecture.

Diagram certainty must follow evidence certainty.

Use distinct representation for:

```text
confirmed
candidate
unresolved
```

Do not draw missing:

- backend;
- remote system;
- topology;
- dependency;

as fact.

A diagram must never appear more certain than the underlying evidence.

---

## 38. Working Principle

If the DataPower implementation is messy, Atlas must expose that mess as structured evidence.

Atlas must not silently make the architecture appear cleaner than the source implementation.

The purpose of Atlas is faithful reconstruction first.

Modernization decisions come later.

Final operating principle:

```text
Reconstruct the architecture that exists.

Do not make it cleaner,
simpler,
more complete,
or more certain
than the evidence supports.

When evidence stops,
Codex stops.
```
