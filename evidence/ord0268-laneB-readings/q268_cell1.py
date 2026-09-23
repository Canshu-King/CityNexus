"""ORD-0268 cell 1 (mechanical): the two shell entries inside ONE precache manifest, read from two real
consecutive generations, no source edited by me.

gen A = the tree at d2665e25855aeb265329266831983de42321697d   (already exported + built earlier)
gen B = the tree at 2b49e3cab1fcdbc55219065520ced8dea4fdfe73   (landed tip, exported and built here)

Both are `git archive` exports built with the repo's own vite build. The point: the manifest carries the
same shell twice with two different revision *shapes* -- one content-derived (changes per generation),
one the hand-written constant `v10-shell` (must not change) -- so a duplicate-URL winner question is
mechanically visible before any behaviour is argued about.
"""
from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
REPO = pathlib.Path(r"D:\moodle\_qoder_integration_20260919")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0268_20260923")
TIP_A = "d2665e25855aeb265329266831983de42321697d"
TIP_B = "2b49e3cab1fcdbc55219065520ced8dea4fdfe73"
NM = pathlib.Path(r"D:\moodle\_qoder_integration_20260919\frontend\node_modules")


def sh(args, cwd=None, timeout=1200) -> subprocess.CompletedProcess:
    return subprocess.run(args, cwd=cwd, capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=timeout)


def export(tip: str, dest: pathlib.Path) -> None:
    if (dest / "frontend" / "index.html").exists():
        return
    dest.mkdir(parents=True, exist_ok=True)
    p = subprocess.run(["git", "-C", str(REPO), "archive", "--format=tar", tip,
                        "frontend", "data", "contracts", "backend"], capture_output=True)
    assert p.returncode == 0, p.stderr[:200]
    subprocess.run(["tar", "-x", "-C", str(dest)], input=p.stdout, check=True)


def build(frontend: pathlib.Path, outdir: str) -> pathlib.Path:
    link = frontend / "node_modules"
    if not link.exists():
        sh(["powershell", "-NoProfile", "-Command",
            f"New-Item -ItemType Junction -Path '{link}' -Target '{NM}'"])
    r = sh(["node", "node_modules/vite/bin/vite.js", "build", "--outDir", outdir],
           cwd=str(frontend), timeout=1200)
    assert r.returncode == 0, (r.stdout or "")[-400:] + (r.stderr or "")[-400:]
    return frontend / outdir


def manifest(dist: pathlib.Path) -> list[dict]:
    src = (dist / "v10-sw.js").read_text(encoding="utf-8")
    m = re.search(r"precacheAndRoute\(\[(.*?)\],\{\}\)", src, re.S)
    body = m.group(1)
    return [{"url": u, "revision": (rev_q if rev_q is not None else rev_raw)}
            for u, rev_q, rev_raw in re.findall(r'\{url:"([^"]+)",revision:(?:"([^"]*)"|([^,}]+))\}', body)]


def blob(b: bytes) -> str:
    return hashlib.sha1(b"blob %d\x00" % len(b) + b).hexdigest()


A = WORK / "genA" / "frontend"
B = WORK / "genB" / "frontend"
export(TIP_A, A.parent)
export(TIP_B, B.parent)
distA = build(A, "dist_ord0268")
distB = build(B, "dist_ord0268")

mA, mB = manifest(distA), manifest(distB)


def urls(entries):
    seen, dup = {}, []
    for e in entries:
        norm = "/" + e["url"].lstrip("/")
        if norm in seen:
            dup.append({"normalized_url": norm, "first": seen[norm], "also": e["url"],
                        "same_raw_string": seen[norm] == e["url"]})
        else:
            seen[norm] = e["url"]
    return dup


def index_hash(dist):
    return blob((dist / "index.html").read_bytes())


out = {
  "at": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"), "order": "ORD-0268 cell 1 (mechanical)",
  "lane": "B c01d72a3", "how": "git archive <tip> of two real consecutive tips + repo's own vite build; "
                                "no source edited, no product file touched",
  "generations": {"A_tip": TIP_A, "B_tip": TIP_B,
                  "A_index_html_blob40": index_hash(distA), "B_index_html_blob40": index_hash(distB),
                  "A_script_tags": sorted(re.findall(r"assets/[A-Za-z0-9._-]+\.(?:js|css)",
                                                     (distA / "index.html").read_text(encoding="utf-8"))),
                  "B_script_tags": sorted(re.findall(r"assets/[A-Za-z0-9._-]+\.(?:js|css)",
                                                     (distB / "index.html").read_text(encoding="utf-8")))},
  "manifest_A": mA, "manifest_B": mB,
  "counts": {"A": len(mA), "B": len(mB)},
  "duplicate_shell_entries": {"A": urls(mA), "B": urls(mB)},
  "revisions_that_did_not_change_between_generations":
      [e["url"] for e in mA if any(f["url"] == e["url"] and f["revision"] == e["revision"] for f in mB)],
  "revisions_that_did_change": [e["url"] for e in mA
                                if any(f["url"] == e["url"] and f["revision"] != e["revision"] for f in mB)],
  "the_shell_pair_read_verbatim": {
      "content_derived": [e for e in mB if e["url"] == "index.html"],
      "hand_written_constant": [e for e in mB if e["url"] == "/index.html"],
      "vite_config_line_that_adds_it": [ln.strip() for ln in
          (B / "vite.config.ts").read_text(encoding="utf-8").splitlines()
          if "additionalManifestEntries" in ln]},
  "sw_js_entry_note": {"url": "sw.js", "points_at": "frontend/public/sw.js",
                       "bytes": (B / "public" / "sw.js").stat().st_size if (B / "public" / "sw.js").exists() else None,
                       "registered_only_in_dev_branch": "main.tsx register(\"/sw.js\") sits under import.meta.env.DEV"},
}
p = WORK / "q268_cell1.json"
p.write_text(json.dumps(out, ensure_ascii=False, indent=1), "utf-8", newline="\n")
print("generations:", json.dumps(out["generations"], ensure_ascii=False, indent=1)[:700])
print("dup A:", json.dumps(out["duplicate_shell_entries"]["A"], ensure_ascii=False))
print("dup B:", json.dumps(out["duplicate_shell_entries"]["B"], ensure_ascii=False))
print("revisions unchanged across generations:", json.dumps(out["revisions_that_did_not_change_between_generations"], ensure_ascii=False))
print("revisions changed:", json.dumps(out["revisions_that_did_change"], ensure_ascii=False))
print("shell pair:", json.dumps(out["the_shell_pair_read_verbatim"], ensure_ascii=False)[:600])
print("->", p)
