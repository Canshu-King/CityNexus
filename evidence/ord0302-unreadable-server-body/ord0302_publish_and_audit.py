"""Publish the ORD-0302 independent read-back, then audit EVERY blob the index claims.

The delivery script proves each file it writes; it cannot prove the index it rebuilt at the end (the receipt
changed after the first index was written, and an index cannot pin its own bytes). This reads the branch and
recomputes a git blob sha1 for every entry, so a stale listing shows up as a finding instead of a sentence.
"""
import hashlib
import json
import pathlib
import subprocess
import sys
import time
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0274sw_20260924")
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
PUBLISHER = pathlib.Path(r"D:\moodle\_qoder_f_run\publish_evidence_fixed.py")
GH, BRC = "Canshu-King/CityNexus", "commander/control"
DIR = "evidence/ord0302-unreadable-server-body"
tok = pathlib.Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(encoding="utf-8").strip()
VERIFY = (WORK / "ord0302_verify_published.json", "ord0302_verify_published.json")
IP = WORK / "ord0302_index.json"


def blob_of(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()


def fetch(name):
    """Return (bytes, blob40) as the branch answers them, or None if the path is not there."""
    url = f"https://api.github.com/repos/{GH}/contents/{DIR}/{urllib_parse_quote(name)}?ref={BRC}"
    last = None
    for i in range(8):
        try:
            req = urllib.request.Request(url, headers={"Authorization": "Bearer " + tok,
                                                       "Accept": "application/vnd.github+json",
                                                       "User-Agent": "citynexus-lane-B-audit"})
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.loads(r.read().decode("utf-8", "replace") or "{}")
            import base64
            raw = base64.b64decode(d["content"])
            if blob_of(raw) != d["sha"]:
                raise ValueError("the answer is not its own blob: " + name)
            return raw, d["sha"]
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return None
            last = e
        except Exception as e:
            last = e
        time.sleep(2 + 3 * i)
    raise last


def urllib_parse_quote(name):
    import urllib.parse
    return urllib.parse.quote(name, safe="")


def push(path, name):
    for attempt in range(4):
        pr = subprocess.run([PY, str(PUBLISHER), str(path), f"{DIR}/{name}", f"ORD-0302: {name}"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        txt = (pr.stdout or "") + (pr.stderr or "")
        if pr.returncode == 0 and ("BYTE-LEVEL MATCH" in txt or "already identical" in txt):
            return
        print(f"attempt {attempt} rc={pr.returncode}: {txt[-160:]!r}")
        time.sleep(5 + 5 * attempt)
    raise SystemExit("would not claim a publish the publisher never proved: " + name)


push(*VERIFY)
idx = json.loads(IP.read_text(encoding="utf-8"))
entries = {e["name"]: e for e in idx["files"]}
raw, want = fetch(VERIFY[1])
entries[VERIFY[1]] = {"name": VERIFY[1], "blob40": want, "bytes": len(raw)}
# The two instruments that made these readings are part of the evidence: a reviewer should be able to run
# them, so they go up too and are listed by the blob the BRANCH answers, not the blob I hope for.
for script in ("ord0302_verify_published.py", "ord0302_publish_and_audit.py"):
    p = pathlib.Path(__file__).with_name(script)
    push(p, script)
    raw, want = fetch(script)
    entries[script] = {"name": script, "blob40": want, "bytes": len(raw)}
idx["files"] = [entries[k] for k in sorted(entries)]
idx["audit"] = "every blob in this list was recomputed from the branch's own answer by ord0302_publish_and_audit.py"
IP.write_text(json.dumps(idx, ensure_ascii=False, indent=1), "utf-8", newline="\n")
push(IP, IP.name)

listed = json.loads(fetch(IP.name)[0])["files"]
bad = []
for e in listed:
    got = fetch(e["name"])
    if got is None:
        bad.append((e["name"], "ABSENT"))
        continue
    if got[1] != e["blob40"]:
        bad.append((e["name"], f"{got[1][:12]} != {e['blob40'][:12]}"))
print(f"index {IP.name} answers {fetch(IP.name)[1][:12]} | local {blob_of(IP.read_bytes())[:12]}"
      f" | entries {len(listed)} | mismatches {len(bad)}")
for n, why in bad:
    print("  MISMATCH", n, why)
sys.exit(0 if not bad and fetch(IP.name)[1] == blob_of(IP.read_bytes()) else 1)
