DataPower Taxonomies V2
======================

Files:
- datapower_properties.yaml
- reference_types.yaml
- relationship_types.yaml
- endpoint_types.yaml
- cross_taxonomy.yaml

Assumed companion files:
- datapower_objects.yaml (V2 clean version created previously)
- file_types.yaml (frozen)
- sensitivity.yaml (frozen)

Important:
This package is intentionally evidence-driven. It covers the high-confidence
object/property chains needed for reference and relationship extraction.
Unknown/unmapped properties must remain preserved in raw parser output and
must not generate graph edges until a verified cross-taxonomy mapping exists.
