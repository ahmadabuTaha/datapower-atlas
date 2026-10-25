# DataPower Atlas — Parameterized End-to-End Service Smoke Test

## Purpose

Perform a focused end-to-end architectural smoke test for ONE explicitly
selected DataPower service.

This is NOT random service selection.

The caller must provide the target service parameters.

The test must validate whether the completed DataPower Atlas can reconstruct
the selected service accurately, efficiently, and traceably from the existing
AS-IS outputs.

The test must also generate two detailed PlantUML architecture views for the
selected service:

1. Detailed Component Diagram
2. Detailed Network Diagram

Both diagrams must elaborate the evidenced frontend and backend sides while
preserving evidence certainty and explicitly showing where evidence stops.

The test is primarily an ARCHITECTURE RETRIEVAL AND RECONSTRUCTION test.

It is NOT a new discovery exercise.

---

# PARAMETERS

Set these values before execution:

TARGET_DOMAIN="<DOMAIN>"
TARGET_SERVICE="<SERVICE_NAME>"

Optional:

TEST_ID="<OPTIONAL_TEST_ID>"

If TEST_ID is empty, derive a deterministic filesystem-safe identifier from:

TARGET_DOMAIN + TARGET_SERVICE

Example only:

TARGET_DOMAIN="STG"
TARGET_SERVICE="Example_Service"
TEST_ID="STG-Example_Service"

Do NOT randomly select another service.

Do NOT silently substitute a similarly named service.

If the exact service cannot be resolved, STOP with:

SMOKE TEST BLOCKED — TARGET SERVICE NOT RESOLVED

and report candidate matches without selecting one.

---

# TEST OBJECTIVE

Starting only from:

TARGET_DOMAIN
TARGET_SERVICE

determine whether the Atlas can reconstruct an evidence-based architecture
profile for that service.

The reconstruction should answer:

1. What is the service?
2. In which domain/environment is it defined?
3. What service type is evidenced?
4. What operations belong to it?
5. What operation patterns are represented?
6. What service Journey exists?
7. What operation-pattern Journeys exist where applicable?
8. How does traffic enter the service?
9. What frontend/listener information is evidenced?
10. How are requests matched?
11. Which processing policies/rules/actions participate?
12. Which referenced artifacts participate?
13. Which artifacts are resolved?
14. Which artifacts remain unresolved?
15. What processing/mediation behavior is evidenced?
16. What configured backend information exists?
17. What actual egress is evidenced?
18. Is routing static, dynamic, script-controlled, transformation-controlled,
    configured-only, runtime-computed, or unresolved?
19. What backend destinations are evidenced?
20. What protocols/connectivity mechanisms are evidenced?
21. What security dependencies are evidenced?
22. What runtime/infrastructure dependencies are evidenced?
23. What capabilities are associated with this service and its operations?
24. What remains not evidenced?
25. Can every major conclusion be traced back through the Atlas?
26. Is domain/environment provenance consistent?

---

# OPERATING MODE

Use:

focused_frozen_evidence_smoke_test

The completed Phase 1–5 AS-IS outputs are FROZEN.

Do not modify them.

The smoke test may READ the frozen outputs.

Do NOT:

- rebuild indexes
- rerun Phase 1–5
- rerun Journey builders
- modify existing Journeys
- modify canonical JSON
- modify service/operation catalogs
- modify context/capability evidence
- modify frozen findings
- introduce new AS-IS facts into frozen outputs
- perform external research
- borrow evidence from another domain/environment
- infer unsupported infrastructure
- infer business-system identities

---

# RETRIEVAL STRATEGY

Follow this retrieval order.

Do NOT begin with broad raw-source inspection.

Use:

Question
  ↓
AS-IS consolidated outputs
  ↓
Service identity
  ↓
Service Journey
  ↓
Operation identity
  ↓
Operation-pattern Journey when applicable
  ↓
Context evidence
  ↓
Capability evidence
  ↓
Existing findings / unresolved registers
  ↓
Supporting indexes only when required
  ↓
Raw/source artifact ONLY for focused verification if strictly necessary

Prefer the shortest evidence path that answers the question.

The smoke test should measure whether the Atlas prevents unnecessary
rediscovery.

---

# AUTHORITATIVE / AVAILABLE OUTPUTS

Leverage the existing outputs.

Start with:

outputs/as-is/05-as-is-pack/AS-IS-FACTS.json

Also use:

outputs/as-is/05-as-is-pack/AS-IS-SUMMARY.md
outputs/as-is/05-as-is-pack/AS-IS-UNRESOLVED.md
outputs/as-is/05-as-is-pack/TO-BE-INPUT.md

Service and operation identity:

outputs/as-is/01-service-catalog/services.json
outputs/as-is/01-service-catalog/operations.json
outputs/as-is/01-service-catalog/services.md
outputs/as-is/01-service-catalog/operations.md

Journey index:

outputs/as-is/02-user-journeys/journey-index.md

Service and operation Journey documents under:

outputs/as-is/02-user-journeys/

Enterprise context:

outputs/as-is/03-context-view/context-facts.json
outputs/as-is/03-context-view/datapower-context.md
outputs/as-is/03-context-view/external-systems.md
outputs/as-is/03-context-view/integration-flows.md

Capability evidence:

outputs/as-is/04-capability-map/capability-evidence.json
outputs/as-is/04-capability-map/datapower-capabilities.md
outputs/as-is/04-capability-map/capability-matrix.md
outputs/as-is/04-capability-map/capability-unresolved.md

Network Infrastructure
outputs/as-is/06-network-infra/sql-host-alias-correlation.md
outputs/as-is/06-network-infra/sql-database-endpoints.md
outputs/as-is/06-network-infra/network-infrastructure.md
outputs/as-is/06-network-infra/artifact-endpoint-resolution.md

Services and Operations Enrichments
outputs/as-is/07-service-enrichment/service-endpoint-evidence.md
outputs/as-is/08-operation-enrichment/operation-endpoint-evidence.md


Existing findings and reports elsewhere in outputs may be used when they
directly reference TARGET_DOMAIN / TARGET_SERVICE.

Prefer JSON for deterministic lookup and Markdown for architecture narrative
and already-aggregated findings.

Do NOT broadly read unrelated service Journeys.

---

# RAW EVIDENCE RULE

Raw CFG/XSLT/GatewayScript/source is NOT the normal retrieval path.

It may be accessed only when:

1. a specific Atlas statement requires verification, OR
2. a contradiction exists between generated outputs, OR
3. an already-resolved referenced artifact needs focused semantic verification.

If raw evidence is accessed:

- state exactly why
- state exactly which file was accessed
- state which claim was being verified
- do not perform broad scanning
- do not turn the smoke test into evidence production

Missing raw artifacts must remain unresolved.

Do not attempt to compensate for missing evidence using another environment.

---

# ENVIRONMENT / DOMAIN ISOLATION

TARGET_DOMAIN is authoritative.

Never borrow evidence from another domain.

For example:

STG evidence must not be used to complete STG-Replica evidence.

STG-Replica evidence must not be used to complete STG evidence.

Identical service names across domains are separate identities.

All evidence must preserve:

domain
service identity
operation identity
source provenance

Any mismatch must be reported.

---

# EVIDENCE STATE MODEL

Every important architecture statement and diagram element must preserve its
evidence state.

Use the following states where applicable:

CONFIRMED

    Directly supported by frozen evidence and, where applicable, resolved
    semantics.

EVIDENCED

    Explicitly represented by the frozen Atlas evidence.

CONFIGURED_ONLY

    Configuration exists, but runtime execution/usage is not independently
    confirmed.

CANDIDATE

    Evidence identifies a candidate relationship or destination but does not
    justify promotion to confirmed runtime behavior.

RUNTIME_COMPUTED

    Runtime logic determines the final value and the final static value is not
    materialized in available evidence.

UNRESOLVED

    Evidence references something that could not be fully resolved.

NOT_EVIDENCED

    The reconstruction contains no evidence supporting the statement.

Do not convert NOT_EVIDENCED into ABSENT.

Do not convert UNRESOLVED into ERROR.

Do not convert CANDIDATE into CONFIRMED.

---

# CORE SEMANTIC GUARDRAILS

Preserve all existing AS-IS rules.

Service != Operation

Configured backend != Actual egress

Configured destination != Confirmed runtime destination

Technical destination != Remote business-system identity

Runtime-computed target != Known static destination

Missing artifact != No dependency

No resolved file != No file reference

NOT_EVIDENCED != ABSENT

UNRESOLVED != ERROR

skip-backside = 1 != No outbound communication

A GatewayScript/XSLT outbound call may represent actual egress even when
backside processing is skipped.

Namespace/schema URIs must never be promoted to outbound destinations.

Do not infer a second backend call from the presence of both configured
backend data and script-controlled egress.

---

# STEP 1 — Resolve Exact Service Identity

Resolve:

TARGET_DOMAIN
TARGET_SERVICE

against the frozen service catalog.

Report:

- domain
- service name
- canonical service ID
- service type
- source provenance
- Journey reference
- number of operations
- number of distinct operation patterns

If exact resolution fails:

STOP.

Do not fuzzy-select another service.

---

# STEP 2 — Build Service Architecture Profile

Create a compact but detailed architecture profile.

Include:

## Identity

- Domain
- Service
- Service ID
- Service type
- provenance

## Operation Landscape

For every operation belonging to the service include:

- operation ID
- operation name/path/match identity as available
- operation pattern ID
- Journey availability
- actual-egress state
- relevant unresolved state

Do not omit operations simply because multiple operations share a pattern.

Clearly distinguish:

operation count
from
distinct operation-pattern count

---

# STEP 3 — Reconstruct Frontend Architecture

Reconstruct the FRONTEND side using existing evidence.

Frontend means the evidenced architecture before/at service ingress.

Look for evidence of:

- caller/client identity
- ingress boundary
- listener/front-side information
- protocol
- port
- host/address
- URL/path
- service exposure
- TLS/security configuration
- certificates
- authentication behavior
- authorization behavior
- request matching
- other evidenced frontend dependencies

Do not assume all fields exist.

For every frontend item record:

VALUE
EVIDENCE_STATE
SOURCE

Examples:

Caller Identity:
    NOT_EVIDENCED

Ingress Boundary:
    EVIDENCED

Authentication:
    NOT_EVIDENCED

Do not fill missing fields using DataPower defaults or generic knowledge.

---

# STEP 4 — Reconstruct Processing Architecture

Reconstruct the service processing chain.

Represent:

Service
→ Operation
→ Match
→ Processing Policy
→ Rule
→ Ordered Actions
→ Referenced Artifacts
→ Extracted Behavior

For each important processing component identify:

- component/object
- relationship
- operation scope
- evidence state
- provenance
- unresolved references

Include resolved XSLT/GatewayScript semantics only when already available in
the frozen Journey/evidence outputs.

Do not broadly re-analyze scripts.

---

# STEP 5 — Reconstruct Backend / Egress Architecture

Reconstruct the BACKEND side carefully.

For each operation determine, where evidenced:

- configured backend
- configured destination
- backend mode
- route-control evidence
- skip-backside evidence
- actual egress
- actual destination
- protocol
- runtime-computed destination
- script-controlled egress
- transformation-controlled egress
- logical datasource target
- unresolved route
- unresolved referenced artifact

Keep configured and runtime behavior separate.

Use a structure similar to:

Operation
  |
  +-- Configured Backend
  |      State: CONFIGURED_ONLY / EVIDENCED / NOT_EVIDENCED
  |
  +-- Route Control
  |      State: ...
  |
  +-- Actual Egress
         State: CONFIRMED / RUNTIME_COMPUTED / UNRESOLVED /
                NOT_EVIDENCED

Do not invent backend systems.

---

# STEP 6 — Dependencies

Identify service-specific dependencies from the existing Atlas.

Include where evidenced:

- referenced artifacts
- XML Managers
- TLS/crypto objects
- certificates
- private keys
- security dependencies
- runtime dependencies
- infrastructure dependencies
- logical datasource dependencies
- shared/default dependencies

For each dependency record:

dependency
type
scope
evidence state
resolution state
source

Preserve unresolved references.

---

# STEP 7 — Capability Mapping

Use the frozen Phase 4 capability evidence.

Determine which of the existing:

6 capability domains
17 capabilities
28 capability functions

are evidenced for TARGET_SERVICE or its operations.

Do NOT create new capabilities.

For each applicable capability report:

Capability Domain
Capability
Function(s)
Service/Operation Scope
Evidence Status
Certainty
Evidence Source

Clearly distinguish:

execution-evidenced
configured-only

Do not claim a capability solely because DataPower supports it generally.

---

# STEP 8 — Existing Findings

Search existing generated findings/reports for direct references to:

TARGET_DOMAIN
TARGET_SERVICE
its operation IDs
its operation-pattern IDs

Bring relevant existing findings into the smoke-test report.

Do not duplicate unrelated global findings.

Classify each relevant item as:

CONFIRMED_FINDING
UNRESOLVED_EVIDENCE
DOCUMENTATION_FINDING
KNOWN_LIMITATION

Do not promote a known limitation to a defect.

---

# STEP 9 — Detailed PlantUML Component Diagram

Generate:

outputs/smoke-tests/<TEST_ID>/diagrams/
    detailed-component-diagram.puml

The component diagram must be SERVICE-SPECIFIC.

It must elaborate BOTH:

FRONTEND
and
BACKEND

with the DataPower processing architecture between them.

Required conceptual layout:

+---------------------------------------------------------------+
| FRONTEND                                                      |
|                                                               |
| Caller / Client                                               |
|    ↓                                                          |
| Front-Side / Listener / Ingress                               |
|    ↓                                                          |
| Security / TLS / Auth where evidenced                         |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
| DATAPOWER SERVICE                                             |
|                                                               |
| Service                                                       |
|   ↓                                                           |
| Operations / Matches                                          |
|   ↓                                                           |
| Processing Policy                                             |
|   ↓                                                           |
| Rules                                                         |
|   ↓                                                           |
| Ordered Actions                                               |
|   ↓                                                           |
| XSLT / GatewayScript / Processing Artifacts                   |
|   ↓                                                           |
| Routing Decision                                              |
+-------------------------------+-------------------------------+
                                |
                                v
+---------------------------------------------------------------+
| BACKEND / EGRESS                                              |
|                                                               |
| Configured Backend                                            |
| Actual Egress                                                 |
| Runtime-Computed Targets                                      |
| Logical Datasources                                           |
| Technical Destinations                                       |
| Remote System Identity                                       |
+---------------------------------------------------------------+

This is a conceptual layout only.

The actual diagram must use the TARGET_SERVICE evidence.

---

# COMPONENT DIAGRAM DETAIL REQUIREMENTS

Do NOT collapse the selected service into one generic box.

Where evidence allows, show:

- caller boundary
- ingress/listener
- protocol
- service
- each relevant operation or grouped operation-pattern structure
- matches
- processing policy
- important rules
- action chain
- resolved processing artifacts
- unresolved processing artifacts
- route-control behavior
- configured backend
- actual egress
- runtime-computed egress
- logical datasource
- technical destination
- security dependencies
- important runtime dependencies

If the service has many operations, preserve readability.

Use operation-pattern grouping when appropriate, but include a note stating:

"<N> operations represented through <M> distinct operation patterns"

Do not lose operation cardinality.

---

# COMPONENT DIAGRAM EVIDENCE FLAGS

Every architecture element where evidence status matters must display an
explicit evidence marker.

Use stereotypes:

<<CONFIRMED>>
<<EVIDENCED>>
<<CONFIGURED_ONLY>>
<<CANDIDATE>>
<<RUNTIME_COMPUTED>>
<<UNRESOLVED>>
<<NOT_EVIDENCED>>

Examples:

component "Configured Backend" as CB <<CONFIGURED_ONLY>>

component "Actual Egress\nhttps://..." as AE <<CONFIRMED>>

component "Caller Identity\nNot evidenced" as Caller <<NOT_EVIDENCED>>

component "Referenced XSLT\nlocal:///..." as X1 <<UNRESOLVED>>

Do not rely only on colors.

The text stereotype must remain visible.

Add a legend explaining all states used in the diagram.

Color may be used only as a secondary visual cue.

Evidence meaning must remain understandable in monochrome.

---

# STEP 10 — Detailed PlantUML Network Diagram

Generate:

outputs/smoke-tests/<TEST_ID>/diagrams/
    detailed-network-diagram.puml

This must also be SERVICE-SPECIFIC.

Its purpose is to show the evidenced communication topology around the
selected service.

Focus on:

FRONTEND CONNECTIVITY
        ↓
DATAPOWER SERVICE BOUNDARY
        ↓
BACKEND CONNECTIVITY

---

# NETWORK DIAGRAM FRONTEND

Show only what is evidenced:

- caller/client if known
- unknown caller boundary if not evidenced
- protocol
- host/address
- port
- ingress/listener
- URL/path where relevant
- TLS/security dependencies where evidenced
- DataPower service endpoint

If caller identity is not evidenced, explicitly show:

Caller / Upstream System
<<NOT_EVIDENCED>>

Do NOT invent an application name.

---

# NETWORK DIAGRAM DATAPOWER SECTION

Show the selected service boundary.

Include where useful:

- domain
- service
- service type
- relevant ingress
- routing decision points
- important service-level dependencies

Do not turn the network diagram into a duplicate of the full component
diagram.

The network diagram should emphasize communication paths.

---

# NETWORK DIAGRAM BACKEND

For every relevant backend/egress relationship show:

- operation/pattern responsible for the route where useful
- configured destination
- actual confirmed destination
- protocol
- port where evidenced
- URL/URI where evidenced
- runtime-computed target
- logical datasource
- unresolved destination
- remote identity state

Do not merge:

configured backend
and
actual egress

unless the frozen evidence explicitly establishes them as the same runtime
relationship.

---

# NETWORK TOPOLOGY GUARDRAILS

Do NOT invent:

- DMZ
- VLAN
- subnet
- firewall
- F5
- load balancer
- router
- switch
- NAT
- OCI VCN
- Kubernetes
- OpenShift
- appliance HA
- cluster
- DR
- geographic region
- physical network segment

unless the selected service evidence explicitly proves it.

The diagram must show WHERE THE EVIDENCE STOPS.

For example:

DataPower
   |
   | HTTPS : CONFIRMED
   v
Technical Destination
   |
   v
Remote Business System Identity
<<NOT_EVIDENCED>>

This is preferred over inventing the system behind the endpoint.

---

# NETWORK DIAGRAM EVIDENCE FLAGS

Use the same stereotypes:

<<CONFIRMED>>
<<EVIDENCED>>
<<CONFIGURED_ONLY>>
<<CANDIDATE>>
<<RUNTIME_COMPUTED>>
<<UNRESOLVED>>
<<NOT_EVIDENCED>>

Every ambiguous boundary must be visually explicit.

Add a legend.

Again:

Do not rely solely on colors.

---

# DIAGRAM RELATIONSHIP LABELS

Relationship labels should carry evidence where useful.

Examples:

--> "HTTPS\n<<CONFIRMED>>"

--> "Configured backside\n<<CONFIGURED_ONLY>>"

--> "Runtime target\n<<RUNTIME_COMPUTED>>"

--> "Referenced artifact\n<<UNRESOLVED>>"

Avoid unlabeled arrows where the relationship meaning is important.

---

# PLANTUML QUALITY RULES

Both diagrams must:

- start with @startuml
- end with @enduml
- compile independently
- use deterministic aliases
- avoid unsupported PlantUML syntax
- use packages/rectangles/components/nodes appropriately
- remain readable in Confluence
- avoid excessive width
- avoid giant single-line labels
- wrap long endpoint values
- include TARGET_DOMAIN and TARGET_SERVICE in the title
- include evidence-state legend
- include generated-from-frozen-evidence note

If a PlantUML compiler is available, compile both diagrams as validation.

Do not require a compiler to complete the test if none exists.

---

# STEP 11 — Smoke-Test Markdown Report

Generate:

outputs/smoke-tests/<TEST_ID>/
    SMOKE-TEST-REPORT.md

The report must be suitable for architecture review and Confluence.

Use this structure:

# DataPower Service End-to-End Smoke Test

## 1. Test Parameters

Domain
Service
Test ID

## 2. Test Result

PASS / PARTIAL / FAIL

Explain why.

## 3. Service Identity

Canonical service identity and provenance.

## 4. Architecture Summary

Concise description of what the service does architecturally based only on
evidence.

## 5. Operation Inventory

Operation-level table.

## 6. Frontend Architecture

Confirmed/evidenced/configured/not-evidenced frontend details.

## 7. Processing Architecture

Service → Operation → Match → Policy → Rule → Actions → Artifacts.

## 8. Backend and Egress Architecture

Configured backend versus actual egress.

## 9. Integration and Connectivity

Protocols, technical destinations, logical datasources, runtime targets.

## 10. Security Dependencies

Only evidenced security/crypto dependencies.

## 11. Runtime / Infrastructure Dependencies

Only evidenced dependencies.

## 12. Capability Mapping

Applicable frozen capabilities/functions.

## 13. Unresolved Evidence

Service-specific unresolved evidence only.

## 14. Existing Relevant Findings

Existing findings related directly to the selected service.

## 15. Evidence Traceability

Show where the major conclusions came from.

## 16. Retrieval Efficiency

Report which layers were required.

## 17. Diagram References

Link:

diagrams/detailed-component-diagram.puml

diagrams/detailed-network-diagram.puml

## 18. Smoke-Test Assessment

Summarize reconstruction quality and any gaps.

---

# STEP 12 — Machine-Readable Result

Also generate:

outputs/smoke-tests/<TEST_ID>/
    smoke-test-result.json

The JSON should capture at minimum:

{
  "test_id": "...",
  "target_domain": "...",
  "target_service": "...",
  "service_id": "...",
  "service_type": "...",

  "result": "PASS|PARTIAL|FAIL",

  "operations": {
    "count": 0,
    "distinct_patterns": 0
  },

  "frontend": {
    "ingress_state": "...",
    "caller_identity_state": "...",
    "authentication_state": "...",
    "authorization_state": "..."
  },

  "processing": {
    "journey_available": true,
    "referenced_artifacts": 0,
    "resolved_artifacts": 0,
    "unresolved_artifacts": 0
  },

  "backend": {
    "configured_backend_state": "...",
    "actual_egress_states": [],
    "runtime_computed_targets": 0,
    "unresolved_routes": 0
  },

  "capabilities": {
    "domains": [],
    "capabilities": [],
    "functions": []
  },

  "evidence": {
    "files_read": [],
    "journey_documents_read": [],
    "raw_source_files_read": []
  },

  "diagrams": {
    "component": "...",
    "network": "..."
  },

  "provenance_consistent": true,

  "violations": []
}

The exact schema may be extended where useful.

Do not remove the minimum fields above.

---

# PASS / PARTIAL / FAIL CRITERIA

## PASS

PASS does NOT mean every architecture fact is known.

PASS means the Atlas correctly represents both known and unknown evidence.

PASS when:

- exact service identity resolves
- domain provenance is consistent
- all catalog operations are represented
- Journey references reconcile
- frontend evidence is represented without invention
- processing relationships are reconstructed from existing evidence
- configured backend is separated from actual egress
- unresolved evidence remains unresolved
- capability mapping uses only frozen capabilities
- diagrams faithfully represent evidence states
- no cross-environment borrowing occurs
- no unsupported architecture is invented
- major claims are traceable

A service MAY PASS while containing:

NOT_EVIDENCED
UNRESOLVED
RUNTIME_COMPUTED

states.

Those states are not test failures when correctly represented.

## PARTIAL

Use PARTIAL when the Atlas retrieval works but a material service-specific
reconstruction area cannot be validated due to existing evidence limitations.

Explain exactly what prevents full validation.

## FAIL

FAIL when the Atlas itself produces contradictory or incorrect reconstruction,
for example:

- wrong service identity
- missing catalog operations
- wrong domain provenance
- cross-environment evidence borrowing
- false backend promotion
- false actual egress
- false capability
- known unresolved evidence presented as confirmed
- namespace/schema URI promoted as destination
- configured backend presented as confirmed actual egress without evidence
- diagram invents infrastructure
- traceability is broken

---

# SMOKE TEST SCORING

Produce diagnostic scores from 0–10.

These scores are for the QUALITY OF THE ATLAS RECONSTRUCTION, not for the
quality of the DataPower service.

Score:

1. Retrieval Efficiency
2. Service Identity Accuracy
3. Operation Coverage
4. Journey Reconstruction
5. Frontend Reconstruction
6. Processing Semantics
7. Backend / Egress Reconstruction
8. Dependency Reconstruction
9. Capability Mapping
10. Provenance / Traceability
11. Component Diagram Fidelity
12. Network Diagram Fidelity

Also provide:

Overall Smoke-Test Result:
PASS / PARTIAL / FAIL

Do not average scores blindly to determine PASS.

A semantic integrity violation may cause FAIL regardless of average.

---

# IMPORTANT KNOWN REGRESSION GUARDS

Explicitly verify:

1. Namespace/schema URIs are not promoted to actual egress.

Examples that must NOT appear as outbound destinations include:

http://www.datapower.com/extensions
http://www.w3.org/1999/XSL/Transform
http://schemas.xmlsoap.org/soap/envelope/
http://www.w3.org/2001/XMLSchema-instance

and schema/namespace identifiers generally.

2. If this service uses the known corrected MQ target, preserve exactly:

dpmq://IssueContract_QMGR/?RequestQueue=ESB.HRSD.CONTCRT.OUT

with protocol:

dpmq

3. skip-backside must not automatically mean no outbound communication.

4. Configured backside candidates must not automatically become actual egress.

5. Missing referenced artifacts must not be interpreted as no file reference.

6. No evidence may be borrowed from another environment.

---

# TOKEN / RETRIEVAL EFFICIENCY

Record the retrieval footprint.

At the end report:

Canonical Phase 5 files read:
<count>

Phase 4 files read:
<count>

Phase 3 files read:
<count>

Phase 2 Journey documents read:
<count>

Phase 1 files read:
<count>

Supporting indexes read:
<count>

Raw/source artifacts read:
<count>

Total relevant files read:
<count>

Do not optimize token usage by sacrificing correctness.

However, unnecessary broad reading should reduce the Retrieval Efficiency
score.

The desired behavior is:

AS-IS facts
→ targeted service evidence
→ targeted Journey evidence
→ targeted supporting evidence

not:

scan everything and reconstruct from scratch.

---

# OUTPUT STRUCTURE

Create only service-specific smoke-test outputs under:

outputs/smoke-tests/<TEST_ID>/

Expected:

outputs/smoke-tests/<TEST_ID>/
├── SMOKE-TEST-REPORT.md
├── smoke-test-result.json
└── diagrams/
    ├── detailed-component-diagram.puml
    └── detailed-network-diagram.puml

Do NOT modify:

outputs/as-is/

The smoke test is a consumer of the frozen AS-IS.

---

# FINAL VALIDATION

Before completion verify:

1. Exact TARGET_DOMAIN used.
2. Exact TARGET_SERVICE used.
3. No random selection occurred.
4. Exact service identity resolved.
5. Service belongs to TARGET_DOMAIN.
6. All catalog operations represented.
7. Operation cardinality reconciles.
8. Operation-pattern cardinality reconciles.
9. Service Journey reconciles.
10. Applicable operation-pattern Journeys reconcile.
11. Frontend evidence state explicitly represented.
12. Caller identity is not invented.
13. Authentication is not invented.
14. Authorization is not invented.
15. Processing relationships trace to existing evidence.
16. Referenced artifacts preserve resolution state.
17. Configured backend remains separate from actual egress.
18. Runtime-computed targets remain runtime-computed.
19. NOT_EVIDENCED is not interpreted as ABSENT.
20. UNRESOLVED is not interpreted as ERROR.
21. CANDIDATE is not interpreted as CONFIRMED.
22. skip-backside is interpreted correctly.
23. No namespace/schema URI is promoted to outbound destination.
24. No evidence borrowed across domains.
25. Technical destination is not presented as business-system identity.
26. Only frozen capabilities are used.
27. Capability evidence status is preserved.
28. Existing findings are not silently reclassified.
29. Component diagram contains explicit evidence-state flags.
30. Component diagram elaborates frontend and backend.
31. Network diagram contains explicit evidence-state flags.
32. Network diagram elaborates frontend and backend.
33. Network diagram contains no invented infrastructure.
34. Both PlantUML files are syntactically valid to the extent tooling allows.
35. Markdown report links to both diagrams.
36. JSON result reconciles with Markdown report.
37. Frozen AS-IS artifacts remain unchanged.
38. Retrieval footprint is reported.
39. Raw evidence access, if any, is explicitly disclosed.
40. All major conclusions remain traceable.

---

# FINAL RESPONSE

Return:

Smoke Test:
<TEST_ID>

Target:
<TARGET_DOMAIN> / <TARGET_SERVICE>

Result:
PASS / PARTIAL / FAIL

Service ID:
<id>

Service Type:
<type>

Operations:
<count>

Distinct Operation Patterns:
<count>

Service Journey:
RESOLVED / UNRESOLVED

Frontend Reconstruction:
PASS / PARTIAL / FAIL

Processing Reconstruction:
PASS / PARTIAL / FAIL

Backend / Egress Reconstruction:
PASS / PARTIAL / FAIL

Capability Mapping:
PASS / PARTIAL / FAIL

Provenance:
PASS / FAIL

Component Diagram:
<path>

Network Diagram:
<path>

Report:
<path>

Machine-Readable Result:
<path>

Journey Documents Read:
<count>

Raw/Source Artifacts Read:
<count>

Cross-Environment Evidence Borrowed:
NO / YES

Unsupported Infrastructure Inferred:
NO / YES

New AS-IS Facts Introduced:
NO / YES

Frozen Artifacts Modified:
NO / YES

Validation Gates:
<PASS_COUNT>/40 PASS

New Reproducible Defects:
NONE
or
<exact defect description>

Then provide the 12 diagnostic scores.

Stop after the smoke-test outputs and validation are complete.