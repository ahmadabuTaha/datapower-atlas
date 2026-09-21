# Skill: investigate-gap

Follow `docs/skill-contract.md`.

## Purpose

Investigate missing, unresolved, contradictory, or suspicious Atlas evidence without prematurely changing parser logic.

This skill decides whether an observation is:

- BUG
- GAP
- FINDING
- EXPECTED_UNRESOLVED
- ARCHITECTURAL_HOTSPOT
- INVESTIGATION_REQUIRED

## Goal

Answer:

> Is this an Atlas defect, a source-configuration condition, or an evidence gap?

## Inputs

Required:

- environment
- domain
- affected service/object/operation
- observed anomaly

Optional:

- stage name
- current finding
- previous validated output

## Investigation Order

Retrieve only what is necessary:

1. affected output record
2. upstream relationship/reference record
3. source object/property
4. raw CFG block
5. previous validated output, if regression is suspected

Stop when the anomaly is explained.

## Classification Logic

### BUG

Use only when there is a reproducible contradiction between authoritative evidence and Atlas output.

Examples:

- explicit CFG relationship exists but parser drops it;
- valid TCP direct network evidence is incorrectly reported as absent.

### GAP

Use when required evidence is absent or unavailable.

Examples:

- referenced application-local file is not in the indexed export;
- source artifact needed for verification is missing.

### FINDING

Use when Atlas correctly reconstructs an unusual or incomplete configuration.

Example:

- an endpoint-rewrite object exists but contains no network rules.

### EXPECTED_UNRESOLVED

Use when unresolved evidence is explainable by platform/built-in behavior.

### ARCHITECTURAL_HOTSPOT

Use for evidence-backed concentration or unusual configuration that deserves review but is not a proven defect.

### INVESTIGATION_REQUIRED

Use when evidence is insufficient to decide safely.

## Frozen Component Rule

If the suspected issue affects a frozen component:

Do not modify it first.

Capture:

- observed behavior
- expected behavior
- raw evidence
- reproduction steps
- affected stage
- downstream impact

Reopen only for:

1. reproducible defect;
2. concrete contradiction;
3. broken downstream requirement.

## Token Rules

Do:

- start from the exact anomaly;
- walk one stage upstream at a time;
- compare only relevant records;
- quote minimal raw evidence.

Do not:

- rerun full-domain analysis unless necessary;
- inspect unrelated objects;
- reduce unresolved counts for cosmetic reasons.

## Few-Shot Scenarios

### Scenario A — Empty network policy

Observed:

- service references an endpoint-rewrite object;
- object exists;
- object has no listener/backend rules.

Correct classification:

`FINDING`

Possible detail:

`empty_endpoint_rewrite_policy`

Do not classify parser failure.

### Scenario B — Missing local artifact

Observed:

- `local:///...` is referenced;
- no matching file exists in inventory.

Correct classification:

`GAP`

Possible meaning:

`missing_artifact_in_indexed_export`

Do not claim deployment failure without runtime/deployment evidence.

### Scenario C — Platform resource

Observed:

- `store:///...` remains unresolved.

Correct approach:

classify as `EXPECTED_UNRESOLVED` when platform/shared-resource semantics support it.

Do not change resolver only to force resolution.

## Output

### Observation

One concise statement.

### Evidence

Only the minimum relevant evidence chain.

### Classification

One allowed class.

### Root Explanation

What the evidence supports.

### Recommended Action

One of:

- no code change
- add taxonomy mapping
- add parser extension
- add resolver support
- collect missing artifact
- collect runtime evidence
- focused regression test

### Reopen Frozen Component?

`YES` or `NO`

If YES, include the explicit reopen reason.

## Final Principle

Classify first.

Change code only when evidence proves Atlas is wrong.
