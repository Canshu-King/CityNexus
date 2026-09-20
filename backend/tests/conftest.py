"""Process-wide opt-in for the doors that are now simulation-gated (ORD-0058),
plus a hygiene pass that makes the suite independent of the developer's shell (ORD-AR1).

`POST /api/v1/demo/reset` deletes 52 tables and refuses a caller that has not claimed the
stage, which is right in production and is also what roughly thirty test modules use as
their fixture door.  Rather than have those modules grow a flag each (or, worse, have the
guard quietly fail open), the test process declares itself a simulation once, here, before
`app.main` reads the setting.

This is deliberately not a change to the product default: run the app without this and the
reset route is a 403, which is the behaviour the order asked for and which
`test_qoder_simulation_mode.py` pins in both states.

The second half is the arbiter's ORD-AR1 fix, merged rather than dropped-in: pytest imports
this file before collecting test modules, so provider cleanup happens before any test can
import `app` and freeze environment-derived settings at module import time.  Without it, a
terminal that happens to export a real key flips the whole "no provider configured -> use the
deterministic fallback" family onto the network path, which is how a green suite turned into
33/13 phantom failures twice tonight.  Tests that intentionally exercise configured providers
must set their own environment explicitly after collection starts.

MERGE NOTE (Commander, measured): the arbiter's branch version of this file does NOT contain
the `CITYNEXUS_DEMO_MODE` line, and the authoritative version does not contain the credential
list.  Overwriting either side wholesale would either re-lock the 140 test modules that use
`/demo/reset` as their fixture door, or leave the suite credential-dependent.  Both halves
have to survive in one file.
"""

from __future__ import annotations

import os

os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")

# Real-provider credentials and provider-selection knobs that can make tests leave the
# deterministic fallback path merely because a developer's terminal happens to be configured.
# Keep this list limited to provider configuration: product/runtime code under backend/app is
# intentionally untouched.
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
