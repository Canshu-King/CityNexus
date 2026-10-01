"""前置单 -- census every testid the four shared-testid neighbours ask the screen for, and say for each
one whether the generation under test actually ships it.

Why this file exists rather than a paragraph: the order asked for the neighbours' readings, red or green,
and four reds out of eight cells in one file is not a cause. A locator the screen no longer carries reads
identically to a screen that broke -- so every `getByTestId(...)` / `data-testid=...` these four specs
name is lifted out of the spec text and checked against the tip's own `frontend/src`, and the sharing
graph (which specs ask the same id) is printed alongside, because "邻居" is a claim about a shared set of
names and a shared set is exactly what can move together when one screen changes.

Nothing is inferred from a file name: present/absent is decided by `git grep` over the tree at the commit
the bundle was built from.
"""
import io
import json
import re
import subprocess
import sys

SHA = "5a4cdbd26d4a58d6ed6b277480e766ac08b15ded"
FRONTEND = "D:/moodle/_qoder_e766b154_ord0472_20260930/wt/frontend"
SPECS = {
    "ord0502": "e2e/qoder-ord0502-phone-mainline.spec.ts",
    "ord0497": "e2e/qoder-bac10f40-ord0497-footprints-on-map.spec.ts",
    "ord0530": "e2e/qoder-bac10f40-ord0530-footprints-by-day.spec.ts",
    "ord0537": "e2e/qoder-bac10f40-ord0537-map-toggle-reach.spec.ts",
}
# How the four files name a testid: getByTestId("x"), getByTestId('x'), a template string, and the
# attribute selector form used inside locator()/querySelector.
PATTERNS = [
    re.compile(r"""getByTestId\(\s*"([^"]+)"\s*\)"""),
    re.compile(r"""getByTestId\(\s*'([^']+)'\s*\)"""),
    re.compile(r"""getByTestId\(\s*`\$\{[^}]*\}([^`]+)`\s*\)"""),
    re.compile(r"""\[data-testid=['"]([^'"]+)['"]\]"""),
    re.compile(r"""data-testid="([a-z0-9-]+)"""),
]
OUT = "D:/moodle/_qoder_e766b154_ord0528_20261001/run/shared_testid_census_r1.json"


def names_in(path):
    with io.open(path, encoding="utf-8") as handle:
        text = handle.read()
    found = set()
    for pattern in PATTERNS:
        found.update(match.group(1) for match in pattern.finditer(text))
    return {name for name in found if name and not name.startswith("$")}


def ships(name):
    """Count the source hits for this testid at the commit the bundle was built from."""
    result = subprocess.run(
        ["git", "grep", "-c", "--", 'data-testid="%s"' % name, SHA, "--", "frontend/src"],
        cwd="D:/moodle/_qoder_e766b154_ord0472_20260930/wt",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    files = [line for line in result.stdout.splitlines() if line.strip()]
    if files:
        return {"present": True, "files": [line.split(":")[2] for line in files], "hits": len(files)}
    # The attribute can also be written with single quotes or built from a variable, so ask for the bare
    # name before calling it absent.
    bare = subprocess.run(
        ["git", "grep", "-l", "--", name, SHA, "--", "frontend/src"],
        cwd="D:/moodle/_qoder_e766b154_ord0472_20260930/wt",
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    named = [line.split(":", 2)[-1] for line in bare.stdout.splitlines() if line.strip()]
    return {"present": bool(named), "files": named, "hits": len(named)}


def main():
    per_spec = {key: sorted(names_in("%s/%s" % (FRONTEND, path))) for key, path in SPECS.items()}
    all_names = sorted({name for names in per_spec.values() for name in names})
    census = {}
    for name in all_names:
        users = [key for key in SPECS if name in per_spec[key]]
        entry = ships(name)
        entry["asked_by"] = users
        entry["shared_by_n"] = len(users)
        census[name] = entry

    shared = {n: e for n, e in census.items() if e["shared_by_n"] > 1}
    absent = {n: e for n, e in census.items() if not e["present"]}
    out = {
        "generation_under_test": SHA,
        "per_spec_names": per_spec,
        "census": census,
        "totals": {
            "names_asked": len(all_names),
            "names_shared_by_more_than_one_spec": len(shared),
            "names_absent_from_the_trees_source": len(absent),
        },
        "shared": shared,
        "absent": absent,
    }
    with io.open(OUT, "w", encoding="utf-8") as handle:
        json.dump(out, handle, indent=1, ensure_ascii=False)
    print("names_asked=%d shared=%d absent=%d"
          % (out["totals"]["names_asked"], len(shared), len(absent)))
    for name in sorted(absent):
        print("  ABSENT %s asked_by=%s" % (name, absent[name]["asked_by"]))
    print("  shared_examples:")
    for name in sorted(shared, key=lambda n: -shared[n]["shared_by_n"])[:10]:
        print("    %s asked_by=%s present=%s" % (name, shared[name]["asked_by"], shared[name]["present"]))
    print("WROTE %s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
