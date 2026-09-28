from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


quality = load_module("analyze_journey_quality", "tools/analyze_journey_quality.py")
renderer = load_module("render_user_journeys", "tools/render_user_journeys.py")


class TcpDirectStateTests(unittest.TestCase):
    def test_current_nested_representation_is_complete(self):
        journey = {
            "tcp_proxy_direct": {
                "ingress": [{"listen_address": "0.0.0.0", "listen_port": "7012"}],
                "egress": [{"host": "10.0.0.2", "port": "5059"}],
            }
        }
        self.assertEqual(
            quality.tcp_direct_state(journey),
            {"present": True, "has_ingress": True, "has_egress": True, "complete": True},
        )

    def test_legacy_flat_representation_remains_supported(self):
        journey = {
            "tcp_proxy_direct": {
                "local_address": "0.0.0.0",
                "local_port": "7012",
                "destination_address": "10.0.0.2",
                "destination_port": "5059",
            }
        }
        self.assertTrue(quality.tcp_direct_state(journey)["complete"])


class OperationGroupingTests(unittest.TestCase):
    def test_different_request_paths_share_a_material_behavior_signature(self):
        props = {
            "rule-a": [{"property_name": "type", "property_value": "request-rule"}],
            "rule-b": [{"property_name": "type", "property_value": "request-rule"}],
            "match-a": [{"property_name": "urlmatch", "property_value": '"/a"'}],
            "match-b": [{"property_name": "urlmatch", "property_value": '"/b"'}],
            "action-a": [{"property_name": "type", "property_value": "results"}],
            "action-b": [{"property_name": "type", "property_value": "results"}],
        }
        base = {
            "action_names": ["action"],
            "dependencies": {"resolved": [], "unresolved": []},
            "file_resolution": {"resolved": [], "unresolved": []},
            "routing": {},
            "semantic_facts": [],
        }
        first = {**base, "processing_rule_id": "rule-a", "matching_rule_ids": ["match-a"], "action_ids": ["action-a"]}
        second = {**base, "processing_rule_id": "rule-b", "matching_rule_ids": ["match-b"], "action_ids": ["action-b"]}
        self.assertEqual(renderer.operation_signature(first, props), renderer.operation_signature(second, props))


if __name__ == "__main__":
    unittest.main()
