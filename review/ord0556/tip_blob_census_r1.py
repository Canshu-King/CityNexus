"""ORD-0556 follow-up, fifth leg (read-only): of the paths present on BOTH tips, how many changed content?

Leg four compared path *sets* and named the gap it left: "6542 common paths, content not compared". This leg
closes that gap with one `ls-tree -r` per ref -- blob oids, not file contents over a pipe -- so the census is
cheap and re-runnable. Buckets answer whether the current tip is a rebuild (files renamed / moved) or a line
where shared files really changed.

Zero product bytes. Reads git objects only. Ancestry is NOT claimed: this clone is shallow.
"""
from __future__ import annotations

import json
import os
import pathlib
import posixpath
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone

ROOT = pathlib.Path("D:/moodle/_qoder_newlane_ord0496")
OUT_DIR = ROOT / "review/ord0556/readouts"
KEY_PATHS = ["frontend/src/i18n/LocaleContext.tsx", "frontend/src/app/V8Experience.tsx",
             "frontend/src/styles.css", "backend/app/main.py", "contracts/openapi.yaml"]


def env_clean() -> dict:
    e = dict(os.environ)
    for k in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy"):
        e.pop(k, None)
    e["NO_PROXY"] = "*"
    return e


def need(*args: str) -> str:
    r = subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace", env=env_clean())
    if r.returncode != 0:
        raise SystemExit(f"ABORT git {' '.join(args)} rc={r.returncode}: {(r.stderr or '')[:180]}")
    return r.stdout or ""


def blobs(ref: str) -> dict:
    out = {}
    for line in need("ls-tree", "-r", ref).split("\n"):
        if not line.strip():
            continue
        meta, path = line.split("\t", 1)
        _, _, oid = meta.split()
        out[path] = oid
    return out


def bucket(p: str) -> str:
    parts = p.split("/")
    return "/".join(parts[:2]) if len(parts) > 1 else parts[0]


def relative_import_check(ref: str, present: set) -> dict:
    """Do the sources at this ref import anything that is not in the same tree? A pruned tree that still
    references a removed module would be broken; this answers that without running a build. Paths are
    normalised (`a/../b`), which is what made an earlier hand run of this check report 102 false hits."""
    srcs = sorted(p for p in present if p.endswith((".ts", ".tsx")) and p.startswith("frontend/"))
    text_cache: dict[str, str] = {}
    dangling = []
    for p in srcs:
        if p not in text_cache:
            text_cache[p] = need("show", f"{ref}:{p}")
        for m in re.finditer(r"from\s+[\"'](\.[^\"']+)[\"']", text_cache[p]):
            cand = posixpath.normpath(posixpath.join(posixpath.dirname(p), m.group(1)))
            if not any(cand + e in present for e in ("", ".ts", ".tsx", "/index.ts", "/index.tsx", ".json", ".css")):
                dangling.append({"path": p, "specifier": m.group(1)})
    return {"files_scanned": len(srcs), "dangling_relative_imports": len(dangling),
            "sample": dangling[:8]}


def main() -> int:
    diff = json.loads(sorted(OUT_DIR.glob("tip_tree_diff_*.json"))[-1].read_text(encoding="utf-8"))
    older, newer = (diff["generation"]["older_ref_from_sweep_receipt"],
                    diff["generation"]["newer_ref_from_ls_remote_now"])
    fresh_tip = need("ls-remote", "origin", "HEAD").split()[0]
    if not re.fullmatch(r"[0-9a-f]{40}", fresh_tip):
        raise SystemExit("ABORT ls-remote HEAD not a full 40-hex")
    subprocess.run(["git", "-C", str(ROOT), "fetch", "--depth=1", "origin", fresh_tip],
                   capture_output=True, text=True, env=env_clean())
    if fresh_tip != newer:
        print(f"note: line moved again since leg four ({newer[:9]} -> {fresh_tip[:9]}); census runs on the newer tip")
        newer = fresh_tip

    bo, bn = blobs(older), blobs(newer)
    common = sorted(set(bo) & set(bn))
    changed = [p for p in common if bo[p] != bn[p]]
    same = [p for p in common if bo[p] == bn[p]]
    by_bucket = Counter(bucket(p) for p in changed)
    keys = {p: {"older": bo.get(p, "absent"), "newer": bn.get(p, "absent"),
                "state": ("ABSENT_ONE_SIDE" if p not in bo or p not in bn
                          else ("SAME_BLOB" if bo[p] == bn[p] else "BLOB_CHANGED"))} for p in KEY_PATHS}
    imports = relative_import_check(newer, set(bn))
    doc = {
        "generation": {"older_ref": older, "newer_ref": newer, "leg4_newer_ref": diff["generation"]["newer_ref_from_ls_remote_now"],
                       "recorded_at": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                       "read_kind": "blob oid comparison over ls-tree -r; no file bodies, no writes",
                       "shallow": need("rev-parse", "--is-shallow-repository").strip()},
        "counts": {"paths_older": len(bo), "paths_newer": len(bn), "common": len(common),
                   "common_same_blob": len(same), "common_changed_blob": len(changed),
                   "only_on_older": len(set(bo) - set(bn)), "only_on_newer": len(set(bn) - set(bo))},
        "changed_by_bucket_top": by_bucket.most_common(12),
        "changed_sample": [{"path": p, "older": bo[p], "newer": bn[p]} for p in changed[:12]],
        "key_paths": keys,
        "imports_at_newer_ref": imports,
        "verdict": "BLOB_CENSUS_READ",
    }
    out = OUT_DIR / f"tip_blob_census_{doc['generation']['recorded_at']}.json"
    out.write_text(json.dumps(doc, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n")
    c = doc["counts"]
    print(json.dumps({"receipt": out.name, **c, "verdict": doc["verdict"],
                      "newer_ref": newer}, ensure_ascii=False))
    print(f"IMPORT_SCAN files={imports['files_scanned']} dangling={imports['dangling_relative_imports']}")
    for b, n in doc["changed_by_bucket_top"]:
        print(f"CHANGED_BUCKET {b} {n}")
    for p, v in keys.items():
        print(f"KEY {p} {v['state']} {v['older'][:9]} {v['newer'][:9]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
