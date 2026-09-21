# Skill: replacement-analysis

Follow `docs/skill-contract.md`.

## Purpose

Translate validated DataPower capabilities into replacement requirements and candidate solution patterns.

This skill answers:

> What must a replacement provide to preserve the required behavior?

It does not assume one DataPower service maps to one replacement product.

---

## Inputs

Required:

- capability inventory from capability-analysis
- relevant NFR/operational characteristics
- known evidence gaps/findings

Optional:

- organization constraints
- platform standards
- target architecture constraints

---

## Analysis Order

1. consume validated capabilities
2. identify mandatory replacement requirements
3. separate functional and non-functional requirements
4. group capabilities into solution roles
5. identify capability gaps/unknowns
6. only then consider candidate technology categories
7. compare products only when explicitly requested

---

## Requirement Types

### Functional

Examples:

- HTTP/S ingress
- SOAP mediation
- transformation
- dynamic routing
- TCP forwarding
- TLS termination
- certificate validation
- messaging integration

### Non-Functional

Examples:

- throughput
- latency
- resilience
- HA/DR
- scaling
- auditability
- observability
- deployment model
- security controls

Only assert NFRs when evidence or project requirements support them.

---

## Solution Role Decomposition

A single DataPower service may require multiple replacement roles.

Possible roles:

- API gateway
- integration runtime
- service mesh / ingress
- Layer-4 proxy
- IAM / policy enforcement
- PKI / secrets management
- messaging platform
- transformation runtime

Do not force all roles into one product.

---

## Candidate Technology Rule

When technology selection is requested:

evaluate technologies against required capabilities.

Do not use mappings like:

`MPGW → Product X`

or:

`WSP → Product Y`

without capability-level comparison.

---

## Few-Shot Scenarios

### Scenario A — Mixed gateway + transformation

Capabilities:

- HTTP ingress
- TLS
- policy execution
- XSLT transformation
- backend routing

Replacement pattern may require:

- API gateway
- plus integration/transformation runtime

Do not assume one gateway product replaces all behavior.

### Scenario B — TCP forwarding only

Capability:

- Layer-4 TCP forwarding

Replacement requirement:

- reliable L4 proxying

Do not introduce API management requirements.

### Scenario C — SOAP mediation

Capabilities:

- SOAP/WSDL mediation
- endpoint rewrite
- transformation
- TLS

Replacement analysis must preserve SOAP semantics or explicitly identify redesign as a separate modernization decision.

---

## Output

### Replacement Scope

- service/domain
- capability baseline used

### Mandatory Requirements

Functional and non-functional.

### Solution Roles

Which architectural roles are needed.

### Candidate Patterns

Pattern-level options first.

### Technology Candidates

Only if requested.

For each candidate:

- supported requirements
- gaps
- assumptions
- evidence dependency

### Open Questions

Only unresolved items that materially affect replacement choice.

---

## Token Rules

Do:

- consume capability summaries;
- compare only relevant capability dimensions;
- keep product discussion scoped.

Do not:

- reload raw CFG unless a capability is disputed;
- restate all service evidence;
- compare broad product feature catalogs unrelated to requirements.

---

## Final Principle

Replace required capabilities, not DataPower object names.

Modernization may preserve, split, simplify, or redesign capabilities, but those are explicit architecture decisions.
