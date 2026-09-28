# DataPower Atlas — Tools

The `tools/` directory contains the deterministic extraction, indexing, resolution, journey-building, and validation pipeline used by **DataPower Atlas**.

These tools transform raw IBM DataPower exports into structured architectural evidence.

They are responsible for **evidence extraction and materialization** — not modernization decisions.

```text
Raw DataPower Export
        ↓
Taxonomy Validation
        ↓
File Inventory
        ↓
Sensitivity Scan
        ↓
CFG Parsing
        ↓
Reference Extraction
        ↓
Relationship Resolution
        ↓
Endpoint Extraction
        ↓
File Reference Resolution
        ↓
Service Journeys
        ↓
Operation Journeys
        ↓
Journey Quality Analysis
```

The authoritative pipeline entry point is:

```bash
tools/run_domain_pipeline.sh
```

---

## Design Principle

Atlas separates deterministic evidence processing from architectural reasoning.

The tools answer questions such as:

```text
What objects exist?
What properties were configured?
What references exist?
Which references can be resolved?
Which endpoints are explicitly configured?
Which files are referenced?
Which referenced files are available?
How are services, policies, rules, and actions connected?
What operation paths can be reconstructed?
What evidence remains unresolved?
```

They do **not** answer:

```text
What should the architecture become?
Which product should replace DataPower?
Is an unresolved reference necessarily a defect?
What architecture would be cleaner?
```

Those questions belong to the higher Atlas analysis layers.

The fundamental rule is:

> Extract what exists. Do not redesign it.

---

# Official Pipeline

The official domain pipeline consists of eleven stages.

| Stage | Tool | Responsibility |
|---:|---|---|
| 1 | `validate_taxonomies.py` | Validate Atlas taxonomy definitions before processing evidence. |
| 2 | `build_file_inventory.py` | Inventory and classify files contained in the DataPower export. |
| 3 | `scan_sensitivity.py` | Detect sensitive content and support sanitized evidence handling. |
| 4 | `parse_datapower_cfg.py` | Parse DataPower configuration into structured objects and properties. |
| 5 | `extract_datapower_references.py` | Extract explicit references between configuration objects and artifacts. |
| 6 | `resolve_datapower_relationships.py` | Resolve supported references into domain-local object relationships. |
| 7 | `extract_datapower_endpoints.py` | Extract explicitly evidenced endpoint information. |
| 8 | `resolve_datapower_file_references.py` | Resolve referenced artifacts against the export/file inventory. |
| 9 | `build_datapower_service_journeys.py` | Aggregate service-level architectural evidence. |
| 10 | `build_operation_journeys.py` | Build operation-level processing and routing evidence. |
| 11 | `analyze_journey_quality.py` | Analyze Journey quality, completeness, and evidence conditions. |

The complete sequence is orchestrated by:

```bash
tools/run_domain_pipeline.sh
```

---

# Running the Pipeline

For normal domain processing, use the orchestrator rather than manually executing individual stages:

```bash
tools/run_domain_pipeline.sh
```

The orchestrator is the authoritative execution path for producing final domain outputs.

Individual tools may be executed directly during:

```text
focused investigation
development
debugging
regression testing
parser validation
resolver validation
journey validation
```

but manually generated partial outputs should not replace the reproducible pipeline result.

---

# Tool Responsibilities

## `validate_taxonomies.py`

Validates the taxonomy definitions used by Atlas.

Taxonomies define the vocabulary required by downstream extraction and classification logic.

Validation happens before raw DataPower evidence is processed so that taxonomy problems do not silently propagate into generated indexes.

Conceptually:

```text
taxonomy/*.yaml
      ↓
taxonomy validation
      ↓
validated classification model
```

A taxonomy validation failure should stop the pipeline rather than allow downstream evidence to be generated against an invalid classification model.

---

## `taxonomy_loader.py`

Provides common taxonomy-loading behavior used by Atlas tools.

It centralizes taxonomy interpretation so individual parsers and extractors do not independently reinterpret taxonomy files.

This supports a core Atlas rule:

```text
one authoritative taxonomy
+
one consistent interpretation
```

rather than tool-specific classification logic.

---

## `build_file_inventory.py`

Builds the domain file inventory.

The inventory records the files available in the DataPower export and provides the evidence foundation for later artifact resolution.

Typical responsibilities include:

```text
file discovery
file classification
artifact identification
path preservation
inventory generation
```

The inventory is important because later stages must distinguish between:

```text
a file reference exists
```

and:

```text
the referenced file exists in the available export
```

Those are different facts.

---

## `scan_sensitivity.py`

Scans available artifacts for sensitive content before deeper processing or evidence sharing.

This stage supports controlled handling of configuration evidence and sanitized artifacts.

Sensitivity scanning is part of the official pipeline rather than an optional post-processing step.

---

## `parse_datapower_cfg.py`

Parses DataPower configuration into structured Atlas evidence.

Conceptually:

```text
Raw CFG
   ↓
Objects
+
Properties
```

The parser should preserve the configuration that exists rather than silently normalize it into a cleaner architecture.

Typical outputs become foundational inputs for:

```text
reference extraction
relationship resolution
endpoint extraction
journey construction
architecture investigation
```

Raw CFG remains authoritative.

Parsed output is derived evidence.

---

## `extract_datapower_references.py`

Extracts explicit references from parsed DataPower configuration.

Examples may include references from a configuration object to:

```text
processing policies
matching rules
processing rules
front-side handlers
XML Managers
TLS profiles
crypto objects
XSLT artifacts
GatewayScript artifacts
other DataPower objects
```

The extractor identifies that a reference exists.

It does not automatically prove that the referenced target exists or that the reference represents runtime execution.

Conceptually:

```text
Source Object
     ↓
Raw Reference
     ↓
Reference Type
```

Resolution occurs later.

---

## `resolve_datapower_relationships.py`

Attempts to resolve extracted object references into explicit Atlas relationships.

Conceptually:

```text
Reference
   ↓
Domain-local lookup
   ↓
Resolved Relationship
        OR
Unresolved Reference
```

Resolution must preserve domain isolation.

Object identity follows the logical model:

```text
environment
+
domain
+
canonical type
+
logical name
```

Name similarity alone must not establish a relationship.

Evidence from another domain must not silently resolve a local dependency.

---

## `extract_datapower_endpoints.py`

Extracts explicitly evidenced endpoint information from supported DataPower configuration.

Endpoint evidence may represent different architectural roles and must not automatically be collapsed into one generic backend concept.

Depending on the configuration, endpoint evidence may contribute to understanding:

```text
ingress
configured backend
remote endpoint
TCP destination
service routing
other explicit network targets
```

Endpoint extraction records configuration evidence.

It does not automatically prove actual runtime egress.

---

## `resolve_datapower_file_references.py`

Resolves explicit file references against the available export/file inventory.

Examples of DataPower URI schemes may include:

```text
local:///
store:///
cert:///
pubcert:///
```

The resolver preserves an important distinction:

```text
file reference exists
!=
file successfully resolved
```

Therefore:

```text
no resolved file
!=
no file reference
```

A referenced artifact that is unavailable in the export remains visible as unresolved evidence.

Typical resolution states may distinguish conditions such as:

```text
resolved
file not found
platform resource
unsupported scheme
ambiguous match
inventory gap
parser gap
```

Atlas should retain the most precise evidence-backed reason available.

---

## `build_datapower_service_journeys.py`

Builds Service Architectural Evidence Bundles.

A Service Journey is not simply a graph traversal.

It aggregates architecture-relevant evidence around a service.

Conceptually:

```text
Service Identity
+
Ingress
+
Processing
+
Operations
+
Resolved Dependencies
+
Unresolved Dependencies
+
File References
+
File Resolution
+
Routing State
+
Egress State
+
Security Dependencies
+
Known Findings
+
Evidence Certainty
+
Provenance
```

The Journey exists to make downstream architectural investigation efficient.

Instead of repeatedly scanning the entire domain, Atlas should normally retrieve the service bundle first.

---

## `build_operation_journeys.py`

Builds operation-level evidence within a service.

A typical evidenced operation path may resemble:

```text
Service
→ Processing Policy
→ Match
→ Matching Rule
→ Processing Rule
→ Processing Actions
→ Routing / Egress
```

Only stages supported by evidence should appear.

Operation Journeys are especially important for services using large or shared processing policies where different operations may have different:

```text
processing actions
transformations
scripts
routing behavior
file dependencies
security dependencies
actual egress
```

Operation-level evidence is the preferred source for operation-specific routing and egress conclusions.

---

## `analyze_journey_quality.py`

Analyzes the quality and evidence condition of generated journeys.

The analyzer helps identify conditions requiring attention without automatically treating every unusual result as a defect.

Examples include:

```text
unresolved dependencies
unresolved artifacts
incomplete evidence paths
provenance inconsistencies
routing uncertainty
egress uncertainty
journey completeness conditions
```

Quality analysis must follow the Atlas evidence model:

```text
unresolved
!=
error
```

and:

```text
large graph
!=
traversal defect
```

A suspicious condition may require investigation before classification.

---

## `reset_generated_outputs.py`

Resets generated Atlas outputs when a clean pipeline regeneration is required.

This tool should be used carefully because generated indexes and reports may be reproducible, but raw source evidence is not treated as disposable generated output.

The reset boundary must remain aligned with the repository's distinction between:

```text
authoritative source evidence
```

and:

```text
derived / reproducible Atlas outputs
```

---

## `run_domain_pipeline.sh`

The authoritative domain pipeline orchestrator.

This script coordinates the complete processing sequence:

```text
validate taxonomies
        ↓
build file inventory
        ↓
sensitivity scan
        ↓
parse CFG
        ↓
extract references
        ↓
resolve relationships
        ↓
extract endpoints
        ↓
resolve file references
        ↓
build service journeys
        ↓
build operation journeys
        ↓
analyze journey quality
```

For normal Atlas operation:

> **Run the pipeline, not a hand-assembled sequence of individual tools.**

This preserves reproducibility and prevents partially regenerated indexes from being mistaken for a validated domain state.

---

## `run_domain_pipeline_artifact.sh`

Provides an artifact-oriented pipeline execution path present in the repository.

It should remain distinct from the primary authoritative domain orchestration performed by:

```text
run_domain_pipeline.sh
```

Any use of this script should preserve the same Atlas evidence principles and should not create a competing definition of the official domain pipeline.

---

# Generated Evidence

The tools produce derived architecture evidence under Atlas output areas such as:

```text
index/
reports/
```

Domain indexes may contain evidence such as:

```text
objects
properties
references
relationships
endpoints
file relationships
unresolved file references
service journeys
operation journeys
journey summaries
findings
```

Exact generated files depend on the pipeline stage and domain evidence.

These outputs are rebuildable.

They do not replace raw source authority.

---

# Source-of-Truth Hierarchy

The tools operate within the following authority model:

```text
Raw DataPower Export
Raw CFG
Referenced Source Artifact
        ↓
Validated Atlas Indexes
        ↓
Journey Evidence Bundles
        ↓
Architecture Investigation
        ↓
Capability Analysis
        ↓
Replacement Analysis
```

If generated evidence contradicts raw evidence:

```text
Raw Evidence Wins
```

The contradiction should then be classified and investigated.

---

# Resolution Rules

Tool development must preserve the following rules.

### Names are not proof

```text
similar_name
!=
resolved_relationship
```

Names may assist investigation but must not establish architecture by themselves.

### Unresolved is valid evidence

```text
unresolved
!=
missing
!=
error
```

A reference may legitimately exist while its target remains unavailable.

### Domain isolation is mandatory

```text
STG evidence
!=
STG-Replica evidence
```

Evidence must not be borrowed across environments or domains to make a local result appear complete.

### Configuration is not runtime behavior

```text
configured backend
!=
actual evidenced egress
```

The actual operation path may depend on processing actions, routing behavior, XSLT, GatewayScript, TCP behavior, messaging, or another explicitly evidenced mechanism.

### Missing source cannot be reconstructed by assumption

```text
missing XSLT
→ unresolved semantics
```

not:

```text
missing XSLT
→ inferred behavior
```

---

# Certainty Model

Architecture-relevant conclusions use the canonical certainty vocabulary:

```text
confirmed
candidate
unresolved
not_evidenced
```

Tools must not strengthen certainty without new evidence.

For example:

```text
unresolved artifact
        ↓
artifact retrieved
        ↓
explicit behavior extracted
        ↓
confirmed
```

is valid.

But silently converting:

```text
candidate → confirmed
```

is not.

---

# Development Rules

## One Authoritative Runtime Tool

There should be exactly one authoritative runtime filename for each tool.

Do not keep active variants such as:

```text
parser_v1.py
parser_v2.py
parser_fixed.py
parser_hotfix.py
resolver_old.py
builder_new.py
```

Version history belongs in Git.

The working tree should contain the authoritative implementation.

---

## Do Not Reopen Frozen Components Without Evidence

Once a pipeline component has passed its agreed validation criteria, treat it as frozen.

New requirements should normally extend Atlas forward through:

```text
taxonomy additions
parser extensions
new mappings
new semantic support
new resolvers
aggregation
correlation
reporting
explicit exceptions
```

A frozen component should be reopened only when there is:

```text
a reproducible defect
a concrete contradiction with authoritative evidence
a broken downstream requirement
```

Enhancement and bug fix are not the same thing.

---

# Regression Validation

Regression testing should validate architecture semantics rather than relying only on counts.

Changes should be inspected for effects on:

```text
object identity
relationship identity
endpoint identity
file references
operation identity
routing state
egress state
certainty
provenance
new records
lost records
classification changes
```

A count change may be valid.

Silent evidence loss is not.

---

# Relationship to Atlas Skills

The tools build deterministic evidence.

Atlas skills consume that evidence.

```text
tools/
  deterministic extraction
  indexing
  resolution
  aggregation
  quality analysis

        ↓

skills/
  domain validation
  service tracing
  operation tracing
  gap investigation
  DataPower semantic interpretation
  capability analysis
  replacement analysis
  architecture rendering
```

The normal reasoning chain is:

```text
run-domain-analysis
        ↓
trace-service
        ↓
trace-operation          when required
        ↓
investigate-gap          when required
        ↓
datapower-semantics      when required
        ↓
capability-analysis
        ↓
replacement-analysis
        ↓
architecture diagrams
```

The tools should remain deterministic wherever possible.

Architectural interpretation belongs in the appropriate downstream evidence and skill layer.

---

# Token-Efficient Architecture

The generated indexes and journeys exist partly to prevent repeated broad investigation.

The intended retrieval strategy is:

```text
Question
   ↓
Exact Environment / Domain
   ↓
Exact Service
   ↓
Service Journey
   ↓
Known Findings
   ↓
Operation Journey          when needed
   ↓
Supporting Index           when needed
   ↓
Raw CFG / Source           only when needed
```

Therefore tool outputs should favor:

```text
compact structured facts
+
stable identities
+
certainty
+
provenance pointers
```

rather than copying large amounts of raw configuration into every derived artifact.

---

# What the Tools Must Never Do

The pipeline must never silently:

```text
invent a backend
invent an endpoint
invent a dependency
invent a missing artifact
borrow evidence from another domain
infer artifact contents from filenames
treat unresolved evidence as absent
treat every unresolved reference as a parser defect
convert configured backend into actual egress
assume HTTPS means mTLS
normalize unusual configuration because it looks incorrect
redesign the AS-IS architecture during extraction
```

If evidence is incomplete:

```text
preserve the gap
+
preserve the reference
+
preserve provenance
+
classify later
```

---

# Working Principle

The `tools/` directory is the deterministic evidence engine of DataPower Atlas.

Its responsibility is not to make the DataPower estate look cleaner.

Its responsibility is to make the estate **observable, structured, traceable, reproducible, and architecturally investigable**.

```text
Extract faithfully.
Resolve only what evidence supports.
Preserve what remains unresolved.
Aggregate without inventing.
```

> **When evidence stops, Atlas stops.**