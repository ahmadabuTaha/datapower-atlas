AS-IS Architecture Reference

Consolidated evidence-backed reference used by the AS-IS Architecture stage.

This document is derived from raw exports and domain-local indexes.
Raw configuration remains the authoritative source.

DataPower Appliance / Default Domain

Evidence Sources

Populate with the exact exported files and relevant pipeline outputs used.

Example format:

Raw:
- export-stg-uat/extracted/default/config/autoconfig.cfg

Derived:
- index/DEFAULT/files.csv
- index/DEFAULT/files_scanned.csv

Appliance Network Summary

To be populated from evidence.

Interfaces

To be populated from evidence.

Recommended fields:

Interface
IP / Prefix
Gateway
MTU
Admin State
Observed Role
Role Confidence
Source

Interface Roles

To be populated from evidence.

Routing

To be populated from evidence.

Recommended fields:

Interface
Destination CIDR
Next Hop
Metric
Operator Comment
Source

DNS

To be populated from evidence.

Static Hosts

To be populated from evidence.

Recommended fields:

Alias
Resolved IP
Documented Intended Destination
Comment
Source

Host Aliases

To be populated from evidence.

Recommended fields:

Alias
IP
Summary
Source

System and Runtime Settings

To be populated from evidence.

Management Services

To be populated from evidence.

Certificate / Crypto Operations

To be populated from evidence.

Cross-Domain Correlations

Only add evidence-backed correlations with application domains.

Do not infer service-to-interface binding from names alone.

Findings

Only architecture-relevant findings derived from evidence.

Classify each as:

FACT
FINDING
HYPOTHESIS
OPEN_EVIDENCE_GAP

Open Evidence Gaps

Record unresolved architecture questions without guessing.