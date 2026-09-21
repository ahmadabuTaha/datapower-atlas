# Skill: classify-finding

Follow `docs/skill-contract.md`.

## Purpose

Assign one precise Atlas classification to an observed condition using minimum evidence.

Use this as a lightweight helper skill.

---

## Allowed Classes

- BUG
- GAP
- FINDING
- EXPECTED_UNRESOLVED
- ARCHITECTURAL_HOTSPOT
- INVESTIGATION_REQUIRED

Avoid vague labels.

---

## Decision Guide

### BUG

Atlas output contradicts reproducible authoritative evidence.

### GAP

Required source evidence or artifact is missing.

### FINDING

Atlas correctly exposes a real configuration condition.

### EXPECTED_UNRESOLVED

Unresolved evidence is expected due to platform/built-in/shared-resource semantics.

### ARCHITECTURAL_HOTSPOT

Evidence shows concentration, unusual limits, or complexity worth architecture review.

### INVESTIGATION_REQUIRED

Available evidence is insufficient for safe classification.

---

## Few-Shot Scenarios

### Scenario A

Evidence:

- endpoint policy object exists
- object is empty

Class:

`FINDING`

### Scenario B

Evidence:

- referenced application-local file missing from export

Class:

`GAP`

### Scenario C

Evidence:

- very large explicit processing graph
- raw configuration supports it

Class:

`ARCHITECTURAL_HOTSPOT`

### Scenario D

Evidence:

- parser omits an explicit source property required downstream

Class:

`BUG`

---

## Output

Return only:

- classification
- one-sentence rationale
- evidence needed next, only if applicable

---

## Token Rules

Keep output minimal.

Do not reopen the whole investigation.

Do not include unrelated DataPower semantics.

---

## Final Principle

Use the narrowest evidence-supported classification.
