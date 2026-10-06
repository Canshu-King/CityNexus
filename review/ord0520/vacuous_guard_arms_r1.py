"""Counterexample arms for the guards: an empty collection must REFUSE, a filled one must pass.

Each guarded r2 file exposes `refuse_when_empty(collection, what)`.  The arms below import those modules
(their real work sits under `if __name__ == "__main__"`, so import runs nothing) and drive the guard
directly:

  * empty input  -> the guard must raise SystemExit with a non-zero code;
  * filled input -> the guard must return quietly (the control, without which "it refused" would also be
    true of a guard that refuses everything, which is a broken instrument rather than a fixed one).

Exit code is non-zero when any arm does not behave, so this file can be the "空输入必须非零" receipt the
block promises.  It prints one line per arm and never asserts a verdict it did not compute.
"""

from __future__ import annotations

import importlib.util
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent


def load(name: str):
    spec = importlib.util.spec_from_file_location(name, HERE / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # safe: both files guard their work behind __main__
    return module


ARMS = [
    {
        "module": "abort_http_probe_r2",
        "what": "the refusal arms recorded over HTTP",
        "empty": {},
        "filled": {"a_refusal": {"http_status": 403, "error_receipt_id": "x"}},
    },
    {
        "module": "abort_glass_provenance_r2",
        "what": "the four provenance checks",
        "empty": [],
        "filled": [{"P1": 1}, {"P2": 1}, {"P3": 1}, {"P4": 1}],
    },
]


def main() -> int:
    failures = []
    for arm in ARMS:
        module = load(arm["module"])
        guard = getattr(module, "refuse_when_empty", None)
        if guard is None:
            failures.append("%s has no guard to drive" % arm["module"])
            print("%-28s NO_GUARD" % arm["module"])
            continue

        refused = False
        try:
            guard(arm["empty"], arm["what"])
        except SystemExit as exc:
            refused = exc.code not in (0, None)
        except Exception as exc:  # noqa: BLE001 -- any other exception is also not a clean refusal
            failures.append("%s raised %s instead of SystemExit" % (arm["module"], type(exc).__name__))
            print("%-28s RAISED_%s" % (arm["module"], type(exc).__name__))
            continue

        allowed = True
        try:
            guard(arm["filled"], arm["what"])
        except SystemExit:
            allowed = False
        except Exception as exc:  # noqa: BLE001
            allowed = False
            failures.append("%s raised %s on a filled input" % (arm["module"], type(exc).__name__))

        verdict = "BITES_AND_ALLOWS" if (refused and allowed) else (
            "DOES_NOT_BITE" if not refused else "REFUSES_EVERYTHING")
        if verdict != "BITES_AND_ALLOWS":
            failures.append("%s -> %s" % (arm["module"], verdict))
        print("%-28s empty_refused=%-5s filled_allowed=%-5s %s"
              % (arm["module"], refused, allowed, verdict))

    # The third site is driven through its own door: a per-state rate computed from a file of lines, so
    # the empty case is an empty file rather than an empty argument.
    flake = load("osmt_flake_attribution_r2")
    workdir = pathlib.Path(__file__).resolve().parent.parent.parent / "tmp"
    workdir.mkdir(parents=True, exist_ok=True)
    empty_file = workdir / "_vacuous_arm_empty_r1.jsonl"
    filled_file = workdir / "_vacuous_arm_filled_r1.jsonl"
    empty_file.write_text("", encoding="utf-8")
    filled_file.write_text(
        '{"state": "patched", "failed": ["x"], "family_red": true}\n'
        '{"state": "tip_bytes", "failed": [], "family_red": false}\n',
        encoding="utf-8",
    )
    refused = False
    try:
        flake.per_state(empty_file, ["test_x"])
    except SystemExit as exc:
        refused = exc.code not in (0, None)
    except Exception as exc:  # noqa: BLE001
        failures.append("osmt_flake_attribution_r2 raised %s on an empty file" % type(exc).__name__)
    allowed = True
    try:
        block = flake.per_state(filled_file, ["test_x"])
        allowed = isinstance(block, dict) and block.get("patched", {}).get("batches") == 1
    except SystemExit:
        allowed = False
    except Exception as exc:  # noqa: BLE001
        allowed = False
        failures.append("osmt_flake_attribution_r2 raised %s on a filled file" % type(exc).__name__)
    verdict = "BITES_AND_ALLOWS" if (refused and allowed) else (
        "DOES_NOT_BITE" if not refused else "REFUSES_EVERYTHING")
    if verdict != "BITES_AND_ALLOWS":
        failures.append("osmt_flake_attribution_r2 -> %s" % verdict)
    print("%-28s empty_refused=%-5s filled_allowed=%-5s %s"
          % ("osmt_flake_attribution_r2", refused, allowed, verdict))
    for path in (empty_file, filled_file):
        path.unlink(missing_ok=True)

    print("VERDICT %s" % ("ALL_GUARDS_BITE_AND_ALLOW" if not failures else "ARM_FAILED"))
    for line in failures:
        print("FAIL %s" % line)
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
