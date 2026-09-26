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
PREV_CAND = os.environ.get("CNX_0323_PREV_CAND", "106195159dbbffd948763299e572905dff19ee16")
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


def arm_name(shape, arm):
    return f"arm__{EV}_{shape}__{arm}.json"


def report_name(shape):
    return f"playwright_report__{EV}_{shape}.json"


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
MATRIX_PUB = "ord0323_arms_matrix_r6.json"   # this pass's published aggregate coordinate
MATRIX_PUB = "ord0323_arms_matrix_r6.json"   # this pass's published aggregate coordinate
MATRIX_NAME = "ord0323_arms_matrix_r4.json"   # the runner's own aggregate, which now carries every field each
# arm wrote; r1/r2/r3 stay on the review ref as the coordinates of the earlier candidates they measured.
MATRIX = json.loads((WORK / MATRIX_NAME).read_text(encoding="utf-8"))
R3 = json.loads((WORK / "ord0323_r3_readings.json").read_text(encoding="utf-8"))
if R3["generations"]["after"] != CAND or MATRIX["measurement_scope"]["generation"]["candidate"] != CAND:
    raise SystemExit("an artifact was measured against a different commit than HEAD; re-run it before quoting it")
EV = "r3"  # coordinate suffix of this measurement pass; published paths are never rewritten
SH, REA = MATRIX["shapes"], MATRIX["per_arm_readings"]
LEG_KEYS = ("T06", "T07", "T08", "T09", "T10", "T11", "T12", "T13")
ARM_KEYS = ("N1", "N2", "N3") + LEG_KEYS + ("Q68a", "Q68b", "Q68c", "Q68d")
PUBLISHED = []
# what the publisher actually wrote, keyed by the local file's own name; the r3 pass may still
# self-revise a name, and a quote must follow that, not the name we first asked for.
PUBMAP = {}
_pubmap = WORK / "ord0323_publish_map.json"
if _pubmap.exists():
    PUBMAP.update(json.loads(_pubmap.read_text(encoding="utf-8")))


def pub(local_name):
    """The published path for a local artifact name, falling back to the name itself."""
    return PUBMAP.get(local_name, local_name)
_rows = WORK / "ord0323_publish_rows.json"
if _rows.exists():
    # a later stage runs in its own process; the index and the block have to quote the same published set
    _loaded = json.loads(_rows.read_text(encoding="utf-8"))
    _by_path = {}
    for _r in _loaded:
        if _r["path"] in _by_path and _by_path[_r["path"]]["blob"] != _r["blob"]:
            raise SystemExit("one published path claims two blobs: " + _r["path"])
        _by_path.setdefault(_r["path"], _r)
    PUBLISHED.extend(_by_path[p] for p in sorted(_by_path))
    print("reloaded", len(PUBLISHED), "distinct published rows from", _rows.name,
          f"(dropped {len(_loaded) - len(_by_path)} duplicate row(s))")
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
def _line_texts(src, numbers):
    """The source lines themselves, so a sentence that quotes code is backed by what the file says."""
    lines = src.splitlines()
    return [{"line": n, "text": lines[n - 1].strip()} for n in numbers if 0 < n <= len(lines)]


def _slice_fn(src, header):
    """One whole function, byte for byte, so "untouched" is a comparison and not a memory."""
    lines = src.splitlines()
    start = next((i for i, l in enumerate(lines) if l.startswith(header)), None)
    if start is None:
        return None
    end = next((i for i in range(start + 1, len(lines)) if lines[i].startswith("}")), start)
    return chr(10).join(lines[start:end + 1])


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
def blocked_producers(src):
    """Every line that can put a BLOCKED: value on screen, and whether it can ever be an empty code."""
    out = []
    for i, l in enumerate(src.splitlines()):
        if "BLOCKED:" not in l or l.strip().startswith("//"):
            continue
        out.append({"line": i + 1, "text": l.strip(),
                    "kind": "reader" if "startsWith" in l else "producer"})
    return out


SHEET_SRC_CAND = g(["show", f"{CAND}:{Q68_SHEET_FILE}"])
SHEET_SRC_BASE = g(["show", f"{BASE}:{Q68_SHEET_FILE}"])
Q68_CODE_SLOT = {
    "file": Q68_SHEET_FILE,
    "serverReasonCode_lines_at_base": _lines(SHEET_SRC_BASE.splitlines(), "function serverReasonCode"),
    "detail_fallback_at_base": Q68_FALLBACK_BASE,
    "detail_fallback_text_at_base": _line_texts(SHEET_SRC_BASE, Q68_FALLBACK_BASE),
    "serverReasonCode_body_at_candidate": _slice_fn(SHEET_SRC_CAND, "function serverReasonCode"),
    "detail_fallback_at_candidate": Q68_FALLBACK_CAND,
    "machine_keys_accepted_at_candidate": _lines(SHEET_SRC_CAND.splitlines(), '["reason_code", "code", "message_key"]'),
    "no_code_copy_line_at_candidate": _lines(SHEET_SRC_CAND.splitlines(), '（没给编号）'),
    "blocked_producers_at_candidate": blocked_producers(SHEET_SRC_CAND),
    "sentence_chain_identical_to_base": (
        _slice_fn(SHEET_SRC_BASE, "function serverReasonSentence")
        == _slice_fn(SHEET_SRC_CAND, "function serverReasonSentence")),
}
print("Q68 slot:", json.dumps({k: v for k, v in Q68_CODE_SLOT.items() if k != "blocked_producers_at_candidate"},
                              ensure_ascii=False)[:300])

# ------------------------------------------------------------------ Q68's two-way legs, read back from the pass
SPEC_SRC_CAND = g(["show", f"{CAND}:{SPEC}"])  # SPEC already carries the frontend/ prefix
if "const Q68_CODE = " not in SPEC_SRC_CAND:
    raise SystemExit(f"the committed spec did not come back from {CAND[:12]}:{SPEC} (an empty source answers every line search with nothing)")
Q68_CODE = re.search(r'const Q68_CODE = "([^"]+)"', SPEC_SRC_CAND).group(1)


def _arm_leg(arm, key):
    return REA["fixed"][arm].get(key)


# Q68a predates the per-key arms, so its envelope key is read out of the committed spec, not remembered.
_Q68A_ENV = re.search(r"askTheSheet\(page, jsonBody\(\{error: \{(\w+): Q68_CODE\}", SPEC_SRC_CAND)
Q68_CODE_FOR_ARM = {"Q68a": Q68_CODE}
Q68_ASKED_KEY_FOR_ARM = {"Q68a": _Q68A_ENV.group(1) if _Q68A_ENV else None}
Q68_LEGS = {
    "arms": list(ARM_KEYS),
    "code_reaches_the_slot": {a: {"asked_key": _arm_leg(a, "asked_key") or Q68_ASKED_KEY_FOR_ARM.get(a),
                                  "asked_code": _arm_leg(a, "asked_code") or Q68_CODE_FOR_ARM.get(a),
                                  "in_card": _arm_leg(a, "code_in_card")}
                              for a in ("Q68a", "Q68c", "Q68d")},
    "sentence_only_leg": {k: REA["fixed"]["Q68b"].get(k) for k in (
        "which_no_code_branch", "no_code_copy_in_the_code_slot", "no_code_copy_in_the_no_plan_state",
        "uppercased_prose_in_code_slot", "uppercased_prose_in_attributes",
        "uppercased_prose_anywhere_but_the_fold", "prose_anywhere_but_the_fold",
        "attributed_sentence_in_fold", "server_label_present", "attribute_pairs_swept")},
    "counter_arm_cell3_code_slot_back": {a: SH["cell3_code_slot_back"]["per_arm"][a]
                                         for a in ("Q68a", "Q68b", "Q68c", "Q68d")},
}

# Is the code slot's own 「（没给编号）」 copy still reachable once requirement ① answers ""?  Decided per
# producer, so the answer is an enumeration a reviewer can check, not a formula that ends in True.
_BLOCKED_GUARD = _lines(SHEET_SRC_CAND.splitlines(), "} else if (blockedCode) {")
Q68_BLOCKED_PRODUCERS = []
for _prod in Q68_CODE_SLOT["blocked_producers_at_candidate"]:
    if _prod["kind"] == "reader":
        continue
    _txt = _prod["text"]
    if "||" in _txt:
        _why = "等号右边带 `|| PLACES_HTTP_<status>`，那台设备自己填的枚举取不到空串"
    elif "CATALOG_" in _txt:
        _why = "两枚设备自造的枚举字面量"
    else:
        _why = "这一行只在 blockedCode 为真值时才执行（guard 在 guard_lines 那一行）"
    Q68_BLOCKED_PRODUCERS.append({"line": _prod["line"], "text": _txt, "guard_lines": _BLOCKED_GUARD,
                                  "can_reach_empty_code": False, "why": _why})
NO_CODE_COPY_REACHABLE = any(x["can_reach_empty_code"] for x in Q68_BLOCKED_PRODUCERS)
Q68_LEGS["blocked_producers"] = Q68_BLOCKED_PRODUCERS
Q68_LEGS["no_code_copy_reachable"] = NO_CODE_COPY_REACHABLE

# ------------------------------------------------------------------ the raw-read panel answers for the wrong call
# The refused leg's own answer is found by the route it belongs to, not by the number we expect to read:
# the first `fulfill({status:` after the plans/generate registration is that leg's answer.
_SPEC_LINES = SPEC_SRC_CAND.splitlines()
RAW_ANSWER_LINES = []
for _gen in _lines(_SPEC_LINES, 'page.route("**/api/v1/journeys/*/plans/generate"'):
    RAW_ANSWER_LINES.append(next(_i + 1 for _i in range(_gen, len(_SPEC_LINES))
                                 if "fulfill({status:" in _SPEC_LINES[_i]))
if not RAW_ANSWER_LINES:
    raise SystemExit("the spec has no plans/generate route to read an answer status off")
_raw_card = REA["fixed"]["Q68b"].get("card_text") or ""
_raw_found = re.search(r"http_status=(\d+).*?bytes=(\d+)", _raw_card)
RAW_PAIRING = {
    "fields_the_panel_shows": ({"http_status": int(_raw_found.group(1)), "bytes": int(_raw_found.group(2))}
                               if _raw_found else None),
    "rawReading_built_at": _lines(SHEET_SRC_CAND.splitlines(), "const rawReading: RawReading = {"),
    "every_setResult_that_carries_it": _lines(SHEET_SRC_CAND.splitlines(), "rawReading,"),
    "answered_status_on_the_refused_leg": int(re.search(
        r"fulfill\(\{status: (\d+)",
        SPEC_SRC_CAND.splitlines()[RAW_ANSWER_LINES[0] - 1]).group(1)),
    "the_refusal_was_answered_at": RAW_ANSWER_LINES,
    "note": "rawReading 在 leg 1 的响应上算出来，然后随 BLOCKED 那一条 setResult 一起交给屏幕；"
            "屏幕读到的 http_status 因此是 leg 1 的那次，不是被拒的 plans/generate 那次。",
}
# is the one channel really the only one on the line?  counted per symbol, not per file mention
_LIVE_TIP_FOR_RECEIPT = g(["rev-parse", "refs/qoder-scan/mirror/integration-frontend-apple-pass1"])
_TIP_SRC_FOR_CHANNEL = g(["show", f"{_LIVE_TIP_FOR_RECEIPT}:{CELL2}"]).splitlines()
CHANNEL_USE = {
    "measured_on_tip": _LIVE_TIP_FOR_RECEIPT,
    "classifyReadFailure_calls": _lines(_TIP_SRC_FOR_CHANNEL, "classifyReadFailure("),
    "copyFor_calls": _lines(_TIP_SRC_FOR_CHANNEL, "copyFor("),
    # the module nobody may import: measured by its path, not by the word
    "importers_of_the_dead_module_on_tip": [l.split(":", 1)[1] for l in subprocess.run(
        ["git", "-C", str(LANE), "grep", "-l", "lib/serverReason", _LIVE_TIP_FOR_RECEIPT, "--", "frontend"],
        capture_output=True, text=True).stdout.splitlines()],
    "module_exists_on_tip": subprocess.run(
        ["git", "-C", str(LANE), "cat-file", "-e", f"{_LIVE_TIP_FOR_RECEIPT}:frontend/src/lib/serverReason.ts"],
        capture_output=True).returncode == 0,
    # and the unrelated variable that happens to share the name, counted separately so the two are not mixed
    "files_naming_a_variable_serverReason_on_tip": sorted({l.split(":", 1)[1] for l in subprocess.run(
        ["git", "-C", str(LANE), "grep", "-l", "serverReason", _LIVE_TIP_FOR_RECEIPT, "--", "frontend"],
        capture_output=True, text=True).stdout.splitlines()}),
    "channel_file_defined_once": len(_lines(g(["show", f"{_LIVE_TIP_FOR_RECEIPT}:{CHANNEL_FILE}"]).splitlines(),
                                           "export function classifyReadFailure")) == 1,
}
print("channel use on the tip:", json.dumps({k: v for k, v in CHANNEL_USE.items() if k != "measured_on_tip"},
                                            ensure_ascii=False)[:240])

# ------------------------------------------------------------------ ORD-0332 landed a receipt field since
_rc = g(["show", f"{_LIVE_TIP_FOR_RECEIPT}:backend/app/error_receipt.py"]).splitlines()
_m = g(["show", f"{_LIVE_TIP_FOR_RECEIPT}:backend/app/main.py"]).splitlines()
RECEIPT_FIELD = {
    "measured_on_tip": _LIVE_TIP_FOR_RECEIPT,
    "field_name": re.search(r'RECEIPT_FIELD = "([^"]+)"', chr(10).join(_rc)).group(1),
    "defines_at_tip": _lines(_rc, "class ReceiptSeed")[:1] + _lines(_rc, "def receipt_for_code")[:1],
    "wired_at_tip": _lines(_m, "from app.error_receipt import")[:1] + _lines(_m, "async def error_receipt_per_request")[:1],
    "request_id_hits_at_tip": len(_lines(_m, "request_id")),
    "request_id_hits_at_base": len(_lines(g(["show", f"{BASE}:backend/app/main.py"]).splitlines(), "request_id")),
}
print("receipt field:", json.dumps(RECEIPT_FIELD, ensure_ascii=False)[:240])

# ------------------------------------------------------------------ E's signoff shape, counted in the spec itself
SIGNOFF = {
    "criterion": "读渲染出来的文字；等值用 == 不用 in；每格署 (sha, nodeid, shape)；双向反件各咬一向",
    "reference_artifact": "evidence/ord0335-three-signoffs-d2305848/ord0335_derived_d2305848.json",
    "reference_blob": "cd0cd36243349311b10326e522d895bcbcbedd50",
    "equality_fields_in_the_committed_spec": {
        n: len(_lines(SPEC_SRC_CAND.splitlines(), n)) for n in (
            "status_field_equals_asked", "machine_half", "last_token_equals", "held_text",
            "fold_text_equals_the_sentence", "failure_text_rendered_field")},
    "equality_first_lines": {n: _lines(SPEC_SRC_CAND.splitlines(), n)[:1]
                             for n in ("status_field_equals_asked", "machine_half", "last_token_equals",
                                        "held_text", "fold_text_equals_the_sentence",
                                        "failure_text_rendered_field")},
    "nodeid_stamped_by_the_instrument": len(_lines(SPEC_SRC_CAND.splitlines(), "body.nodeid = ")),
    "negative_sweeps_stay_substring_because": "一处子串命中就是更强的违规：等值只用于「这一格写的正是这句话」那种主张",
}
print("signoff:", json.dumps(SIGNOFF["equality_fields_in_the_committed_spec"], ensure_ascii=False),
      "| nodeid stamp lines:", SIGNOFF["nodeid_stamped_by_the_instrument"])
print("raw pairing:", json.dumps(RAW_PAIRING, ensure_ascii=False)[:260])

print("r4 per file:", json.dumps(R4["per_file_lines"], ensure_ascii=False)[:160])
print("channel importers:", CHANNEL["importers_in_src"], "this file uses it:",
      CHANNEL["journey_inbox_workbench_uses_it"])

# ------------------------------------------------------------------ the ten-cell expansion's own facts
PARENT_LIVE = g(["rev-parse", "HEAD^"])

# ------------------------------------------------------------------ ORD-0323 甲 follow-on (CMDR 04:53)
# the generation the four forms were still open in is where this branch left the authority line, not
# `HEAD^`: after seven commits on the branch, HEAD^ is one of my own fixed states.
BRANCH_POINT = g(["merge-base", "HEAD", "refs/qoder-scan/mirror/integration-frontend-apple-pass1"])
JIW_PARENT = g(["show", f"{BRANCH_POINT}:{CELL2}"])
FOUR_FORM_CONSTRUCTS = {
    "F1_unguarded_body_read": "await response.json()",
    "F2_reply_sentence_as_status_line": "result.reason ??",
    "F3_memory_summary_rendered": "{item.reasoning_summary}</p>",
    "F4_draft_summary_rendered": "{draft.interpretation.reasoning_summary}</p>",
}
FOUR_FORM_REPLACEMENTS = {
    "F1_unguarded_body_read": "OriginResponseUnusableError(",
    "F2_reply_sentence_as_status_line": "${t(\"inbox.extractionStatus\")} ${result.status}",
    "F3_memory_summary_rendered": "v13-2-memory-summary-held",
    "F4_draft_summary_replaced": "v13-2-draft-summary-held",
}
FOUR_FORMS = {
    "file": CELL2,
    "pre_fix_generation": BRANCH_POINT,
    "pre_fix_generation_is_branch_point": True,
    "construct_lines_at_pre_fix": {k: _lines(JIW_PARENT.splitlines(), v)
                                    for k, v in FOUR_FORM_CONSTRUCTS.items()},
    "construct_lines_at_candidate": {k: _lines(CAND_JIW, v)
                                      for k, v in FOUR_FORM_CONSTRUCTS.items()},
    "replacement_present_at_candidate": {k: len(_lines(CAND_JIW, v)) > 0
                                          for k, v in FOUR_FORM_REPLACEMENTS.items()},
    "channel_blob_at_ordered_base": revblob(BASE, CHANNEL_FILE),
    "channel_blob_at_candidate": revblob(CAND, CHANNEL_FILE),
    "no_second_helper": revblob(BASE, CHANNEL_FILE) == revblob(CAND, CHANNEL_FILE),
    "forms": ["F1", "F2", "F3", "F4"],
    "construct_key": {"F1": "F1_unguarded_body_read", "F2": "F2_reply_sentence_as_status_line",
                      "F3": "F3_memory_summary_rendered", "F4": "F4_draft_summary_rendered"},
    "replacement_key": {"F1": "F1_unguarded_body_read", "F2": "F2_reply_sentence_as_status_line",
                        "F3": "F3_memory_summary_rendered", "F4": "F4_draft_summary_replaced"},
}
print("four forms: construct lines at pre-fix",
      {k: v for k, v in FOUR_FORMS["construct_lines_at_pre_fix"].items()},
      "| at candidate", {k: v for k, v in FOUR_FORMS["construct_lines_at_candidate"].items()},
      "| channel unchanged:", FOUR_FORMS["no_second_helper"])

print("Q68 legs:", json.dumps({k: v for k, v in Q68_LEGS.items() if k == "sentence_only_leg"}, ensure_ascii=False)[:260])
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
