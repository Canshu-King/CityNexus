"""ORD-0556 follow-up, eighth leg: name what the live tip actually dropped.

Leg six found /v8/trash absent at the live tip and leg four found the tip carries 4020 paths fewer than the
sweep base. This names the shape of that gap instead of the size: which route keys exist on each side, which
of them still have a nav dictionary entry, and which feature directories the missing paths belong to.

Read-only: two ls-tree reads and a handful of blob reads, no ports, no product bytes.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
from datetime import datetime, timezone

WT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
OUT = WT / "review/ord0556/readouts"
RUN = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
SWEEP_BASE = "4d43f8bc25a1a2f4e4c752afe08851032ab6c71d"
ROUTES = "frontend/src/routes/v8Routes.ts"
DICT = "frontend/src/i18n/LocaleContext.tsx"
KEY = re.compile(r'key:\s*"([a-z]+)"')
NAV = re.compile(r'"nav\.([a-z]+)":')


def git(*a: str) -> str:
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    e["NO_PROXY"] = "*"
    r = subprocess.run(["git", "-C", str(WT), *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=e)
    if r.returncode != 0:
        raise SystemExit(f"ABORT git {' '.join(a)}: {(r.stderr or '')[:160]}")
    return r.stdout


def main() -> int:
    tip = git("ls-remote", "origin", "HEAD").split()[0]
    sides = {"live_tip": tip, "sweep_base": SWEEP_BASE}
    doc: dict = {"generation": {"run": RUN, "live_tip": tip, "sweep_base": SWEEP_BASE,
                                "read_only": True, "paths": {}, "routes": {}, "nav": {}}}
    path_sets = {}
    for label, ref in sides.items():
        paths = [p for p in git("ls-tree", "-r", "--name-only", ref).split("\n") if p.strip()]
        path_sets[label] = set(paths)
        keys = sorted(set(KEY.findall(git("show", f"{ref}:{ROUTES}"))))
        nav = sorted(set(NAV.findall(git("show", f"{ref}:{DICT}"))))
        doc["generation"]["paths"][label] = len(paths)
        doc["generation"]["routes"][label] = keys
        doc["generation"]["nav"][label] = nav

    only_old = sorted(path_sets["sweep_base"] - path_sets["live_tip"])
    only_new = sorted(path_sets["live_tip"] - path_sets["sweep_base"])
    buckets: dict[str, int] = {}
    for p in only_old:
        parts = p.split("/")
        buckets["/".join(parts[:2])] = buckets.get("/".join(parts[:2]), 0) + 1
    top = sorted(buckets.items(), key=lambda kv: (-kv[1], kv[0]))[:14]

    keys_old = set(doc["generation"]["routes"]["sweep_base"])
    keys_new = set(doc["generation"]["routes"]["live_tip"])
    dropped = sorted(keys_old - keys_new)
    added = sorted(keys_new - keys_old)
    nav_old = set(doc["generation"]["nav"]["sweep_base"])
    nav_new = set(doc["generation"]["nav"]["live_tip"])
    # Which order each key came in with, read from the comment block the registry carries above the row:
    # quoting the ORD ids from memory would make them unverifiable, so they are parsed out of the file.
    reg = git("show", f"{SWEEP_BASE}:{ROUTES}").split("\n")
    ids_by_key: dict[str, list[str]] = {}
    for i, line in enumerate(reg):
        m = KEY.search(line)
        if not m:
            continue
        # Only the CONTIGUOUS comment block directly above the row. A fixed-width window reached into the
        # previous row's comment and attributed its order id to this key (access picked up ORD-0402, which
        # belongs to trash).
        block = []
        j = i - 1
        while j >= 0:
            t = reg[j].strip()
            if t.startswith(("{", "]", "}", "export")) or "as const" in t or 'key: "' in t:
                break
            block.append(reg[j])
            j -= 1
        ids_by_key[m.group(1)] = sorted(set(re.findall(r"ORD-\d+", "\n".join(block))))
    families = {}
    for key in dropped:
        families[key] = {
            "orders_that_added_it": ids_by_key.get(key, []),
            "nav_on_sweep_base": key in nav_old,
            "nav_on_live_tip": key in nav_new,
            "paths_named_after_it_only_on_sweep_base":
                len([p for p in only_old if re.search(rf"(^|/){key}", p, re.I)]),
        }
    doc.update({"only_on_sweep_base": len(only_old), "only_on_live_tip": len(only_new),
                "only_on_sweep_base_top_buckets": top, "route_keys_dropped": dropped,
                "route_keys_added": added, "dropped_families": families,
                "verdict": "DROPPED_ROUTES_READ"})
    OUT.joinpath(f"dropped_routes_{RUN}.json").write_text(
        json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    print(f"live_tip={tip} sweep_base={SWEEP_BASE}")
    print(f"paths live={len(path_sets['live_tip'])} sweep={len(path_sets['sweep_base'])} "
          f"only_on_sweep_base={len(only_old)} only_on_live_tip={len(only_new)}")
    print(f"route_keys live={len(keys_new)} sweep={len(keys_old)} dropped={len(dropped)} added={len(added)}")
    print("dropped_keys=" + ",".join(dropped))
    for key, f in families.items():
        print(f"family {key} orders={','.join(f['orders_that_added_it']) or 'none'} "
              f"nav_sweep={f['nav_on_sweep_base']} nav_live={f['nav_on_live_tip']} "
              f"named_paths_only_on_sweep={f['paths_named_after_it_only_on_sweep_base']}")
    print("top_buckets=" + " ".join(f"{b}:{n}" for b, n in top))
    print("receipt dropped_routes_" + RUN + ".json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
