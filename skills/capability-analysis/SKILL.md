# Skill: capability-analysis

Follow `docs/skill-contract.md`.

## Purpose

Convert validated AS-IS DataPower evidence into functional capability statements.

This skill answers:

> What capabilities does this service or domain actually provide?

It must not jump directly to replacement products.

---

## Inputs

Required:

- validated service/domain trace
- evidence-backed relationships/endpoints/dependencies

Optional:

- operation summaries
- quality findings
- NFR evidence

---

## Retrieval Strategy

Use validated Atlas outputs first.

Preferred order:

1. service trace
2. operation summaries
3. endpoint roles
4. security dependencies
5. file/script/transformation dependencies
6. XML/runtime configuration
7. raw CFG only if capability evidence is ambiguous

Do not reread the full domain if the service trace is already sufficient.

---

## Capability Derivation Rules

Derive capabilities from observed behavior, not object names alone.

Examples:

- listener evidence + service root
  → ingress capability

- explicit route/backend evidence
  → routing/backend integration capability

- XSLT/GatewayScript references
  → transformation/scripting capability

- TLS/crypto relationships
  → transport/security capability

- MQ relationships
  → messaging integration capability

- TCP local/destination configuration
  → Layer-4 TCP forwarding capability

- WSP processing + endpoint rewrite evidence
  → SOAP/service mediation capability

---

## Capability Categories

Use only categories supported by evidence.

Suggested categories:

- ingress
- protocol mediation
- routing
- backend integration
- transformation
- scripting
- policy execution
- authentication / authorization
- TLS / PKI
- messaging integration
- SOAP / WSDL mediation
- Layer-4 forwarding
- XML processing
- file/resource dependency
- operational control
- observability, only when evidenced

Do not force every service into every category.

---

## Evidence Strength

For each capability, record one of:

- DIRECT — explicitly evidenced
- DERIVED — supported by multiple explicit relationships
- NOT_EVIDENCED — do not claim it

Avoid speculative capability labels.

---

## NFR Handling

Separate functional capability from operational characteristic.

Examples:

Functional:

`XML transformation`

Operational characteristic:

`very high parser limits configured`

Do not convert configuration hotspots into functional capabilities.

---

## Few-Shot Scenarios

### Scenario A — TCP service

Evidence:

- local listener
- destination host/port
- no policy graph required

Capability:

`Layer-4 TCP forwarding`

Do not invent transformation or API gateway capabilities.

### Scenario B — Service with XSLT + routing

Evidence:

- processing action references XSLT
- explicit backend route exists

Capabilities:

- `transformation`
- `backend routing`

### Scenario C — Large processing policy

Evidence:

- many explicit operations and processing actions

Capability:

`policy-based request processing`

Finding:

`high_processing_concentration`

Do not turn the finding into a separate capability.

---

## Output

### Scope

- environment
- domain
- service or domain

### Capability Inventory

For each capability:

- capability name
- evidence strength
- concise evidence reference
- relevant operational note

### Capability Gaps

Only where evidence is materially absent.

### Findings Affecting Capability Interpretation

Only relevant findings.

---

## Token Rules

Do:

- use service/operation summaries;
- group repeated behavior;
- produce compact capability statements.

Do not:

- restate the full AS-IS journey;
- dump raw evidence;
- include product recommendations;
- repeat the same evidence under multiple capabilities.

---

## Final Principle

Capabilities describe observed behavior.

Object names are not capabilities.

Replacement analysis starts only after capability decomposition is complete.
