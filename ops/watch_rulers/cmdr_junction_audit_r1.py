"""Read-only auditor: which of MY derived directories carry a junction, and where each one points.

Why this exists: every `_build_*` copy under live_checks links `frontend/node_modules` back to the real
`D:/moodle/CityNexus/frontend/node_modules`.  A recursive delete of a build directory therefore walks
through the link and destroys the repository's own node_modules -- which is exactly the thing a disk
cleanup must never do.  This script never deletes, never writes into the scanned trees, and prints the
target of every reparse point it finds so a human or a later commander can see the landmine without
re-deriving it.

Usage: python cmdr_junction_audit_r1.py [root]
"""
import json
import os
import sys

ROOT = sys.argv[1] if len(sys.argv) > 1 else r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
REPARSE_FLAG = 0x400  # FILE_ATTRIBUTE_REPARSE_POINT


def main():
    dirs = sorted(d for d in os.listdir(ROOT) if d.startswith("_build_") and os.path.isdir(os.path.join(ROOT, d)))
    findings = []
    for d in dirs:
        for root, subdirs, _files in os.walk(os.path.join(ROOT, d)):
            for x in list(subdirs):
                p = os.path.join(root, x)
                try:
                    st = os.lstat(p)
                except OSError:
                    continue
                if getattr(st, "st_file_attributes", 0) & REPARSE_FLAG:
                    try:
                        target = os.readlink(p)
                    except OSError as e:
                        target = "READLINK_FAILED:%s" % type(e).__name__
                    findings.append({"build_dir": d, "link": os.path.relpath(p, ROOT).replace("\\", "/"),
                                     "target": str(target).replace("\\", "/")})
    out = {
        "instrument": "cmdr_junction_audit_r1",
        "root": ROOT.replace("\\", "/"),
        "build_dirs_scanned": len(dirs),
        "reparse_points_found": len(findings),
        "distinct_targets": sorted({f["target"] for f in findings}),
        "links_pointing_at_the_product_repo_node_modules": sum(
            1 for f in findings if "CityNexus/frontend/node_modules" in f["target"]),
        "rule": "a recursive delete of any of these build dirs follows the link and destroys the target; "
                "detach each junction with a plain rmdir on the LINK itself before deleting the tree",
        "findings": findings,
    }
    dest = os.path.join(ROOT, "cmdr_junction_audit_r1.json")
    with open(dest, "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=2)
    print(json.dumps({k: out[k] for k in ("build_dirs_scanned", "reparse_points_found",
                                          "distinct_targets",
                                          "links_pointing_at_the_product_repo_node_modules")},
                     ensure_ascii=False, indent=1))
    print("wrote", dest.replace("\\", "/"), os.path.getsize(dest), "B")


if __name__ == "__main__":
    main()
