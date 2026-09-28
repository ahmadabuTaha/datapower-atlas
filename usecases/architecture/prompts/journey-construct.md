# DataPower Atlas — User Journey Reconstruction

Reconstruct DataPower journeys as architectural evidence bundles.

Do not treat a Journey as only a graph traversal.

The journey must combine structural traversal with resolved semantics, dependency state, routing evidence, and provenance.

For each service:

1. Identify the service.
2. Identify exposed operations/request patterns.
3. Link each operation to its processing policy.
4. Resolve match rules.
5. Resolve processing rules.
6. Preserve ordered processing actions.
7. Resolve referenced artifacts where available.
8. Incorporate already-extracted XSLT/GatewayScript semantics.
9. Identify routing decisions.
10. Separate configured backend from actual evidenced egress.
11. Capture unresolved evidence explicitly.
12. retain provenance and evidence certainty.

Use this conceptual model:

Domain
→ Service
→ Operation
→ Match
→ Processing Policy
→ Rule
→ Ordered Actions
→ Referenced Artifact
→ Extracted Behavior
→ Routing Decision
→ Actual Egress

For each journey include:

### Identity
- environment
- domain
- service
- operation
- method
- path

### Entry
- listener/interface
- protocol
- port
- TLS evidence

### Processing
- processing policy
- match
- rule
- direction
- ordered actions

### Semantics
- validation
- transformation
- security
- authentication
- authorization
- routing
- enrichment
- logging
- error handling
- protocol mediation
- script-based behavior

### Dependencies
For every dependency record:

- reference
- dependency type
- resolved/unresolved
- resolved artifact if available
- evidence source

Never convert:

"reference exists but artifact unresolved"

into:

"dependency does not exist."

### Routing

Represent separately:

configured_backend:
dynamic | static | none | unresolved

configured_backend_target:
<value if evidenced>

route_control:
<skip-backside / route action / dynamic route / etc.>

actual_egress_status:
confirmed | candidate | unresolved | not_evidenced

actual_egress:
<target only when supported by evidence>

actual_egress_mechanism:
backend | route_action | gateway_script | xslt | other_evidenced_mechanism

### Certainty

Every material architectural conclusion must be classified as:

confirmed
derived
candidate
unresolved

Do not upgrade candidate or unresolved evidence to confirmed.

### Provenance

Every material conclusion must be traceable to:

- environment
- domain
- service
- source/index
- artifact when applicable

Do not borrow evidence from another environment.

---

# Journey Granularity

Create a service-level journey first.

Create separate operation-level journeys only when operations materially differ in:

- processing
- dependencies
- routing
- transformation
- security
- actual egress
- error behavior

If 50 operations share the same architectural behavior, do not generate 50 verbose duplicate documents.

Represent the shared journey once and identify the operations using it.

If one or more operations diverge, generate focused operation journeys for those differences.

This optimization is required to reduce token usage without losing architectural fidelity.

---

# Output Goal

The resulting Journey must allow a future architecture analysis to answer:

"What happens to this request?"

without reopening raw DataPower configuration unless verification is specifically required.