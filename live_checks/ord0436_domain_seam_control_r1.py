"""ORD-0436 -- control on the contract-seam arm: can it go red at all?

The arm compares the visibility ladder on screen with `ShareVisibility` in the artifacts the server
publishes. At this tip neither artifact names that domain, so the arm's `CHECKED` branch has never
run -- an arm that cannot fail is not an arm. This file makes it fail on purpose, three ways, using
only real text:

  A  this tip's `contracts/openapi.yaml` + `frontend/src/generated/api.ts`   -> no domain (null)
  B  ORD-0434's candidate, both artifacts                                    -> its four levels
  C  B's contract with one level renamed                                     -> a domain that
     disagrees with the screen, so the same comparison must come out false

It also drops B's yaml to prove the fallback reads the generated client. The ref is named by full
sha in the readout, because a branch can be force-moved and a stale pin is the difference between a
control and a guess.
"""

from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import tempfile

REPO = pathlib.Path(__file__).resolve().parents[1]
OUT = REPO / "review" / "ord0436-access" / "CONTRACT_DOMAIN_R1.json"
UPSTREAM_REF = "refs/heads/review/qoder-0434-share-grants-r1"
# The levels the screen offers, read out of the live reading rather than retyped here.
SCREEN = json.loads(
    (REPO / "review" / "ord0436-access" / "TWO_ARMS_R1.json").read_text(encoding="utf-8")
)["reading"]["zh"]["visibilityAttributes"]
NODE = "node"


def git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", "-C", str(REPO), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", check=False)


def show(rev: str, path: str) -> str | None:
    got = git("show", f"{rev}:{path}")
    return got.stdout if got.returncode == 0 else None


def fixture(root: pathlib.Path, name: str, yaml_text: str | None, client_text: str | None) -> pathlib.Path:
    cell = root / name
    (cell / "contracts").mkdir(parents=True, exist_ok=True)
    (cell / "frontend" / "src" / "generated").mkdir(parents=True, exist_ok=True)
    if yaml_text is not None:
        (cell / "contracts" / "openapi.yaml").write_text(yaml_text, encoding="utf-8", newline="\n")
    if client_text is not None:
        (cell / "frontend" / "src" / "generated" / "api.ts").write_text(client_text, encoding="utf-8",
                                                                        newline="\n")
    return cell


def probe(cell: pathlib.Path) -> dict[str, object]:
    script = (
        "import { contractDomain } from %r;\n"
        f"console.log(JSON.stringify(contractDomain({str(cell.as_posix())!r})));\n"
    ) % (REPO / "live_checks" / "ord0436_contract_domain.mjs").as_uri()
    tmp = cell.parent / "run.mjs"
    tmp.write_text(script, encoding="utf-8", newline="\n")
    ran = subprocess.run([NODE, str(tmp)], capture_output=True, text=True, encoding="utf-8",
                         errors="replace", check=False)
    if ran.returncode != 0:
        return {"error": ran.stderr.strip()[:300]}
    try:
        return json.loads(ran.stdout.strip() or "null")
    except ValueError:
        return {"error": f"unparsed: {ran.stdout[:200]}"}


def main() -> int:
    tip = git("rev-parse", "HEAD").stdout.strip()
    upstream = git("rev-parse", UPSTREAM_REF).stdout.strip()
    resolved = git("rev-parse", "--verify", "--quiet", UPSTREAM_REF).returncode == 0
    rows: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="ord0436-domain-") as raw:
        root = pathlib.Path(raw)
        cell_a = fixture(root, "A", show(tip, "contracts/openapi.yaml"),
                         show(tip, "frontend/src/generated/api.ts"))
        cell_b = fixture(root, "B", show(upstream, "contracts/openapi.yaml"),
                         show(upstream, "frontend/src/generated/api.ts")) if resolved else None
        mutated = (show(upstream, "contracts/openapi.yaml") or "").replace(
            "enum: [PRIVATE, LINK_READ, INVITEES_ONLY, PUBLIC]",
            "enum: [PRIVATE, LINK_READ, INVITEES, PUBLIC]",
        )
        cell_c = fixture(root, "C", mutated, None) if resolved else None
        landed = (show(tip, "contracts/openapi.yaml") or "") + (show(tip, "frontend/src/generated/api.ts") or "")
        rows.append({"case": "A_tip", "parsed": probe(cell_a)})
        if resolved:
            rows.append({"case": "B_upstream", "parsed": probe(cell_b)})
            rows.append({"case": "C_mutant_one_level_renamed", "parsed": probe(cell_c)})
            # Same cell with its yaml moved away: the domain must still come out of the client.
            (cell_b / "contracts" / "openapi.yaml").rename(cell_b / "contracts" / "held.yaml")
            fallback = probe(cell_b)
            (cell_b / "contracts" / "held.yaml").rename(cell_b / "contracts" / "openapi.yaml")
            rows.append({"case": "B_generated_client_fallback", "parsed": fallback})
        parsed_b = next((r["parsed"] for r in rows if r["case"] == "B_upstream"),
                    {"skipped": f"{UPSTREAM_REF} not present locally"})

    def levels(parsed: dict[str, object]) -> list[str]:
        value = parsed.get("levels")
        return [str(v) for v in value] if isinstance(value, list) else []

    match_b = sorted(levels(parsed_b)) == sorted(SCREEN)
    match_c = any(sorted(levels(r.get("parsed", {}))) == sorted(SCREEN) for r in rows
                  if r["case"] == "C_mutant_one_level_renamed")
    readout = {
        "what": "control on the contract-seam arm of the ORD-0436 reading",
        "tip": tip,
        "upstream_ref": UPSTREAM_REF,
        "upstream_sha": upstream or None,
        "upstream_resolves": resolved,
        "screen_levels": SCREEN,
        "tip_names_the_domain": "ShareVisibility" in landed,
        "parsed_at_upstream": parsed_b,
        "cases": rows,
        "verdicts": {
            "arm_would_pass_against_upstream_domain": match_b,
            "arm_would_go_red_against_the_renamed_domain": not match_c,
        },
        "command": "python live_checks/ord0436_domain_seam_control_r1.py",
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(readout, ensure_ascii=False, indent=2) + "\n", "utf-8", newline="\n")
    print(json.dumps(readout["verdicts"], ensure_ascii=False), "| screen", len(SCREEN), "levels |", OUT.name)
    if not (match_b and not match_c):
        print("CONTROL RED: the seam arm does not bite as claimed", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
