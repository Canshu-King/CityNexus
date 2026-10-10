"""Decide whether a phone swap is a real generation change before running the deploy gauge.

Why this exists: a commit can move `frontend/src` without moving the emitted bundle -- a
type-only or comment-only change is erased by the TypeScript build, so vite reproduces the same
content hash.  The deploy gauge then reports `B_NEW_INDEX` RED, because its predicate is "the old
asset name must be absent from the served index", and that can never happen when the new bytes are
the old bytes.  That red is a void premise, not a deployment failure, and treating it as either
"ignore reds" or "deploy again" would cost me the only arm that catches a real stale bundle.

So the decision is made here, before touching anything:

  SWAP_REQUIRED        -- the build names assets the server does not currently serve
  NO_RUNTIME_DELTA     -- the build names exactly what is served; the source still differs
  STALE_BUILD_SUSPECT  -- the build names what is served AND the source does not differ

Read-only: it runs no git write, no copy, no switch.
"""
import json
import pathlib
import re
import subprocess
import sys
import urllib.request

REPO = "D:/moodle/CityNexus"
SERVE = pathlib.Path("D:/moodle/_qoder_preview_20260920/dist")
BASE = "http://127.0.0.1:4781"
REF_RE = re.compile(r"/assets/[A-Za-z0-9_\-\.]+\.(?:js|css)")


def refs_of_html(html):
    return sorted(set(REF_RE.findall(html)))


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: cmdr_swap_decision_r1.py <40-hex-tip> [--prev <40-hex>] [--out file]")
    sha = sys.argv[1]
    out = pathlib.Path(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[2] == "--out" else \
        pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks/cmdr_swap_decision_last.json")

    rep = {"tip": sha, "built_dist": None}
    dist = pathlib.Path("D:/moodle/_qoder_cmdr_ref_20260921/live_checks") / ("_build_%s" % sha[:7]) / "frontend" / "dist"
    if not (dist / "index.html").is_file():
        rep["decision"] = "NO_BUILD_YET"
        out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
        print("NO_BUILD_YET", dist)
        return 1
    built_refs = refs_of_html((dist / "index.html").read_text(encoding="utf-8", errors="replace"))
    served_refs = refs_of_html((SERVE / "index.html").read_text(encoding="utf-8", errors="replace"))
    op = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        online_refs = refs_of_html(op.open(BASE + "/", timeout=15).read().decode("utf-8", "replace"))
    except Exception as e:
        online_refs = None
        rep["online_error"] = str(e)[:160]

    # does the source actually differ from what is served now?  the served generation's sha is on disk
    # the previous generation is passed in (the deploy gauge does not stamp a marker file), so this
    # tool never guesses a sha from disk state it does not own.
    prev_sha = ""
    for i, a in enumerate(sys.argv):
        if a == "--prev" and i + 1 < len(sys.argv):
            prev_sha = sys.argv[i + 1].strip()
    src_diff = []
    if prev_sha and len(prev_sha) >= 12:
        r = subprocess.run(["git", "-C", REPO, "diff", "--name-only", prev_sha, sha, "--", "frontend/src"],
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        src_diff = [x for x in (r.stdout or "").splitlines() if x.strip()]

    rep.update({"built_refs": built_refs, "served_disk_refs": served_refs,
                "online_refs": online_refs, "previous_generation": prev_sha,
                "source_diff_frontend_src": src_diff})

    if built_refs != served_refs:
        rep["decision"] = "SWAP_REQUIRED"
    elif src_diff:
        rep["decision"] = "NO_RUNTIME_DELTA"
        rep["why"] = ("the tip changes frontend/src in the files listed above, but the emitted bundle "
                      "names the same assets -- type-only/comment-only edits are erased by the build. "
                      "The deploy gauge's B_NEW_INDEX arm cannot pass here (it demands the old asset "
                      "name be absent), so its RED would be a void premise, not a failure.")
    else:
        rep["decision"] = "STALE_BUILD_SUSPECT"
        rep["why"] = "same asset names AND no source diff: the build is not newer than what is served"
    out.write_text(json.dumps(rep, ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps({"decision": rep["decision"], "built_refs": built_refs,
                      "served_disk_refs": served_refs, "src_diff_files": len(src_diff)},
                     ensure_ascii=False).encode("ascii", "replace").decode())
    return 0


if __name__ == "__main__":
    sys.exit(main())
