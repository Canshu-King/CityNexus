"""No-network checks for wb2api->Hermes environment configuration.

Run locally:
    py -3.13 -m unittest discover -s trial -p "test_wb2api_agent.py"
"""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from wb2api_agent import agent_settings, read_key_file


class TestWb2ApiAgentSettings(unittest.TestCase):
    def test_free_router_routes_only_auto_cheapest(self):
        with patch.dict(os.environ, {"WB2API_KEY": "local-fixture-key"}):
            configured, identity = agent_settings()
        self.assertEqual(identity, "wb2api-free-router")
        self.assertEqual(configured["CITYNEXUS_HERMES_API_URL"],
                         "http://127.0.0.1:7865/v1/chat/completions")
        self.assertEqual(configured["CITYNEXUS_HERMES_MODEL"], "auto:cheapest")
        self.assertEqual(configured["CITYNEXUS_HERMES_MODEL_FALLBACKS"], "")
        self.assertEqual(configured["CITYNEXUS_HERMES_API_KEY"], "local-fixture-key")
        self.assertEqual(configured["CITYNEXUS_AI_ENABLED"], "true")
        self.assertEqual(configured["CITYNEXUS_GUARDIAN_AUTORUN"], "false")
        self.assertEqual(configured["CITYNEXUS_PAYMENT_PROVIDER"], "mock-payment")
        self.assertNotIn("OPENAI_API_KEY", configured)

    def test_explicit_7863_target_is_not_sent_to_7865(self):
        with patch.dict(os.environ, {"WB2API_KEY": "local-fixture-key"}):
            configured, identity = agent_settings(direct_model="global:deepseek-v4.1-flash")
        self.assertEqual(identity, "wb2api-direct")
        self.assertEqual(configured["CITYNEXUS_HERMES_API_URL"],
                         "http://127.0.0.1:7863/v1/chat/completions")
        self.assertEqual(configured["CITYNEXUS_HERMES_MODEL"], "global:deepseek-v4.1-flash")

    def test_rejects_forged_direct_model_and_url(self):
        with patch.dict(os.environ, {"WB2API_KEY": "local-fixture-key"}):
            for model in ("auto:cheapest", "other:model", "http://evil.invalid/x", "", "cn:model\nSecret: key"):
                with self.subTest(model=model), self.assertRaises(ValueError):
                    agent_settings(direct_model=model)

    def test_unset_key_fails_closed(self):
        with patch.dict(os.environ, {"WB2API_KEY": ""}):
            with patch("wb2api_agent.getpass.getpass", return_value=""):
                with self.assertRaises(ValueError):
                    agent_settings()

    def test_explicit_guide_key_overrides_unrelated_environment(self):
        with patch.object(Path,"stat",return_value=SimpleNamespace(st_size=100)), \
             patch.object(Path,"read_text",return_value="| **API Key** | `local-fixture-guide-key` |"), \
             patch.dict(os.environ,{"WB2API_KEY":"wrong-fixture-environment"}), \
             patch("wb2api_agent.getpass.getpass") as prompt:
            configured,_=agent_settings(key_file=Path("TEST_FIXTURE.md"))
        self.assertEqual(configured["CITYNEXUS_HERMES_API_KEY"],"local-fixture-guide-key")
        prompt.assert_not_called()

    def test_single_key_and_invalid_documents(self):
        with patch.object(Path,"stat",return_value=SimpleNamespace(st_size=100)):
            with patch.object(Path,"read_text",return_value="local-fixture-plain-key\n"):
                self.assertEqual(read_key_file(Path("TEST_FIXTURE.txt")),"local-fixture-plain-key")
            for text in ('{"api_key":"wrong-field"}',"not a key\nrun something",""):
                with patch.object(Path,"read_text",return_value=text),self.assertRaises(ValueError):
                    read_key_file(Path("TEST_FIXTURE.txt"))


if __name__ == "__main__":
    unittest.main()
