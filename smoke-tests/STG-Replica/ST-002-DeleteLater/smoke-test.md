# ST-002 — STG-Replica DeleteLater

## 1. Selected Service

- **Environment:** `STG`
- **Domain:** `STG-Replica`
- **Service:** `DeleteLater`
- **Canonical type:** `multi_protocol_gateway`
- **Service ID:** `obj:STG:multi_protocol_gateway:DeleteLater`
- **Overall result:** `PASS_WITH_FINDINGS`

The compact STG-Replica Journey enumeration contains three services. `DeleteLater` was selected because it is one of the two smaller 79-operation services rather than the 129-operation maximum, while still exercising ingress, a large evidence-backed processing policy, XSLT database calls, one GatewayScript HTTP call, dynamic routing, a configured backend, skip-backside, shared/default runtime objects, resolved local artifacts, and unresolved platform resources.

The logical name is not treated as lifecycle evidence. Nothing in the retrieved evidence proves that the service is temporary, retired, orphaned, or unused.

## 2. AS-IS Trace

### Service-level path

```text
HTTP handler 8679
→ DeleteLater MPGW
→ GetUserEstablishmentsQuery_Service_V2_ProcessingPolicy
→ 79 explicit match/rule paths
→ 234 processing actions
→ operation-scoped XSLT or GatewayScript behavior
```

Structural evidence:

| Item | Result | Certainty |
|---|---:|---|
| Graph nodes / edges | `396 / 396` | confirmed |
| Processing policy relationships | `1` | confirmed |
| Match relationships | `79` | confirmed |
| Processing-rule relationships | `79` | confirmed |
| Processing actions | `234` | confirmed |
| Operation Journeys | `79` | confirmed |
| Missing processing rules | `0` | confirmed |

The operation count is supported by explicit policy, match, rule, and action relationships. It is not treated as traversal duplication.

### Ingress and shared/default dependencies

| Dependency | Result | Certainty |
|---|---|---|
| HTTP front-side handler `8679` | Resolved locally | confirmed |
| XML Manager `default` | Resolved locally in STG-Replica | confirmed |
| User Agent `default` | Resolved locally in STG-Replica | confirmed |
| TLS/crypto relationship | None in the selected service graph | not_evidenced |

The shared names `default` are valid resolved configuration. They are neither gaps nor cross-domain resolutions. HTTPS syntax establishes encrypted transport intent for the relevant destinations, but no TLS handshake success, client certificate, mTLS, trust configuration, or crypto dependency is inferred.

### Routing and operation distribution

- **Backend mode:** `dynamic`, confirmed from `type = dynamic-backend`.
- **Configured backend:** `https://10.240.169.62:5058/`, confirmed configuration.
- **Route action:** not evidenced.
- **Service-level skip-backside:** `true`, confirmed from 77 operation paths.
- **Remote system identity/topology:** not evidenced.

Operation-level actual egress:

| Classification | Operations | Meaning |
|---|---:|---|
| Confirmed database egress | 76 | Resolved XSLT contains `dp:sql-execute`. |
| Confirmed GatewayScript HTTP egress | 1 | Resolved script contains dynamic `urlopen.open` POST. |
| Candidate configured backside | 2 | Backend is configured, but these response/error operations do not prove invocation. |
| Unresolved | 0 | No operation-specific route reference is unresolved. |
| Not evidenced | 0 | The two otherwise non-outbound operations retain candidate—not confirmed—configured backside evidence. |

The configured backend is not promoted to confirmed execution for any operation lacking operation-level proof. It is also not drawn as an additional call for the 77 operations with explicit XSLT/GatewayScript egress.

### Representative database operation

```text
Qiwa_Insert_UnifiedNumber-Match
→ Qiwa_Insert_UnifiedNumber_Policy_rule_188
→ Qiwa_Insert_UnifiedNumber_Policy_rule_188_xform_1
→ local:///MOL_SPs_Ext/Qiwa_Insert_UnifiedNumber.xsl
→ dp:sql-execute('MOL_Generation_phaseI', $sqlString)
```

- **Operation:** `op:STG:STG-Replica:701ac6af345dc483eeca`
- **Mechanism:** `datapower_sql` / database
- **Datasource:** `MOL_Generation_phaseI`
- **Datasource type:** literal
- **Statement:** `$sqlString`
- **Statement type:** computed
- **Source line:** XSLT line `54`
- **Certainty:** confirmed

The logical datasource proves an outbound database interaction. It does not identify a database host, port, instance, owner system, or network topology.

Across all 76 database operations, seven exact logical datasource identifiers occur:

- `MOL_Generation_phaseI` — 57 operations
- `MOL_Nitaqat_III` — 10
- `MOL_Generation_phaseI_WriteNode` — 5
- `TST_Qiwa_GetEstablishmentAllData` — 1
- `MOL_Generation_phaseI_127` — 1
- `HRSDDPtoHRSDDB_ReadOnly` — 1
- `MOL_Main_STG` — 1

These identifiers are preserved exactly and are not interpreted as network endpoints or remote-system identities.

### Representative GatewayScript operation

```text
WPSSaudizationCertificate_Match
→ QiwatoHRSDRouter_WPSSaudizationCertificate_rule_25
→ GatewayScript action
→ local:///WPS/WPS.JS
→ POST https://api.qiwa.uat.info + var://service/URI
```

- **Operation:** `op:STG:STG-Replica:530233e89e3bee879d12`
- **Mechanism:** GatewayScript `urlopen.open`
- **Method:** `POST`
- **Base target:** `https://api.qiwa.uat.info`
- **Dynamic component:** `var://service/URI`
- **Certainty:** confirmed

The destination remains dynamic; the base URL is not reported as the complete runtime URL. The hostname does not establish a remote business-system identity or topology.

### Candidate response/error paths

Two operations do not contain explicit outbound behavior:

1. `GetUserEstablishmentsQuery_Service_V2_ProcessingPolicy_RespRule`
   - resolves `local:///NonXMLProcessing.xsl`;
   - the stylesheet processes DataPower error variables and rejects/parses content;
   - no outbound construct is present.
2. `GetUserEstablishmentsQuery_Service_V2_ProcessingPolicy_ErrorRule`
   - contains only a results action;
   - no operation-specific executable reference exists.

For both, `skip-backside` is not evidenced and the configured backend is retained only as `candidate`. Runtime invocation is not asserted.

### Artifact resolution

Service-level resolved references:

- `77` XSLT records representing `76` distinct XSLT artifacts;
- `1` GatewayScript record;
- `78` resolved records / `77` distinct artifacts total.

Unresolved platform references:

- `store:///filter-reject-all.xsl`
- `store:///identity.xsl`

These are explicit references owned by the processing policy. They remain unresolved without being labeled deployment failures.

### Provenance

- Journey environment/domain: `STG / STG-Replica`
- Source configuration: `export-stg-uat/extracted/STG-Replica/config/STG-Replica.cfg`
- Domain-consistency status: `consistent`
- All 79 operation provenance states: `consistent`
- Front-side handler: CFG line `22369`
- XML Manager: CFG line `22370`
- Configured backend: CFG line `22374`
- Processing policy: CFG line `22456`
- Dynamic backend: CFG line `22457`

The `obj:STG:...` object-ID prefix is consistent with the `environment=STG` identity dimension and does not contradict `domain=STG-Replica`. No STG-domain record was used.

## 3. Capability Analysis

| Observed capability | Strength | Evidence | Constraint / note |
|---|---|---|---|
| HTTP service ingress | DIRECT | Resolved HTTP front-side handler | Listener address and port are not materialized in this Journey. |
| Policy-based operation dispatch | DIRECT | 79 match/rule paths and 234 actions | Large policy is an architectural concentration, not a traversal defect. |
| XSLT execution | DIRECT | 77 resolved XSLT references | XSLT is executable behavior, not merely a file dependency. |
| Database integration | DIRECT | 76 operation-scoped `dp:sql-execute` facts | Logical datasource is known; network destination is not. |
| Computed SQL/request construction | DIRECT | `$sqlString` passed by all 76 database facts | SQL meaning is operation-specific and should not be inferred from names alone. |
| GatewayScript execution | DIRECT | Resolved `local:///WPS/WPS.JS` | One operation uses scripted mediation. |
| Dynamic outbound HTTPS integration | DIRECT | `urlopen.open`, POST, base URL + `var://service/URI` | Final URL remains runtime-computed. |
| Backside-bypass route control | DIRECT | 77 operations set skip-backside | Not evidenced for the two response/error rules. |
| Candidate configured backside behavior | DIRECT evidence of uncertainty | Two operations retain configured backend without execution proof | Must remain candidate. |
| Shared XML runtime dependency | DIRECT | Local `default` XML Manager and User Agent relationships | Shared naming is valid resolved configuration. |
| Error/response content processing | DIRECT | `NonXMLProcessing.xsl` reads DataPower error variables | No outbound interaction is evidenced from that stylesheet. |
| Executable artifact dependency management | DIRECT | 78 resolved executable references | Deployment and version traceability are required. |

Not evidenced and therefore not claimed: authentication/authorization policy, TLS client profile, client certificates, mTLS, database topology, remote system ownership, observability, retry policy, throughput, latency, HA, or runtime success.

## 4. Replacement Requirements / Solution Roles

| Current function | Capability | Evidenced constraint / NFR | Replacement requirement | Solution role |
|---|---|---|---|---|
| HTTP handler | HTTP ingress | Preserve current request entry; listener details remain open | Accept and route the existing HTTP request contract | Ingress / API gateway role |
| 79-rule processing policy | Policy dispatch and orchestration | High configuration concentration and operation-specific behavior | Preserve deterministic match/rule/action selection with operation-level traceability and testing | Policy/orchestration role |
| XSLT `dp:sql-execute` | Database integration | Seven logical datasource identifiers; physical endpoints unknown | Execute equivalent parameterized/computed database interactions through governed datasource configuration | Database integration/runtime role |
| Computed `$sqlString` | Dynamic database request construction | Statements are computed and operation-specific | Preserve required statement construction safely and test equivalence per operation | Integration/transformation role |
| GatewayScript `urlopen.open` | Dynamic HTTPS integration | Runtime URI component must remain dynamic | Support outbound POST/JSON behavior and runtime URL construction without converting it to a static endpoint | HTTP integration client role |
| `skip-backside` | Explicit route control | Applies to 77 operations, not all 79 | Support per-operation bypass/routing semantics rather than one service-wide assumption | Gateway policy role |
| Configured backend candidate | Conditional/uncertain backside path | Invocation is not proven for response/error rules | Preserve the configuration distinction and validate required runtime behavior before migration | Migration validation responsibility |
| Default XML Manager/User Agent | Shared XML runtime dependency | Shared local objects are valid configuration | Provide equivalent parsing/runtime behavior only to the extent confirmed by configuration and tests | XML processing/runtime role |
| Local XSLT and GatewayScript files | Executable artifact management | 77 distinct executable artifacts | Provide versioned deployment, provenance, rollback, and operation-to-artifact traceability | Delivery/runtime governance role |
| Sensitive authentication header in WPS script | Credential injection | Sensitive-looking value is embedded in source and omitted here | Externalize, protect, rotate, and inject equivalent credentials | Secrets-management role |

No replacement product is selected. The evidence supports multiple solution roles, which may or may not be implemented by one platform.

Open replacement questions:

- What physical database endpoints and connection/security characteristics sit behind each logical datasource?
- Which of the two candidate backside paths, if any, actually executes at runtime?
- What listener address/port and external client contract must be preserved?
- What TLS trust, certificate, and client-authentication requirements apply to the HTTPS paths?
- What availability, throughput, latency, retry, transaction, and recovery requirements apply?
- Which `store:///` behaviors require explicit equivalents outside DataPower?

## 5. Findings / Evidence Gaps

### ARCHITECTURAL_HOTSPOT — Mega Policy concentration

The 79 operations and 393 processing relationships are evidence-backed. The concentration increases migration and test scope but is not a parser/traversal defect and does not prove runtime failure.

### FINDING — service name is not lifecycle evidence

`DeleteLater` is retained as the configured logical name. No retirement, temporary status, or lack of use is inferred.

### FINDING — configured backend differs from actual evidenced egress

The configured URL `https://10.240.169.62:5058/` is confirmed configuration. Seventy-seven operations instead contain explicit database or GatewayScript outbound behavior. The two response/error operations retain the configured URL only as a candidate execution path.

### GAP — mixed service-egress aggregation

The service bundle contains 76 database semantic facts and one GatewayScript HTTP semantic fact and marks `script_mediated=true`, but service-level `actual_egress` contains only the database mechanism and database targets. Operation Journeys correctly preserve all 77 confirmed paths. This is classified as a forward service-aggregation coverage gap; no pipeline code is changed during ST-002.

The `actual_egress.mechanism` field also differs in shape between database (`"database"`) and GatewayScript (`["gatewayscript"]`) operation records. The meaning is recoverable, but the output shape is not fully uniform.

### GAP — executable artifact sensitivity coverage

`local/WPS/WPS.JS` contains a hard-coded authentication header value, intentionally omitted here. Its file inventory row reports `sensitivity_scan_status=not_scanned`, and no sensitivity finding exists. This requires focused validation but does not yet prove a sensitivity-scanner logic defect.

### EXPECTED_UNRESOLVED — platform XSLTs

The two `store:///` references remain unresolved platform/shared-resource evidence. They are not treated as absent references or failed deployment.

### Evidence gaps retained

- physical database hosts, ports, instances, and topology;
- remote business-system identities;
- TLS/crypto configuration and runtime handshake outcome;
- runtime use of the two candidate backside paths;
- performance, availability, and operational NFRs.

## 6. Smoke-Test Verdict

**PASS_WITH_FINDINGS**

| Test dimension | Result | Rationale |
|---|---|---|
| User Journey-first retrieval | PASS | Selection and reconstruction began with the three-row service summary and exact service bundle. |
| Retrieval discipline | PASS | Only the selected service's 79 operations were aggregated; three representative operation records and their artifacts were inspected in detail. |
| AS-IS correctness | PASS | All 79 match/rule paths and 234 actions are preserved without shrinking the Mega Policy. |
| Shared/default interpretation | PASS | Local default XML Manager and User Agent are treated as valid resolved dependencies. |
| Routing correctness | PASS | Database, GatewayScript, candidate backside, and configured backend states remain distinct. |
| Evidence certainty preservation | PASS | Confirmed and candidate routes, unresolved platform files, and not-evidenced topology remain separate. |
| Capability decomposition | PASS | Capabilities derive from explicit operation behavior rather than object or datasource names. |
| Replacement reasoning | PASS | Requirements follow capability and constraint evidence and are decomposed into solution roles. |
| Diagram fidelity | PASS | The diagram summarizes the Mega Policy, separates actual paths from configured/candidate backside, and preserves unresolved links. |
| Context/token efficiency | PASS | No STG comparison, full CFG read, whole-domain CSV reconstruction, or unrelated artifact scan occurred. |

The findings concern service-level mixed-egress aggregation, mechanism-field consistency, sensitivity coverage, and known architectural concentration. They do not invalidate the operation-level reconstruction.

