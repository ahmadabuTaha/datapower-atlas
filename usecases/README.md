# Use Case Prompts

The Markdown documents in this folder establish the as-is phases.

## DataPower As-Is Reconstruction: Five-Phase Summary

The five-phase approach transforms raw DataPower configuration evidence into a traceable enterprise architecture baseline, suitable for modernization and future to-be design.

| Phase | Purpose | Key outcome |
|---|---|---|
| 1. Service and Operation Catalog | Establish what exists | 193 services, 617 operations, and 614 distinct operation patterns |
| 2. User Journey Reconstruction | Understand how services and operations behave | 193 service journeys, 86 operation-pattern journeys, and 279 journey documents |
| 3. Enterprise Context View | Understand connectivity and architectural context | Ingress, routing, destinations, dependencies, integration patterns, and evidence gaps |
| 4. Capability Map | Identify the capabilities DataPower provides in this estate | 6 capability domains, 17 capabilities, and 28 functions |
| 5. As-Is Consolidation | Produce the authoritative architecture baseline and to-be handoff | Canonical as-is facts, summary, unresolved register, and modernization input |

## Phase 1 — Service and Operation Catalog

Phase 1 established the structural inventory of the DataPower estate. It identified DataPower services and distinguished service-level objects from the business or API operations they expose.

The frozen baseline contains 193 services, 617 operations, and 614 distinct operation patterns. This phase provides the identity and catalog foundation for every subsequent phase.

**Core question:** What exists in the DataPower estate?

## Phase 2 — User Journey Reconstruction

Phase 2 reconstructed how requests are processed through DataPower. The canonical journey model follows this sequence:

1. Domain
2. Service
3. Operation
4. Match
5. Processing policy
6. Rule
7. Ordered actions
8. Referenced artifact
9. Extracted behavior
10. Routing decision
11. Actual egress

This phase produced 193 service journeys and 86 focused operation-pattern journey documents, for a total of 279 journey documents representing the 617 cataloged operations.

It also preserves important distinctions, such as configured backend versus actual egress, and recognizes that outbound communication can occur within processing logic such as GatewayScript or XSLT.

**Core question:** How does each service or operation work?

## Phase 3 — Enterprise Context View

Phase 3 expanded the analysis from internal DataPower processing to the enterprise integration context surrounding DataPower. It consolidated ingress boundaries, configured destinations, confirmed actual egress, runtime-computed destinations, integration patterns, security dependencies, infrastructure dependencies, and unresolved external identities.

For example, the analysis identified 425 confirmed actual-egress relationships, 83 unique confirmed immediate destinations, 120 unique configured destinations, and 200 destination registry entries.

However, the evidence did not establish the business identities of those remote systems. Therefore, the number of confirmed external-system identities remains zero; identities were not inferred from technical names.

**Core question:** Where does DataPower sit in the current enterprise integration landscape, and what does it communicate with?

## Phase 4 — DataPower Capability Map

Phase 4 translated technical implementation evidence into an architecture capability model. Rather than documenting generic IBM DataPower product features, it identified only capabilities demonstrated by the current estate.

The resulting model contains:

- 6 capability domains
- 17 capabilities
- 28 capability functions
- 12 capability dependencies

The six domains are:

1. Traffic Exposure
2. Processing and Mediation
3. Routing and Flow Control
4. Integration Connectivity
5. Security and Cryptographic Configuration
6. Runtime Dependencies

The capability model represents all 193 services and 617 operations.

This phase is especially important for modernization. Instead of asking, “Which DataPower product features must we replace?”, future architecture analysis can ask, “Which evidenced enterprise capabilities must the future architecture provide, redesign, relocate, or deliberately retire?”

**Core question:** What architectural capabilities does the current DataPower estate provide?

## Phase 5 — As-Is Consolidation and To-Be Handoff

Phase 5 consolidated the previous four frozen phases into the authoritative as-is architecture baseline.

Its canonical entry point is:

`outputs/as-is/05-as-is-pack/AS-IS-FACTS.json`

The baseline has three human-readable views:

- `AS-IS-SUMMARY.md`
- `AS-IS-UNRESOLVED.md`
- `TO-BE-INPUT.md`

`AS-IS-UNRESOLVED.md` deliberately preserves evidence gaps rather than hiding them or making assumptions. Examples include 49 operations for which actual egress is not evidenced, 34 runtime-computed targets, 421 unresolved artifact references, and 200 destinations whose remote-system identities are not evidenced.

`TO-BE-INPUT.md` provides the formal bridge to modernization without prematurely selecting technologies or designing the future state.

Phase 5 passed all 33 validation gates, with deterministic, byte-identical regeneration.

**Core question:** What do we know definitively about the current architecture, what remains unresolved, and what must future modernization analysis consider?

## Overall Architecture Flow

```text
Raw DataPower Evidence
        │
        ▼
┌──────────────────────────────┐
│ Phase 1 — WHAT EXISTS        │
│ Services and Operations      │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ Phase 2 — HOW IT WORKS       │
│ User Journeys and Behavior   │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ Phase 3 — WHERE IT CONNECTS  │
│ Enterprise Context           │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ Phase 4 — WHAT IT PROVIDES   │
│ Capabilities and Functions   │
└──────────────┬───────────────┘
               ▼
┌──────────────────────────────┐
│ Phase 5 — WHAT WE KNOW       │
│ Canonical As-Is Baseline     │
└──────────────┬───────────────┘
               ▼
        AS-IS COMPLETE
               │
               ▼
         To-Be Analysis
```

The main achievement is the transition from configuration analysis to architectural knowledge. The final as-is baseline is traceable, evidence-driven, deterministic, and explicit about uncertainty. It is structured so that future to-be analysis can begin with capabilities and requirements rather than rediscovering DataPower configuration.