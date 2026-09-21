# Skill: trace-operation

Follow `docs/skill-contract.md`.

## Purpose

Reconstruct one DataPower operation inside a service using the smallest evidence set possible.

Use this skill when a service contains multiple operations or a large processing policy.

## Goal

Answer:

> What happens for this operation, based on explicit configuration evidence?

Do not analyze the whole domain unless required.

## Inputs

Required:

- environment
- domain
- service identity
- operation identity

Preferred identity:

`environment + domain + service + operation`

## Retrieval Order

Use Index-First retrieval:

1. operation journey record
2. matching-rule relationship
3. processing-rule relationship
4. processing actions
5. routing/endpoints
6. referenced files/security dependencies
7. raw CFG only if verification is required

Do not load all operations for the service unless comparison is necessary.

## Trace Model

Typical path:

Service
→ Processing Policy
→ Match
→ Matching Rule
→ Processing Rule
→ Processing Actions
→ Route / Backend

Only include stages supported by evidence.

## Rules

### Exact Evidence Only

Do not infer an operation from its name.

### Large Policy Is Not a Bug

A service may legitimately contain many operations.

Do not classify a large operation set as traversal overreach without raw evidence.

### Missing Route Stays Missing

If no route/backend evidence exists:

`routing_not_evidenced`

Do not invent one.

### Preserve Dynamic Routing

If routing is expression-based, record it as dynamic evidence rather than forcing a static endpoint.

## Token Rules

Do:

- retrieve one operation record;
- retrieve only directly related relationships/actions;
- summarize repeated action patterns;
- open raw CFG only for ambiguity.

Do not:

- dump the full policy;
- load all service operations;
- repeat complete raw statements unless needed.

## Output

### Identity

- environment
- domain
- service
- operation

### Operation Journey

Concise path based on evidence.

### Match

- matching rule
- match evidence

### Processing

- processing rule
- ordered/linked actions
- transformation/script dependencies

### Routing

- static endpoint
- dynamic route
- route candidate
- missing route evidence

### Security / Files

Only directly referenced dependencies.

### Findings

Use:

- BUG
- GAP
- FINDING
- EXPECTED_UNRESOLVED
- ARCHITECTURAL_HOTSPOT
- INVESTIGATION_REQUIRED

### Confidence

- HIGH
- MEDIUM
- LOW

Confidence measures evidence completeness only.

## Few-Shot Scenarios

### Scenario A — Large operation set

Evidence:

- service has many operation journeys;
- each operation maps to explicit matching and processing rules.

Correct result:

`ARCHITECTURAL_HOTSPOT: high_processing_concentration`

Incorrect result:

`traversal_bug`

unless duplicated traversal is proven.

### Scenario B — Dynamic route

Evidence:

- processing action contains a route expression;
- no static backend is configured.

Correct result:

`dynamic_route_expression`

Do not fabricate a static backend.

## Final Principle

Trace one operation from explicit relationships.

Do not let the size or naming of the policy replace evidence.
