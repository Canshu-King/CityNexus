"""Process-wide opt-in for the doors that are now simulation-gated (ORD-0058).

`POST /api/v1/demo/reset` deletes 52 tables and refuses a caller that has not claimed the
stage, which is right in production and is also what roughly thirty test modules use as
their fixture door.  Rather than have those modules grow a flag each (or, worse, have the
guard quietly fail open), the test process declares itself a simulation once, here, before
`app.main` reads the setting.

This is deliberately not a change to the product default: run the app without this and the
reset route is a 403, which is the behaviour the order asked for and which
`test_qoder_simulation_mode.py` pins in both states.
"""

from __future__ import annotations

import os

os.environ.setdefault("CITYNEXUS_DEMO_MODE", "true")
