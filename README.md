# DataPower Atlas
<img src="image/cover.jpg" width="50%" >

**Evidence-driven architecture reconstruction for IBM DataPower
modernization.**

DataPower Atlas transforms raw IBM DataPower exports into structured, Indexed
and traceable architecture evidence that can be used to reconstruct the
AS-IS landscape, understand service and operation behavior, derive
functional capabilities, Draw User Journey and support evidence-based modernization and
,replacement analysis.

Atlas is not a generic DataPower documentation generator and it is not a
configuration beautifier. Its first responsibility is to reconstruct the
implementation that actually exists.

> **Reconstruct the architecture that exists. Do not make it cleaner,
> simpler, more complete, or more certain than the evidence supports.
> When evidence stops, Atlas stops.**

------------------------------------------------------------------------

## Why DataPower Atlas Exists

Large DataPower estates are difficult to modernize because the
architecture is rarely represented in one place.

The real implementation is distributed across configuration objects,
processing policies, matching rules, processing actions, XSLT,
GatewayScript, endpoints, TLS and crypto configuration, XML Managers,
local and platform resources, appliance-level networking, and
environment-specific configuration.

A modernization assessment therefore cannot safely start with a product
comparison such as:

``` text
DataPower object
→ replacement product
```

Atlas instead builds an evidence chain:

``` text
Raw DataPower Export
        ↓
Structured Architecture Index
        ↓
Service Journeys
        ↓
Operation Journeys
        ↓
Architectural Findings
        ↓
Functional Capabilities
        ↓
Replacement Requirements
        ↓
Solution Roles
        ↓
Candidate Technologies
```

This keeps AS-IS reconstruction separate from TO-BE design.

------------------------------------------------------------------------

## Core Objectives

DataPower Atlas is designed around four objectives:

1.  **Reconstruct the AS-IS architecture faithfully** from DataPower
    evidence.
2.  **Derive functional capabilities from observed behavior**, not
    object names.
3.  **Support evidence-based modernization requirements** without
    jumping directly from DataPower objects to products.
4.  **Minimize unnecessary retrieval and token consumption** through
    compact indexes, evidence bundles, and targeted investigation.

Codex operates within Atlas as an **Architecture Investigation Engine**.

------------------------------------------------------------------------

## Evidence Model

Atlas uses a strict source-of-truth hierarchy:

``` text
Raw CFG / Raw Export / Referenced Source Artifact
                    ↓
          Validated Atlas Indexes
                    ↓
        Journey Evidence Bundles
                    ↓
              Skill Outputs
                    ↓
 Capability / Replacement / Diagram Outputs
```

Raw configuration and referenced source artifacts remain authoritative.

All indexes, journeys, findings, reports, capability inventories, and
modernization outputs are derived and must remain traceable to source
evidence.

If a derived artifact conflicts with authoritative source evidence:

``` text
Raw Evidence Wins
```

The contradiction must then be investigated rather than silently
normalized.

------------------------------------------------------------------------

## What Is a Journey?

A Journey is not merely a graph summary.

Atlas treats a Service Journey or Operation Journey as an
**Architectural Evidence Bundle** containing the compact evidence
required for downstream reasoning.

Conceptually:

``` text
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

The goal is to make the Journey sufficiently complete for architecture
analysis without forcing Codex to repeatedly scan broad indexes or
reopen raw configuration.

### Service Architectural Evidence Bundle

A service bundle may contain:

``` yaml
service_journey:
  identity:
    environment:
    domain:
    service_type:
    service_name:
    service_id:

  ingress:
    listeners: []
    protocols: []
    ingress_status:
    certainty:

  processing:
    processing_policies: []
    operation_count:
    operation_ids: []
    certainty:

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
    generated_from: []
```

### Operation Architectural Evidence Bundle

Operation Journeys provide the operation-level evidence required to
understand processing and actual egress:

``` yaml
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

Resolved XSLT or GatewayScript artifacts may contribute compact semantic
facts such as transformation behavior or explicit outbound communication
when the source actually supports those conclusions.

------------------------------------------------------------------------

## Evidence Certainty

Atlas uses four canonical certainty states:

  -----------------------------------------------------------------------
  State                               Meaning
  ----------------------------------- -----------------------------------
  `confirmed`                         Direct or sufficiently resolved
                                      evidence supports the statement.

  `candidate`                         Evidence supports a plausible
                                      interpretation but is insufficient
                                      for confirmation.

  `unresolved`                        A known evidence path exists, but
                                      Atlas cannot currently complete its
                                      resolution.

  `not_evidenced`                     Available evidence does not
                                      establish the architecture element
                                      or behavior.
  -----------------------------------------------------------------------

Certainty is local to each fact.

A service can legitimately contain:

``` text
Ingress                 confirmed
Processing              confirmed
Configured Backend      confirmed
Actual Egress           unresolved
Remote System Identity  not_evidenced
```

A downstream stage must not strengthen certainty unless it retrieves new
supporting evidence and preserves its provenance.

For example:

``` text
unresolved
→ referenced artifact retrieved
→ explicit outbound behavior observed
→ confirmed
```

is valid.

But:

``` text
candidate → confirmed
unresolved → confirmed
not_evidenced → candidate
```

without new evidence is not.

------------------------------------------------------------------------

## Critical Evidence Rules

Atlas deliberately preserves ambiguity where the source is ambiguous.

``` text
Names are hints, not evidence.

Unresolved is not automatically a bug.

Unresolved is not absent.

No resolved file is not the same as no file reference.

Missing artifact does not permit inference of its contents.

Configured backend is not automatically actual egress.

Dynamic routing does not identify a destination.

Cross-domain similarity does not resolve a local dependency.

Large processing graph does not automatically mean traversal defect.

Configuration hotspot does not prove runtime causality.

HTTPS does not by itself prove mTLS.
```

These distinctions are fundamental to the reliability of the
reconstructed architecture.

------------------------------------------------------------------------

## Domain Isolation

Each DataPower domain is treated as an independent evidence boundary.

Object identity is based on:

``` text
environment
+
domain
+
canonical_type
+
logical_name
```

Atlas does not merge objects merely because names match.

Resolution remains local to the originating environment and domain.
Evidence from another application domain or from `DEFAULT` must not be
silently borrowed to complete local uncertainty.

Cross-domain relationships are handled later as explicit correlation
analysis.

Examples of correlation classes include:

``` text
same_logical_service_candidate
replica_variant
shared_configuration_candidate
configuration_drift
domain_specific_service
shared_default_dependency_candidate
```

Correlation is derived evidence. It is not local resolution.

------------------------------------------------------------------------

## Official Analysis Pipeline

Every application domain follows the same official pipeline:

``` text
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
```

The authoritative orchestrator is:

``` bash
tools/run_domain_pipeline.sh
```

Final domain outputs must be reproducible through this pipeline.

Individual tools may be executed during focused investigations, but
there should be exactly one authoritative runtime implementation for
each tool. Version history belongs in Git rather than in runtime
filenames such as `_v2`, `_fixed`, or `_hotfix`.

------------------------------------------------------------------------

## Retrieval Strategy

Token efficiency is an architecture requirement, not merely a prompt
optimization.

The target is:

``` text
minimum evidence retrieval
+
maximum architectural correctness
```

The default retrieval pattern is:

``` text
Question
   ↓
Exact Environment / Domain
   ↓
Exact Service
   ↓
Service Journey / Service Evidence Bundle
   ↓
Relevant Known Findings
   ↓
Operation Journey / Operation Evidence Bundle
        when required
   ↓
Supporting Index
        when required
   ↓
Raw CFG / Source Artifact
        only when required
```

Or more compactly:

``` text
Index First
→ Journey First
→ Exact Target Retrieval
→ Supporting Evidence Only When Needed
→ Raw CFG / Source Only When Needed
```

Atlas avoids whole-domain scans, complete findings-register retrieval,
full CFG loading, all-operation retrieval, duplicate evidence loading,
and broad DataPower semantic documentation unless the investigation
actually requires them.

------------------------------------------------------------------------

## Skill Architecture

Atlas skills form a staged evidence pipeline.

``` text
run-domain-analysis
        ↓
trace-service
        ↓
trace-operation            when required
        ↓
investigate-gap            when required
        ↓
datapower-semantics        supporting lookup
        ↓
capability-analysis
        ↓
replacement-analysis
        ↓
generate-architecture-diagrams
```

For cross-domain work:

``` text
validated domain outputs
        ↓
default-domain-analysis    when required
        ↓
compare-domains
        ↓
cross-domain architectural evidence
        ↓
capability-analysis
        ↓
replacement-analysis
        ↓
generate-architecture-diagrams
```

A downstream skill should consume the smallest sufficient validated
output from upstream rather than repeating the investigation.

### `run-domain-analysis`

Runs and validates the official domain pipeline.

It checks pipeline execution, generated evidence, quality findings,
regressions, and open gaps before deeper architectural analysis begins.

Expected result states include:

``` text
PASS
PASS_WITH_FINDINGS
INVESTIGATION_REQUIRED
PIPELINE_FAILURE
```

### `trace-service`

Reconstructs one service AS-IS journey using the minimum necessary
evidence.

Typical scope includes:

``` text
Ingress
Processing
Operations
Routing / Egress
Security
Files / Artifacts
Configuration Dependencies
Evidence Gaps
Findings
Provenance
```

The service is reconstructed from what configuration evidence
proves---not from what its name suggests it should do.

### `trace-operation`

Traces one operation inside a service or Mega Policy.

Typical structural path:

``` text
Service
→ Processing Policy
→ Match
→ Matching Rule
→ Processing Rule
→ Processing Actions
→ Routing / Egress
```

Only the selected operation is retrieved unless broader policy analysis
is explicitly required.

### `investigate-gap`

Investigates missing, unresolved, contradictory, or suspicious evidence
before any parser or resolver change is proposed.

It answers:

``` text
Is this an Atlas defect,
a source-configuration condition,
or an evidence gap?
```

### `datapower-semantics`

Provides compact DataPower-specific interpretation only when generic
Atlas evidence is insufficient.

It is intentionally not a broad DataPower CLI encyclopedia.

### `capability-analysis`

Converts validated AS-IS evidence into functional capability statements.

Capabilities come from observed behavior.

Examples include:

``` text
HTTP/S ingress
policy-based request processing
dynamic routing
backend integration
XSLT transformation
GatewayScript execution
TLS / PKI
SOAP / WSDL mediation
messaging integration
Layer-4 TCP forwarding
XML processing
```

An object type does not automatically imply that every possible
capability of that object is being used.

### `replacement-analysis`

Translates validated capabilities into replacement requirements and
solution roles.

The required reasoning chain is:

``` text
Current Function
→ Capability
→ NFR / Constraint
→ Replacement Requirement
→ Solution Role
→ Candidate Technology
```

Atlas does not perform direct mappings such as:

``` text
MPGW → Product X
WSP  → Product Y
```

without capability-level analysis.

### `compare-domains`

Compares already-validated domain outputs while preserving domain-local
truth.

It identifies evidence-backed drift, replica variants, shared
configuration candidates, domain-specific services, and shared/default
dependency candidates.

### `default-domain-analysis`

Treats the DataPower `DEFAULT` domain as an appliance/platform layer
rather than a normal application-service domain.

Analysis may include evidenced:

``` text
network interfaces
IP addressing
gateways and routes
DNS
static hosts
host aliases
management configuration
system/runtime settings
certificate and crypto services
shared platform resources
```

`DEFAULT` is not an automatic fallback resolver for unresolved
application-domain dependencies.

### `classify-finding`

Provides lightweight, evidence-backed classification of an observed
condition.

### `generate-architecture-diagrams`

Renders validated architecture evidence.

It is a renderer, not an investigator, and diagrams must never appear
more certain than the underlying evidence.

------------------------------------------------------------------------

## Finding Classification

Atlas uses explicit finding classes:

  -----------------------------------------------------------------------
  Classification                      Meaning
  ----------------------------------- -----------------------------------
  `BUG`                               Atlas output reproducibly
                                      contradicts authoritative evidence.

  `GAP`                               Atlas lacks required source
                                      evidence, semantic support,
                                      taxonomy, mapping, or another
                                      legitimate architecture-relevant
                                      construct.

  `FINDING`                           Atlas correctly exposes a notable
                                      source-configuration condition.

  `EXPECTED_UNRESOLVED`               The unresolved state is understood
                                      and expected under the
                                      source/platform model.

  `ARCHITECTURAL_HOTSPOT`             Evidence shows unusual
                                      concentration, complexity, limits,
                                      reuse, or dependency density worth
                                      architectural attention.

  `INVESTIGATION_REQUIRED`            Available evidence is contradictory
                                      or insufficient for safe
                                      classification.
  -----------------------------------------------------------------------

Classification and remediation are separate decisions.

Possible remediation actions include:

``` text
NO_CHANGE
ADD_TAXONOMY
ADD_MAPPING
ADD_SEMANTIC_SUPPORT
FIX_LOGIC
COLLECT_MORE_EVIDENCE
RECORD_FINDING
```

Atlas avoids vague catch-all classifications when a precise reason can
be retained.

------------------------------------------------------------------------

## Routing and Egress

Routing is modeled explicitly rather than collapsed into a generic
`backend` field.

``` text
Backend Mode
Configured Backend
Route-Control Evidence
Actual Egress
Remote System Identity
Remote Topology
```

This distinction is essential for services where the configured backside
is not the actual operation path.

Possible egress mechanisms include:

``` text
backside
route_action
gatewayscript
xslt
tcp_direct
mq
database
other_explicit_mechanism
```

Actual egress may be:

``` text
confirmed
candidate
unresolved
not_evidenced
```

For example, if a request path bypasses normal backside routing and a
resolved GatewayScript performs an outbound HTTP request, the configured
backend remains configuration evidence while the script-mediated
outbound request may become the actual evidenced egress.

Atlas does not create two runtime calls merely because both
configuration forms exist.

------------------------------------------------------------------------

## File and Artifact Evidence

Explicit file references remain evidence independently of whether the
target can be resolved.

Examples include:

``` text
local:///
store:///
cert:///
pubcert:///
```

Atlas preserves:

``` text
raw reference
reference type
URI scheme
owner
resolution status
resolved path when available
artifact type
certainty
provenance
```

A referenced but unavailable artifact remains unresolved.

``` text
no resolved file
!=
no file reference
```

For resolved executable artifacts, file resolution and semantic
extraction are separate states. A file may be resolved even when
semantic extraction was not attempted or could not be completed.

------------------------------------------------------------------------

## Supported Service Patterns

### Multi-Protocol Gateway

Typical evidenced structure:

``` text
Ingress
→ MPGW
→ Processing Policy
→ Matching Rule
→ Processing Rule
→ Processing Actions
→ Routing / Egress
```

Stages are included only when evidence supports them.

### Web Service Proxy

A WSP journey may include:

``` text
WSP
→ XML Manager
→ TLS Client Profile
→ WSM Processing Policy
→ Matching Rule
→ WSM Processing Rule
→ Endpoint Rewrite
→ Front Side Handler / Remote Endpoint
```

Atlas does not assume every WSP contains every element and does not
invent missing endpoint-rewrite semantics.

### TCP Proxy

TCP Proxy uses a direct network model:

``` text
local-address:local-port
→ TCP Proxy
→ destination-address:destination-port
```

It is not forced into MPGW-style policy semantics.

------------------------------------------------------------------------

## Mega Policies

Large processing graphs are not automatically traversal defects.

A service may legitimately contain many operations and processing
relationships.

Before treating a large graph as an Atlas defect, the evidence path must
be checked:

``` text
Processing Policy
→ Matches
→ Matching Rules
→ Processing Rules
→ Processing Actions
```

For normal service analysis, Atlas retrieves operation summaries first
and selected operation details only when needed.

The complete operation set is appropriate for questions involving
policy-wide comparison, concentration, shared behavior, patterns, or
coverage.

------------------------------------------------------------------------

## Appliance / DEFAULT Analysis

The `DEFAULT` domain is analyzed as a platform domain.

The analysis is evidence-first and does not assume a predetermined
appliance topology.

Potential architecture areas include:

``` text
Network foundation
Management plane
Security foundation
Shared runtime services
Shared crypto / TLS
Shared infrastructure dependencies
```

The process reuses existing exports and pipeline outputs where possible.

A typical flow is:

``` text
Existing pipeline outputs?
        ↓
Locate actual appliance configuration
        ↓
Discover observed top-level configuration families
        ↓
Reconstruct interfaces
        ↓
Reconstruct routes
        ↓
Reconstruct DNS / aliases
        ↓
Reconstruct system/runtime settings
        ↓
Separate facts, findings, hypotheses, and evidence gaps
        ↓
Update consolidated AS-IS architecture reference
```

Application-domain evidence may later be correlated with appliance
evidence, but a route or matching subnet alone does not prove that a
specific service uses a particular interface.

------------------------------------------------------------------------

## Freeze Philosophy

Validated pipeline components become **Frozen**.

A frozen component is not reopened simply because new evidence appears.

Reopening requires one of:

``` text
1. reproducible defect
2. concrete contradiction with authoritative evidence
3. broken downstream requirement
```

Where possible, Atlas extends the pipeline forward through additive
changes such as:

``` text
new taxonomy mapping
new parser extension
new resolver
new semantic support
new aggregation layer
new correlation rule
explicit exception
new reporting layer
```

rather than redesigning already validated behavior.

This protects validated evidence and reduces regression risk.

------------------------------------------------------------------------

## Regression Philosophy

Regression validation is semantic, not count-only.

A valid change may legitimately alter totals.

Atlas therefore inspects changes to:

``` text
object identity
relationship identity
endpoint identity
operation identity
file references
routing state
egress state
evidence certainty
provenance
new/lost records
classification changes
```

Unexpected silent loss of evidence is a failure.

------------------------------------------------------------------------

## Modernization Boundary

Atlas keeps extraction and modernization separate.

``` text
Extraction:
What exists?

Modernization:
What should exist?
```

The modernization sequence is:

``` text
Current DataPower Function
        ↓
Required Functional Capability
        ↓
NFRs / Constraints
        ↓
Operational Characteristics
        ↓
Replacement Requirement
        ↓
Solution Role
        ↓
Candidate Technology
```

A single DataPower service may require multiple replacement roles.

Examples may include:

``` text
API gateway
integration runtime
service mesh / ingress
Layer-4 proxy
IAM / policy enforcement
PKI / secrets management
messaging platform
transformation runtime
```

Atlas does not force all DataPower behavior into one replacement
product.

------------------------------------------------------------------------

## Architecture Diagrams

Architecture diagrams are derived renderings of validated evidence.

They must preserve certainty and visibly distinguish:

``` text
confirmed
candidate
unresolved
```

A diagram must not invent a missing backend, remote system, topology, or
dependency.

In other words:

``` text
Diagram Certainty
<=
Evidence Certainty
```

------------------------------------------------------------------------

## Repository Contracts

The operating model is governed by two primary contracts:

``` text
docs/skill-contract.md
docs/journey-evidence-contract.md
```

`skill-contract.md` defines:

``` text
skill execution chain
shared terminology
input/output contracts
certainty propagation
finding classifications
token-efficiency rules
integration reasoning patterns
```

`journey-evidence-contract.md` defines:

``` text
Service Architectural Evidence Bundle
Operation Architectural Evidence Bundle
dependency semantics
file reference and resolution states
routing and egress semantics
route-control semantics
evidence certainty
provenance
aggregation rules
```

Skill-specific instructions must conform to these shared contracts.

------------------------------------------------------------------------

## Consolidated AS-IS Reference

Appliance/default-domain architecture evidence is consolidated into:

``` text
docs/as-is-architecture-reference.md
```

The reference is derived from raw exports and domain-local indexes.

Raw configuration remains authoritative.

Architecture-relevant statements should retain enough provenance to
trace them back to their source.

------------------------------------------------------------------------

## Typical Investigation Workflow

When an anomaly is discovered:

``` text
1. Identify environment
2. Identify domain
3. Identify service / object / operation
4. Inspect existing Journey Evidence Bundle
5. Reuse relevant known findings
6. Inspect supporting index evidence only when required
7. Inspect raw CFG / source only when required
8. Reproduce the issue
9. Isolate the affected stage
10. Compare derived output with raw evidence
11. Classify the anomaly
12. Determine downstream impact
13. Select the minimum corrective action
```

The rule is simple:

``` text
Classify first.
Change code only when evidence proves Atlas is wrong.
```

------------------------------------------------------------------------

## Design Principles

DataPower Atlas is built around a small number of non-negotiable
principles:

``` text
Raw evidence is authoritative.

Names are hints, not evidence.

Domain-local truth must be preserved.

Unresolved evidence stays unresolved.

Missing evidence stays visible.

Configured backend is not automatically actual egress.

Dynamic routing does not permit destination inference.

Capabilities come from observed behavior.

Replacement analysis follows capability analysis.

Known evidence should be retrieved once and reused.

Raw source should be opened only when necessary.

Diagrams render evidence; they do not create architecture.
```

------------------------------------------------------------------------

## Project Philosophy

Real enterprise integration estates are rarely clean.

A useful architecture reconstruction system must resist the temptation
to silently normalize that reality.

If the implementation contains duplicated configuration, shared Mega
Policies, unresolved artifacts, dynamic routing, incomplete endpoint
definitions, unusual limits, or domain-specific inconsistencies, Atlas
should expose those conditions as structured evidence.

The purpose of Atlas is **faithful reconstruction first**.

Modernization decisions come later.

> **When evidence stops, Atlas stops.**
