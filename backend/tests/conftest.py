"""Make backend tests independent of provider credentials inherited from the shell.

Pytest imports this file before collecting test modules, so the cleanup happens
before any test can import app and freeze environment-derived settings at
module import time. Tests that intentionally exercise configured providers must
set their own environment explicitly after collection starts.
"""

from __future__ import annotations

import os


# Real-provider credentials and provider-selection knobs that can make tests
# leave the deterministic fallback path merely because a developer's terminal
# happens to be configured. Keep this list limited to provider configuration:
# product/runtime code under backend/app is intentionally untouched.
_INHERITED_PROVIDER_ENV = (
    "DEEPSEEK_API_KEY",
    "OPENAI_API_KEY",
    "CITYNEXUS_AI_API_KEY",
    "CITYNEXUS_AI_ENABLED",
    "CITYNEXUS_AI_PROVIDER",
    "CITYNEXUS_AI_MODEL",
    "CITYNEXUS_AI_VISION_MODEL",
    "CITYNEXUS_HERMES_API_KEY",
    "CITYNEXUS_HERMES_API_SERVER_KEY",
    "CITYNEXUS_HERMES_MODEL",
    "CITYNEXUS_HERMES_NATIVE_PROVIDER",
    "CITYNEXUS_HERMES_NATIVE_MODEL",
)

for _name in _INHERITED_PROVIDER_ENV:
    os.environ.pop(_name, None)

del _name
