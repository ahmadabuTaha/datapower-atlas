# DataPower Atlas
<img src="image/cover.jpg" width="50%" >



**Evidence-driven architecture reconstruction for IBM DataPower modernization.**

> DataPower Atlas is an evidence-first DataPower architecture reconstruction framework. It converts raw IBM DataPower exports into structured, traceable AS-IS evidence such as service and operation journeys, dependency maps, endpoint and file resolution, findings, and capability analysis. It preserves raw-source authority, distinguishes confirmed vs unresolved facts, keeps domain boundaries isolated, and follows a reproducible pipeline so modernization analysis is based on what the configuration actually proves—not on assumptions, cleaned-up views, or product-driven shortcuts.
------------------------------------------------------------------------

## Components and Elements

| Component | Details |
|-----------|---------|
| taxonomy | Helps identify DataPower objects, how they map to one another, the files they use, and how they are called by each object. For more information, see [Datapower Objects , Taxonomies and Relations](taxonomy/README.md).|
| skills | Contains skills organized in a `Funnel Pattern`. The master skill narrows the inputs for subsequent skills, saving tokens while improving answer accuracy. |
| docs | Contains common skills used across the other skills. |
| tools | Contains scripts and tools for parsing DataPower exports and indexing objects, relationships, files, services, operations, and user journeys. For more information, see [Tools and Scripts](tools/README.md). |
| usecases | Contains use cases and guidance for agents, providing consistent prompts for AS-IS and to-be assessments. For more information, see [use cases](usescases/README.md). |
| AGENTS.md | The master file for orchestrating all skills to produce the AS-IS architecture. |


For More Details about the DataPower Atlas,  see [DataPower Atlas - Operating Model and Guidlines ](guidelines/moredetails.md).
