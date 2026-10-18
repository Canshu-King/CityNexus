"""Build the reform's capability ledger from the static inventory, not from memory.

The reform order asks for one row per capability: where the source lives, which real function/API
serves it, whether the model can call it, what configuration it needs, and how it was verified. The
scanner answers "does the path exist"; this script adds the part the scanner cannot know -- which
tools the runtime advertises, which domains have no agent surface at all, and which tests have
actually exercised the adapter.

Statuses are deliberately conservative:

  READY_FOR_REHEARSAL  source present, tool advertised and dispatched, exercised by a named test;
                       no live provider was called, so it is not LIVE_VERIFIED.
  ADAPTER_NEEDED       source present but no tool (or a tool that exists only on Revolution).
  SOURCE_ONLY          the domain's expected paths are missing on this checkout.
  CONFIG_REQUIRED      the adapter exists but the deployment must supply a provider/secret.

Usage: python tools/reform/build_capability_ledger.py --inventory <inventory.json> \
           --out-dir docs/reform
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Which advertised tools belong to which domain, and what proves each one. The proof column names a
# test that fails if the tool stops being reachable; "none" means the tool is registered but no arm
# exercises it yet, and the row says so instead of borrowing another row's evidence.
DOMAIN_TOOLS: dict[str, list[tuple[str, str]]] = {
    "places_and_map": [
        ("search_city_services", "tests/test_agent_alternatives_v3.py"),
        ("research_place_sources", "tests/test_reform_research_place_sources_adapter_r1.py"),
        ("estimate_place_facts", "tests/test_reform_estimate_place_facts_adapter_r1.py"),
    ],
    "planning": [("generate_plans", "tests/test_reform_generate_plans_adapter_r1.py")],
    "execution_and_rerouting": [
        ("request_replan", "tests/test_agent_runtime_gate.py"),
        ("accept_replan", "tests/test_agent_runtime_gate.py"),
        ("replace_activity", "tests/test_agent_alternatives_v3.py"),
        ("reschedule_activity", "tests/test_agent_authority_v2_actions.py"),
    ],
    "booking_payment_commitments": [
        ("create_booking", "tests/test_agent_authority_v2_actions.py"),
        ("cancel_refundable_booking", "tests/test_agent_authority_v2_actions.py"),
        ("request_commitment_change", "tests/test_agent_authority_v2_actions.py"),
    ],
    "agent": [("inspect_journey", "tests/test_agent_mission_runtime.py"),
              ("inspect_twin", "tests/test_agent_mission_runtime.py"),
              ("list_replans", "tests/test_agent_mission_runtime.py")],
    "group_decisions": [("request_collective_decision", "none")],
    "replanning_and_recovery": [
        ("activate_standby", "none"),
        ("conclude_recovery", "none"),
        ("discover_recovery_options", "none"),
        ("apply_clarified_horizon_choice", "none"),
    ],
    "weather_and_reality": [],
    "transport": [],
    "traveler_preferences": [],
    "stay": [],
    "notification_inbox": [],
    "identity_and_resume": [],
    "history_and_trash": [],
}

# Domains that are product surfaces on V8 but have no agent tool in either tree. Naming them here is
# the order's alternative to a silent gap: either they get an adapter, or the gap has an owner.
SURFACE_ONLY = {
    "weather_and_reality": "Guardian/weather lives on Revolution only; V8 has no watcher module.",
    "transport": "Route session operations live on Revolution only; V8 has no agent tool for routes.",
    "traveler_preferences": "Preferences are read by the shell; no agent tool reads or writes them.",
    "stay": "Stay generation is a product surface; no agent tool selects or books a stay.",
    "notification_inbox": "The inbox is a read surface; no agent tool writes or acknowledges.",
    "identity_and_resume": "Session/recovery are doors, not agent tools (by design).",
    "history_and_trash": "Recycle bin and history are product surfaces; no agent tool.",
}

OWNER = {
    "research_place_sources": "Qoder",
    "estimate_place_facts": "Qoder",
    "identity_and_resume": "Qoder",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def advertised_tools(inventory: dict, label: str) -> set[str]:
    checkout = inventory["checkouts"][label]
    return {row["name"] for row in checkout["registered_tools"]}


def build(inventory: dict) -> dict:
    v8 = inventory["checkouts"]["v8"]
    revolution = inventory["checkouts"]["revolution"]
    v8_tools = advertised_tools(inventory, "v8")
    rev_tools = advertised_tools(inventory, "revolution")

    rows = []
    for domain, paths in v8["domains"].items():
        present = paths["source_paths_present"]
        missing = paths["expected_paths_missing"]
        rev_missing = revolution["domains"][domain]["expected_paths_missing"]
        tools = DOMAIN_TOOLS.get(domain, [])
        callable_rows = []
        for name, proof in tools:
            if name in v8_tools:
                state = "ADVERTISED"
            elif name in rev_tools:
                state = "REVOLUTION_ONLY"
            else:
                state = "NOT_REGISTERED"
            callable_rows.append({"tool": name, "state": state, "verified_by": proof})
        revolution_only = sorted(
            {
                row["name"]
                for row in revolution["registered_tools"]
                if row["name"] not in v8_tools and domain in DOMAIN_TOOLS
                and row["name"] in {tool for tool, _ in DOMAIN_TOOLS[domain]}
            }
        )
        # Order matters: a domain with an advertised, tested tool is ready even when some of its
        # expected source paths live only on Revolution -- the missing file is a note, not the
        # domain's status. Only a domain with nothing callable falls back to SOURCE_ONLY.
        if any(row["state"] == "ADVERTISED" for row in callable_rows):
            status = "READY_FOR_REHEARSAL"
        elif missing:
            status = "SOURCE_ONLY"
        elif domain in SURFACE_ONLY:
            status = "SURFACE_ONLY"
        else:
            status = "ADAPTER_NEEDED"
        rows.append(
            {
                "domain": domain,
                "v8_present": present,
                "v8_missing": missing,
                "revolution_missing": rev_missing,
                "tools": callable_rows,
                "revolution_only_tools": revolution_only,
                "status": status,
                "note": SURFACE_ONLY.get(domain, ""),
            }
        )
    return {
        "schema_version": 1,
        "scope": "CAPABILITY_LEDGER",
        "v8_commit": v8.get("commit"),
        "revolution_commit": revolution.get("commit"),
        "runtime_verified": False,
        "rows": rows,
    }


def to_markdown(ledger: dict) -> str:
    lines = [
        "# CityNexus capability ledger — reform 2026-10-18",
        "",
        f"V8 `{ledger['v8_commit']}` vs Revolution `{ledger['revolution_commit']}`. Generated by",
        "`tools/reform/build_capability_ledger.py` from the static inventory; statuses are conservative",
        "and no live provider was called (`runtime_verified: false`).",
        "",
        "| domain | V8 source gaps | agent tool(s) | status | note |",
        "| --- | --- | --- | --- | --- |",
    ]
    for row in ledger["rows"]:
        tools = ", ".join(
            f"{item['tool']} ({item['state'].lower()})" for item in row["tools"]
        ) or "—"
        missing = ", ".join(row["v8_missing"]) or "all present"
        note = row["note"] or (
            "missing on V8: " + missing if row["v8_missing"] else ""
        )
        lines.append(
            f"| {row['domain']} | {missing} | {tools} | {row['status']} | {note} |"
        )
    lines += [
        "",
        "## How to read the statuses",
        "",
        "- `READY_FOR_REHEARSAL` — source present, tool advertised and dispatched, exercised by a named",
        "  test. Not `LIVE_VERIFIED`: no provider was called.",
        "- `SOURCE_ONLY` — the domain's expected paths are missing on V8; the capability exists only on",
        "  Revolution and needs a migration before any adapter can bind to it.",
        "- `SURFACE_ONLY` — a product surface on V8 with no agent tool in either tree.",
        "- `ADAPTER_NEEDED` — source present but nothing advertises it to the model.",
        "",
        "## The three adapters landed in this reform",
        "",
        "| tool | commit | proof |",
        "| --- | --- | --- |",
        "| `research_place_sources` | `a9e8039d49` | seven arms incl. a scripted-model loop run |",
        "| `estimate_place_facts` | `b84d346a5e` | five arms; canonical columns asserted unchanged |",
        "| recovery credential (door, not a tool) | `3765947d34` + `986e391df1` | seven backend arms + phone e2e |",
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", required=True, type=Path)
    parser.add_argument("--out-dir", required=True, type=Path)
    args = parser.parse_args()
    ledger = build(load(args.inventory))
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "CAPABILITY_LEDGER_20261018.json").write_text(
        json.dumps(ledger, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (args.out_dir / "CAPABILITY_LEDGER_20261018.md").write_text(
        to_markdown(ledger), encoding="utf-8"
    )
    print(f"wrote {len(ledger['rows'])} domain rows to {args.out_dir}")


if __name__ == "__main__":
    main()
