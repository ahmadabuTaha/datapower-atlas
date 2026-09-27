# ST-001 — STG AjeerCancelVisa

## 1. Selected Service

- **Environment / domain:** `STG / STG`
- **Service:** `AjeerCancelVisa`
- **Canonical type:** `multi_protocol_gateway`
- **Service ID:** `obj:STG:multi_protocol_gateway:AjeerCancelVisa`
- **Overall result:** `PASS_WITH_FINDINGS`

This service was selected because one compact operation exercises the complete reasoning chain without broad retrieval: HTTP ingress, a processing policy and rule, three processing actions, a resolved GatewayScript, dynamic route control, `skip-backside`, a configured backend that must remain separate from actual egress, an explicit TLS client-profile dependency, and unresolved platform resources.

## 2. AS-IS Trace

### Evidence-backed journey

```text
AjeerCancelVisa_HTTPHandler
→ AjeerCancelVisa MPGW
→ AjeerCancelVisa processing policy
→ built-in/default match evidence: __default-accept-service-providers__
→ AjeerCancelVisa_rule_0
→ GatewayScript action
→ set-variable action
→ results action
→ script-mediated HTTPS POST to a runtime-computed destination
```

The match token is present in the policy relationship but is not represented as a separately resolved matching-rule object. The processing rule and all three actions are resolved.

### Ingress and configuration dependencies

| Evidence | State | Certainty |
|---|---|---|
| Front-side handler `AjeerCancelVisa_HTTPHandler` | Resolved | confirmed |
| XML Manager `default` | Resolved locally in STG | confirmed |
| User Agent `default` | Resolved locally in STG | confirmed |
| TLS client profile `AjeerCancelVisa-ClientProfile` | Resolved relationship | confirmed |

The evidence supports an HTTP ingress capability and an outbound TLS client-profile dependency. It does not establish mTLS, caller identity, remote-system identity, or remote topology.

### Operation trace

- **Operation:** `op:STG:STG:438702032f781bbc4e77`
- **Policy:** `AjeerCancelVisa`
- **Rule:** `AjeerCancelVisa_rule_0`
- **Actions:**
  1. `AjeerCancelVisa_rule_0_gatewayscript_0`
  2. `AjeerCancelVisa_rule_0_setvar_0`
  3. `AjeerCancelVisa_rule_0_results_0`

Resolved executable reference:

```text
local:///AjeerCancelVisa/AjeerCancelVisa.js
→ local/AjeerCancelVisa/AjeerCancelVisa.js
```

### Routing and actual egress

| Fact | Evidence-backed result | Certainty |
|---|---|---|
| Backend mode | `dynamic` | confirmed |
| Configured backend | `https://preprod.gw-proxy.tamkeen.cloud` | confirmed configuration |
| `skip-backside` | `var://service/mpgw/skip-backside = "1"` | confirmed |
| Explicit route action | Not evidenced | not_evidenced |
| Script-mediated path | Present | confirmed |
| Actual operation egress | GatewayScript HTTPS `POST` | confirmed |
| Destination construction | base URL + `var://service/URI` | confirmed dynamic construction |
| Remote system identity | Not established | not_evidenced |
| Remote topology | Not established | not_evidenced |

The GatewayScript explicitly:

- reads `var://service/URI`;
- appends it to `https://preprod.gw-proxy.tamkeen.cloud`;
- sets method `POST`;
- invokes `urlopen.open`.

The base URL is not treated as the complete runtime URL. The configured backend remains separate configuration evidence and is not drawn as a second runtime call. Because `skip-backside=true`, no normal backside execution is inferred.

### Files and unresolved evidence

Resolved:

- `local:///AjeerCancelVisa/AjeerCancelVisa.js` — GatewayScript, confirmed.

Unresolved platform references:

- `store:///filter-reject-all.xsl`
- `store:///identity.xsl`

These references remain visible and unresolved. Their `store:///` scheme is consistent with platform/shared resources; absence from the local inventory does not prove deployment failure. They do not block reconstruction of the operation-specific script egress.

### Provenance

- Journey environment/domain: `STG / STG`
- Source configuration: `export-stg-uat/extracted/STG/config/STG.cfg`
- Domain-consistency status: `consistent`
- GatewayScript relationship provenance: CFG line `5309`
- Policy/rule provenance: CFG line `30860`
- Action provenance: CFG lines `25854–25856`
- Configured-backend provenance: CFG line `38844`
- Skip-backside provenance: CFG lines `5361–5362`
- Dynamic-backend provenance: CFG line `38927`

Raw CFG content was not needed because the Journey contains consistent source pointers and the referenced source artifact directly proves the disputed runtime behavior.

## 3. Capability Analysis

| Observed capability | Strength | Evidence | Constraint / note |
|---|---|---|---|
| HTTP service ingress | DIRECT | Resolved HTTP front-side handler | Listener address/port are not materialized in the selected Journey. |
| Policy-based request execution | DERIVED | Service → policy → rule → three actions | Only one evidence-backed operation is present. |
| GatewayScript execution | DIRECT | Resolved action and local JavaScript artifact | Script behavior is part of the required AS-IS function. |
| JSON request/response mediation | DIRECT | Script reads and writes JSON | No broader schema-validation capability is claimed. |
| Dynamic outbound HTTPS routing | DIRECT | Base URL concatenated with `var://service/URI` | Runtime URI must remain dynamic. |
| Outbound HTTP integration | DIRECT | `urlopen.open`, method `POST` | Destination is the computed URL, not merely the base URL. |
| Backside-bypass route control | DIRECT | `skip-backside = 1` | Normal configured backside use is not evidenced for this operation. |
| Outbound TLS configuration | DIRECT | HTTPS destination plus TLS client-profile relationship | Client-certificate/mTLS behavior is not evidenced. |
| Outbound authentication-header injection | DIRECT | Script assigns client/API authentication headers | Values are hard-coded in source and must not be reproduced in reports. |
| Local executable dependency management | DIRECT | Resolved `local:///` GatewayScript | Artifact deployment/versioning must be preserved. |

No authentication/authorization policy, rate limiting, caching, observability integration, HA, throughput, latency, or retry capability is claimed because those behaviors are not established by the selected evidence.

## 4. Replacement Requirements / Solution Roles

| Current function | Capability | Evidenced constraint / NFR | Replacement requirement | Solution role |
|---|---|---|---|---|
| HTTP front-side handler | HTTP ingress | Preserve the exposed request path; caller identity is unknown | Accept the existing HTTP request contract and forward it into the processing flow | Ingress / API gateway role |
| Policy and processing rule | Policy-based execution | One ordered rule with script, route-control, and result actions | Preserve deterministic action ordering and error propagation | Gateway policy or integration orchestration role |
| GatewayScript JSON handling | JSON mediation and scripting | Behavior is implemented in code rather than declarative routing | Execute equivalent request/response logic with testable source and deployment controls | Integration/scripting runtime role |
| `var://service/URI` concatenation | Dynamic routing | Runtime path component must not be converted into a static endpoint | Construct the outbound URL from the approved base plus the inbound/runtime URI | Dynamic routing role |
| `urlopen.open` with `POST` | Outbound HTTP integration | The script, not normal backside routing, performs the call | Provide an outbound HTTPS client supporting POST, JSON payloads, response handling, and explicit failure handling | HTTP integration client role |
| TLS client-profile dependency | Transport security | TLS is evidenced; mTLS details are not | Support configurable outbound TLS policy without assuming client-certificate requirements | TLS / PKI configuration role |
| Authentication headers in script | Credential injection | Sensitive values are embedded in source | Externalize, protect, rotate, and inject equivalent credentials without embedding secret values in application code | Secrets-management and credential-injection role |
| Local GatewayScript artifact | Executable dependency | Operation behavior depends on a deployed local file | Provide versioned artifact deployment, traceability, rollback, and environment-specific configuration | Delivery/runtime governance role |

No product is selected. The evidence supports multiple logical roles; whether one platform or several products implement them is a later architecture decision.

Open replacement questions:

- What are the required ingress address, port, and external contract details?
- Does `AjeerCancelVisa-ClientProfile` require client identity credentials or only server validation?
- What timeout, retry, circuit-breaker, availability, throughput, and latency characteristics are required?
- Are the unresolved `store:///` resources platform defaults that require equivalents in the target runtime?
- What system owns the dynamically addressed backend, and what topology lies beyond the immediate URL?

## 5. Findings / Evidence Gaps

### FINDING — configured backend is not actual operation egress

The MPGW has a confirmed configured backend, but the operation sets `skip-backside=1` and performs the outbound call through GatewayScript. The two facts must remain separate. No second runtime call is evidenced.

### FINDING — dynamic destination must remain dynamic

The source constructs the destination from a confirmed base URL and `var://service/URI`. The final path cannot be resolved statically from the available evidence.

### FINDING — hard-coded authentication material

The referenced GatewayScript contains hard-coded authentication header values. Values are intentionally omitted here. This is source-configuration evidence and creates a secrets-management requirement; it does not establish the identity of the remote system.

### GAP — executable artifact sensitivity coverage

The file inventory reports `sensitivity_scan_status=not_scanned` for the GatewayScript even though targeted source inspection identified sensitive-looking hard-coded authentication material. This is a coverage gap requiring focused validation, not yet proof of a sensitivity-scanner implementation defect. No parser, resolver, or Journey component is reopened by this smoke test.

### EXPECTED_UNRESOLVED — platform XSLTs

The two `store:///` references remain unresolved. They are retained as evidence and are not classified as deployment failures.

## 6. Smoke-Test Verdict

**PASS_WITH_FINDINGS**

| Test dimension | Result | Rationale |
|---|---|---|
| Retrieval discipline | PASS | Began from the exact STG Journey, retrieved one operation, one artifact relationship, one file/sensitivity row, and the referenced script only. |
| AS-IS correctness | PASS | Service → policy → rule → actions → script → dynamic HTTPS POST is reconstructed without adding a normal backside call. |
| Evidence certainty preservation | PASS | Confirmed, unresolved, and not-evidenced facts remain distinct. |
| Capability decomposition | PASS | Capabilities are derived from observed listener, policy, script, routing, and TLS evidence. |
| Replacement reasoning | PASS | Requirements follow capability and constraint evidence and are decomposed into solution roles without direct product mapping. |
| Diagram fidelity | PASS | Configured backend is shown as configuration, dynamic script egress as the actual path, and platform references as unresolved. |
| Token/context efficiency | PASS | No full-domain CSV load, no all-service operation scan, no raw CFG read, and no unrelated artifact inspection occurred. |

The qualification is for the hard-coded authentication material and the unscanned executable artifact. These findings do not undermine the Journey reconstruction itself.

