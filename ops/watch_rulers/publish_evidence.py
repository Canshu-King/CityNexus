"""Publish a local file to the arbiter-readable branch, with a byte-level (git blob sha1) proof.

Why this exists: the arbiter audits from GitHub, and the working-tip SHAs are NOT resolvable
there (measured 2026-09-22: 50b35e0 / 3e259bd / 522c414 all return 422 "No commit found for
SHA" on both Canshu-King/CityNexus and CityNexus-Workspace). So a diff/receipt that only exists
in a local worktree is, to the auditor, not evidence at all. This publishes it to the one branch
that IS readable: Canshu-King/CityNexus @ commander/control (the established ledger-mirror lane).

Usage: publish_evidence.py <local_file> <repo_path> [commit_message]
"""
import base64
import hashlib
import io
import json
import re as _re          # Q23: module-level because the synthetic-fixture probes run at import
import sys
import time
import urllib.error
import urllib.request

TOK = open(r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920", encoding="utf-8").read().strip()
REPO = "Canshu-King/CityNexus"
BRANCH = "commander/control"
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "citynexus-commander"}

# --- fail-closed upload guard (arbiter 5775258233 §A + 5775473121 §1: the publisher must refuse,
# --- not rely on the operator remembering).  A refusal prints WHICH rule fired; nothing is sent.
FORBIDDEN_SUFFIXES = (
    ".db", ".db-wal", ".db-shm", ".db-journal", ".db.bak", ".db.backup",
    ".sqlite", ".sqlite3", ".sqlite-wal", ".sqlite-shm", ".sqlite-journal",
    ".sqlite3-wal", ".sqlite3-shm", ".sqlite3-journal",   # B4: the .sqlite3 sidecar family
    ".pem", ".key", ".p12", ".pfx", ".jks", ".keystore",
    ".bak", ".backup", ".old", ".orig",   # a DB copy under any of these names may lack the magic
)
FORBIDDEN_BASENAMES = {".env", "credentials", "credentials.json", "id_rsa", "id_ed25519"}
# The publisher's own token file is `.api_tok_20260920`; `api_tok` must be here or the publisher
# can upload the very credential it depends on (arbiter's "hole A", called out as the worst one).
FORBIDDEN_NAME_FRAGMENTS = (
    "token", "cookie", "secret", "credential", "password", "_live", "_preview",
    "api_tok", "_tok_", "apikey", "api_key",
)
ALLOWED_REPO_PREFIXES = ("evidence/", "live_checks/")
SQLITE_MAGIC = b"SQLite format 3\x00"
# Value-shaped content scan: match real secret VALUES, never the bare words (tests/docs mention
# "token" constantly and must not be killed).
import re as _re

SECRET_VALUE_PATTERNS = (
    ("PEM_PRIVATE_KEY", _re.compile(rb"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("AUTH_HEADER", _re.compile(rb"(?im)^\s*(authorization|proxy-authorization)\s*:\s*\S+")),
    ("BEARER_TOKEN", _re.compile(rb"(?i)\b(bearer)\s+[A-Za-z0-9._\-]{20,}")),
    # B3: prefixed env names (GITHUB_TOKEN=, DEEPSEEK_API_KEY=) and quoted JSON/YAML keys.
    ("ENV_SECRET_ASSIGNMENT", _re.compile(
        rb"(?i)\b[A-Z0-9_]*(api[_-]?key|secret|password|passwd|token|access[_-]?key|client[_-]?secret)"
        rb"[A-Z0-9_]*\b\s*[:=]\s*['\"]?[A-Za-z0-9._\-/+]{16,}")),
    ("QUOTED_JSON_SECRET", _re.compile(
        rb"(?i)['\"](api[_-]?key|secret|password|token|access[_-]?key)['\"]\s*:\s*"
        rb"['\"][A-Za-z0-9._\-/+]{16,}['\"]")),
    ("URI_CREDENTIAL", _re.compile(rb"[a-zA-Z][a-zA-Z0-9+.\-]*://[^/\s:@]{2,}:[^/\s:@]{6,}@")),
    ("KNOWN_KEY_PREFIX", _re.compile(rb"\b(gh[pousr]_[A-Za-z0-9]{20,}|sk-[A-Za-z0-9]{20,})\b")),
)
PLACEHOLDER_MARKERS = (b"YOUR_", b"EXAMPLE", b"REDACTED", b"PLACEHOLDER", b"xxxx", b"****", b"<", b"changeme")

# ---- PUBLISHER_SECRET_SCAN_DEBT_1 (arbiter supplementary ruling on Q23, 2026-09-24T23:0x+08) -------
# The hole this closes: the placeholder skip used to look at the WHOLE matched line, and for the two
# assignment-shaped rules that matched line contains the VARIABLE NAME.  So an identifier that itself
# says "placeholder" used to wash a real-looking quoted value out of the guard - the VALUE never had to
# say anything at all.  The ruling is narrow and mechanical: placeholder treatment may only be earned by
# the value the pattern objected to, never by a name, a key or a neighbouring comment.
#
# MEASURED COST of the tightening, found by trying to publish this very file: a comment that quotes the
# hole with a real-looking example is now itself a credential-shaped literal, so the guard refused its own
# source until the example was written in prose instead of as an assignment.  The literal lives on in the
# DEBT-1 instrument, which is where a test fixture belongs - and that instrument is therefore also
# refused by the guard, which is the Q23 question the arbiter has still to settle.
#
# This is deliberately NOT the synthetic exemption (that stays disarmed until this debt item is reviewed):
# stacking "allow synthetic" on top of "skip too much" is how two holes become a feature.
_ASSIGNMENT_RULES = ("ENV_SECRET_ASSIGNMENT", "QUOTED_JSON_SECRET", "AUTH_HEADER")
_ASSIGN_SPLIT = _re.compile(r"[:=]\s*(.+)$", _re.S)


def _matched_secret_value(rule: str, matched: bytes) -> bytes:
    """The value the guard actually objected to.  Empty bytes = there is no value in this match at all."""
    if rule not in _ASSIGNMENT_RULES:
        return matched                      # PEM / bearer / URI / known-prefix: the match IS the value
    m = _ASSIGN_SPLIT.search(matched.decode("latin-1"))
    if not m:
        return b""                          # no right-hand side at all: nothing to wash, stay RED
    return m.group(1).strip().strip("'\",;").encode("latin-1")


def _placeholder_in_value(value: bytes) -> bool:
    """Only a marker INSIDE the value counts; an empty value can never be washed by a name."""
    low = value.lower()
    return bool(value) and any(ph.lower() in low for ph in PLACEHOLDER_MARKERS)


def _content_refusal(blob: bytes) -> str | None:
    # B1: a refusal must name the RULE, never the matched bytes - otherwise the gate blocks the
    # upload and then pastes the credential into its own log ("ID on the noticeboard").
    # B2: scan the whole blob; the 2 MB cap was a silent fail-open for large patches/receipts.
    for rule, pat in SECRET_VALUE_PATTERNS:
        for m in pat.finditer(blob):
            if _placeholder_in_value(_matched_secret_value(rule, m.group(0))):
                continue
            return f"FORBIDDEN_CONTENT(secret_pattern={rule})"
    return None


# ---- Q23 / SYNTHETIC_TEST_FIXTURE_ALLOWED (arbiter ruling 2026-09-24T20:1x+08) -----------------
# My own content guard refused the ORD-0275 r3 INSTRUMENT because it contains a synthetic fixture shaped
# like a credential assignment - which is the guard working, not failing.  The ruling keeps the guard and
# adds the narrowest possible exemption, because "see the word synthetic and pass" is how a real leak
# eventually walks in dressed as test data.  Three conditions, ALL required; everything else keeps refusing.
#
# It deliberately re-uses the guard's OWN matches instead of inventing a second secret regex: an exemption
# that looks at different bytes than the block is an exemption that can be argued about.
INSTRUMENT_REPOS = ("live_checks/",)
INSTRUMENT_NAME_HINTS = ("test_", "_instrument", "/instrument/")
SYNTHETIC_NAME_RE = _re.compile(r"^[ 	]*([A-Z][A-Z0-9_]{2,})[ 	]*[=:]")
QUOTED_RE = _re.compile(r""""([^"
]{4,})"|'([^'
]{4,})'""")
SYNTHETIC_WORDS = ("synthetic", "placeholder", "not-a-real", "dummy", "fake", "example-value", "test-fixture")
MAX_REAL_RUN = 20                    # a >=20-char unbroken alphanumerical run IS the shape of a live key


def _placeholder_shaped_literal(lit: str) -> bool:
    low = lit.lower()
    if not any(w in low for w in SYNTHETIC_WORDS):
        return False                  # must SAY what it is; a short value is not proof of harmlessness
    longest = max([len(x) for x in _re.split(r"[^A-Za-z0-9]", lit)] or [0])
    return longest < MAX_REAL_RUN     # one real-shaped run anywhere in it and the answer is "looks real"


def synthetic_fixture_exemption(repo_path: str, blob: bytes) -> str | None:
    """Reason string when this upload is a declared synthetic instrument; None (= keep refusing) otherwise."""
    rp = repo_path.replace("\\", "/")
    name = rp.rsplit("/", 1)[-1]
    where_ok = rp.startswith(INSTRUMENT_REPOS) or any(h in name for h in INSTRUMENT_NAME_HINTS)
    if not where_ok:
        return None
    text = blob.decode("utf-8", "replace")
    declared = sorted({n for n in SYNTHETIC_NAME_RE.findall(text) if "SYNTHETIC" in n})
    if not declared:
        return None
    objected = []
    for rule, pat in SECRET_VALUE_PATTERNS:
        for m in pat.finditer(blob):
            matched = m.group(0)
            # PUBLISHER_SECRET_SCAN_DEBT_1: one source of truth for "is this match placeholder-washed".
            # This layer must not disagree with _content_refusal about WHICH BYTES carry the marker, or
            # the two layers end up arguing over different text and the exemption becomes unprovable.
            if _placeholder_in_value(_matched_secret_value(rule, matched)):
                continue
            objected.append((rule, matched.decode("utf-8", "replace")))
    if not objected:
        return None                    # nothing the guard objected to here - the refusal came from elsewhere
    for rule, line in objected:
        lits = [a or b for a, b in QUOTED_RE.findall(line)]
        if not lits or not all(_placeholder_shaped_literal(x) for x in lits):
            return None                # one real-shaped literal anywhere in the objected lines and it is refused
    return ("SYNTHETIC_TEST_FIXTURE_ALLOWED(marker=%s,objected_lines=%d,all_literals_placeholder_shaped=true)"
            % (",".join(declared)[:60], len(objected)))


def _name_refusal(candidate: str, scope: str) -> str | None:
    """ORD-0275: THE single source of truth for "is this one file name / path component forbidden?".

    Arbiter 5805656486 §5 forbids the obvious shortcut of copying the denylist twice - two lists drift,
    and the gap that this order exists to close was exactly "local names are checked, repo_path is not".
    Local basenames and every component of repo_path must therefore go through THIS helper.
    """
    c = candidate.lower()
    if c in FORBIDDEN_BASENAMES or c.endswith(".env") or ".env." in c:
        return f"FORBIDDEN_BASENAME(scope={scope}: {c})"
    if c.endswith(FORBIDDEN_SUFFIXES):
        return f"FORBIDDEN_SUFFIX(scope={scope}: {c})"
    hit = [f for f in FORBIDDEN_NAME_FRAGMENTS if f in c]
    if hit:
        return (f"FORBIDDEN_NAME_FRAGMENT(scope={scope}: {hit[0]} in {c})"
                " -- ACTIONABLE: this is a NAME-shaped guard (a second belt on top of the SQLite-magic"
                " content scan). If the artifact is a read-only INSTRUMENT that merely documents such a"
                " path, rename the FILE and keep the content untouched; the rename shows up in the"
                " receipt, so it stays auditable. Do NOT weaken the fragment list and do NOT strip"
                " content to get past it (HARNESS 2026-09-23 hit this with a _live-named witness script)")
    return None


def guard_pre(local_path: str, repo_path: str, blob: bytes) -> str | None:
    """Q18 hard boundary 1+2, first half: everything that must pass BEFORE any compatibility judgement.

    The arbiter's rule (bus 5806436649) is that a historically denylisted repo_path may be tolerated ONLY
    as a read-only no-op when the remote object is byte-identical.  That exemption is deliberately narrow:
    local name guards, the SQLite magic and the secret-content scan still run first, so a dirty LOCAL file
    can never borrow a legacy remote path, and traversal is still refused before any GET.
    """
    import os.path as _p

    for candidate, scope in ((_p.basename(local_path), "local"),
                             (_p.basename(_p.realpath(local_path)), "local-realpath")):
        refused = _name_refusal(candidate, scope)  # a symlink must not smuggle a denylisted file
        if refused:
            return refused
    if blob[:16] == SQLITE_MAGIC:
        return "FORBIDDEN_CONTENT(sqlite file header)"
    refused = _content_refusal(blob)
    if refused:
        # Q23 STATUS 2026-09-24 20:4x: the exemption below is deliberately NOT armed.  Measured reason:
        # `_content_refusal` already skips a line whenever a placeholder word appears ANYWHERE in it, which
        # is looser than the ruling wants (probe: `SYNTHETIC_SECRET = "hunter2hunter2"` passes today with no
        # objection at all, i.e. the guard never reaches my code).  Arming a new narrow exemption on top of a
        # loose existing skip would make the two layers argue about different bytes - and shipping an inert
        # "looks like a loosened guard" path costs every future reader without buying anything.  So the
        # refusal stands unchanged, and the ruling is recorded as NOT-YET-DONE with its counter-example.
        return refused
    rp = repo_path.replace("\\", "/")
    if ".." in rp.split("/"):
        return f"FORBIDDEN_REPO_PATH(traversal: {repo_path})"
    return None


def repo_path_name_refusal(repo_path: str) -> str | None:
    """The ONE layer Q18 allows to be judged against an already-existing remote object."""
    rp = repo_path.replace("\\", "/")
    for comp in [c for c in rp.split("/") if c]:
        refused = _name_refusal(comp, "repo_path")
        if refused:
            return refused
    return None


def guard_target(repo_path: str, message: str = "", control_tool: bool = False) -> str | None:
    """Q18 hard boundary 2, second half: allowed-prefix / --control-tool / commit-message checks.

    These run BEFORE any compatibility judgement too - the exemption covers the name layer only, never
    prefix or permission, so an evidence submission still cannot rewrite live_checks/** without the flag.
    """
    rp = repo_path.replace("\\", "/")
    # B6: an evidence-submission tool must not double as a control-tool rewriter.  Default target
    # is evidence/** only; live_checks/** needs the explicit --control-tool flag.
    if rp.startswith("evidence/"):
        pass
    elif rp.startswith("live_checks/"):
        if not control_tool:
            return (f"FORBIDDEN_TARGET(control tool path {repo_path} requires --control-tool; "
                    "an evidence submission may only write evidence/**)")
    else:
        return f"FORBIDDEN_REPO_PREFIX(must start with evidence/ (or live_checks/ with --control-tool): {repo_path})"
    if message:
        refused = _content_refusal(message.encode("utf-8", "replace"))
        if refused:
            return f"FORBIDDEN_COMMIT_MESSAGE({refused})"
    return None


def guard(local_path: str, repo_path: str, blob: bytes, message: str = "",
          control_tool: bool = False) -> str | None:
    """The same judge as before Q18, composed from the three parts: pre -> repo-path name -> target.

    Kept as one function because ORD-0275 r2 reads its verdicts through this name; the ORDER of the checks
    is unchanged on purpose, so no existing reading silently changes meaning.
    """
    refused = guard_pre(local_path, repo_path, blob)
    if refused:
        return refused
    # ORD-0275 cell 2: a clean local name must not be enough.  Every component of the remote target is
    # judged by the same helper, so `evidence/x/_live.db`-shaped or token-shaped targets are refused
    # before anything is PUT, regardless of what the file is called on this disk.
    refused = repo_path_name_refusal(repo_path)
    if refused:
        return refused
    return guard_target(repo_path, message, control_tool)


def call(method, path, payload=None):
    req = urllib.request.Request("https://api.github.com" + path, method=method)
    for k, v in HDRS.items():
        req.add_header(k, v)
    data = None
    if payload is not None:
        data = json.dumps(payload).encode()
        req.add_header("Content-Length", str(len(data)))
    try:
        with urllib.request.urlopen(req, data, timeout=240) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:  # noqa: BLE001
        return type(e).__name__, str(e)[:300]


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    control_tool = "--control-tool" in sys.argv
    local_path, repo_path = args[0], args[1]
    message = args[2] if len(args) > 2 else f"commander: publish {repo_path}"
    blob = io.open(local_path, "rb").read()
    # Q18 (arbiter 5806436649): the guard is consulted in LAYERS.  Every structural and content scan
    # runs here, before any request at all - the legacy exemption added below covers ONLY the repo_path
    # NAME layer, never prefix, --control-tool, traversal, SQLite magic or secret content.
    refusal = guard_pre(local_path, repo_path, blob) or guard_target(repo_path, message, control_tool)
    if refusal:
        print(f"REFUSED (fail-closed, nothing uploaded): {refusal}")
        print(f"  local={local_path}  repo_path={repo_path}  bytes={len(blob)}")
        return 5
    want = hashlib.sha1(b"blob %d\x00" % len(blob) + blob).hexdigest()

    # ---- Q18: a historically denylisted repo_path may be tolerated ONLY as a read-only no-op.
    # 200 + existing_sha == want  => ALREADY_IDENTICAL_LEGACY_PATH / NO_WRITE / rc=0
    # 404                         => REFUSED_LEGACY_ABSENT,   0 PUT
    # 200 + different sha         => REFUSED_LEGACY_DIFFERENT, 0 PUT, never overwrite
    # 401/403/undecidable         => fail-closed,               0 PUT
    # It proves "this object was already there and this run wrote nothing"; it does NOT re-approve the name,
    # so a NEW artifact must still choose a clean path (hard boundary 5 of the ruling).
    name_refusal = repo_path_name_refusal(repo_path)
    if name_refusal:
        st, meta = call("GET", f"/repos/{REPO}/contents/{repo_path}?ref={BRANCH}")
        if st in (401, 403):
            print(f"AUTH_FAILURE({st}) on the legacy-path GET - fail-closed, 0 PUT.")
            return 6
        if st == 404:
            print(f"REFUSED_LEGACY_ABSENT: {name_refusal} | the remote object is not there either, so the "
                  "forbidden name stands and NOTHING was uploaded (0 PUT).")
            return 5
        if st != 200:
            print(f"INITIAL_GET_FAILED({st}) while judging a denylisted repo_path - fail-closed, 0 PUT.")
            return 7
        existing = meta.get("sha") if isinstance(meta, dict) else None
        if existing and existing == want:
            print("ALREADY_IDENTICAL_LEGACY_PATH / NO_WRITE: the object already sits at that historical path")
            print(f"  byte-for-byte (sha1 {want[:16]}), so this run PROVED it and wrote nothing (0 PUT).")
            print("  NOT a re-approval of the name: a NEW artifact must still choose a clean path.")
            return 0
        print(f"REFUSED_LEGACY_DIFFERENT: {name_refusal} | remote sha={str(existing)[:10]} != "
              f"local sha={want[:10]} - refused, and this tool will NOT overwrite a denylisted path.")
        return 5

    # B5: fail closed on the initial GET.  Only 200 (object exists) or 404 (confirmed absent) may
    # proceed; an auth failure stops here with NO PUT and NO retry, per the frozen auth rule.
    st, meta = call("GET", f"/repos/{REPO}/contents/{repo_path}?ref={BRANCH}")
    if st in (401, 403):
        print(f"AUTH_FAILURE({st}) on the initial GET - fail-closed, no PUT attempted, no retry.")
        print("  NOT a credential rotation trigger on its own: record status + endpoint only.")
        return 6
    if st == 200:
        existing = meta.get("sha") if isinstance(meta, dict) else None
    elif st == 404:
        existing = None
    else:
        print(f"INITIAL_GET_FAILED({st}) - fail-closed, no PUT attempted. body={str(meta)[:120]}")
        return 7
    print(f"GET {repo_path}: {st} existing_sha={str(existing)[:10]}")
    if existing == want:
        print("already identical - nothing to push")
        return 0
    payload = {"message": message, "content": base64.b64encode(blob).decode(), "branch": BRANCH}
    if existing:
        payload["sha"] = existing
    st, res = call("PUT", f"/repos/{REPO}/contents/{repo_path}", payload)
    commit = (res.get("commit", {}) or {}).get("sha", "")[:12] if isinstance(res, dict) else str(res)[:200]
    print(f"PUT -> {st} commit={commit}")
    if st not in (200, 201):
        return 3
    time.sleep(2)
    auth_anomaly = None
    saw_a_dict = False
    for attempt in range(1, 4):
        st, after = call("GET", f"/repos/{REPO}/contents/{repo_path}?ref={BRANCH}")
        if st in (401, 403):
            # SAFE-DEFAULT 2026-09-23 (arbiter 5775473121 §2, mirrored from mirror_v2.py): a 401 on
            # the read-back is a MEASUREMENT failure, not a delivery failure.  The PUT already
            # returned 2xx with a commit, so the artifact is published - but the byte-level proof
            # was not taken.  The old code fell through to "MISMATCH after retries", which reports an
            # unproven publish as a wrong publish.  Say which one it is; never rotate the token here.
            auth_anomaly = (st, str(after)[:120])
            print(f"AUTH_ANOMALY_TAIL_READ({st}) on GET /repos/{REPO}/contents/{repo_path}?ref={BRANCH}")
            time.sleep(3)
            continue
        if isinstance(after, dict):
            saw_a_dict = True
            if after.get("sha") == want:
                print("PROOF (git blob sha1 equality): BYTE-LEVEL MATCH")
                print(f"local bytes {len(blob)} | remote size {after.get('size')} | sha1 {want[:16]}")
                return 0
        print("attempt", attempt, "remote", str(after)[:80] if not isinstance(after, dict) else after.get("sha", "")[:10])
        time.sleep(3)
    if auth_anomaly and not saw_a_dict:
        print(f"PUBLISHED_UNPROVEN: the PUT succeeded (commit {commit}) so the artifact is on "
              f"{BRANCH}, but every read-back answered {auth_anomaly[0]} - this is an AUTH/transport "
              f"anomaly on the read path, NOT a hash mismatch and NOT a credential failure.")
        print(f"  do not rotate or edit the token; re-run this publish to take the proof. body={auth_anomaly[1]}")
        return 7
    print("MISMATCH after retries - do not claim the publish")
    return 4


if __name__ == "__main__":
    sys.exit(main())
