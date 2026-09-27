# DataPower Atlas — Journey Evidence Contract

## Purpose

This contract defines the canonical architectural evidence model used by DataPower Atlas for:

```text
Service Journeys
Operation Journeys
Journey Aggregation
Codex Retrieval
Capability Analysis
Replacement Analysis
Architecture Diagram Generation
```

Its purpose is to turn Atlas journey outputs into a compact, evidence-backed architectural representation that is sufficiently complete for downstream reasoning without forcing Codex to repeatedly rediscover information from broad indexes or raw configuration.

The contract is designed around the following goals:

```text
Correct AS-IS Reconstruction
+
Evidence Traceability
+
No Invented Architecture
+
No Rediscovery of Known Evidence
+
Low Token Retrieval
+
Consistent Evidence Certainty
```

This contract defines:

1. Architectural Evidence Bundle principles
2. Service Evidence Bundle schema
3. Operation Evidence Bundle schema
4. Dependency model
5. File reference and resolution model
6. Routing and egress model
7. Route-control semantics
8. Evidence certainty model
9. Provenance requirements
10. Aggregation rules
11. Evidence propagation rules
12. Forbidden inference rules
13. Compatibility with existing Atlas outputs
14. Acceptance criteria

This contract does **not** replace raw Atlas indexes.

It defines how relevant evidence from existing indexes is aggregated into a stable architectural representation.

---

# 1. Architectural Evidence Bundle Principles

## 1.1 Raw Evidence Remains Authoritative

The authoritative source remains:

```text
Raw DataPower Export
Raw CFG
Referenced Source Artifacts
```

Journey evidence is derived evidence.

If a Journey record conflicts with raw source evidence:

```text
Raw Evidence Wins
```

and the inconsistency must be investigated.

---

## 1.2 Journey Is an Architectural Evidence Bundle

A Journey is not only a graph summary.

It must aggregate enough information to support architecture reasoning without forcing broad rediscovery.

The intended model is:

```text
Graph Structure
+
Resolved Dependencies
+
Unresolved Dependencies
+
File References
+
File Resolution Status
+
Relevant Findings
+
Routing State
+
Egress State
+
Evidence Certainty
+
Provenance
```

---

## 1.3 Missing Evidence Must Stay Visible

The contract must preserve the distinction between:

```text
no reference exists
```

and:

```text
reference exists but target is unresolved
```

Therefore:

```text
no resolved file
!=
no file reference
```

and:

```text
unresolved dependency
!=
missing dependency
```

---

## 1.4 Configuration Is Not Runtime Behavior

The contract must distinguish between:

```text
configured backend
actual evidenced egress
candidate egress
unresolved egress
not-evidenced egress
```

A configured backend must never automatically become actual runtime egress.

---

## 1.5 Evidence Certainty Must Be Explicit

Every architecture-relevant conclusion that may carry uncertainty must use the canonical certainty vocabulary:

```text
confirmed
candidate
unresolved
not_evidenced
```

---

## 1.6 Domain Isolation Must Be Preserved

Every Service and Operation Journey must remain bound to its originating:

```text
environment
domain
source evidence
```

Evidence from another domain must never be silently borrowed to resolve local uncertainty.

---

## 1.7 Journey Must Be Compact but Sufficient

The bundle must contain enough information for downstream reasoning, but it must not copy raw source content unnecessarily.

Prefer:

```text
compact semantic facts
+
evidence pointers
```

over:

```text
large repeated raw evidence blocks
```

---

# 2. Service Evidence Bundle Schema

A Service Architectural Evidence Bundle should follow the logical structure below.

```yaml
service_journey:

  identity:
    environment:
    domain:
    service_type:
    service_name:
    service_id:
    occurrence_ids: []

  ingress:
    listeners: []
    protocols: []
    ingress_status:
    certainty:
    evidence: []

  processing:
    processing_policies: []
    operation_count:
    operation_ids: []
    certainty:
    evidence: []

  dependencies:
    resolved: []
    unresolved: []

  file_dependencies:
    resolved: []
    unresolved: []

  routing:
    backend_mode:
    configured_backend:
    route_control:
    actual_egress:
    remote_system_identity:
    remote_topology:

  security:
    dependencies: []

  shared_dependencies: []

  known_findings: []

  evidence:
    overall_certainty:
    source_pointers: []

  provenance:
    environment:
    domain:
    source_files: []
    builder:
    generated_from: []
```

The physical implementation may use JSON, JSONL, CSV-derived materialization, or another structured representation.

The logical meaning of each field must remain consistent.

---

## 2.1 Service Identity

Required fields:

```text
environment
domain
service_type
service_name
service_id
```

Recommended fields:

```text
occurrence_ids
source object identifiers
```

Identity must be globally safe.

Preferred logical identity model:

```text
environment
+
domain
+
canonical service type
+
logical service name
```

Service identity must never rely on name alone.

---

## 2.2 Ingress

Ingress should represent evidenced entry points.

Possible data includes:

```text
listener
front-side handler
local address
local port
protocol
HTTP / HTTPS
TCP direct ingress
WSP listener evidence
```

Ingress status should distinguish:

```text
confirmed
candidate
unresolved
not_evidenced
```

Absence of ingress evidence must not automatically be treated as a parser defect.

---

## 2.3 Processing

Processing should summarize:

```text
processing policy
operation count
operation identifiers
rule/action structure
processing mode
shared policy usage when evidenced
```

For Mega Policies, the Service Journey should retain summary-level information and references to operation-level evidence rather than duplicate full operation detail inline.

---

## 2.4 Dependencies

Dependencies must be separated into:

```text
resolved
unresolved
```

The Service Journey must not collapse both into one undifferentiated list.

Dependency structure is defined in Section 4.

---

## 2.5 File Dependencies

File dependencies must be separated into:

```text
resolved
unresolved
```

Every explicit file reference must remain visible even if the referenced file cannot be resolved.

The File Reference Model is defined in Section 5.

---

## 2.6 Routing

Routing is a structured model and must not be represented by one generic `backend` field.

The required concepts are:

```text
backend_mode
configured_backend
route_control
actual_egress
remote_system_identity
remote_topology
```

Details are defined in Sections 6 and 7.

---

## 2.7 Security

Security dependencies may include:

```text
TLS client profile
TLS server profile
crypto identification credentials
crypto validation credentials
certificate dependencies
private key dependencies
AAA policy
password alias references
other evidenced security dependencies
```

Security conclusions must preserve certainty and provenance.

HTTPS alone must not imply mTLS.

---

## 2.8 Shared Dependencies

Shared dependencies represent dependencies that are evidenced as:

```text
shared
default
reused
platform-level
common configuration
```

The scope must be explicit.

A shared dependency must not be inferred from repeated naming alone.

---

## 2.9 Known Findings

Known findings relevant to the Service Journey should be embedded or referenced compactly.

The Journey should include only findings relevant to:

```text
current domain
current service
objects belonging to the current service graph
dependencies referenced by the current graph
service-level routing / file / security behavior
```

The Journey must not load the full findings register.

Recommended finding reference structure:

```yaml
- finding_id:
  classification:
  scope:
  summary:
  certainty:
  evidence_refs: []
```

---

## 2.10 Evidence

The service bundle should preserve:

```text
overall certainty
source pointers
supporting evidence references
```

The overall certainty field must not hide lower-certainty sub-elements.

A service may contain:

```text
confirmed ingress
confirmed processing
unresolved actual egress
```

The bundle must preserve those differences.

---

## 2.11 Provenance

Every Service Journey must include enough provenance to trace the bundle back to its source.

Required:

```text
environment
domain
source files
generated-from indexes
builder identity/version where available
```

Recommended:

```text
object IDs
occurrence IDs
line references
artifact paths
evidence hashes
```

---

# 3. Operation Evidence Bundle Schema

An Operation Architectural Evidence Bundle should use the logical structure below.

```yaml
operation_journey:

  identity:
    environment:
    domain:
    service_id:
    operation_id:
    match_name:
    matching_rule:
    processing_rule:

  actions: []

  dependencies:
    resolved: []
    unresolved: []

  file_dependencies:
    resolved: []
    unresolved: []

  routing:
    backend_mode:
    configured_backend:
    route_control:
    actual_egress:

  semantic_facts: []

  known_findings: []

  evidence:
    certainty:
    source_pointers: []

  provenance:
    environment:
    domain:
    source_files: []
```

The Operation Journey is the primary unit for operation-specific routing and semantic reconstruction.

---

## 3.1 Operation Identity

Operation identity must be evidence-derived.

It may include:

```text
match relationship
matching rule
processing rule
service membership
operation identifier
```

Names may assist readability but must not independently establish operation identity.

---

## 3.2 Actions

Actions should retain the ordered or structurally relevant action evidence available from Atlas.

Examples:

```text
transform
GatewayScript execution
set-variable
results
route
conditional action
other processing actions
```

Action order must be preserved when order is architecture-relevant.

---

## 3.3 Operation Dependencies

Operation-level dependencies must be represented separately from service-level dependencies where the operation has distinct references.

Examples:

```text
specific XSLT
specific GatewayScript
route target
specific crypto/security dependency
shared XML Manager
```

---

## 3.4 Operation Routing

Operation-level routing is the preferred location for actual egress evidence.

The service-level routing summary may aggregate operation states, but operation evidence should remain the primary source for per-operation egress.

---

## 3.5 Semantic Facts

Resolved XSLT or GatewayScript analysis may produce compact semantic facts.

Examples:

```yaml
- fact_type: outbound_http_request
  method: POST
  protocol: https
  destination_type: dynamic
  certainty: confirmed
  evidence_refs: []
```

or:

```yaml
- fact_type: request_transformation
  mechanism: xslt
  certainty: confirmed
  evidence_refs: []
```

Semantic facts must be extracted only when evidence supports them.

They must not be inferred from artifact names.

---

# 4. Dependency Model

Every dependency should follow a common structure.

```yaml
dependency:
  relationship_type:
  source_id:
  source_type:
  target_id:
  target_type:
  raw_reference:
  resolution_status:
  certainty:
  evidence_refs: []
  provenance: {}
```

Not every field is mandatory for every dependency, but the semantic distinction must remain.

---

## 4.1 Resolved Dependency

A dependency is resolved when the referenced target is mapped to a known Atlas target.

Example state:

```text
resolution_status = resolved
certainty = confirmed
```

Resolved does not necessarily mean runtime-used.

It means the reference target was successfully identified.

---

## 4.2 Unresolved Dependency

A dependency is unresolved when:

```text
the reference exists
AND
the target cannot currently be resolved
```

Possible reasons include:

```text
target_not_found
artifact_missing_from_export
unsupported_reference_form
cross_domain_candidate_not_locally_resolved
parser_or_mapping_gap
ambiguous_target
```

Use specific reasons.

Avoid vague labels such as:

```text
unknown
other
misc
```

when a more precise reason is available.

---

## 4.3 Dependency Resolution Status

Recommended canonical values:

```text
resolved
unresolved_target_not_found
unresolved_artifact_missing
unresolved_ambiguous_target
unresolved_cross_domain_candidate
unresolved_parser_gap
unresolved_mapping_gap
not_applicable
```

Implementations may add more precise values where justified.

---

## 4.4 Dependency Rules

The following are mandatory:

```text
Name similarity does not resolve a dependency.

Cross-domain presence does not resolve a local dependency.

Unresolved does not mean absent.

Missing target does not permit target invention.

Resolved reference does not automatically prove runtime execution.
```

---

# 5. File Reference and Resolution Model

Every explicit file reference must be preserved.

Recommended structure:

```yaml
file_reference:
  owner_id:
  owner_type:
  property_name:
  raw_reference:
  reference_type:
  scheme:
  resolution_status:
  resolved_path:
  artifact_type:
  certainty:
  evidence_refs: []
  provenance: {}
```

---

## 5.1 File Reference Exists Independently of Resolution

This rule is mandatory:

```text
file reference existence
!=
file resolution success
```

A file reference remains part of the Journey even when:

```text
resolved_path = null
```

---

## 5.2 Canonical File Resolution States

Recommended values:

```text
resolved
unresolved_file_not_found
unresolved_platform_resource
unresolved_unsupported_scheme
unresolved_ambiguous_match
unresolved_inventory_gap
unresolved_parser_gap
```

Use the most specific reason supported by evidence.

---

## 5.3 Resolved File

A resolved file may carry:

```text
resolved path
artifact type
file ID
hash
semantic extraction status
```

Example:

```yaml
resolution_status: resolved
artifact_type: gatewayscript
resolved_path: local/path/to/script.js
```

---

## 5.4 Unresolved File

An unresolved file must preserve:

```text
raw reference
reference type
scheme
resolution reason
owner
evidence
```

Example:

```yaml
raw_reference: local:///transform.xsl
reference_type: xslt_file
resolution_status: unresolved_file_not_found
certainty: unresolved
```

---

## 5.5 File Semantic Extraction Status

For resolved executable artifacts, the Journey may record semantic extraction state.

Recommended values:

```text
not_required
not_attempted
extracted
partially_extracted
extraction_failed
```

This is distinct from file resolution.

A file can be:

```text
resolved
but semantic extraction not attempted
```

or:

```text
resolved
but semantic extraction failed
```

These states must not be collapsed.

---

# 6. Routing and Egress Model

Routing must use a structured model.

Recommended logical structure:

```yaml
routing:

  backend_mode:
    value:
    certainty:
    evidence_refs: []

  configured_backend:
    value:
    certainty:
    evidence_refs: []

  route_control:
    skip_backside:
    dynamic_route:
    route_action:
    script_mediated:
    transformation_mediated:

  actual_egress:
    status:
    mechanism:
    targets: []
    reason:
    certainty:
    evidence_refs: []

  remote_system_identity:
    value:
    certainty:
    evidence_refs: []

  remote_topology:
    value:
    certainty:
    evidence_refs: []
```

---

## 6.1 Backend Mode

Backend mode may represent:

```text
static
dynamic
none
direct
unresolved
not_evidenced
```

Use only evidence-backed values.

---

## 6.2 Configured Backend

Configured backend represents DataPower configuration.

Possible values may include:

```text
static URL
configured host/port
dynamic-backend mode
no configured backside
direct destination
```

Configured backend evidence must remain separate from actual egress evidence.

---

## 6.3 Actual Egress

Actual egress is operation/runtime-path evidence reconstructed from available source/configuration evidence.

Canonical status:

```text
confirmed
candidate
unresolved
not_evidenced
```

Recommended structure:

```yaml
actual_egress:
  status:
  mechanism:
  targets: []
  reason:
  certainty:
  evidence_refs: []
```

---

## 6.4 Egress Mechanisms

Possible values include:

```text
backside
route_action
gatewayscript
xslt
tcp_direct
mq
database
other_explicit_mechanism
unresolved
not_evidenced
```

Do not add a mechanism unless evidence supports it.

---

## 6.5 Confirmed Egress

Confirmed egress requires direct supporting evidence.

Examples:

```text
explicit static backend path that is actually used
explicit route action
resolved script containing outbound request behavior
TCP direct destination
explicit MQ destination
explicit database target
```

---

## 6.6 Candidate Egress

Candidate egress may be used when:

```text
evidence points to a likely target
but runtime path is not sufficiently confirmed
```

Candidate must never be rendered or described as confirmed.

---

## 6.7 Unresolved Egress

Unresolved egress means:

```text
there is evidence of routing behavior or a referenced path
but the destination or semantics cannot be fully resolved
```

Example reasons:

```text
referenced_routing_artifact_missing
dynamic_destination_not_resolved
semantic_extraction_incomplete
route_target_not_resolved
```

---

## 6.8 Not-Evidenced Egress

Not-evidenced egress means:

```text
available evidence does not establish an outbound destination or interaction
```

This differs from unresolved.

---

## 6.9 Remote System Identity

Remote system identity must be separate from endpoint value.

For example:

```text
endpoint is known
but remote business/system identity is not evidenced
```

Then:

```text
actual egress target = confirmed
remote system identity = not_evidenced
```

Do not infer remote system identity from service name alone.

---

## 6.10 Remote Topology

Remote topology represents evidence beyond the immediate DataPower target.

Examples:

```text
downstream gateway
integration layer
external network hop
government system
remote platform
```

Remote topology must remain:

```text
confirmed
candidate
unresolved
not_evidenced
```

based on evidence.

Do not fabricate topology beyond the available evidence.

---

# 7. Route-Control Semantics

Route-control evidence influences whether configured backend information represents the actual execution path.

Recommended structure:

```yaml
route_control:
  skip_backside:
    value:
    certainty:
    evidence_refs: []

  dynamic_route:
    value:
    certainty:
    evidence_refs: []

  route_action:
    present:
    certainty:
    evidence_refs: []

  script_mediated:
    present:
    certainty:
    evidence_refs: []

  transformation_mediated:
    present:
    certainty:
    evidence_refs: []
```

---

## 7.1 skip-backside

If `skip-backside` or equivalent evidence indicates that normal backside routing is bypassed:

```text
configured backend
must not automatically become
actual egress
```

Actual egress must then be determined from operation-level evidence.

---

## 7.2 Dynamic Route

Dynamic routing indicates:

```text
destination determined dynamically
```

It does not identify a specific destination by itself.

---

## 7.3 Route Action

A route action may provide explicit or dynamic route evidence.

Its destination must be interpreted according to the evidence available.

---

## 7.4 Script-Mediated Routing

When a resolved script performs outbound communication, the Journey may identify:

```text
script-mediated egress
```

Only explicit evidence should be used.

---

## 7.5 Transformation-Mediated Routing

XSLT or other transformation artifacts may influence routing.

If the transformation artifact cannot be resolved:

```text
routing semantics remain unresolved
```

Do not infer behavior from the filename.

---

# 8. Evidence Certainty Model

The canonical certainty vocabulary is:

```text
confirmed
candidate
unresolved
not_evidenced
```

This contract must remain consistent with:

```text
docs/skill-contract.md
```

---

## 8.1 Confirmed

Meaning:

```text
Direct or sufficiently resolved evidence supports the statement.
```

---

## 8.2 Candidate

Meaning:

```text
Evidence supports a plausible interpretation,
but not enough for confirmation.
```

---

## 8.3 Unresolved

Meaning:

```text
A known evidence path exists,
but Atlas cannot complete resolution.
```

---

## 8.4 Not Evidenced

Meaning:

```text
No sufficient evidence currently supports the statement.
```

---

## 8.5 Certainty Must Be Local to the Fact

Do not assign one certainty to the entire service and hide local uncertainty.

Example:

```text
Ingress                confirmed
Processing             confirmed
Configured Backend     confirmed
Actual Egress          unresolved
Remote System Identity not_evidenced
```

This is valid.

---

# 9. Provenance Requirements

Every architecture-relevant conclusion must be traceable.

Recommended provenance structure:

```yaml
provenance:
  environment:
  domain:
  source_file:
  source_object_id:
  source_occurrence_id:
  source_line_start:
  source_line_end:
  artifact_path:
  evidence_hash:
  derived_from: []
```

Not every field is required in every record.

At minimum, provenance must retain enough information to identify:

```text
where the evidence came from
which domain it belongs to
which source/index produced it
```

---

## 9.1 Domain Identity Consistency

The following must agree unless explicitly documented otherwise:

```text
Journey top-level domain
service identity domain
operation identity domain
source object domain
source path domain
relationship domain
```

Any contradiction must be treated as:

```text
INVESTIGATION_REQUIRED
```

until reproduced and classified.

---

## 9.2 Derived Evidence Provenance

Derived semantic facts must preserve references to the evidence that produced them.

Example:

```text
semantic fact
→ source artifact
→ source statement / evidence pointer
```

Do not produce semantic facts without traceable evidence.

---

# 10. Aggregation Rules

Journey aggregation must be deterministic and scope-aware.

---

## 10.1 Service Scope

A Service Journey may aggregate:

```text
service object
front-side / ingress dependencies
processing policy
matching rules
processing rules
processing actions
security dependencies
file dependencies
route-control facts
operation summaries
service-relevant findings
shared/default dependency state
```

Only evidence connected to the current service graph should be included.

---

## 10.2 Operation Scope

An Operation Journey may aggregate:

```text
matching evidence
processing rule
actions
referenced files
operation-specific route-control
actual egress
operation-specific findings
semantic facts
```

Do not include unrelated service operations.

---

## 10.3 Finding Correlation

A finding may be included when at least one of the following applies:

```text
finding scope = current domain
and materially affects the current service

finding service = current service

finding object belongs to the current service graph

finding dependency matches a dependency in the current graph

finding artifact matches a referenced artifact in the current graph

finding operation = current operation
```

Broad domain findings should only be included when relevant to the current service question.

---

## 10.4 Shared Dependency Aggregation

Shared/default dependencies should retain explicit scope such as:

```text
local
shared
default
platform
cross_domain_candidate
```

No shared dependency should be upgraded to confirmed cross-domain resolution without explicit evidence.

---

## 10.5 Operation Aggregation for Mega Policies

For large operation sets:

```text
service bundle
→ operation summary references
→ selected operation bundle on demand
```

Do not inline all operation details into the Service Journey unless specifically required.

---

## 10.6 Aggregation Must Not Strengthen Evidence

Aggregation combines evidence.

It does not create stronger evidence by itself.

Example:

```text
unresolved file reference
+
dynamic backend
```

must not become:

```text
confirmed remote destination
```

---

# 11. Evidence Propagation Rules

These rules apply when evidence moves through:

```text
Journey
→ Skill
→ Capability Analysis
→ Replacement Analysis
→ Diagram
```

---

## 11.1 Preserve Certainty

A downstream consumer must preserve certainty unless new evidence is explicitly collected.

---

## 11.2 Preserve Resolution State

The following must remain distinguishable:

```text
resolved
unresolved
not_evidenced
```

Do not flatten them into a generic missing state.

---

## 11.3 Preserve Configuration vs Behavior

The following must remain separate:

```text
configured backend
actual egress
remote identity
remote topology
```

---

## 11.4 Preserve Domain Provenance

No downstream consumer may remove domain provenance in a way that permits accidental cross-domain evidence merging.

---

## 11.5 Preserve Known Findings

Relevant known findings should move forward with the bundle.

Downstream skills should not rediscover them unless validation or deeper investigation is required.

---

# 12. Forbidden Inference Rules

The following are prohibited.

---

## 12.1 No Name-Based Relationship Inference

Forbidden:

```text
Object A looks related to Object B
→ create relationship
```

Allowed:

```text
explicit property/reference
→ resolve target
```

---

## 12.2 No Backend Invention

Forbidden:

```text
service has dynamic backend
→ assume target
```

Forbidden:

```text
service name resembles external system
→ infer backend
```

---

## 12.3 No Cross-Domain Evidence Borrowing

Forbidden:

```text
artifact missing in Domain A
artifact exists in Domain B
→ treat Domain B artifact as Domain A evidence
```

Cross-domain comparison may identify a candidate, but local evidence remains unresolved.

---

## 12.4 No Missing-Artifact Semantic Inference

Forbidden:

```text
file reference = route.xsl
artifact missing
→ assume it performs routing
```

Artifact names are hints, not behavior evidence.

---

## 12.5 No Automatic Runtime Assumption from Configuration

Forbidden:

```text
configured backend exists
→ actual egress confirmed
```

Actual egress requires evidence that the path is used.

---

## 12.6 No mTLS Inference from HTTPS Alone

HTTPS does not imply mTLS.

mTLS requires appropriate evidence such as:

```text
client identification credentials
client certificate/private key
validation credentials/trust
outbound TLS usage
```

---

## 12.7 No Outage Causality from Configuration Hotspots

Forbidden:

```text
large limits
→ caused outage
```

or:

```text
large Mega Policy
→ caused performance incident
```

Runtime causality requires runtime evidence.

---

## 12.8 No Traversal Bug from Graph Size Alone

Large graphs or large operation counts do not automatically indicate traversal overreach.

A traversal defect requires contradictory or reproducible evidence.

---

# 13. Compatibility with Existing Atlas Outputs

This contract is an aggregation contract.

It should consume existing validated Atlas outputs wherever possible.

Expected source layers include:

```text
objects
properties
references
relationships
endpoints
file-reference resolution
service journeys
operation journeys
findings
quality reports
raw CFG
resolved source artifacts
```

The preferred direction is:

```text
Existing Atlas Outputs
        ↓
Journey Aggregation / Enrichment
        ↓
Architectural Evidence Bundle
        ↓
Codex
```

The preferred implementation is additive.

Do not reopen frozen extraction layers unless:

```text
a concrete contradiction exists
a reproducible defect exists
a downstream requirement is broken
```

---

## 13.1 Existing Relationship Traversal

The existing traversal model:

```text
Service
→ Processing Policy
→ Match
→ Matching Rule
→ Processing Rule
→ Processing Actions
```

should be reused.

The purpose of this contract is to enrich and materialize architectural meaning around that traversal.

---

## 13.2 Existing File Resolution

Existing file-resolution outputs should be reused.

The Journey layer should aggregate:

```text
file reference
resolution state
resolved artifact
unresolved reason
semantic extraction state
```

without redefining the underlying resolver.

---

## 13.3 Existing Findings

Existing findings should be correlated into relevant journeys.

Do not require Codex to load and rediscover the entire findings corpus for every service question.

---

# 14. Acceptance Criteria

The Journey Evidence Contract is successfully implemented when the following conditions are met.

---

## 14.1 Service Reconstruction

For a selected service, Codex can retrieve one Service Journey and obtain:

```text
identity
ingress
processing
operation summary
resolved dependencies
unresolved dependencies
file references
file resolution states
routing state
configured backend
route-control evidence
actual egress state
security dependencies
relevant findings
certainty
provenance
```

without immediately loading broad indexes.

---

## 14.2 Operation Reconstruction

For a selected operation, Codex can retrieve one Operation Journey and obtain:

```text
match
rule
actions
file dependencies
routing semantics
actual egress
semantic facts when available
known findings
certainty
provenance
```

---

## 14.3 Missing Artifact Behavior

When a referenced artifact is unavailable:

```text
reference remains visible
resolution remains unresolved
artifact contents are not invented
actual egress remains unresolved when artifact semantics are required
```

---

## 14.4 Configured vs Actual Egress

The model must support:

```text
configured backend = confirmed
actual egress = confirmed / candidate / unresolved / not_evidenced
```

as separate facts.

---

## 14.5 Certainty Preservation

No downstream stage may strengthen:

```text
candidate
unresolved
not_evidenced
```

without explicit new evidence.

---

## 14.6 Provenance

Every architecture-relevant fact can be traced to:

```text
domain
source object / artifact / index
supporting evidence pointer
```

---

## 14.7 Domain Isolation

A Journey must not silently consume evidence from another domain.

Cross-domain evidence must remain explicitly marked as correlation or candidate evidence.

---

## 14.8 Known Finding Reuse

Relevant known findings appear in the Journey bundle before Codex performs deeper investigation.

Codex should not repeatedly rediscover known evidence that has already been materialized.

---

## 14.9 Token Efficiency

Service-level investigation should follow:

```text
Journey
→ targeted operation evidence when required
→ supporting index when required
→ raw CFG/source only when required
```

and not:

```text
load entire domain
load entire findings corpus
load all relationships
load all raw CFG
```

---

## 14.10 Frozen Layer Protection

Implementation of this contract must not require redesign of already validated extraction layers unless a focused investigation proves that an upstream defect exists.

---

# Final Contract Principles

The Journey and Aggregation layer MUST preserve the following:

```text
Raw source remains authoritative.

Journey is an architectural evidence bundle, not only a graph.

No resolved file does not mean no file reference.

Unresolved does not mean absent.

Configured backend does not equal actual egress.

Dynamic routing does not identify a destination by itself.

Missing artifacts must remain unresolved.

Known findings should be reused, not rediscovered.

Evidence certainty must remain explicit.

Provenance must remain traceable.

Domain evidence must not be borrowed automatically.

Large graphs are not traversal defects by default.

Semantic facts require source evidence.

The Journey layer should enrich forward,
not reopen frozen extraction layers without proof.

Codex should start from compact aggregated evidence
and retrieve raw source only when necessary.
```
