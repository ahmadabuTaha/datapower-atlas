# Skill: run-domain-analysis

Follow `docs/skill-contract.md`.

## Purpose

Run and validate the official DataPower Atlas pipeline for one domain.

This skill is responsible for:

- executing the official domain pipeline;
- validating expected outputs;
- identifying pipeline-stage failures;
- detecting suspicious regressions;
- summarizing domain-level architecture evidence;
- deciding whether deeper investigation is required.

This skill must not redesign parser, resolver, or journey logic.

---

## Primary Goal

Produce a reliable domain analysis baseline that can be used for:

- AS-IS architecture reconstruction;
- service investigation;
- operation investigation;
- capability analysis;
- cross-domain comparison;
- modernization analysis.

---

## Inputs

Required:

- environment
- domain
- path to raw DataPower export
- Atlas repository root

Optional:

- previous validated run for regression comparison
- existing findings register
- freeze register

---

## Authoritative Execution

Use only:

tools/run_domain_pipeline.sh

Do not manually reproduce the full pipeline unless investigating a failed stage.

The official stage order is:

1. validate taxonomies
2. build file inventory
3. sensitivity scan
4. CFG parsing
5. reference extraction
6. relationship resolution
7. endpoint extraction
8. file reference resolution
9. service journey generation
10. operation journey generation
11. journey quality analysis

---

## Evidence Retrieval Strategy

Use Index-First retrieval.

Do not load the full raw configuration unless required.

Default inspection order:

1. pipeline execution summary
2. generated stage summaries
3. service journey summary
4. operation journey summary
5. relationship summary
6. endpoint summary
7. file-reference summary
8. quality findings
9. detailed index records if anomaly exists
10. raw CFG only when verification is required

Indexes are retrieval aids.

Raw CFG remains authoritative.

---

## Token Efficiency Rules

Do not:

- read all generated JSONL files;
- load all CFG content;
- inspect every object individually;
- repeat large evidence blocks;
- dump complete indexes into context.

Prefer:

- counts;
- summaries;
- targeted queries;
- exact service/object lookups;
- small evidence slices.

Only expand context when a specific anomaly requires investigation.

---

## Pre-Run Checks

Before running:

1. confirm repository root;
2. confirm requested domain;
3. confirm raw export path exists;
4. confirm official tool files exist;
5. confirm taxonomy validation passes;
6. confirm no versioned runtime tools are being selected.

Do not select:

- *_v1.py
- *_v1_1.py
- *_v2.py
- *_fixed.py
- *_hotfix.py
- *.keep

Git contains version history.

The working tree contains the authoritative runtime version.

---

## Run Procedure

Execute the official pipeline.

Capture:

- exit status;
- stage that failed, if any;
- output directory;
- report directory.

Do not immediately modify code after failure.

First determine whether the failure is:

- input issue;
- source-data issue;
- environment issue;
- taxonomy gap;
- parser defect;
- resolver defect;
- downstream assumption;
- expected unresolved condition.

---

## Validation Strategy

Validation must be semantic, not based only on counts.

Review:

### Parsing

- object occurrences
- unique logical objects
- property preservation
- malformed/partial blocks
- unclassified top-level statements

### References

- properties scanned
- references extracted
- taxonomy gaps

### Relationships

- references processed
- resolved
- unresolved
- deferred non-object references

Unresolved != Error.

### Endpoints

- static endpoints
- dynamic endpoint expressions
- unsupported/invalid endpoints
- endpoint roles

Do not infer missing endpoints.

### Files

- resolved file references
- unresolved file references
- URI families involved

Missing file != deployment failure.

### Service Journeys

Review root coverage for:

- multi_protocol_gateway
- web_service_proxy
- tcp_proxy

### Operation Journeys

Review:

- operation counts
- services with operations
- operations without processing rule
- unusually concentrated policies

Large graph != traversal bug.

### Journey Quality

Review:

- missing ingress
- missing egress
- processing gaps
- empty endpoint rewrite policies
- TCP direct journeys

TCP Proxy direct network configuration is valid ingress/egress evidence.

---

## Regression Comparison

If a previous validated run exists, compare:

- object identity
- relationship identity
- endpoint identity
- service journey identity
- operation identity
- new records
- removed records
- new unresolved references
- resolved-to-unresolved changes
- unresolved-to-resolved changes
- quality classification changes

Do not treat count changes alone as regressions.

A count change must be explained by evidence.

---

## Investigation Trigger

Open a focused investigation only when one of the following occurs:

- pipeline stage fails;
- previously resolved evidence disappears;
- new unsupported syntax appears;
- journey contradicts raw configuration;
- endpoint evidence is lost;
- operation traversal becomes inconsistent;
- TCP Proxy is incorrectly flagged as missing network edges;
- WSP processing evidence is unexpectedly absent;
- provenance is lost.

Use `investigate-gap` for deeper investigation.

---

## Known Conditions That Are Not Automatic Bugs

Examples:

- built-in matching rule unresolved;
- store:/// platform resource unresolved;
- cert:/// resource absent from export;
- local:/// artifact absent from indexed export;
- empty WSP endpoint rewrite;
- very large processing graph;
- elevated XML Manager limits.

These require classification, not automatic parser changes.

---

## Domain Isolation

All validation is domain-local.

Never automatically resolve references into another domain.

DEFAULT must not be used as an implicit fallback resolver.

Cross-domain relationships belong to a later correlation stage.

---

## Freeze Rule

If a failing observation affects a frozen component:

Do not change it immediately.

First document:

- observed behavior;
- expected behavior;
- raw evidence;
- reproduction method;
- affected pipeline stage;
- downstream impact.

A frozen component may be reopened only for:

1. reproducible defect;
2. concrete contradiction;
3. broken downstream requirement.

---

## Expected Output

Produce a concise run report:

### Domain

- environment
- domain
- pipeline status

### Pipeline

- PASS / FAIL
- failed stage if applicable

### Evidence Summary

- objects
- references
- relationships
- endpoints
- files
- service journeys
- operation journeys

### Quality

- genuine findings
- expected unresolved
- investigation candidates

### Regression

- no material regression
or
- targeted regression details

### Decision

One of:

PASS

PASS_WITH_FINDINGS

INVESTIGATION_REQUIRED

PIPELINE_FAILURE

Do not label unresolved references as failure without evidence.

---

## Output Philosophy

The report should answer:

1. Did the domain process successfully?
2. Is the generated architecture evidence trustworthy?
3. Are there new anomalies?
4. Are they configuration findings or Atlas defects?
5. Is deeper investigation required?

Keep the report compact.

Do not reproduce large index datasets.

---

## Relationship to Other Skills

Use:

trace-service
when a specific service needs AS-IS reconstruction.

trace-operation
when an individual operation requires analysis.

investigate-gap
when evidence appears missing or contradictory.

datapower-semantics
when DataPower-specific behavior needs interpretation.

capability-analysis
only after AS-IS evidence is considered reliable.

replacement-analysis
only after capability decomposition is complete.