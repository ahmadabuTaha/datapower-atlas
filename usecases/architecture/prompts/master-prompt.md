# DataPower Atlas — AS-IS Architecture Reconstruction

## Objective

Build an evidence-based AS-IS architecture representation of the current DataPower estate.

The purpose of this task is NOT to redesign, modernize, optimize, or recommend replacement technologies.

The purpose is to reconstruct what currently exists, what DataPower currently does, how traffic and processing flow through it, and which architectural capabilities it currently provides.

The resulting AS-IS package will become an authoritative input to a separate TO-BE modernization analysis.

---

## Core Questions

The AS-IS analysis must answer four questions:

1. What services and operations currently exist in DataPower?
2. How does each relevant request travel through DataPower and its dependencies?
3. What does the overall DataPower integration landscape look like at enterprise context level?
4. What functional and architectural capabilities is DataPower currently providing?

---

# Evidence Retrieval Strategy

Use the existing indexes, relationships, findings, Journey/Aggregation outputs, dependency resolution outputs, and extracted semantics before inspecting raw source artifacts.

Preferred retrieval order:

Question
→ Service / Operation Catalog
→ User Journey
→ Aggregated known findings
→ Dependency indexes
→ Extracted XSLT / GatewayScript semantics
→ targeted raw CFG/source verification only when required

Do not start by broadly reading raw configuration files.

Do not repeatedly rediscover evidence already represented in indexes or journey aggregates.

Raw CFG/source artifacts remain authoritative when verification is required.

---

# Evidence Rules

Never invent architecture.

Never infer an actual backend merely because a configured backend property exists.

Maintain a strict distinction between:

- configured backend
- dynamically selected backend
- evidenced operation egress
- candidate egress
- unresolved egress
- no egress evidenced

Preserve unresolved references as unresolved.

A referenced file that cannot be resolved is NOT equivalent to no file dependency.

Do not borrow evidence between environments or domains.

Preserve environment and domain provenance.

If conflicting provenance exists, report the contradiction explicitly.

Do not silently repair evidence.

Do not use vague classifications such as:

- Other
- Others
- Various
- Misc
- Many
- Unknown

When something cannot be classified, state the precise reason, for example:

- unclassified_due_to_missing_artifact
- unclassified_due_to_parser_gap
- unresolved_dynamic_routing
- unresolved_external_dependency
- conflicting_domain_provenance

---

# Important Service Modeling Rule

Do NOT assume:

DataPower Service = Business/API Operation

A single DataPower service may expose multiple operations, paths, matches, rules, or processing behaviors.

Model separately:

DataPower Service
→ Operation / Request Pattern
→ Processing Rule
→ Processing Actions
→ Dependencies
→ Actual or Candidate Egress

Where multiple operations share infrastructure or processing policies, preserve that shared relationship rather than duplicating or flattening it.

---

# Execution Phases

Execute the following phases sequentially.

## Phase 1 — Service & Operation Catalog

Create a normalized inventory of:

- domains
- DataPower services
- service types
- exposed interfaces where evidenced
- operations
- paths
- HTTP methods where evidenced
- match rules
- processing policies
- processing rules
- backend configuration mode
- actual egress status
- shared dependencies
- unresolved dependencies
- evidence certainty
- source provenance

A service containing multiple operations must remain one DataPower service with child operations.

Do not flatten every operation into an independent DataPower service.

Outputs:

outputs/as-is/01-service-catalog/services.md
outputs/as-is/01-service-catalog/services.json
outputs/as-is/01-service-catalog/operations.md
outputs/as-is/01-service-catalog/operations.json

---

## Phase 2 — User Journey Reconstruction

For each relevant service, construct a service-level journey.

For operations with materially different processing or routing behavior, construct operation-level journeys.

A journey should capture, where evidenced:

Consumer / Caller
→ DataPower Entry Point
→ Service
→ Match
→ Processing Policy
→ Rule
→ Actions
→ Transformation / Script
→ Routing Decision
→ Backend / External Dependency

Also capture:

- resolved dependencies
- unresolved dependencies
- file references and resolution status
- XSLT dependencies
- GatewayScript dependencies
- XML Manager usage
- SSL/TLS dependencies where relevant
- AAA/security processing
- validation
- transformation
- routing
- logging
- error handling
- protocol mediation
- skip-backside or equivalent route-control behavior
- configured backend
- actual evidenced egress
- certainty
- provenance

Do not assume that skip-backside means that no outbound call exists.

An outbound call may be performed inside GatewayScript, XSLT, or another processing action.

Outputs:

outputs/as-is/02-user-journeys/journey-index.md
outputs/as-is/02-user-journeys/service-journeys/
outputs/as-is/02-user-journeys/operation-journeys/

Avoid unnecessary duplication.

Create operation journeys only where operation-specific behavior materially changes the architectural path.

---

## Phase 3 — Enterprise Context View

Now zoom OUT.

Do NOT draw every processing action, XSLT, rule, or operation.

Construct a high-level context view showing DataPower's position in the enterprise integration landscape.

The context view should answer:

Who calls DataPower?

What major logical service groups does DataPower expose?

Which enterprise platforms or external systems does DataPower communicate with?

What major traffic patterns exist?

Group detailed services into evidence-based logical clusters when possible.

Examples of acceptable context-level concepts include:

Consumer Systems
Channels
Internal Applications
API Management
Integration Platforms
DataPower
Government / Partner Systems
Enterprise Backend Systems
Security / Identity Systems
Observability / Logging Systems

These are examples only.

Use only categories supported by the discovered architecture.

Do not force unsupported categories into the model.

Do not expand every service into every operation in the context diagram.

The purpose is architectural comprehension, not configuration visualization.

Create:

outputs/as-is/03-context-view/datapower-context.md
outputs/as-is/03-context-view/datapower-context.mmd
outputs/as-is/03-context-view/external-systems.md
outputs/as-is/03-context-view/integration-flows.md

The Mermaid diagram should remain readable.

If the diagram becomes too large to understand, aggregate at the next logical architectural boundary.

---

## Phase 4 — DataPower Capability Map

Derive the capabilities DataPower CURRENTLY provides from evidence.

Do not produce a generic IBM DataPower product capability list.

A capability may only be included as "evidenced" when the current estate contains evidence that DataPower performs that capability.

Build a hierarchical capability map.

Example structure:

DataPower Platform
├── Traffic Management
├── Security
├── Protocol Mediation
├── Transformation
├── Routing
├── Integration
├── API / Service Exposure
├── Policy Enforcement
├── Observability
└── Operational Platform Services

These are candidate categories only.

Create the final taxonomy from actual evidence.

For each capability record:

- capability
- sub-capability
- description
- evidence
- services using it
- operations using it where practical
- dependency/component implementing it
- certainty
- architectural importance
- evidence source

Do NOT convert architectural importance into a modernization recommendation.

Do NOT recommend a replacement product.

Do NOT produce TO-BE decisions.

Outputs:

outputs/as-is/04-capability-map/datapower-capabilities.md
outputs/as-is/04-capability-map/capability-evidence.json
outputs/as-is/04-capability-map/capability-map.mmd

---

# Phase 5 — AS-IS Consolidation

Consolidate the previous outputs.

Create:

outputs/as-is/05-as-is-pack/AS-IS-SUMMARY.md

It should summarize:

- estate size
- domains
- services
- operations
- major architectural patterns
- major dependency patterns
- major routing patterns
- major capability groups
- major external integrations
- important unresolved evidence
- evidence quality

Do not repeat every service.

This is an architectural summary.

---

Create:

outputs/as-is/05-as-is-pack/AS-IS-FACTS.json

This must contain machine-readable confirmed architectural facts that a future TO-BE analysis can consume without rescanning the DataPower estate.

Facts should retain provenance and certainty.

---

Create:

outputs/as-is/05-as-is-pack/AS-IS-UNRESOLVED.md

Explicitly capture:

- unresolved file references
- unresolved routes
- unresolved external systems
- parser gaps
- missing artifacts
- conflicting evidence
- provenance inconsistencies
- areas where actual egress cannot be proven

Do not convert unresolved evidence into assumptions.

---

Finally create:

outputs/as-is/05-as-is-pack/TO-BE-INPUT.md

This document is the formal handoff from AS-IS reconstruction to future TO-BE modernization analysis.

It must contain:

## Current Architecture

Concise description of the existing DataPower landscape.

## Current Service Estate

Service and operation counts and major logical groupings.

## Current Integration Patterns

Evidence-based patterns currently implemented.

## Current DataPower Capabilities

The capability hierarchy derived from the estate.

## Current Dependencies

Major internal, external, shared, runtime, security, and integration dependencies.

## Current Architectural Constraints

Only constraints demonstrated by evidence.

## Evidence Gaps

Anything the future TO-BE analysis must not assume.

## AS-IS Invariants

Facts that a future modernization design must account for unless explicitly retired or changed.

Do NOT recommend technologies or define the target architecture.

---

# Validation

Before completing the task, validate:

1. Every DataPower service discovered by the authoritative indexes is represented in the service catalog.
2. Multi-operation services have not been incorrectly flattened.
3. Every operation is traceable to its parent service.
4. Journey information preserves resolved and unresolved dependencies.
5. Configured backend and evidenced egress are not conflated.
6. Environment/domain evidence has not been mixed.
7. Context diagrams remain architectural rather than configuration-level.
8. Capability claims have evidence.
9. No generic DataPower product capabilities have been inserted without estate evidence.
10. TO-BE recommendations have not leaked into AS-IS.
11. Machine-readable outputs retain evidence provenance.
12. Existing validated/frozen components were not redesigned merely to generate these reports.

If a previously validated component appears incorrect, record the suspected defect separately.

Do not modify or redesign the frozen component unless a focused regression demonstrates a concrete defect that blocks the AS-IS reconstruction.

---

# Completion Report

At completion report:

- services discovered
- operations discovered
- journeys produced
- context-level integration groups discovered
- capabilities discovered
- unresolved dependencies
- unresolved egresses
- evidence conflicts
- generated output files

Also report any AS-IS claim that remains below confirmed evidence certainty.