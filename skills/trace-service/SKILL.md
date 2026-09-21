Skill: trace-service

Follow `docs/skill-contract.md`.

# Purpose

Reconstruct the AS-IS architecture journey of one DataPower service using the minimum evidence required.

This skill is for evidence-based service investigation. It must produce a realistic, traceable view of:

- ingress
- service root
- processing
- operation decomposition
- routing
- backend endpoints
- security dependencies
- file dependencies
- XML/runtime configuration dependencies
- unresolved evidence
- architectural findings

The goal is accurate AS-IS reconstruction first. Do not perform replacement analysis inside this skill.

# Primary Goal

Answer: What does this DataPower service actually do, based on configuration evidence?

The result must be suitable as input to:

- capability-analysis
- replacement-analysis
- compare-domains
- architecture reporting

# Core Principles

## 1. Index First

Use generated Atlas indexes before reading raw CFG.

## 2. Raw Evidence When Needed

Use raw CFG only to:

- verify ambiguity
- confirm a suspicious relationship
- investigate missing evidence
- validate a finding
- resolve contradictions between derived artifacts

## 3. No Inference Beyond Evidence

Never invent:

- ingress
- backend
- operation
- relationship
- dependency
- lifecycle status

## 4. Token Efficiency

Retrieve only records related to the requested service and its explicitly connected dependencies.

Do not load full domain datasets when a targeted lookup is sufficient.

# Inputs

## Required

- environment
- domain
- service identity or service name

Preferred identity:

- environment + domain + canonical_type + logical_name

## Optional

- specific operation name
- investigation question
- previous finding
- comparison target

# Supported Service Roots

Primary service roots currently include:

- multi_protocol_gateway
- web_service_proxy
- tcp_proxy

Other root types may be supported later only when backed by taxonomy and pipeline evidence.

# Evidence Retrieval Order

Use this order by default.

## 1. Service Journey Index

Locate the exact service journey.

Extract only the service record and directly linked evidence.

Use it to establish:

- service type
- ingress evidence
- processing evidence
- security evidence
- endpoint evidence
- file/dependency evidence

## 2. Operation Journey Index

If the service has processing operations, retrieve only operations owned by the target service.

Do not load unrelated operations.

Use it to establish:

- match
- matching rule
- processing rule
- processing actions
- routing candidates
- operation count

## 3. Relationship Index

Retrieve only relationships where the target service or its directly connected processing objects are source or target.

Use explicit relationship types only.

Examples may include:

- uses_processing_policy
- contains_processing_rule
- contains_processing_action
- uses_matching_rule
- uses_xml_manager
- uses_tls_client_profile
- uses_endpoint_rewrite_policy
- uses_front_side_handler

## 4. Endpoint Index

Retrieve only endpoints owned by or explicitly connected to the target service.

Classify endpoints by evidence-backed role.

Examples:

- configured_default_backend
- dynamic_route_expression
- processing_action_route_candidate
- web_service_proxy_remote_endpoint
- tcp_proxy_direct

Do not convert a missing endpoint into an inferred backend.

## 5. File Reference Index

Retrieve only file references connected to the service or its processing dependencies.

Preserve URI scheme and resolution state.

Examples:

- local:///
- store:///
- cert:///
- pubcert:///

Unresolved file references must remain unresolved unless evidence proves otherwise.

## 6. Object / Property Index

Retrieve only object/property records necessary to interpret the service.

Examples:

- XML Manager limits
- TLS profile references
- crypto references
- TCP local/destination addresses
- WSP endpoint rewrite configuration
- service listener configuration

## 7. Raw CFG

Read only the relevant source blocks when verification is needed.

Raw CFG remains authoritative.

# Service Trace Workflow

## Step 1 — Resolve Exact Service Identity

Find the service using:

- environment
- domain
- canonical type
- logical name

Do not merge similarly named services across domains.

If multiple exact candidates exist, report ambiguity. Do not guess.

## Step 2 — Identify Service Pattern

Classify the service root as one of the supported patterns.

### Multi-Protocol Gateway

Typical evidence path:

Ingress → MPGW → Processing Policy → Matching Rule → Processing Rule → Processing Actions → Routing / Backend

### Web Service Proxy

Typical evidence path may include:

WSP → XML Manager → TLS Client Profile → WSM Processing Policy → Matching Rule → WSM Processing Rule → Endpoint Rewrite → Front Side Handler / Remote Endpoint

Do not assume every WSP contains every element.

### TCP Proxy

Use direct network evidence:

local-address:local-port → TCP Proxy → destination-address:destination-port

Do not force MPGW processing semantics onto TCP Proxy.

## Step 3 — Reconstruct Ingress

Identify explicit ingress evidence only.

Possible evidence includes:

- front-side handler relationship
- service listener configuration
- WSP listener configuration
- TCP local address/port
- other taxonomy-supported network configuration

If no ingress evidence exists, report `ingress_not_evidenced`.

Do not infer from service name or backend.

## Step 4 — Reconstruct Processing

For MPGW/WSP-style services, trace only explicit processing relationships.

Typical sequence:

Service → Processing Policy → Matching Rule → Processing Rule → Processing Actions

Capture:

- processing policy
- matching rule
- processing rule
- action sequence
- operation identity
- explicit routing actions
- transformation/script dependencies

Large processing graphs are not automatically defects.

### Mega Policy Rule

If the service has many operations:

- Do not assume over-traversal.
- Before classifying a traversal defect, verify:
  - the processing policy
  - matching rules
  - processing rules
  - processing actions
  - whether the operation set exists in configuration evidence

Examples already known in Atlas show real Mega Policies.

Therefore:

- `large_operation_count != traversal_bug`

## Step 5 — Reconstruct Routing and Egress

Collect explicit routing evidence.

Possible sources include:

- configured backend endpoint
- dynamic route expression
- processing-action route candidate
- WSP remote endpoint
- endpoint rewrite
- TCP destination address/port

Classify each endpoint by role.

If backend evidence is missing, report it as missing evidence.

Never infer a likely backend from:

- service name
- domain
- similar service
- hostname naming convention

## Step 6 — Reconstruct Security Dependencies

Retrieve only explicit security relationships.

Potential dependencies include:

- TLS Client Profile
- TLS Server Profile
- crypto certificate
- crypto key
- identification credentials
- validation credentials
- password alias

Do not infer crypto relationships from naming similarity.

Report only explicit or resolver-supported relationships.

## Step 7 — Reconstruct XML / Processing Dependencies

Identify relevant XML Manager and processing configuration.

Capture evidence such as:

- XML Manager identity
- parser limits
- XSL cache-related configuration
- explicit custom processing limits

High values may be classified later as architectural hotspots.

Do not claim runtime failure or outage causality from configuration alone.

## Step 8 — Reconstruct File Dependencies

Collect explicit referenced artifacts such as:

- XSLT
- GatewayScript
- certificates
- keys
- local artifacts
- platform resources

Preserve:

- URI
- file type
- resolution status
- source object
- source property

Interpret unresolved references carefully.

Examples:

- `store:///` may represent platform/shared resources.
- `local:///` may represent missing application-local artifacts in the indexed export.

Neither condition alone proves deployment failure.

## Step 9 — Inspect Operation Journeys

If operation journeys exist, summarize:

- total operations
- operation identities
- matching rules
- processing rules
- action counts
- routing evidence
- missing processing-rule evidence

Do not print all operations unless explicitly requested.

For large services, show:

- operation count
- representative operation patterns
- architectural concentration findings
- targeted operations relevant to the investigation

Use `trace-operation` for detailed single-operation analysis.

## Step 10 — Identify Findings

Classify only evidence-supported observations.

Allowed classifications:

- BUG
- GAP
- FINDING
- EXPECTED_UNRESOLVED
- ARCHITECTURAL_HOTSPOT
- INVESTIGATION_REQUIRED

Examples:

### Empty WSP Endpoint Rewrite

If endpoint rewrite exists but contains no network configuration, possible finding:

- `empty_endpoint_rewrite_policy`

Do not invent missing ingress or backend.

### Large Processing Policy

If configuration proves a large operation graph, possible finding:

- `high_processing_concentration`

Do not call it a traversal bug unless reproducible evidence proves that.

### Elevated XML Manager Limits

Possible classification:

- `ARCHITECTURAL_HOTSPOT`

Do not claim runtime outage causality.

# Known Atlas Conditions

## SOCPA Pattern

An Endpoint Rewrite object may exist but be empty.

Correct behavior:

- preserve the object
- preserve missing ingress/egress
- classify the finding
- do not repair the journey by inference

## STG-Replica Mega Policy Pattern

Very large operation graphs may be real configuration.

Correct behavior:

- trace evidence
- preserve the graph
- classify architectural concentration

## Shared Operation Sets

Two service roots may share the same processing operation set.

Correct behavior:

- report the shared evidence
- do not infer that either service is retired, temporary, or unused

## TCP Proxy

Direct network configuration is valid ingress/egress evidence.

Do not create false missing-network findings.

# Provenance Requirements

Every important service-trace statement should be traceable to evidence.

Preserve where available:

- environment
- domain
- service type
- service name
- source file
- source line
- raw statement
- owner object
- source object
- target object
- relationship type
- endpoint role
- file URI
- resolution status

Do not include large raw evidence blocks in the normal report.

Keep evidence references compact.

# Token Efficiency Rules

## Do

- locate exact service first
- retrieve one service journey
- retrieve only that service's operations
- filter relationships by target service/dependencies
- retrieve only related endpoints/files
- summarize counts
- open raw CFG only for disputed evidence

## Do Not

- load full objects index
- load full relationships index
- read all operation journeys
- read entire raw CFG
- duplicate evidence across sections
- produce exhaustive DataPower CLI explanations

# Stop Conditions

Stop expanding evidence when all requested questions are supported.

Do not continue traversing unrelated dependencies.

A service trace is complete when the investigation has enough evidence to describe:

- ingress
- processing
- operations
- routing/egress
- security
- files
- significant configuration dependencies
- evidence gaps
- findings

If an area is not evidenced, state that explicitly.

# Expected Output

Produce a compact AS-IS report.

## Service Identity

- environment
- domain
- canonical type
- logical name

## AS-IS Journey

Use a concise architecture path such as:

Ingress → Service → Processing Policy → Matching / Rules → Processing Actions → Routing → Backend

Adapt the path to actual evidence. Do not include stages that are not evidenced.

### Ingress

Evidence-backed network entry points.

### Processing

- processing policy
- operation count
- matching/rule structure
- major processing behavior

### Routing / Egress

- static endpoints
- dynamic routing
- route candidates
- direct TCP destination if applicable

### Security

Explicit TLS/crypto/security dependencies.

### Files / Artifacts

Referenced application/platform artifacts and resolution state.

### Configuration Dependencies

Examples:

- XML Manager
- endpoint rewrite
- front-side handler

### Evidence Gaps

Only genuine missing/ambiguous evidence.

### Findings

Evidence-backed findings with classification.

## Confidence

Use one of:

- HIGH — direct evidence is complete for the requested scope
- MEDIUM — core journey is supported but some dependencies are unresolved
- LOW — material parts of the journey lack source evidence

Confidence refers to evidence completeness. It must not be used as a subjective quality score for the implementation.

# Output Example

Service: GetUserEstablishmentsQuery_Service

Domain: STG-Replica

Type: multi_protocol_gateway

AS-IS Journey: Ingress → MPGW → Processing Policy → 129 evidence-backed operations → Processing Actions → Routing evidence

Processing: 129 operations are present in configuration-derived operation journeys. The large graph is treated as actual configuration unless contradictory raw evidence is found.

Dependencies: Custom XML Manager is explicitly linked.

Findings:

- `ARCHITECTURAL_HOTSPOT`
- `high_processing_concentration`

Evidence Gap: No additional gap should be invented beyond unresolved evidence present in Atlas.

Confidence: HIGH

The example illustrates report shape only. Always use the actual indexed/raw evidence of the requested service.

# Relationship to Other Skills

- Use `run-domain-analysis` when the domain pipeline itself must be executed or validated.
- Use `trace-operation` when one operation requires detailed analysis.
- Use `investigate-gap` when service evidence is missing or contradictory.
- Use `datapower-semantics` when DataPower-specific configuration needs interpretation.
- Use `capability-analysis` only after the AS-IS journey is sufficiently evidenced.
- Use `replacement-analysis` only after capability decomposition is complete.

# Final Principle

Trace the service that exists.

Do not trace the service that its name suggests should exist.

Indexes provide efficient retrieval. Raw configuration provides final authority.

AS-IS accuracy comes before any other use case such as modernization.
