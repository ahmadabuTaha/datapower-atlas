# Skill: compare-domains

Follow `docs/skill-contract.md`.

## Purpose

Compare validated domain-level Atlas outputs without merging domain-local truth.

Use this skill to identify:

- configuration drift
- shared patterns
- replica variants
- domain-specific services
- candidate shared/default dependencies

---

## Inputs

Required:

- two or more validated domain indexes

Preferred:

- object identities
- relationships
- endpoints
- service journeys
- operation summaries
- findings

---

## Comparison Rules

### Domain Isolation First

Never resolve across domains during comparison.

Comparison produces correlation candidates only.

### Names Are Not Proof

Matching names may start a comparison but cannot establish equivalence alone.

Use evidence such as:

- canonical type
- processing relationships
- operation sets
- endpoints
- explicit dependencies
- properties

### Preserve Differences

Do not normalize away drift.

---

## Comparison Order

1. compare service root inventories
2. compare object identities
3. compare processing structures
4. compare operation sets
5. compare endpoints
6. compare security/file dependencies
7. compare findings
8. produce correlation candidates

---

## Correlation Classes

Use:

- same_logical_service_candidate
- replica_variant
- shared_configuration_candidate
- configuration_drift
- domain_specific_service
- shared_default_dependency_candidate

Do not create a generic `same` label.

---

## Few-Shot Scenarios

### Scenario A — Same operation set

Evidence:

- two service roots share the same explicit operation set.

Correct result:

`shared_configuration_candidate`

Do not infer lifecycle state.

### Scenario B — Same name, different endpoints

Evidence:

- names match
- backend endpoints differ

Correct result:

`configuration_drift`

Do not merge.

### Scenario C — DEFAULT dependency candidate

Evidence:

- unresolved local-domain reference
- matching object exists in DEFAULT

Correct result:

`shared_default_dependency_candidate`

Do not auto-resolve it.

---

## Output

### Domains Compared

List domains.

### Correlation Candidates

For each:

- source domain/object
- target domain/object
- correlation class
- supporting evidence
- conflicting evidence

### Drift Summary

Only material differences.

### Open Investigations

Only unresolved correlations.

---

## Token Rules

Do:

- compare compact indexes;
- hash/group large operation sets when possible;
- retrieve details only for changed/candidate records.

Do not:

- load complete raw CFG for every domain;
- duplicate identical evidence;
- treat name equality as sufficient.

---

## Final Principle

Compare domains without weakening domain-local truth.

Correlation is derived evidence, not resolution.
