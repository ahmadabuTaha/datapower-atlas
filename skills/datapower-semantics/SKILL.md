# Skill: datapower-semantics

Follow `docs/skill-contract.md`.

## Purpose

Provide compact DataPower-specific interpretation needed by Atlas investigations.

This is not a DataPower CLI encyclopedia.

Use it only to interpret architecture-relevant configuration encountered by:

- trace-service
- trace-operation
- investigate-gap
- capability-analysis

## Goal

Translate DataPower configuration evidence into architecture meaning without inventing relationships.

## Core Object Semantics

### Multi-Protocol Gateway

Architecture role may include:

- network ingress
- processing policy execution
- transformation/script execution
- routing
- backend integration
- security enforcement

Actual capabilities must be proven by linked evidence.

### Web Service Proxy

Architecture role may include:

- SOAP/service exposure
- WSDL-aware mediation
- processing rules
- endpoint rewrite
- TLS/security
- remote endpoint mediation

Do not assume all WSPs contain complete ingress/egress configuration.

### TCP Proxy

Architecture role:

- Layer-4 TCP forwarding

Canonical journey:

`local-address:local-port`
→ TCP Proxy
→ `destination-address:destination-port`

Do not force policy-processing semantics onto it.

### Style / Processing Policy

Represents service processing orchestration.

Typical structure:

Policy
→ Match
→ Matching Rule
→ Processing Rule
→ Processing Actions

Large policies may be real implementation patterns.

### XML Manager

Architecture relevance may include:

- XML parser behavior
- parser/resource limits
- XSL processing/cache behavior

Large limits are configuration hotspots, not proven outage causes.

### TLS / Crypto

Interpret only explicit references among:

- TLS client/server profiles
- certificates
- keys
- identification credentials
- validation credentials
- password aliases

Names are not relationship evidence.

## Endpoint Semantics

Recognize evidence-backed roles such as:

- configured_default_backend
- dynamic_route_expression
- processing_action_route_candidate
- web_service_proxy_remote_endpoint
- tcp_proxy_direct

Do not collapse all endpoint evidence into one generic backend.

## URI / File Semantics

### `local:///`

Usually application/domain-local content.

If referenced but absent from inventory:

preserve as an evidence gap.

### `store:///`

May represent platform/shared DataPower content.

Unresolved does not automatically mean defect.

### `cert:///` and `pubcert:///`

Represent certificate-related resources.

Absence from export requires classification, not automatic failure.

## Evidence Rules

1. explicit property/reference beats naming;
2. unresolved is not automatically wrong;
3. empty configuration is still valid evidence;
4. large graph is not automatically parser overreach;
5. configuration hotspot is not runtime causality;
6. missing backend must not be inferred.

## Token Rules

Use this skill as a compact semantic lookup.

Do not load broad DataPower documentation.

Return only semantics relevant to the current object/property.

## Few-Shot Scenarios

### Scenario A — TCP Proxy

Evidence:

- local address and port;
- destination address and port.

Interpretation:

`Layer-4 TCP forwarding capability`

Do not report missing ingress/egress because no MPGW-style graph exists.

### Scenario B — WSP endpoint rewrite exists but is empty

Interpretation:

the object exists, but network semantics are not evidenced.

Report the gap/finding.

Do not infer remote endpoint.

### Scenario C — Very large XML limits

Interpretation:

`configuration/resource-pressure hotspot candidate`

Do not claim:

`outage root cause`

without runtime evidence.

### Scenario D — Shared operation set

Two service roots point to the same evidence-backed processing operation set.

Interpretation:

shared configuration/process behavior.

Do not infer:

- retired
- clone
- temporary
- unused

unless external evidence proves it.

## Output

When invoked, return only:

### Object / Property

What is being interpreted.

### Architecture Meaning

One concise explanation.

### Evidence Constraints

What must be explicitly present before asserting the relationship/capability.

### Common Misread

Only when relevant.

## Final Principle

Teach Codex only the DataPower semantics required to reconstruct the architecture correctly.

Everything else stays out of context.
