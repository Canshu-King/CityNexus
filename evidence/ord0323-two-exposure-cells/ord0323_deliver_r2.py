"""ORD-0323 delivery: publish the evidence, build a receipt whose cells justify themselves, hand the block
to the ledger inbox (Q63=③: lanes do not write the ledger), then knock on the bus.

Every number in the prose is read back out of the artifacts this order produced -- the arms matrix, the r3
reading files, the per-arm evidence, git's own answers. `cite()` moves each value a sentence names into that
cell's own record or aborts; Q38 grades the cells; Q43 grades the prose; and every 40-hex coordinate is
resolved with `git cat-file -t` after fetching all branches.

stages: publish -> receipt -> block -> post  (run with --stage, or no argument for all four in order)
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
import urllib.request

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import ord0299_cite as C  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
LANE = pathlib.Path(r"D:\moodle\_qoder_b_lane_20260923")
FROZEN = pathlib.Path(r"D:\moodle\CityNexus")
SPIKE = pathlib.Path(r"D:\moodle\_qoder_spike_20260921")
WORK = pathlib.Path(r"D:\moodle\_qoder_b_ord0323_20260926")
INBOX = pathlib.Path(r"D:\moodle\_qoder_ledger_inbox")
PUBLISHER = pathlib.Path(r"D:\moodle\_qoder_f_run\publish_evidence_fixed.py")
LIVE = pathlib.Path(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks")
Q38 = LIVE / "receipt_cell_derivation_check_r2.py"
Q43S = [LIVE / "claim_coordinate_check_r3.py", LIVE / "claim_coordinate_check_r4b.py"]
CLOSING = (LIVE / "CLOSING_LINE.txt").read_text(encoding="utf-8").strip()
PY = r"D:\moodle\CityNexus\.venv\Scripts\python.exe"
GH, BRC = "Canshu-King/CityNexus", "commander/control"
WS = "Canshu-King/CityNexus-Workspace"
DIR = "evidence/ord0323-two-exposure-cells"
BRANCH = os.environ.get("CNX_0323_BRANCH", "review/0323-ten-cells-b")
PREV_BRANCH = "review/0323-two-exposure-cells-b"   # the two-cell candidate, published and left where it is
PREV_CAND = "e302e4c433712284a23c1c0ab11147fe105e1e22"
URL = "git@github.com:Canshu-King/CityNexus.git"
BASE = "9a669c8bec863fadf31d5158f4a1be66aec49f23"
R3_BLOB = "44e062e6ce9c7b5d97d78e09e432072da102292c"
R4_BLOB = "eb262f59e54d5142ad0e8041704e751eac473ace"
CELL1 = "frontend/src/components/ProductErrorBoundary.tsx"
CELL2 = "frontend/src/features/inbox/JourneyInboxWorkbench.tsx"
SPEC = "frontend/e2e/qoder-ord0323-two-exposure-cells.spec.ts"
PATS = C.ruler_patterns()
tok = pathlib.Path(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920").read_text(encoding="utf-8").strip()


def g(args):
    return subprocess.run(["git", "-C", str(LANE), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


def blob_of(path_or_bytes):
    b = path_or_bytes if isinstance(path_or_bytes, bytes) else pathlib.Path(path_or_bytes).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(b) + b).hexdigest()


def api(path, data=None):
    last = None
    for i in range(8):
        try:
            req = urllib.request.Request("https://api.github.com" + path,
                                         data=(json.dumps(data).encode() if data else None),
                                         headers={"Authorization": "Bearer " + tok,
                                                  "Accept": "application/vnd.github+json",
                                                  "Content-Type": "application/json",
                                                  "User-Agent": "citynexus-lane-B"},
                                         method=("POST" if data else "GET"))
            with urllib.request.urlopen(req, timeout=150) as r:
                raw = r.read()
            if not raw and data is None:
                raise OSError("zero-byte answer")
            return json.loads(raw.decode("utf-8", "replace") or "{}")
        except urllib.error.HTTPError as e:
            if e.code in (403, 404):
                raise
            last = e
        except OSError as e:
            last = e
        time.sleep(2 + 4 * i)
    raise last


def push(local, name):
    for attempt in range(4):
        pr = subprocess.run([PY, str(PUBLISHER), str(local), f"{DIR}/{name}",
                             f"ORD-0323 lane B: publish {name}"],
                            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
        txt = (pr.stdout or "") + (pr.stderr or "")
        if pr.returncode == 0 and ("BYTE-LEVEL MATCH" in txt or "already identical" in txt):
            return
        if "REFUSED" in txt.upper() or "FORBIDDEN" in txt.upper():
            raise SystemExit("publisher refused " + name + ": " + txt[-240:])
        time.sleep(4 + 4 * attempt)
    raise SystemExit("would not claim an unpublishable file: " + name)


def gate(text, label):
    p = WORK / "gate_input.txt"
    p.write_text(text, "utf-8", newline="\n")
    outs = {}
    for ruler in Q43S:
        r = subprocess.run([PY, str(ruler), "--text", str(p)], capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=300)
        outs[ruler.name] = {"rc": r.returncode, "output": ((r.stdout or "") + (r.stderr or "")).strip()}
    for k, v in outs.items():
        print(f"Q43 {k} [{label}]: rc={v['rc']} "
              f"{[l for l in v['output'].splitlines() if 'claims checked' in l][:1]}")
    bad = {k: v for k, v in outs.items() if v["rc"] != 0}
    if bad:
        for k, v in bad.items():
            print(v["output"][:1800])
        raise SystemExit(f"a claim gate refused the {label}")
    return {k: "rc0" for k in outs}


def q38(path):
    r = subprocess.run([PY, str(Q38), "--receipt", str(path), "--min-cells", "4"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600)
    out = ((r.stdout or "") + (r.stderr or "")).strip()
    return {"rc": r.returncode, "green": "Q38_GATE_GREEN" in out,
            "headline": [l for l in out.splitlines() if l.startswith("cells ")][:1],
            "output": out[:1500]}


# ------------------------------------------------------------------ state, read from git right now
CAND = g(["rev-parse", "HEAD"])
COMMITS = int(g(["rev-list", "--count", f"{BASE}..HEAD"]))
CHANGED = [l for l in g(["diff", "--name-only", f"{BASE}..HEAD"]).splitlines() if l]
# The candidate sits on the live tip, so BASE..HEAD also carries the orders that landed there before me.
# Only commits this order signed are "my" changes; quoting the wider set would claim their files as mine.
_LOG = [l.split("\t", 1) for l in g(["log", "--format=%H\t%s", f"{BASE}..HEAD"]).splitlines() if l]
OWN_COMMITS = [h for h, s in _LOG if s.startswith("ORD-0323")]
FOREIGN_COMMITS = [h[:12] for h, s in _LOG if not s.startswith("ORD-0323")]
OWN_FILES = sorted({f for c in OWN_COMMITS
                    for f in g(["show", "--name-only", "--format=", c]).splitlines() if f})
if g(["status", "--porcelain", "frontend/src", "frontend/e2e"]):
    raise SystemExit("my own tree is dirty; the blobs I would quote are not the committed ones")
if subprocess.run(["git", "-C", str(LANE), "merge-base", "--is-ancestor", BASE, "HEAD"],
                  capture_output=True).returncode != 0:
    raise SystemExit(f"{BASE[:12]} is not an ancestor of {CAND[:12]}")
MATRIX_NAME = "ord0323_arms_matrix_r3.json"   # rebuilt from the pass's own per-arm evidence, because that pass
# ran before the runner stopped filtering readings; the file names the candidate it measured inside itself.
MATRIX = json.loads((WORK / MATRIX_NAME).read_text(encoding="utf-8"))
R3 = json.loads((WORK / "ord0323_r3_readings.json").read_text(encoding="utf-8"))
if R3["generations"]["after"] != CAND or MATRIX["measurement_scope"]["generation"]["candidate"] != CAND:
    raise SystemExit("an artifact was measured against a different commit than HEAD; re-run it before quoting it")
SH, REA = MATRIX["shapes"], MATRIX["per_arm_readings"]
LEG_KEYS = ("T06", "T07", "T08", "T09", "T10", "T11", "T12", "T13")
ARM_KEYS = ("N1", "N2", "N3") + LEG_KEYS + ("Q68a", "Q68b")
PUBLISHED = []
_rows = WORK / "ord0323_publish_rows.json"
if _rows.exists():
    # a later stage runs in its own process; the index and the block have to quote the same published set
    PUBLISHED.extend(json.loads(_rows.read_text(encoding="utf-8")))
    print("reloaded", len(PUBLISHED), "published rows from", _rows.name)
# git's own blob id, not a re-hash of captured stdout: the first receipt quoted `blob_of(git show ...)`,
# and `g()` strips the file's final newline, so those five ids were sha1s of a truncated byte string and
# resolved nowhere. r2 quotes rev-parse; the was/now pair is disclosed in the receipt and in the block.
def revblob(ref, path):
    return g(["rev-parse", f"{ref}:{path}"])


REV = os.environ.get("CNX_0323_REV", "r2")
ERRATUM_BLOBS = {
    "spec@candidate": {"r1_wrong": blob_of(g(["show", f"{CAND}:{SPEC}"]).encode("utf-8")),
                       "r2_true": revblob(CAND, SPEC)},
    "ProductErrorBoundary@base": {"r1_wrong": blob_of(g(["show", f"{BASE}:{CELL1}"]).encode("utf-8")),
                                  "r2_true": revblob(BASE, CELL1)},
    "ProductErrorBoundary@candidate": {"r1_wrong": blob_of(g(["show", f"{CAND}:{CELL1}"]).encode("utf-8")),
                                       "r2_true": revblob(CAND, CELL1)},
    "JourneyInboxWorkbench@base": {"r1_wrong": blob_of(g(["show", f"{BASE}:{CELL2}"]).encode("utf-8")),
                                   "r2_true": revblob(BASE, CELL2)},
    "JourneyInboxWorkbench@candidate": {"r1_wrong": blob_of(g(["show", f"{CAND}:{CELL2}"]).encode("utf-8")),
                                        "r2_true": revblob(CAND, CELL2)},
}
CELL1_BLOB = revblob(BASE, CELL1)
CELL1_CAND_BLOB = revblob(CAND, CELL1)
CELL2_BLOB = revblob(BASE, CELL2)
CELL2_CAND_BLOB = revblob(CAND, CELL2)
SPEC_CAND_BLOB = revblob(CAND, SPEC)
spec_src = g(["show", f"{CAND}:{SPEC}"]).splitlines()
SKIP_HITS = [i + 1 for i, l in enumerate(spec_src) if re.search(r"\b(test\.skip|test\.fixme|\.skipIf|expect\.configure)", l)]
EXPECT_CALLS = sum(l.count("expect(") for l in spec_src)
print("candidate", CAND, "commits above base", COMMITS, "changed", len(CHANGED),
      "matrix", MATRIX["verdict"], "skip lines", SKIP_HITS, "expect calls", EXPECT_CALLS)

# ---------------------------------------------------------------- what the order did NOT name, measured
ADJ = {}
for label, path, needles in (
    ("requestJson_unguarded_json_parse", CELL2, ["const payload = (await response.json())"]),
    ("showResult_server_reason_to_message", CELL2, ["result.reason ??"]),
    ("reasoning_summary_to_dom", CELL2, ["{item.reasoning_summary &&", "{draft.interpretation?.reasoning_summary &&"]),
    ("boundary_copy_locale_source", CELL1, ["const lang = (typeof navigator"]),
):
    src = g(["show", f"{CAND}:{path}"]).splitlines()
    ADJ[label] = {"file": path, "lines": [i + 1 for i, l in enumerate(src) for n in needles if n in l],
                  "text": [src[i].strip() for i in range(len(src)) if any(n in src[i] for n in needles)]}


# ------------------------------------------------------------------ the authority line, read live, then re-read after my push
AUTH_REF = "refs/heads/mirror/integration-frontend-apple-pass1"   # the commander's own name for 现尖 (CMDR 04:05)
WATCHED = (AUTH_REF, "refs/heads/cmdr/land-ord0302-b5", "refs/heads/commander/control")


def lsremote(refs):
    out = subprocess.run(["git", "ls-remote", URL, *refs], capture_output=True, text=True,
                         encoding="utf-8", errors="replace", timeout=300,
                         env={**os.environ, "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}).stdout
    answers = {}
    for line in out.splitlines():
        if "\t" in line:
            sha, ref = line.split("\t", 1)
            answers[ref.strip()] = sha.strip()
    return answers


AUTHORITY_BEFORE = lsremote(WATCHED)
PUSHED = False
if not os.environ.get("CNX_0323_SKIP_PUSH"):
    pr = subprocess.run(["git", "-C", str(LANE), "push", URL, f"refs/heads/{BRANCH}:refs/heads/{BRANCH}"],
                        capture_output=True, text=True, encoding="utf-8", errors="replace",
                        env={**os.environ, "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}, timeout=900)
    PUSHED = pr.returncode == 0
    print("push rc", pr.returncode, (pr.stdout or "") + (pr.stderr or "")[-300:])
    if not PUSHED:
        raise SystemExit("the candidate ref did not land; nothing further is claimed")
lsr = subprocess.run(["git", "ls-remote", URL, f"refs/heads/{BRANCH}"], capture_output=True, text=True,
                     env={**os.environ, "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}, timeout=300).stdout.strip()
REMOTE_SHA = lsr.split("\t")[0].strip() if lsr else ""
if REMOTE_SHA != CAND:
    raise SystemExit(f"the remote answers {REMOTE_SHA[:12]}, not my candidate {CAND[:12]}")
AUTHORITY_AFTER = lsremote(WATCHED)
MOVED = {ref: {"before": AUTHORITY_BEFORE.get(ref), "after": AUTHORITY_AFTER.get(ref)}
         for ref in WATCHED if AUTHORITY_BEFORE.get(ref) != AUTHORITY_AFTER.get(ref)}
# Fetch what the authority line answers now, into this lane's own object store, so the coexistence
# numbers below are measured against it rather than against the tip that was current when I started.
subprocess.run(["git", "-C", str(LANE), "fetch", "-q", URL, f"+{AUTH_REF}:refs/cnx/authority"],
               capture_output=True, text=True, timeout=900,
               env={**os.environ, "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"})
NEW_TIP = (AUTHORITY_AFTER.get(AUTH_REF) or "")
if not NEW_TIP:
    raise SystemExit("the authority ref answered nothing; I would be guessing at the generation")
if subprocess.run(["git", "-C", str(LANE), "cat-file", "-t", NEW_TIP], capture_output=True).returncode != 0:
    raise SystemExit(f"{NEW_TIP} did not fetch into this lane; not claiming a reading against it")
TIP_META = g(["log", "-1", "--format=%h %ad %an %s", "--date=format:%H:%M", NEW_TIP])
for ref, m in MOVED.items():
    if ref == AUTH_REF:
        continue
    subprocess.run(["git", "-C", str(LANE), "fetch", "-q", URL, f"+{ref}:refs/cnx/watch"],
                   capture_output=True, timeout=900,
                   env={**os.environ, "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"})
    m["new_commit_by"] = g(["log", "-1", "--format=%an %s", "refs/cnx/watch"]) if m["after"] else None
    m["mine"] = bool(m["after"]) and CAND in (m["after"] or "")
MOVES_NOT_MINE = all((not m.get("mine", True)) for m in MOVED.values())
PUSH_TARGETS = [f"refs/heads/{BRANCH}"]
print("remote ref ok:", REMOTE_SHA, "| refs that moved during my run:", json.dumps(MOVED, ensure_ascii=False)[:220])
print("authority line now:", TIP_META)
if not MOVES_NOT_MINE:
    raise SystemExit("a watched ref answers with my own commit; the single-writer claim would be false")

# ------------------------------------------------------------------ the coexistence proof against that tip
TIP_GAP = int(g(["rev-list", "--count", f"{BASE}..{NEW_TIP}"])) if subprocess.run(
    ["git", "-C", str(LANE), "merge-base", "--is-ancestor", BASE, NEW_TIP], capture_output=True).returncode == 0 else None
TIP_FILES = g(["diff", "--name-only", BASE, NEW_TIP]).splitlines() if TIP_GAP is not None else []
TIP_FRONTEND = [f for f in TIP_FILES if f.startswith("frontend/")]
BLOB_PAIR = {p: {"at_ordered_base": g(["rev-parse", f"{BASE}:{p}"]),
                 "at_live_tip": g(["rev-parse", f"{NEW_TIP}:{p}"]) if TIP_GAP is not None else "unreachable"}
             for p in (CELL1, CELL2)}
MT = subprocess.run(["git", "-C", str(LANE), "merge-tree", "--write-tree", NEW_TIP, BRANCH],
                    capture_output=True, text=True, encoding="utf-8", errors="replace")
mt_lines = [l for l in (MT.stdout or "").splitlines() if l]
PREDICT = {"rc": MT.returncode, "predicted_tree": mt_lines[0] if mt_lines else None,
           "conflict_lines": len([l for l in mt_lines[1:] if "\t" in l]) if len(mt_lines) > 1 else 0}
print("live tip", NEW_TIP[:12], "gap", TIP_GAP, "frontend files touched", len(TIP_FRONTEND),
      "merge-tree rc", PREDICT["rc"], "conflicts", PREDICT["conflict_lines"])


# ------------------------------------------------------------------ reachability and the request_id gap
MAIN = g(["show", f"{BASE}:backend/app/main.py"])
MAIN_LINES = len(MAIN.splitlines())
REQ_ID = {
    "main_py_at_base": {"path": "backend/app/main.py", "lines": MAIN_LINES,
                        "request_id_hits": MAIN.count("request_id"),
                        "require_404_line": [i + 1 for i, l in enumerate(MAIN.splitlines())
                                             if "was not found" in l][:1],
                        "require_404_text": [l.strip() for l in MAIN.splitlines() if "was not found" in l][:1]},
    "agent_domain_hits_file": "backend/app/agent/contracts.py",
    "agent_domain_hit_lines": [i + 1 for i, l in enumerate(
        g(["show", f"{BASE}:backend/app/agent/contracts.py"]).splitlines()) if "request_id" in l],
}
BASE_JIW = g(["show", f"{BASE}:{CELL2}"]).splitlines()
CAND_JIW = g(["show", f"{CAND}:{CELL2}"]).splitlines()


def _lines(src, needle):
    return [i + 1 for i, l in enumerate(src) if needle in l]


REACH = {
    "mount_effects_at_base": _lines(BASE_JIW, "void loadMemory();")[:1] + _lines(BASE_JIW, "void readInbox();")[:1],
    "mount_effects_at_candidate": _lines(CAND_JIW, "void loadMemory();")[:1] + _lines(CAND_JIW, "void readInbox();")[:1],
    "no_click_needed_proof": "N2 那一趟没有任何点击：GET .../memory 与 GET .../inbox 在挂载时被回答成 "
                             "500/503，改前的屏幕上就出现了服务器那句原文",
    "shape": "cell2_baseline_throw",
}
print("request_id in main.py:", REQ_ID["main_py_at_base"]["request_id_hits"], "of", MAIN_LINES, "lines;",
      "mount effects", REACH["mount_effects_at_base"], "->", REACH["mount_effects_at_candidate"])

# The two source sites the prose names by line number, located per generation instead of typed.
Q68_SHEET_FILE = "frontend/src/features/planning/PlanWithAiSheet.tsx"
CELL2_ORIGIN_BASE = _lines(BASE_JIW, "payload.error?.message ?? payload.detail")
CELL2_ORIGIN_CAND = _lines(CAND_JIW, "payload.error?.message ?? payload.detail")
_SHEET_NEEDLE = "detail.slice(0, 60).toUpperCase()"
Q68_FALLBACK_BASE = _lines(g(["show", f"{BASE}:{Q68_SHEET_FILE}"]).splitlines(), _SHEET_NEEDLE)
Q68_FALLBACK_CAND = _lines(g(["show", f"{CAND}:{Q68_SHEET_FILE}"]).splitlines(), _SHEET_NEEDLE)
print("origin throw line", CELL2_ORIGIN_BASE, "->", CELL2_ORIGIN_CAND,
      "| Q68 fallback line", Q68_FALLBACK_BASE, "->", Q68_FALLBACK_CAND)

# ------------------------------------------------------------------ the superseding ruler, and the channel that already exists
R4 = json.loads((WORK / "ord0323_r4_readings.json").read_text(encoding="utf-8"))
if R4["generations"]["after"] != CAND:
    raise SystemExit("r4 was measured against a different commit than HEAD")
R5 = json.loads((WORK / "ord0323_r5_readings.json").read_text(encoding="utf-8"))
if R5["generations"]["after"] != CAND or R5["generations"]["before"] != BASE:
    raise SystemExit("r5 was measured against a different generation pair than the one this order names")
R6 = json.loads((WORK / "ord0323_r6_readings.json").read_text(encoding="utf-8"))
if R6["generations"]["after"] != CAND or R6["generations"]["before"] != BASE:
    raise SystemExit("r6 was measured against a different generation pair than the one this order names")
CHANNEL_FILE = "frontend/src/lib/failureAttribution.ts"
CH_SRC = g(["show", f"{CAND}:{CHANNEL_FILE}"]).splitlines()
CHANNEL = {
    "path": CHANNEL_FILE, "lines": len(CH_SRC),
    "exports_helpers": [i + 1 for i, l in enumerate(CH_SRC) if l.startswith("export function classifyReadFailure")],
    "typed_error_class": [i + 1 for i, l in enumerate(CH_SRC)
                          if l.startswith("export class OriginResponseUnusableError")],
    "importers_in_src": [l.split(":", 1)[1] for l in subprocess.run(
        ["git", "-C", str(LANE), "grep", "-l", "failureAttribution", CAND, "--", "frontend/src"],
        capture_output=True, text=True).stdout.splitlines()],
    "journey_inbox_workbench_uses_it": "failureAttribution" in g(["show", f"{CAND}:{CELL2}"]),
}
print("r4 per file:", json.dumps(R4["per_file_lines"], ensure_ascii=False)[:160])
print("channel importers:", CHANNEL["importers_in_src"], "this file uses it:",
      CHANNEL["journey_inbox_workbench_uses_it"])

# ------------------------------------------------------------------ the ten-cell expansion's own facts
PARENT_LIVE = g(["rev-parse", "HEAD^"])
TRIAGE_BLOB = "36feb4ae91c61dcadecc117ed3a741ad46052210"
_triage = json.loads((WORK / "ord0320_triage_d_r2.json").read_text(encoding="utf-8"))
TRIAGE_ROWS = [r for r in _triage["rows"] if r["file"] == CELL2]
TRIAGE_CELLS = {r["id"]: r["ruler_anchor_line"] for r in TRIAGE_ROWS}
CELL2_BASE_BLOB = revblob(PARENT_LIVE, CELL2)
RECUT_ROWS = []
for _p in (CELL1, CELL2, SPEC):
    _a, _b = revblob(PREV_CAND, _p), revblob(CAND, _p)
    RECUT_ROWS.append({"file": _p, "at_prev_candidate": _a, "at_candidate": _b,
                       "byte_identical": _a == _b})
RECUT_BLOBS = {r["file"].split("/")[-1]: {PREV_CAND[:8]: r["at_prev_candidate"],
                                          CAND[:8]: r["at_candidate"]} for r in RECUT_ROWS}
RECUT_SAME = {r["file"]: r["byte_identical"] for r in RECUT_ROWS}
_prev_ls = subprocess.run(["git", "ls-remote", URL, f"refs/heads/{PREV_BRANCH}"], capture_output=True,
                          text=True, encoding="utf-8", timeout=300,
                          env={**os.environ, "GIT_SSH_COMMAND": "ssh -o BatchMode=yes"}).stdout.strip()
PREV_REMOTE = _prev_ls.split("\t")[0].strip() if _prev_ls else ""
print("triage cells:", json.dumps(TRIAGE_CELLS, ensure_ascii=False),
      "| recut blob identity:", all(len(set(v.values())) == 1 for v in RECUT_BLOBS.values()),
      "| prev remote:", PREV_REMOTE[:12])
