"""ORD-0556 follow-up, fourth leg (read-only): compare two tips' file trees, path by path.

Why: while re-checking landing status the authoritative tip had moved again, and the new tree is much
smaller than the one my screen sweep ran against. Ancestry cannot be proven in this shallow clone, so this
leg does NOT claim anyone deleted anything -- it states the tree-level difference and names what is present
on one side only, bucketed, with the named landed paths of this lane checked one by one.

Zero product bytes. Reads git objects only.
"""
from __future__ import annotations

import json
import os
import pathlib
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

ROOT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
OUT_DIR = ROOT / "review/ord0556/readouts"
OLDER = "4d43f8bc25a1a2f4e4c752afe08851032ab6c71d"   # the tip my screen sweep was measured against
LANE_SPECS = "qoder-ord05"


def env_clean() -> dict:
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    e["NO_PROXY"] = "*"
    return e


def git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", env=env_clean())


def need(*args: str) -> str:
    r = git(*args)
    if r.returncode != 0:
        raise SystemExit(f"ABORT git {' '.join(args)} rc={r.returncode}: {(r.stderr or '')[:200]}")
    return (r.stdout or "").strip()


def paths(ref: str) -> set[str]:
    return {p for p in need("ls-tree", "-r", "--name-only", ref).split("\n") if p.strip()}


def bucket(p: str) -> str:
    parts = p.split("/")
    return "/".join(parts[:2]) if len(parts) > 1 else parts[0]


def main() -> int:
    tip = need("ls-remote", "origin", "HEAD").split()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", tip):
        raise SystemExit("ABORT ls-remote HEAD did not return a full 40-hex")
    need("fetch", "--depth=1", "origin", tip)
    older_paths, new_paths = paths(OLDER), paths(tip)

    only_older = sorted(older_paths - new_paths)
    only_new = sorted(new_paths - older_paths)
    common = older_paths & new_paths

    named = {
        "slice6_product": ["frontend/src/features/poiimport/PoiImportPanel.tsx",
                           "frontend/src/features/poiimport/poiImportCopy.ts"],
        "slice6_harness": ["frontend/e2e/qoder-ord0545s6-copy-cells-r1.spec.ts",
                           "frontend/playwright.ord0545s6-copy-cells.config.ts"],
        "ord0556_target": ["frontend/src/i18n/LocaleContext.tsx"],
        "sweep_instruments": ["review/ord0556/route_sweep_dev_r1.py",
                              "review/ord0556/bookings_caps_reader_r1.js"],
    }
    named_read = {}
    for group, plist in named.items():
        named_read[group] = {}
        for p in plist:
            ob = git("rev-parse", "--verify", f"{OLDER}:{p}").stdout.strip()
            nb = git("rev-parse", "--verify", f"{tip}:{p}").stdout.strip()
            named_read[group][p] = {
                "blob_older": ob if re.fullmatch(r"[0-9a-f]{40}", ob or "") else "absent",
                "blob_new": nb if re.fullmatch(r"[0-9a-f]{40}", nb or "") else "absent",
                "state": ("SAME_ON_BOTH" if ob and nb and ob == nb else
                          ("ONLY_ON_OLDER" if ob and not nb else
                           ("ONLY_ON_NEW" if nb and not ob else "ON_BOTH_DIFFERENT" if ob and nb else "ABSENT_BOTH"))),
            }

    def spec_count(ref: str) -> int:
        return len([p for p in paths(ref) if LANE_SPECS in p])

    parents_older = [l.split()[-1] for l in need("cat-file", "-p", OLDER).split("\n") if l.startswith("parent ")]
    parents_new = [l.split()[-1] for l in need("cat-file", "-p", tip).split("\n") if l.startswith("parent ")]
    anc = git("merge-base", "--is-ancestor", OLDER, tip)

    doc = {
        "generation": {"older_ref_from_sweep_receipt": OLDER, "newer_ref_from_ls_remote_now": tip,
                       "recorded_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                       "read_kind": "tree-level path set comparison; ancestry NOT proven",
                       "parents_older": parents_older, "parents_newer": parents_new,
                       "merge_base_is_ancestor_rc": anc.returncode,
                       "shallow": need("rev-parse", "--is-shallow-repository")},
        "counts": {"paths_older": len(older_paths), "paths_new": len(new_paths),
                   "only_on_older": len(only_older), "only_on_new": len(only_new), "common": len(common)},
        "only_on_older_by_bucket_top": Counter(bucket(p) for p in only_older).most_common(14),
        "only_on_new_by_bucket_top": Counter(bucket(p) for p in only_new).most_common(10),
        "lane_spec_files": {"older": spec_count(OLDER), "new": spec_count(tip)},
        "named_paths": named_read,
        "sample_only_on_older": only_older[:12],
        "verdict": "TREE_DIFF_READ",
    }
    out = OUT_DIR / f"tip_tree_diff_{doc['generation']['recorded_at']}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    c = doc["counts"]
    print(json.dumps({"receipt": out.name, "older": c["paths_older"], "new": c["paths_new"],
                      "only_older": c["only_on_older"], "only_new": c["only_on_new"],
                      "common": c["common"], "specs": doc["lane_spec_files"],
                      "anc_rc": doc["generation"]["merge_base_is_ancestor_rc"],
                      "shallow": doc["generation"]["shallow"]}, ensure_ascii=False))
    for g, rows in named_read.items():
        for p, v in rows.items():
            print(f"NAMED {g} {p} {v['state']} old={(v['blob_older'] or '')[:9]} new={(v['blob_new'] or '')[:9]}")
    print("TOP_BUCKETS_ONLY_ON_OLDER", json.dumps(doc["only_on_older_by_bucket_top"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
