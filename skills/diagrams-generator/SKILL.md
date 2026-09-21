# Skill: generate-architecture-diagrams

Follow `docs/skill-contract.md`.

## Purpose
Generate evidence-based PlantUML diagrams from validated DataPower Atlas outputs.

Supported modes:
- component
- network
- service-journey
- cross-domain

This skill renders architecture already reconstructed. It must not discover, infer, or repair architecture while drawing.

## Core Rule
Evidence first. Diagram second.

If evidence is incomplete, the diagram must preserve that incompleteness.

## Inputs

### Component
- service journeys
- operation summaries
- relationships
- endpoint roles
- security dependencies
- file/script dependencies
- capability summaries

### Network
- Default/appliance analysis
- interfaces
- IPs/subnets
- gateways/routes
- DNS/host aliases
- service endpoints
- validated cross-domain correlations

### Service Journey
- one service trace
- ingress
- processing
- operation summary
- routing
- security/dependencies

### Cross-Domain
- compare-domains output
- correlation candidates
- configuration drift
- shared/default dependency candidates

## Evidence Levels

### Confirmed
Directly supported by validated Atlas or raw evidence.

```plantuml
A --> B : confirmed
```

### Candidate
Supported but not proven.

```plantuml
A ..> B : candidate
```

### Unresolved
Known dependency/path without resolved target.

```plantuml
A ..> B : unresolved
```

Never render candidate or unresolved links as confirmed.

## Component Diagram Rules
Show architecture-significant roles only.

Typical abstraction:

```text
Service
→ Processing
→ Security / Transformation
→ Routing
→ Backend
```

Do not render every low-level DataPower object.

## Network Diagram Rules
May show:
- appliance/interface
- interface IP/subnet
- gateway
- static route
- DNS/host alias
- destination subnet
- known endpoint
- candidate correlation

Do not infer firewall, NAT, tunnel termination, load balancer behavior, or physical topology unless explicitly evidenced.

## Service Journey Rules
Use one service per diagram by default.

Show only evidenced:
- ingress
- service root
- processing
- operation grouping
- routing
- backend
- significant security/file dependencies

For large operation sets, summarize:

```text
Processing Policy
→ N operations
```

Expand selected operations only when requested.

## Cross-Domain Rules
Preserve domain boundaries.

```plantuml
package "STG" { ... }
package "STG-Replica" { ... }
package "DEFAULT" { ... }
```

Cross-domain relationships remain correlation evidence unless explicitly confirmed.

## Output Structure

```text
docs/diagrams/
  component/
  network/
  service/
  cross-domain/
```

Recommended filenames:

```text
component/<domain>-<service>.puml
network/<environment>-datapower-network.puml
service/<domain>-<service>-journey.puml
cross-domain/<environment>-domain-correlation.puml
```

Do not use `_v1`, `_v2`, `_final`, `_fixed`. Git provides version history.

## PlantUML Conventions
Prefer simple portable constructs:
- component
- node
- package
- database
- queue
- cloud
- rectangle
- note

Avoid decorative complexity.

## Provenance
Include compact evidence comments:

```plantuml
' Evidence:
' index/STG/service_journeys.jsonl
' index/STG/relationships.csv
' index/STG/endpoints.csv
```

Do not embed large raw evidence blocks.

## Token Rules
Do:
- consume validated summaries first;
- render one requested scope at a time;
- group repeated components;
- summarize large operation sets;
- reuse existing trace/capability outputs.

Do not:
- reload full CFG;
- reload all domain indexes;
- enumerate every processing action;
- repeat evidence already summarized upstream.

## Few-Shot Scenarios

### Scenario A — Confirmed backend
Evidence: explicit backend endpoint.

```plantuml
component "Service A" as A
component "Backend B" as B
A --> B : confirmed backend
```

### Scenario B — Candidate DEFAULT dependency
Evidence: unresolved locally, matching DEFAULT object exists, correlation not proven.

```plantuml
package "STG" {
  component "Service A" as A
}
package "DEFAULT" {
  component "Shared TLS Profile" as T
}
A ..> T : candidate dependency
```

### Scenario C — Missing backend evidence
Render only the known path.

```plantuml
note right of A
Backend not evidenced
end note
```

Do not invent a backend node.

### Scenario D — Large processing graph
Prefer:

```plantuml
component "Processing Policy\n129 operations" as P
```

instead of drawing every operation.

### Scenario E — Network route
Evidence: interface, gateway, static route.

```plantuml
node "DataPower Appliance" {
  node "eth1\n10.x.x.x/28" as ETH1
}
cloud "Gateway\n10.x.x.1" as GW
cloud "Destination Subnet\n10.y.y.0/24" as DEST

ETH1 --> GW : configured route
GW --> DEST : route evidence
```

Do not invent NAT/firewall/tunnel devices.

## Output Requirements
For each requested diagram produce:
1. `.puml` source
2. concise purpose
3. evidence scope
4. candidate/unresolved links preserved visually
5. no unsupported architecture elements

Do not generate PNG/SVG unless explicitly requested.

## Validation Checklist
Verify:
- every component is evidence-backed;
- every solid link is confirmed;
- candidate links are visually distinct;
- domain boundaries are preserved;
- no backend is inferred;
- no cross-domain auto-resolution occurred;
- large operation sets are summarized;
- provenance is present.

## Final Principle
Render only what Atlas can support.

A diagram must never look more certain than the evidence behind it.
