# Datapower Atlas - Skillset

**Purpose:** Define the responsibilities, execution order, inputs, outputs, and architectural boundaries of the Codex skills used by DataPower Atlas.

## 1. Skills Catalog
| Skill | Primary Responsibility | Expected Output |
|---|---|---|
| run-domain-analysis | Orchestrate domain-level architectural investigation | Domain analysis and evidence summary |
| trace-service | Reconstruct a specific DataPower service | Service Architectural Evidence Bundle |
| trace-operation | Investigate individual operation processing paths | Operation Architectural Evidence Bundle |
| investigate-gap | Investigate missing, unresolved, or contradictory evidence | Evidence-backed gap findings |
| datapower-semantics | Interpret DataPower-specific configuration and execution semantics | Semantic findings with supporting evidence |
| capability-analysis | Identify functional capabilities currently delivered by DataPower | AS-IS capability decomposition |
| replacement-analysis | Derive modernization requirements and assess replacement considerations | Evidence-based replacement analysis |
| Architecture rendering | Visualize supported architecture relationships and journeys | Architecture diagrams |

## 2. Recommended Execution Sequence
| Order | Skill | Trigger | Dependency |
|---|---|---|---|
| 1 | run-domain-analysis | Domain-wide assessment | Validated Atlas indexes |
| 2 | trace-service | Service investigation | Service Journey |
| 3 | trace-operation | Operation-specific investigation | Operation Journey |
| 4 | investigate-gap | Unresolved evidence or inconsistency | Targeted indexes and source evidence |
| 5 | datapower-semantics | Processing or routing behavior requires interpretation | Resolved configuration and source artifacts |
| 6 | capability-analysis | Functional decomposition | Validated AS-IS findings |
| 7 | replacement-analysis | Modernization assessment | Capability model and requirements |
| 8 | Architecture rendering | Visual documentation | Confirmed architectural evidence |

The sequence is a recommended reasoning workflow, not a requirement to invoke every skill for every question.

## 3. Additional Skills
| Skill | Purpose | Key Constraint |
|---|---|---|
| default-domain-analysis | Analyze appliance-level and DEFAULT-domain evidence | Keep DEFAULT evidence separate from service-domain evidence |
| compare-domains | Compare validated domain architectures | Never use another domain to silently resolve missing local evidence |
| classify-finding | Classify a finding and identify the appropriate next action | Distinguish defects, coverage gaps, and valid unresolved states |
| generate-architecture-diagrams | Generate PlantUML diagrams from validated architectural evidence | Render evidence; do not invent relationships |

## 4. Inputs and Outputs
| Skill | Main Inputs | Main Outputs |
|---|---|---|
| run-domain-analysis | Environment, domain, raw export, Atlas repository | Validated pipeline outputs, execution status, domain summary |
| trace-service | Service identity, Service Journey, supporting indexes | Ingress, processing, routing, dependencies, evidence gaps |
| trace-operation | Service, operation, Operation Journey | Processing path, actions, routing and egress evidence |
| investigate-gap | Unresolved reference, anomaly, or contradiction | Classification, supporting evidence, recommended action |
| datapower-semantics | Specific configuration or processing question | Focused semantic interpretation |
| default-domain-analysis | DEFAULT-domain and appliance evidence | Appliance/shared-configuration analysis |
| compare-domains | Validated outputs from multiple domains | Cross-domain comparison and correlation |
| classify-finding | Finding evidence and context | Finding classification and rationale |
| capability-analysis | Validated service/domain traces | Functional capability inventory |
| replacement-analysis | Capabilities, constraints, NFR evidence | Replacement requirements and candidate solution roles |
| generate-architecture-diagrams | Validated architectural relationships | PlantUML component, network, service-journey, or cross-domain diagrams |

## 5. Shared Operating Rules
| Rule | Requirement |
|---|---|
| Evidence authority | Raw CFG and source artifacts remain authoritative |
| Retrieval | Start with compact Journey evidence and indexes |
| Domain isolation | Do not borrow evidence across domains |
| Unresolved references | Preserve unresolved dependencies |
| Certainty | Never increase evidence certainty without new evidence |
| Operation tracing | Do not load all operations unless necessary |
| Runtime behavior | Distinguish configured backend from actual egress |
| Findings | Classify before recommending code or taxonomy changes |
| Frozen components | Reopen only for reproducible defects or broken requirements |
| Modernization | Derive capabilities before evaluating replacement products |
| Diagrams | Never display greater certainty than the underlying evidence |

## 6. Execution Contracts
| Contract | Responsibility |
|---|---|
| AGENTS.md | Project-wide Codex operating rules |
| docs/skill-contract.md | Skill execution chain, terminology, inputs/outputs, certainty propagation |
| docs/journey-evidence-contract.md | Service and Operation Evidence Bundle structure and semantics |
| Individual SKILL.md | Skill-specific procedures and constraints |
| tools/run_domain_pipeline.sh | Authoritative domain pipeline execution |