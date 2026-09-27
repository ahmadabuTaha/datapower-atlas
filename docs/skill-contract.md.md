# DataPower Atlas — Skill Contract

## Purpose

This contract defines how Codex skills cooperate across the DataPower Atlas analysis workflow.

It establishes:

1. the official skill execution chain;
2. shared terminology;
3. input/output contracts;
4. evidence certainty propagation rules;
5. finding classifications;
6. token-efficiency rules;
7. integration few-shot scenarios.

This contract does **not** define the internal schema of Service or Operation Architectural Evidence Bundles.

The authoritative representation of aggregated journey evidence is defined separately in:

```text
docs/journey-evidence-contract.md
```

Skills that consume or produce Service / Operation architectural evidence MUST conform to that contract.

---

# 1. Skill Execution Chain

## 1.1 Primary Analysis Flow

The primary skill chain is:

```text
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

The sequence is evidence-driven.

Not every skill must run for every question.

A downstream skill SHOULD reuse validated upstream output before retrieving the same evidence again.

---

## 1.2 Cross-Domain Flow

Cross-domain analysis follows:

```text
run-domain-analysis
        ↓
validated domain outputs
        ↓
default-domain-analysis    when DEFAULT/appliance analysis is required
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

Cross-domain analysis MUST NOT weaken domain-local truth.

Domain-local evidence remains authoritative for that domain.

---

## 1.3 Skill Roles

### run-domain-analysis

Purpose:

```text
Run and validate the official Atlas pipeline for one domain.
```

Primary responsibilities:

- run the official pipeline;
- validate expected outputs;
- inspect summary-level evidence first;
- identify regressions, anomalies, or gaps;
- avoid modifying frozen components unless a reproducible defect is confirmed.

Expected result states:

```text
PASS
PASS_WITH_FINDINGS
INVESTIGATION_REQUIRED
PIPELINE_FAILURE
```

---

### trace-service

Purpose:

```text
Reconstruct one service AS-IS journey using the minimum necessary evidence.
```

Default retrieval order:

```text
Service Journey
→ Relevant aggregated evidence
→ Operation summaries / Operation Journeys when required
→ Supporting indexes when required
→ Raw CFG / source artifact only when verification is required
```

The skill MUST reconstruct what the configuration actually evidences.

It MUST NOT reconstruct what the service name suggests should exist.

---

### trace-operation

Purpose:

```text
Trace one operation inside a service or Mega Policy.
```

Typical structural path:

```text
Service
→ Processing Policy
→ Match
→ Matching Rule
→ Processing Rule
→ Processing Actions
```

The skill MAY retrieve referenced XSLT or GatewayScript artifacts when operation semantics cannot be established from aggregated evidence.

It MUST NOT load all operations unless the user question or investigation requires it.

---

### investigate-gap

Purpose:

```text
Investigate unresolved, contradictory, missing, or suspicious Atlas evidence.
```

The skill MUST classify the issue before recommending any code or taxonomy change.

It MUST distinguish between:

```text
real source configuration behavior
Atlas coverage gap
taxonomy gap
semantic mapping gap
parser / resolver defect
expected unresolved state
missing evidence
```

---

### datapower-semantics

Purpose:

```text
Provide compact DataPower-specific semantic interpretation when generic Atlas evidence is insufficient.
```

This skill is a supporting lookup skill.

It MUST NOT become a broad DataPower CLI encyclopedia.

Project-specific facts SHOULD NOT be stored as universal semantic rules.

---

### capability-analysis

Purpose:

```text
Translate validated AS-IS architectural evidence into functional capabilities.
```

Capabilities MUST describe observed behavior.

Object names alone MUST NOT be treated as capabilities.

Capability derivation MUST preserve evidence certainty.

---

### replacement-analysis

Purpose:

```text
Translate validated capabilities into replacement requirements and solution roles.
```

The required reasoning chain is:

```text
Current Function
→ Capability
→ NFR / Constraint
→ Replacement Requirement
→ Solution Role
→ Candidate Technology
```

The skill MUST NOT perform direct object-to-product replacement mapping.

---

### compare-domains

Purpose:

```text
Compare already-validated domain outputs without weakening domain isolation.
```

Possible correlation classes may include:

```text
same_logical_service_candidate
replica_variant
shared_configuration_candidate
configuration_drift
domain_specific_service
shared_default_dependency_candidate
```

Correlation MUST NOT be inferred from names alone.

---

### default-domain-analysis

Purpose:

```text
Analyze the DEFAULT / appliance layer as a platform domain rather than as a normal application-service domain.
```

Typical areas include:

```text
network foundation
management plane
security foundation
shared runtime services
shared crypto / TLS
shared infrastructure dependencies
```

DEFAULT MUST NOT be used as an automatic resolution fallback for unresolved application-domain dependencies.

---

### classify-finding

Purpose:

```text
Provide a lightweight classification of an observed issue or finding.
```

Expected output:

```text
classification
one-sentence rationale
next evidence needed, when applicable
```

The skill SHOULD remain minimal.

---

### generate-architecture-diagrams

Purpose:

```text
Render already-validated evidence into architecture diagrams.
```

This skill is a renderer, not an investigator.

The diagram MUST NOT appear more certain than the evidence.

---

## 1.4 Smoke-Test Validation Behavior

Smoke testing is used to validate the operating model, skill chain, evidence retrieval behavior, and downstream reasoning.

Codex MAY use generated Atlas directories and indexes available in the local workspace as validation evidence.

Smoke-test inputs and outputs that are intentionally ignored by Git MUST remain local validation material.

They MUST NOT be copied into:

```text
committed architecture contracts
skills
schemas
taxonomy
permanent reference examples
```

A smoke test SHOULD follow:

```text
Question
→ Service / User Journey
→ Relevant aggregated evidence
→ Operation evidence when required
→ Supporting indexes when required
→ Raw CFG / source artifact only for verification
```

Smoke testing SHOULD verify that:

- known evidence is reused rather than rediscovered;
- unresolved references remain unresolved;
- missing artifacts are not treated as absent references;
- configured backend is not automatically treated as actual operation egress;
- evidence is not borrowed from another domain;
- evidence certainty is not strengthened without new evidence;
- raw source is opened only when aggregated evidence is insufficient.

Smoke-test observations MAY result in generalized contract or implementation improvements.

Service-specific, operation-specific, or domain-specific facts MUST NOT become permanent skill rules.

---

# 2. Shared Terminology

All skills MUST use the following terminology consistently.

---

## 2.1 Raw Evidence

Evidence taken directly from authoritative source artifacts.

Examples:

```text
raw CFG
exported XSLT
exported GatewayScript
exported XML / WSDL / XSD
other source artifacts from the DataPower export
```

Raw evidence is authoritative over derived Atlas outputs.

---

## 2.2 Derived Evidence

Evidence produced from raw evidence by deterministic or analytical Atlas stages.

Examples:

```text
objects
properties
references
relationships
endpoints
file-resolution records
service journeys
operation journeys
findings
aggregated evidence bundles
```

Derived evidence is rebuildable.

---

## 2.3 Service Journey

The structured architectural representation of one service and its directly relevant:

```text
ingress
processing
operations
dependencies
routing
security
files
findings
provenance
```

The exact structure is defined by:

```text
docs/journey-evidence-contract.md
```

---

## 2.4 Operation Journey

The structured evidence path for one operation within a service.

Typical scope:

```text
match
matching rule
processing rule
processing actions
referenced artifacts
routing behavior
operation-level egress
evidence status
provenance
```

---

## 2.5 Dependency

An evidence-backed relationship from one architecture element to another.

A dependency MUST originate from explicit evidence.

Names alone MUST NOT create dependencies.

---

## 2.6 Resolved Dependency

A dependency where the referenced target has been resolved to a known Atlas object, artifact, endpoint, or evidence record.

---

## 2.7 Unresolved Dependency

A dependency whose reference exists but whose target or semantics cannot currently be fully resolved.

Important:

```text
unresolved
!=
absent
```

and:

```text
no resolved target
!=
no reference
```

---

## 2.8 File Reference

An explicit source reference to an external or local artifact.

Examples:

```text
local:///
store:///
cert:///
pubcert:///
```

The file reference remains evidence even when the referenced artifact cannot be resolved.

---

## 2.9 Configured Backend

A backend, backend URL, destination, or backend mode represented in service configuration.

A configured backend MUST NOT automatically be interpreted as actual operation egress.

---

## 2.10 Actual Egress

An outbound interaction or destination supported by operation-level evidence.

Actual egress may be implemented through:

```text
normal backside routing
route action
GatewayScript
XSLT-driven behavior
TCP direct forwarding
other evidenced mechanisms
```

---

## 2.11 Candidate Egress

A plausible outbound destination supported by partial evidence but not sufficient evidence for confirmation.

---

## 2.12 Dynamic Routing

Routing behavior where the destination is determined dynamically rather than by one static configured endpoint.

Dynamic routing MUST NOT be converted into a static destination unless evidence resolves the destination.

---

## 2.13 Script-Mediated Egress

Outbound behavior performed by a referenced script rather than by the normal configured service backside path.

---

## 2.14 Finding

An evidence-backed observation about architecture, configuration, quality, coverage, or risk.

A finding is not automatically a bug.

---

## 2.15 Evidence Gap

A known area where evidence is insufficient to confirm architecture or behavior.

An evidence gap MUST remain explicit.

It MUST NOT be filled by assumption.

---

## 2.16 Provenance

Information that allows an Atlas-derived statement to be traced back to its origin.

Provenance may include:

```text
environment
domain
source file
object identity
occurrence identity
line range
artifact path
evidence record
hash / source pointer
```

---

# 3. Input / Output Contracts

## 3.1 General Rule

Skills MUST consume the smallest sufficient upstream output.

They SHOULD NOT bypass validated upstream outputs and independently rediscover the same evidence unless:

```text
verification is required
upstream evidence is incomplete
upstream evidence is contradictory
new evidence is explicitly required
```

Service and operation architectural evidence exchanged between skills MUST conform to:

```text
docs/journey-evidence-contract.md
```

---

## 3.2 run-domain-analysis

### Input

```text
domain
environment when applicable
official Atlas workspace
official pipeline
```

### Output

```text
pipeline result state
validated domain output locations
summary counts
findings
regression indicators
open evidence gaps
```

### Must Not

```text
redesign frozen pipeline components without evidence
treat every unresolved record as failure
```

---

## 3.3 trace-service

### Input

```text
domain
service identity
available Journey / Atlas indexes
optional user investigation question
```

### Output

```text
Service Architectural Evidence Bundle
relevant operation summaries
relevant findings
unresolved evidence requiring deeper investigation
source / provenance pointers
```

### Must Not

```text
invent missing backend
infer relationships from service names
load the whole domain when exact service evidence exists
borrow unresolved evidence from another domain
```

---

## 3.4 trace-operation

### Input

```text
validated Service Architectural Evidence Bundle
selected operation identity
available Operation Journey / supporting indexes
```

### Output

```text
Operation Architectural Evidence Bundle
processing path
referenced artifacts
routing semantics
operation-level egress status
relevant findings
provenance
```

### Must Not

```text
load unrelated operations by default
convert missing artifacts into missing references
infer a route from a dynamic-backend flag alone
```

---

## 3.5 investigate-gap

### Input

```text
specific gap, inconsistency, unresolved state, or suspected defect
relevant upstream evidence
supporting indexes when required
raw source when required
```

### Output

```text
classification
evidence summary
impact
recommended action
next evidence required, when applicable
```

### Recommended Actions

```text
NO_CHANGE
ADD_TAXONOMY
ADD_MAPPING
ADD_SEMANTIC_SUPPORT
FIX_LOGIC
COLLECT_MORE_EVIDENCE
RECORD_FINDING
```

Classification and remediation action MUST remain separate concepts.

---

## 3.6 datapower-semantics

### Input

```text
specific DataPower construct or behavior requiring interpretation
minimal surrounding evidence
```

### Output

```text
compact semantic interpretation
architecture relevance
limitations / ambiguity
```

### Must Not

```text
load broad unrelated DataPower documentation
turn project-specific behavior into universal rules
```

---

## 3.7 capability-analysis

### Input

```text
validated Service / Operation Architectural Evidence Bundle
relevant findings
evidence certainty
```

### Output

```text
functional capabilities
supporting evidence
certainty
constraints / NFR indicators when evidenced
```

### Must Not

```text
derive a capability from an object name alone
convert unresolved behavior into confirmed capability
select replacement technology
```

---

## 3.8 replacement-analysis

### Input

```text
validated capabilities
relevant NFRs
constraints
operational characteristics
```

### Output

```text
replacement requirements
solution roles
candidate technology categories when requested
assumptions / unresolved constraints
```

### Must Not

```text
perform direct object-to-product mapping
ignore unresolved capabilities
strengthen certainty without new evidence
```

---

## 3.9 compare-domains

### Input

```text
two or more validated domain outputs
domain-local evidence bundles
cross-domain comparison question
```

### Output

```text
evidence-backed correlations
differences
configuration drift indicators
shared dependency candidates
domain-specific behavior
```

### Must Not

```text
merge objects by name alone
resolve one domain using another domain automatically
overwrite domain-local truth
```

---

## 3.10 default-domain-analysis

### Input

```text
DEFAULT domain / appliance-level export evidence
```

### Output

```text
platform architecture evidence
network foundation
management services
security foundation
shared runtime / service capabilities
shared dependency candidates
```

### Must Not

```text
treat DEFAULT as a normal application-service domain
automatically resolve application-domain references into DEFAULT
```

---

## 3.11 classify-finding

### Input

```text
one specific observed issue
minimal supporting evidence
```

### Output

```text
classification
one-sentence rationale
next evidence needed, when applicable
```

---

## 3.12 generate-architecture-diagrams

### Input

```text
validated architectural evidence
evidence certainty
requested diagram mode
```

### Output

```text
PlantUML or equivalent diagram source
```

Supported modes may include:

```text
component
network
service-journey
cross-domain
```

### Must Not

```text
invent missing architecture
hide unresolved relationships
render candidate relationships as confirmed
```

---

# 4. Evidence Certainty Propagation

## 4.1 Canonical Certainty States

All skills MUST use the following certainty vocabulary:

```text
confirmed
candidate
unresolved
not_evidenced
```

---

## 4.2 confirmed

Meaning:

```text
Direct or sufficiently resolved evidence supports the statement.
```

Examples:

```text
explicit relationship resolved to target
explicit endpoint configuration
resolved source artifact containing outbound behavior
```

---

## 4.3 candidate

Meaning:

```text
Evidence supports a plausible interpretation,
but is insufficient for confirmation.
```

Candidate MUST remain visibly distinct from confirmed.

---

## 4.4 unresolved

Meaning:

```text
A reference, dependency, or expected evidence path exists,
but Atlas cannot currently complete its resolution.
```

Unresolved MUST NOT be converted into absent or false.

---

## 4.5 not_evidenced

Meaning:

```text
Available evidence does not establish the architecture element or behavior.
```

Not evidenced is different from unresolved.

```text
unresolved
= known evidence path cannot be completed

not_evidenced
= no supporting evidence was found
```

---

## 4.6 Propagation Rule

A downstream skill MUST NOT strengthen evidence certainty unless it explicitly obtains new supporting evidence.

Examples:

```text
confirmed
→ confirmed
```

Allowed.

```text
candidate
→ candidate
```

Default behavior.

```text
unresolved
→ unresolved
```

Default behavior.

```text
not_evidenced
→ not_evidenced
```

Default behavior.

The following is prohibited without new evidence:

```text
candidate
→ confirmed

unresolved
→ confirmed

not_evidenced
→ candidate

not_evidenced
→ confirmed
```

---

## 4.7 Certainty Upgrade

A certainty state MAY be strengthened only when:

```text
new evidence is explicitly retrieved
AND
the evidence supports the stronger conclusion
AND
provenance for that evidence is preserved
```

Example:

```text
unresolved
→ referenced source artifact retrieved
→ outbound behavior observed
→ confirmed
```

The skill performing the upgrade MUST preserve the evidence source used for the upgrade.

---

## 4.8 Certainty Downgrade

A downstream skill MAY downgrade certainty if contradictory or weaker evidence is discovered.

Example:

```text
confirmed derived output
→ raw CFG contradicts derived output
→ derived conclusion downgraded
→ investigate-gap opened
```

Raw evidence wins over derived output.

---

# 5. Finding Classifications

The following classifications are shared across skills.

---

## 5.1 BUG

Use when:

```text
Atlas output is proven incorrect
AND
the incorrect behavior is reproducible.
```

Typical action:

```text
FIX_LOGIC
```

---

## 5.2 GAP

Use when:

```text
Atlas does not yet support a legitimate architecture-relevant construct,
mapping, taxonomy entry, or semantic path.
```

Typical actions:

```text
ADD_TAXONOMY
ADD_MAPPING
ADD_SEMANTIC_SUPPORT
```

---

## 5.3 FINDING

Use when:

```text
Atlas accurately represents a notable characteristic
of the source configuration.
```

A finding is not automatically a defect.

Typical action:

```text
RECORD_FINDING
```

---

## 5.4 EXPECTED_UNRESOLVED

Use when:

```text
The unresolved state is understood and is expected
under the current source/export/platform model.
```

Typical action:

```text
NO_CHANGE
```

---

## 5.5 ARCHITECTURAL_HOTSPOT

Use when:

```text
Evidence shows unusual architectural concentration,
complexity, limits, reuse, or dependency density
that deserves attention.
```

A hotspot MUST NOT be presented as a proven runtime failure or outage cause without runtime evidence.

Typical action:

```text
RECORD_FINDING
```

or:

```text
COLLECT_MORE_EVIDENCE
```

---

## 5.6 INVESTIGATION_REQUIRED

Use when:

```text
Available evidence is contradictory, incomplete,
or insufficient to classify safely.
```

Typical action:

```text
COLLECT_MORE_EVIDENCE
```

---

## 5.7 Classification Rules

The following shortcuts are prohibited:

```text
unresolved
→ BUG

large graph
→ BUG

missing local artifact
→ deployment failure

high configuration limit
→ proven outage cause

similar object names
→ same logical object
```

Classification MUST be evidence-driven.

---

# 6. Token-Efficiency Rules

Token efficiency is a core architecture requirement.

The goal is not merely shorter prompts.

The goal is:

```text
minimum evidence retrieval
while preserving correct AS-IS reconstruction
```

---

## 6.1 Default Retrieval Principle

Use:

```text
Index First
→ Journey First
→ Exact Target Retrieval
→ Supporting Evidence Only When Needed
→ Raw CFG / Source Only When Needed
```

---

## 6.2 Reuse Upstream Evidence

If an upstream skill already produced validated evidence, downstream skills SHOULD reuse it.

Do not independently rediscover:

```text
same dependency
same finding
same file-resolution state
same route-control fact
same provenance
same evidence status
```

unless verification is required.

---

## 6.3 Exact Target Before Broad Search

When investigating one service or operation:

```text
locate exact service / operation
→ retrieve directly connected evidence
```

Do not load:

```text
all services
all operations
all findings
all relationships
all CFG
```

unless the question explicitly requires broad analysis.

---

## 6.4 Journey First

For service-level questions:

```text
Service Journey / Architectural Evidence Bundle
```

is the primary retrieval entry point.

For operation-level questions:

```text
Operation Journey / Operation Evidence Bundle
```

is the primary operation entry point.

Supporting indexes are secondary.

---

## 6.5 Known Evidence Reuse

If the Journey Evidence Bundle already contains:

```text
known finding
dependency state
file-resolution state
route-control evidence
configured backend
actual egress state
provenance
```

the skill MUST reuse it before opening broader indexes.

---

## 6.6 Raw Source Retrieval

Raw CFG or source artifacts SHOULD be opened only when:

```text
aggregated evidence is insufficient
verification is required
evidence is contradictory
operation semantics require source inspection
a suspected Atlas defect must be confirmed
```

Raw source SHOULD NOT be loaded merely because it exists.

---

## 6.7 Operation-Level Retrieval

Do not retrieve every operation for a Mega Policy by default.

Retrieve:

```text
operation summary first
→ selected operation details only when needed
```

Whole-policy operation analysis is appropriate only for questions involving:

```text
policy-wide comparison
operation concentration
shared behavior
pattern analysis
coverage analysis
```

---

## 6.8 Findings Retrieval

Do not load the entire findings register for one service investigation.

Retrieve only findings relevant to:

```text
current domain
current service
objects in the current service graph
dependencies referenced by the current graph
selected operation when applicable
```

---

## 6.9 Domain Isolation and Tokens

Do not load another domain to resolve missing evidence in the current domain unless the task is explicitly:

```text
cross-domain comparison
correlation
shared dependency analysis
```

This rule prevents both incorrect inference and unnecessary token use.

---

## 6.10 Semantic Lookup

Use `datapower-semantics` only when interpretation is required.

Do not load broad semantic guidance for constructs whose architectural meaning is already known from current evidence.

---

## 6.11 Avoid Evidence Duplication

Downstream outputs SHOULD reference upstream evidence rather than reproduce large evidence blocks.

Prefer:

```text
compact evidence summary
+
source pointers
```

over repeated raw evidence.

---

# 7. Integration Few-Shot Scenarios

These scenarios demonstrate reasoning patterns only.

They are intentionally generic.

They MUST NOT contain permanent facts from local smoke-test data, ignored test artifacts, specific project services, or specific project domains.

---

## Scenario 1 — Configured Backend vs Actual Egress

### Evidence

A service has:

```text
a configured backend
a request-processing path that bypasses normal backside routing
a resolved script referenced by the operation
an outbound HTTP request inside that script
```

### Expected Skill Behavior

`trace-service`:

```text
preserves the configured backend as configuration evidence
preserves route-control evidence
does not declare configured backend as actual operation egress
```

`trace-operation`:

```text
retrieves the resolved script when needed
identifies script-mediated outbound behavior
records actual egress separately
```

`capability-analysis`:

```text
derives outbound integration capability from evidenced behavior
preserves certainty
```

`generate-architecture-diagrams`:

```text
does not render both configured backend and script call
as two confirmed runtime calls unless evidence proves both occur
```

### General Rule

```text
Configured Backend
!=
Actual Evidenced Egress
```

---

## Scenario 2 — Referenced Artifact Is Missing

### Evidence

An operation contains:

```text
an explicit local XSLT reference
```

The referenced artifact is not present in the indexed export.

### Expected Skill Behavior

`trace-operation`:

```text
preserves the raw file reference
marks artifact resolution as unresolved
does not interpret "not resolved" as "no file reference"
```

`investigate-gap`:

```text
classifies the evidence state before recommending changes
does not automatically classify it as parser defect
```

`capability-analysis`:

```text
does not derive transformation or routing semantics
that require unavailable artifact contents
```

### General Rules

```text
no resolved file
!=
no file reference
```

and:

```text
missing artifact
!=
permission to infer its contents
```

---

## Scenario 3 — Dynamic Routing Without Resolved Destination

### Evidence

A service has:

```text
dynamic backend behavior
route-control evidence
no resolved destination
```

### Expected Skill Behavior

`trace-service`:

```text
records dynamic routing
preserves unresolved actual egress
```

`trace-operation`:

```text
retrieves only directly referenced routing evidence when required
```

`capability-analysis`:

```text
may identify dynamic routing capability
but must not identify a specific remote system without evidence
```

`generate-architecture-diagrams`:

```text
shows unresolved/candidate routing state
rather than inventing a destination
```

---

## Scenario 4 — Large Mega Policy

### Evidence

A service has many operations and a large number of processing relationships.

All relationships are consistently supported by:

```text
processing policy
matches
matching rules
processing rules
actions
```

### Expected Skill Behavior

`trace-service`:

```text
does not assume traversal overreach merely because the graph is large
```

`trace-operation`:

```text
retrieves one operation when the question is operation-specific
retrieves broader operation summaries only for policy-wide questions
```

`investigate-gap`:

```text
classifies traversal as a bug only if contradictory evidence proves over-traversal
```

### General Rule

```text
Large graph
!=
traversal bug
```

---

## Scenario 5 — Shared or Default Dependency Candidate

### Evidence

An application-domain object references a dependency that is unresolved locally.

A similarly named object exists in another domain or DEFAULT.

### Expected Skill Behavior

`trace-service`:

```text
keeps the application-domain dependency unresolved
```

`compare-domains` or `default-domain-analysis`:

```text
may identify a cross-domain dependency candidate
when explicit comparison is requested
```

No skill may silently convert the candidate into a resolved local dependency.

### General Rule

```text
Cross-domain similarity
!=
cross-domain resolution
```

---

## Scenario 6 — Configuration Hotspot

### Evidence

A service or shared object contains unusually high configuration limits or unusually concentrated processing behavior.

No runtime performance evidence is available.

### Expected Skill Behavior

`trace-service`:

```text
records the configuration evidence
```

`classify-finding`:

```text
may classify it as ARCHITECTURAL_HOTSPOT
```

`capability-analysis`:

```text
may record capacity or processing characteristics where evidenced
```

No skill may state that the configuration caused an outage or runtime failure without supporting runtime evidence.

### General Rule

```text
Configuration hotspot
!=
proven runtime root cause
```

---

## Scenario 7 — Downstream Certainty Preservation

### Evidence

`trace-service` identifies:

```text
candidate remote dependency
```

No downstream skill retrieves new evidence.

### Expected Skill Behavior

```text
trace-service: candidate
        ↓
capability-analysis: candidate
        ↓
replacement-analysis: candidate / unresolved requirement dependency
        ↓
diagram: candidate visual treatment
```

The following is prohibited:

```text
candidate
→ confirmed
```

without new evidence.

---

## Scenario 8 — New Evidence Resolves a Gap

### Evidence

`trace-service` reports:

```text
actual egress = unresolved
```

`trace-operation` retrieves a referenced source artifact and finds explicit outbound behavior.

### Expected Skill Behavior

`trace-operation` MAY upgrade:

```text
unresolved
→ confirmed
```

only when:

```text
new evidence is preserved
provenance is recorded
the evidence directly supports the conclusion
```

Downstream skills may then consume the confirmed result.

---

# Final Contract Principles

All skills MUST preserve the following rules:

```text
Raw evidence is authoritative.

Names are hints, not evidence.

Unresolved is not automatically a bug.

Missing artifact is not missing reference.

Large graph is not automatically traversal overreach.

Configured backend is not automatically actual egress.

Dynamic routing does not permit destination inference.

Cross-domain evidence must not be borrowed automatically.

A downstream skill must not strengthen certainty without new evidence.

Configuration hotspots are not proven runtime failures.

Capabilities must come from observed behavior.

Replacement analysis must follow capability analysis.

Evidence should be retrieved once and reused whenever possible.

Raw CFG / source artifacts should be opened only when needed.

The architecture must not be made cleaner or more certain than the source evidence.
```
