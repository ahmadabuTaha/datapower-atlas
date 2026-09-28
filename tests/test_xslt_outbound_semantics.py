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


operation_builder = load_module("build_operation_journeys", "tools/build_operation_journeys.py")
service_builder = load_module("build_datapower_service_journeys", "tools/build_datapower_service_journeys.py")


class XsltOutboundSemanticTests(unittest.TestCase):
    def extract_with_both_builders(self, text: str):
        path = Path("artifact.xsl")
        file_row = {"source_object_id": "action-1"}
        return [
            module.extract_xslt_outbound_semantic_facts(text, path, file_row)
            for module in (operation_builder, service_builder)
        ]

    def test_namespace_uris_and_payload_url_open_are_not_egress(self):
        text = '''<xsl:stylesheet
          xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
          xmlns:dp="http://www.datapower.com/extensions" version="1.0">
          <xsl:template match="/"><url-open><response/></url-open></xsl:template>
        </xsl:stylesheet>'''
        for facts in self.extract_with_both_builders(text):
            self.assertEqual(facts, [])

    def test_literal_dp_url_open_preserves_non_http_protocol(self):
        text = '''<xsl:stylesheet
          xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
          xmlns:dp="http://www.datapower.com/extensions" version="1.0">
          <xsl:template match="/">
            <dp:url-open target="'dpmq://QM/?RequestQueue=OUT'"/>
          </xsl:template>
        </xsl:stylesheet>'''
        for facts in self.extract_with_both_builders(text):
            self.assertEqual(len(facts), 1)
            self.assertEqual(facts[0]["fact_type"], "outbound_request")
            self.assertEqual(facts[0]["protocol"], "dpmq")
            self.assertEqual(facts[0]["targets"], ["dpmq://QM/?RequestQueue=OUT"])

    def test_literal_variable_target_is_resolved(self):
        text = '''<xsl:stylesheet
          xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
          xmlns:dp="http://www.datapower.com/extensions" version="1.0">
          <xsl:variable name="MqUrl" select="'dpmq://IssueContract_QMGR/?RequestQueue=ESB.HRSD.CONTCRT.OUT'"/>
          <xsl:template match="/"><dp:url-open target="{$MqUrl}"/></xsl:template>
        </xsl:stylesheet>'''
        for facts in self.extract_with_both_builders(text):
            self.assertEqual(facts[0]["protocol"], "dpmq")
            self.assertEqual(
                facts[0]["targets"],
                ["dpmq://IssueContract_QMGR/?RequestQueue=ESB.HRSD.CONTCRT.OUT"],
            )

    def test_unresolved_variable_target_remains_dynamic(self):
        text = '''<xsl:stylesheet
          xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
          xmlns:dp="http://www.datapower.com/extensions" version="1.0">
          <xsl:template match="/"><dp:url-open target="{$runtimeTarget}"/></xsl:template>
        </xsl:stylesheet>'''
        for facts in self.extract_with_both_builders(text):
            self.assertEqual(facts[0]["targets"], [])
            self.assertEqual(facts[0]["protocol"], "dynamic")
            self.assertEqual(facts[0]["destination_type"], "dynamic_or_runtime_computed")
            self.assertEqual(facts[0]["dynamic_components"], ["$runtimeTarget"])


if __name__ == "__main__":
    unittest.main()
