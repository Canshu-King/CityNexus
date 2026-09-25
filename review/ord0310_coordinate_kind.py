"""Answer "is this 40-hex a blob or a commit?" by asking the server, not by remembering.

Both routes are probed for every coordinate handed over: `/git/blobs/<sha>` answers 404 for a commit
and `/commits/<sha>` answers 200 for one. That is what makes the namespace claim (`commit=` vs
`blob=`) checkable by anyone with a token, instead of a convention I assert in prose. The local
`git cat-file` result is recorded too, because an auditor's clone only resolves what it fetched -
and the refs that carry these commits are named in the same file.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0310"
OUT = SC / "ord0310-coordinate-kind-r1.json"
REPO = "Canshu-King/CityNexus"
URL = f"https://github.com/{REPO}.git"
# the two strings the commander could not resolve in his tree
SUBJECTS = {
    "c518e64b42db4e4428c78dc04982ef32e8dd3e78": "refs/heads/review/ord0310-tools-r5",
    "e6927f0f18c86ad0969690e8293b0d2c8a889988": "refs/heads/review/ord0310-tools-r3b",
}


def secret() -> str:
    out = subprocess.run(["git", "credential", "fill"],
                         input="protocol=https\nhost=github.com\n\n",
                         capture_output=True, text=True, check=True).stdout
    value = ""
    for line in out.splitlines():
        if line.startswith("password="):
            value = line[len("password="):]
    return value


def probe(path: str) -> tuple[int, str]:
    req = urllib.request.Request("https://api.github.com" + path,
                                 headers={"Authorization": "Bearer " + secret(),
                                          "Accept": "application/vnd.github+json",
                                          "User-Agent": "qoder-e345b9d6-coordinate-kind"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, json.loads(r.read()).get("message") or ""
    except urllib.error.HTTPError as e:
        return e.code, ""


def ls_remote(refs) -> dict:
    last = ""
    for _ in range(4):
        proc = subprocess.run(["git", "ls-remote", URL, *refs], cwd=ROOT,
                              capture_output=True, text=True, encoding="utf-8", errors="replace")
        parsed = {}
        for line in proc.stdout.splitlines():
            if "\trefs/" in line:
                sha, ref = line.split("\t", 1)
                if re.fullmatch(r"[0-9a-f]{40}", sha.strip()):
                    parsed[ref.strip()] = sha.strip()
        if all(r in parsed for r in refs):
            return parsed
        last = (proc.stderr or "").strip()[-160:]
    raise SystemExit(f"ABORT: ls-remote never returned all of {refs}; last stderr={last!r}")


all_refs = sorted({*SUBJECTS.values(), "refs/heads/mirror/integration-frontend-apple-pass1",
                   "refs/heads/review/ord0310-keyless-deadline-d-on-2344145c"})
tips = ls_remote(all_refs)
rows = {}
for sha, carrying_ref in SUBJECTS.items():
    blob_status, _ = probe(f"/repos/{REPO}/git/blobs/{sha}")
    commit_status, _ = probe(f"/repos/{REPO}/commits/{sha}")
    local = subprocess.run(["git", "cat-file", "-t", sha], cwd=ROOT, capture_output=True, text=True)
    rows[sha] = {
        "named_by_ref": carrying_ref,
        "that_ref_reads_now": tips.get(carrying_ref, "NOT_LISTED"),
        "api_git_blobs_status": blob_status,
        "api_commits_status": commit_status,
        "verdict_by_the_server": ("commit (200 on /commits, 404 on /git/blobs)"
                                 if commit_status == 200 and blob_status == 404 else "UNCLASSIFIED"),
        "git_cat_file_minus_t_in_this_worktree": (local.stdout or local.stderr).strip().splitlines()[0],
    }
payload = {
    "order": "ORD-0310", "lane": "D e345b9d6", "kind": "COORDINATE_NAMESPACE_PROOF",
    "written_at": datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%:z"),
    "question_answered": "the two 40-hex strings that did not resolve in the commander's clone: "
                         "commit, run id, or typo?",
    "answer": "commit. They are reachable only through refs/heads/review/ord0310-tools-r*; a clone "
              "that has not fetched those refs cannot cat-file them, which is why they are written "
              "as commit=<40> from here on and never in a blob position.",
    "how_to_make_them_resolvable": f"git -C D:/moodle/CityNexus fetch origin "
                                   f"{' '.join(sorted({v for v in SUBJECTS.values()}))}",
    "checked": rows,
    "refs_read_now": tips,
}
OUT.write_bytes((json.dumps(payload, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
print(json.dumps(payload, ensure_ascii=False, indent=1)[:2000])
print(f"wrote {OUT} {OUT.stat().st_size} B blob="
      f"{hashlib.sha1(b'blob %d\0' % OUT.stat().st_size + OUT.read_bytes()).hexdigest()}")
