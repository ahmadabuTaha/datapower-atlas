#!/usr/bin/env python3
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


class DuplicateKeyError(ValueError):
    pass


class UniqueKeyLoader(yaml.SafeLoader):
    """YAML loader that fails on duplicate mapping keys."""


def _construct_mapping(
    loader: UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            mark = key_node.start_mark
            raise DuplicateKeyError(
                f"Duplicate YAML key {key!r} at "
                f"line {mark.line + 1}, column {mark.column + 1}"
            )
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True)
class TaxonomyBundle:
    root: Path
    file_types: Dict[str, Any]
    datapower_objects: Dict[str, Any]
    sensitivity: Dict[str, Any]
    datapower_properties: Dict[str, Any]
    reference_types: Dict[str, Any]
    relationship_types: Dict[str, Any]
    endpoint_types: Dict[str, Any]
    cross_taxonomy: Dict[str, Any]


EXPECTED_FILES = {
    "file_types": "file_types.yaml",
    "datapower_objects": "datapower_objects.yaml",
    "sensitivity": "sensitivity.yaml",
    "datapower_properties": "datapower_properties.yaml",
    "reference_types": "reference_types.yaml",
    "relationship_types": "relationship_types.yaml",
    "endpoint_types": "endpoint_types.yaml",
    "cross_taxonomy": "cross_taxonomy.yaml",
}


def load_yaml(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Missing taxonomy file: {path}")

    text = path.read_text(encoding="utf-8")
    data = yaml.load(text, Loader=UniqueKeyLoader)

    if data is None:
        raise ValueError(f"Empty YAML document: {path}")
    if not isinstance(data, dict):
        raise TypeError(
            f"Top-level YAML document must be a mapping: {path}"
        )

    return data


def load_taxonomies(root: str | Path = "taxonomy") -> TaxonomyBundle:
    root = Path(root).resolve()

    loaded = {
        name: load_yaml(root / filename)
        for name, filename in EXPECTED_FILES.items()
    }

    return TaxonomyBundle(
        root=root,
        file_types=loaded["file_types"],
        datapower_objects=loaded["datapower_objects"],
        sensitivity=loaded["sensitivity"],
        datapower_properties=loaded["datapower_properties"],
        reference_types=loaded["reference_types"],
        relationship_types=loaded["relationship_types"],
        endpoint_types=loaded["endpoint_types"],
        cross_taxonomy=loaded["cross_taxonomy"],
    )


def get_mapping(
    data: Dict[str, Any],
    key: str,
    source_name: str,
) -> Dict[str, Any]:
    value = data.get(key)
    if value is None:
        raise KeyError(
            f"{source_name}: missing required top-level key {key!r}"
        )
    if not isinstance(value, dict):
        raise TypeError(
            f"{source_name}.{key}: expected mapping, "
            f"got {type(value).__name__}"
        )
    return value


def as_list(value: Any) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]
