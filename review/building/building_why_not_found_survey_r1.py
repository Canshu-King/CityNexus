"""The building's foundation survey: which "why is this place not found" causes the product can name today.

The building's job is to make "one place cannot be found" a product truth: a user who searches a place name,
or asks a category in a city, must be able to tell apart three causes -- never registered, resolved to no
canonical identity, resolved but carrying no coordinate -- instead of seeing one empty list.

This survey answers the question the building has to start from: of those three, which can the product
already name?  It reads the reason-code tables and the screen-side rendering, and it reports the gap
honestly -- including a negative reading ("this word appears in no screen file") with the files that were
actually searched, because "the keyword is absent" and "the capability is absent" are different claims.

Read-only: git plus file reads; nothing is written into the tree.
"""

from __future__ import annotations

import json
import pathlib
import re
import subprocess

TREE = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/wt504")
OUT = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run")
CAPABILITY = "backend/app/anywhere_capability.py"
SERVICES = "backend/app/services.py"
PANEL = "frontend/src/features/discovery/DestinationPreparationPanel.tsx"
SCREEN_DIR = "frontend/src"

# the three causes the building must make distinguishable
CAUSES = {
    "never_registered": ("CATALOG_EMPTY", "解析到了城市、但这类地点一条都没登记"),
    "no_canonical_identity": ("NO_CANONICAL_IDENTITY", "这个名字解析不出规范身份"),
    "resolved_but_no_coordinate": ("", "解析到了身份、但它没有可用坐标"),
}
# every reason code the product can already name, so the survey is not just the three
ALL_CODES = ["CATALOG_CURRENT", "COVERAGE_INCOMPLETE", "CATALOG_STALE", "NO_CANONICAL_IDENTITY",
             "DESTINATION_AMBIGUOUS", "DESTINATION_RESOLVER_UNAVAILABLE", "CATALOG_EMPTY",
             "CATALOG_INSUFFICIENT"]


def git(*args: str) -> str:
    proc = subprocess.run(["git", "-C", str(TREE), *args], capture_output=True,
                          text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        print(f"REFUSE: git {' '.join(args)}: {proc.stderr.strip()[:140]}")
        raise SystemExit(9)
    return proc.stdout.strip()


def main() -> int:
    tip = [l.split("\t")[0] for l in git("ls-remote", "--refs", "origin").splitlines()
           if l.endswith("refs/heads/mirror/integration-frontend-apple-pass1")][0]
    out: dict[str, object] = {"tip": tip}

    cap = git("cat-file", "blob", git("rev-parse", f"{tip}:{CAPABILITY}"))
    svc = git("cat-file", "blob", git("rev-parse", f"{tip}:{SERVICES}"))
    panel = git("cat-file", "blob", git("rev-parse", f"{tip}:{PANEL}"))
    out["blobs"] = {CAPABILITY: git("rev-parse", f"{tip}:{CAPABILITY}"),
                    SERVICES: git("rev-parse", f"{tip}:{SERVICES}"),
                    PANEL: git("rev-parse", f"{tip}:{PANEL}")}

    codes_in_product = {}
    for code in ALL_CODES:
        hit_app = [CAPABILITY if f'"{code}"' in cap else None, SERVICES if f'"{code}"' in svc else None]
        codes_in_product[code] = [p for p in hit_app if p]
    out["codes_in_product"] = codes_in_product

    # screen side: where does each code reach a rendered surface
    screen_files = [p for p in git("ls-tree", "-r", "--name-only", tip, SCREEN_DIR).splitlines() if p]
    out["screen_files_searched"] = len(screen_files)
    code_on_screen = {}
    for code in ALL_CODES:
        hits = []
        for p in screen_files:
            if p.endswith((".ts", ".tsx")):
                body = git("cat-file", "blob", f"{tip}:{p}")
                if code in body:
                    hits.append(p)
        code_on_screen[code] = hits
    out["codes_on_screen"] = code_on_screen

    # the panel is where the honest wording lives; count how many causes it can already say out loud
    worded = re.findall(r'case "([A-Z_]+)":', panel)
    out["panel_cases"] = worded
    out["panel_case_count"] = len(worded)

    # the three building causes, judged against both surfaces
    causes = {}
    for name, (code, what) in CAUSES.items():
        if not code:
            causes[name] = {"what": what, "code": None, "in_product": False,
                            "on_screen": False, "named": False,
                            "note": "no code exists for this cause -- this is the gap the building closes"}
            continue
        in_prod = bool(codes_in_product[code])
        on_scr = bool(code_on_screen[code])
        causes[name] = {"what": what, "code": code, "in_product": in_prod, "on_screen": on_scr,
                        "named": in_prod and on_scr,
                        "screen_files": code_on_screen[code][:3]}
    out["causes"] = causes
    out["named_count"] = sum(1 for c in causes.values() if c["named"])
    out["gap_count"] = sum(1 for c in causes.values() if not c["named"])

    text = json.dumps(out, ensure_ascii=False, indent=1)
    (OUT / "building_why_not_found_survey_r1.json").write_text(text, encoding="utf-8", newline="\n")
    for name, c in causes.items():
        print(f"{name:26s} code={c['code'] or '(none)'} product={c['in_product']} screen={c['on_screen']} "
              f"named={c['named']}")
    print(f"panel wording cases={out['panel_case_count']} | named causes={out['named_count']} "
          f"| gaps={out['gap_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())