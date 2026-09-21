# Skill: Analyze DataPower Default / Appliance Domain

Follow `docs/skill-contract.md`.

## Purpose

Use this skill to reconstruct the **DataPower Default Domain / appliance-level AS-IS architecture** from existing exported evidence.

The goal is not to search for predetermined findings. The goal is to discover, from evidence, what actually exists at the appliance/default-domain layer, such as:

- network interfaces
- IP addresses
- gateways and routes
- DNS and static hosts
- host aliases
- management-level configuration
- system/runtime settings
- certificate/system services
- other appliance-level configuration present in the export

### Primary Objective

The primary objective is to identify architecture-relevant objects, services, and shared platform capabilities that are typically not represented in application domains, including:

- system and network infrastructure
- management interfaces and services
- access and control security
- shared appliance-level runtime and security services

The skill must remain evidence-driven and must not assume that any specific object, service, interface, route, or control exists before it is observed in the exported configuration.

The result must be suitable for reuse in the consolidated **AS-IS Architecture**.

---

## Core Rule

**Evidence first. Findings second.**

Do not assume that the Default Domain contains a specific object, route, interface, alias, management service, or topology before reading the available configuration.

Examples in this skill are **few-shot examples only**. They illustrate how to reason from evidence. They are not facts that must exist in another environment or appliance.

---

## When to Use

Use this skill when:

- analyzing the DataPower `default` domain
- reconstructing appliance-level network architecture
- locating interfaces, routes, DNS, host aliases, management/runtime settings
- preparing Default Domain facts for the AS-IS Architecture
- investigating how application-domain endpoints may map to appliance-level network paths

---

## Source-of-Truth Order

Use evidence in this order:

```text
1. Existing raw export files
2. Existing domain pipeline outputs under index/<DOMAIN>/
3. Existing domain reports under reports/<DOMAIN>/
4. Derived findings produced by this skill
5. Consolidated AS-IS reference
```

The raw exported configuration remains authoritative.

Derived files are rebuildable.

---

## Important: Do Not Re-Export If the Pipeline Already Ran

Before doing anything, inspect whether the domain has already been processed.

Check:

```text
index/<DOMAIN>/
reports/<DOMAIN>/
```

Typical existing outputs may include:

```text
files.csv
files_scanned.csv
objects.csv
object_properties.csv
references.csv
relationships.csv
endpoints.csv
endpoint_catalog.csv
service_journey_summary.csv
operation_journey_summary.csv
unresolved_*.csv
```

If these already exist and correspond to the current export:

```text
DO NOT perform another export.
DO NOT regenerate the source package.
DO NOT duplicate the pipeline just to inspect the Default Domain.
```

Instead:

1. read the existing inventory
2. identify the raw files already captured by the export
3. inspect the relevant configuration files directly
4. reuse existing pipeline outputs where useful
5. add Default/appliance analysis forward from the existing evidence

Only rerun a pipeline stage if there is a concrete reason such as:

```text
missing output
stale output
known parser defect
changed raw export
broken downstream requirement
```

---

## Step 1 — Locate the Actual Default-Domain Configuration Evidence

Do not assume `default.cfg` is the complete appliance configuration.

Use the existing file inventory to identify candidate configuration files under the exported `default/config/` area.

Look for files such as:

```text
default.cfg
autoconfig.cfg
auto-startup.cfg
auto-user.cfg
```

These names are examples, not guaranteed requirements.

Compare candidates using:

```text
file size
hash
content structure
top-level configuration blocks
generation header
```

### Decision rule

Choose the file or files that actually contain appliance-level configuration evidence.

Do not select a file only because its name is `default.cfg`.

---

## Few-Shot Example 1 — Selecting the Correct Config File

Example evidence:

```text
default.cfg       = 95 bytes
autoconfig.cfg    = 36 KB
auto-startup.cfg  = 36 KB

autoconfig.cfg and auto-startup.cfg have the same SHA256.
```

Example reasoning:

```text
The small default.cfg contains almost no architecture-relevant configuration.

autoconfig.cfg contains appliance configuration blocks such as:
network
ethernet
dns
host-alias
ntp-service
throttle
...

Therefore autoconfig.cfg is the relevant appliance-level evidence source.
```

This is an example of evidence-based file selection.

Do not assume these exact filenames, sizes, or hashes in another export.

---

## Step 2 — Discover Top-Level Configuration Families

Inspect the selected configuration file without pre-classifying the expected findings.

Identify top-level blocks actually present.

Examples may include:

```text
network
interface
ethernet
dns
host-alias
domain-settings
radius
ntp-service
timezone
throttle
sql-runtime-settings
snmp
sslproxy
crypto
cert-monitor
```

These are example families discovered in one appliance.

They are not a mandatory checklist.

For each observed top-level family, record:

```text
block type
object name if present
source file
source line range
admin-state if available
key properties
```

---

## Step 3 — Reconstruct Network Interfaces

For each actual interface block, capture evidence such as:

```text
interface/ethernet name
IP address
prefix/subnet
default gateway
static routes
MTU
admin state
DHCP/static mode
IPv6 state
link aggregation state
standby configuration
hardware offload
```

Be careful with firmware compatibility blocks.

The same physical/logical interface may appear more than once under conditions such as:

```text
%if% unavailable "link-aggregation"
interface "ethX"
...

%if% available "link-aggregation"
ethernet "ethX"
...
```

Do not count these automatically as two different interfaces.

Normalize them to one interface only when the evidence clearly represents the same interface identity.

---

## Few-Shot Example 2 — Interface Normalization

Example evidence:

```text
interface "eth1"
  ip address "10.x.x.x/28"
  ...

ethernet "eth1"
  ip-address 10.x.x.x/28
  ...
```

Example reasoning:

```text
Both conditional blocks use the same interface name and same IP.
They are compatibility representations of the same interface.

Result:
one interface = eth1
```

Do not generalize this unless the evidence supports equivalence.

---

## Step 4 — Derive Interface Roles Only from Evidence

Do not label an interface as `STG`, `UAT`, `Management`, `External`, or `Internal` from intuition.

Possible evidence for a role may include:

```text
host-alias names
comments in route definitions
matching interface IPs
domain/application subnet descriptions
management addresses
explicit configuration summaries
```

Role confidence should be reported as:

```text
confirmed
strongly_supported
candidate
unclassified
```

---

## Few-Shot Example 3 — Interface Role Mapping

Example evidence:

```text
ethernet "eth0"
  ip-address 10.65.38.4/28

host-alias "mgmt"
  ip-address 10.65.38.4
```

Example result:

```text
eth0
role: management
confidence: confirmed_from_matching_host_alias
```

Example evidence:

```text
ethernet "eth1"
  ip-address 10.65.38.9/28

host-alias "stg"
  ip-address 10.65.38.9
```

Example result:

```text
eth1
role: STG
confidence: confirmed_from_matching_host_alias
```

These mappings are examples from one observed configuration only.

---

## Step 5 — Reconstruct Routing Evidence

For each interface and route, preserve:

```text
destination CIDR
next hop
metric if present
comment/summary
source interface
source file/line
```

Comments are evidence of operator intent, but they are not automatically proof of the actual external network implementation.

For example, a route comment may say:

```text
"HRSD DataPower A via IPsec tunnel..."
```

Record the comment exactly as evidence.

Do not invent the tunnel implementation, firewall policy, NAT, or external device unless separately evidenced.

---

## Few-Shot Example 4 — Network Reachability

Example evidence:

```text
ip-route "10.240.169.0/24" "10.65.38.1" ... "HRSD DataPower A via IPsec ..."
```

Example architecture fact:

```text
Destination network: 10.240.169.0/24
Next hop: 10.65.38.1
Operator description: HRSD DataPower A via IPsec
```

Do not automatically assert:

```text
DataPower itself terminates the IPsec tunnel
```

unless separate configuration proves that.

---

## Step 6 — Reconstruct DNS and Name Resolution

Treat different resolution mechanisms separately.

Possible mechanisms include:

```text
dns name-server
dns static-host
host-alias objects
```

Do not merge them into one concept if the configuration models them differently.

For each entry capture:

```text
mechanism
logical name
resolved IP
summary/comment
documented intended destination if present
source evidence
```

---

## Few-Shot Example 5 — Static Host Indirection

Example evidence:

```text
static-host "a5051" "10.2.4.23"
  "egress alias -> 10.240.169.61:5051"
```

Correct representation:

```text
logical alias: a5051
configured resolved IP: 10.2.4.23
documented intended destination: 10.240.169.61:5051
```

Do not collapse these into one endpoint.

Do not claim what `10.2.4.23` is unless separately evidenced.

---

## Few-Shot Example 6 — Host Alias

Example evidence:

```text
host-alias "hrsddphost-stg"
  summary "HRSD STG Hostname"
  ip-address 10.240.169.61
```

Correct result:

```text
name: hrsddphost-stg
IP: 10.240.169.61
description: HRSD STG Hostname
mechanism: host-alias
```

Again, this is an example, not a mandatory expected object.

---

## Step 7 — Reconstruct System / Runtime Configuration

Inspect appliance-level blocks actually present.

Possible examples:

```text
domain-settings
NTP
timezone
throttle/resource protection
SQL runtime
SNMP
management SSL proxy
certificate monitor
crypto/system services
```

For each observed block capture:

```text
object/family
admin state
important properties
source evidence
architecture relevance
```

Do not convert every property into a finding.

First capture facts.

Then identify only architecture-relevant observations.

---

## Step 8 — Distinguish Facts, Findings, and Hypotheses

Every conclusion must be classified as one of:

```text
FACT
FINDING
HYPOTHESIS
OPEN_EVIDENCE_GAP
```

### FACT

Directly supported by configuration evidence.

Example:

```text
eth1 has IP 10.x.x.x/28.
```

### FINDING

An architecture-relevant observation derived from facts.

Example:

```text
A single appliance exposes separate interface-address mappings for management, STG, and UAT.
```

### HYPOTHESIS

A possible explanation not yet proven.

Example:

```text
10.2.4.23 may act as an egress intermediary.
```

### OPEN_EVIDENCE_GAP

Required explanation is missing.

Example:

```text
The configuration documents an intended destination behind an alias,
but the transformation from the resolved host to that destination is not present in the inspected export.
```

Never promote a hypothesis to a fact.

---

## Step 9 — Correlate with Application Domains Carefully

After the Default Domain is reconstructed, application-domain evidence may be compared against it.

Examples:

```text
backend endpoint subnet
DNS alias
host alias
interface route
environment subnet
```

Correlation must remain evidence-based.

Do not automatically conclude:

```text
service X uses interface eth1
```

just because a route to its destination exists there.

Instead record:

```text
service endpoint
matching route/interface candidate
evidence level
```

Only promote to a stronger statement when routing semantics and evidence support it.

---

## Step 10 — Write Results to the Unified AS-IS Reference

The final output of this skill must be written to:

```text
docs/as-is-architecture-reference.md
```

This file is the consolidated architecture reference that later AS-IS Architecture work should consume.

Do not overwrite unrelated sections.

Update or append the Default/Appliance section.

Recommended structure:

```text
# AS-IS Architecture Reference

## DataPower Appliance / Default Domain

### Evidence Sources

### Appliance Network Summary

### Interfaces

### Interface Roles

### Routing

### DNS

### Static Hosts

### Host Aliases

### System and Runtime Settings

### Management Services

### Certificate / Crypto Operations

### Cross-Domain Correlations

### Findings

### Open Evidence Gaps
```

Every architecture statement must carry enough provenance to trace back to its source.

Recommended evidence notation:

```text
Source:
export-stg-uat/extracted/default/config/autoconfig.cfg:L90-L118
```

or equivalent source metadata if exact line references are available programmatically.

---

## Output Quality Rules

The final reference must:

```text
1. Separate observed facts from interpretation.
2. Preserve exact interface/IP/route/alias evidence.
3. Avoid name-based inference.
4. Avoid assuming findings before inspection.
5. Avoid duplicating conditional representations as separate objects.
6. Reuse existing exports and pipeline outputs.
7. Never re-export merely to perform analysis.
8. Never overwrite application-domain truth with Default-domain assumptions.
9. Clearly mark evidence gaps.
10. Remain reusable by the AS-IS Architecture stage.
```

---

## Minimal Execution Pattern

Use this mental sequence:

```text
Existing pipeline?
    |
    +-- yes → reuse index/<DOMAIN>/ + raw export
    |
    +-- no  → run required pipeline only if needed

Locate real appliance config
    ↓
Discover actual top-level blocks
    ↓
Reconstruct interfaces
    ↓
Reconstruct routes
    ↓
Reconstruct DNS / aliases
    ↓
Reconstruct system/runtime settings
    ↓
Classify facts/findings/gaps
    ↓
Write/update docs/as-is-architecture-reference.md
```

---

## Anti-Patterns

Do not:

```text
assume default.cfg is always authoritative
rerun export when evidence already exists
search only for predefined findings
treat examples as mandatory findings
guess interface roles
guess what an intermediate IP represents
merge static-host and host-alias semantics
infer service-to-interface binding from names alone
hide missing evidence
write conclusions without provenance
```

---

## Completion Criteria

This skill is complete when:

```text
1. Relevant appliance/default configuration source is identified.
2. Network interfaces are reconstructed.
3. Routes and gateways are captured.
4. DNS/static-host/host-alias evidence is captured.
5. Observed system/runtime settings are summarized.
6. Facts, findings, hypotheses, and evidence gaps are separated.
7. Existing domain outputs were reused where available.
8. No unnecessary re-export was performed.
9. docs/as-is-architecture-reference.md was updated.
10. Every important statement is traceable to raw evidence.
```
