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


def _content_refusal(blob: bytes) -> str | None:
    # B1: a refusal must name the RULE, never the matched bytes - otherwise the gate blocks the
    # upload and then pastes the credential into its own log ("ID on the noticeboard").
    # B2: scan the whole blob; the 2 MB cap was a silent fail-open for large patches/receipts.
    for rule, pat in SECRET_VALUE_PATTERNS:
        for m in pat.finditer(blob):
            line = m.group(0)
            if any(ph.lower() in line.lower() for ph in PLACEHOLDER_MARKERS):
                continue
            return f"FORBIDDEN_CONTENT(secret_pattern={rule})"
    return None


def guard(local_path: str, repo_path: str, blob: bytes, message: str = "",
          control_tool: bool = False) -> str | None:
    """Return a refusal reason, or None when the upload may proceed."""
    import os.path as _p

    name = _p.basename(local_path).lower()
    real = _p.basename(_p.realpath(local_path)).lower()  # a symlink must not smuggle a denylisted file
    for candidate in {name, real}:
        if candidate in FORBIDDEN_BASENAMES or candidate.endswith(".env") or ".env." in candidate:
            return f"FORBIDDEN_BASENAME({candidate})"
        if candidate.endswith(FORBIDDEN_SUFFIXES):
            return f"FORBIDDEN_SUFFIX({candidate})"
        hit = [f for f in FORBIDDEN_NAME_FRAGMENTS if f in candidate]
        if hit:
            return f"FORBIDDEN_NAME_FRAGMENT({hit[0]} in {candidate})"
    if blob[:16] == SQLITE_MAGIC:
        return "FORBIDDEN_CONTENT(sqlite file header)"
    refused = _content_refusal(blob)
    if refused:
        return refused
    rp = repo_path.replace("\\", "/")
    if ".." in rp.split("/"):
        return f"FORBIDDEN_REPO_PATH(traversal: {repo_path})"
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
    refusal = guard(local_path, repo_path, blob, message, control_tool=control_tool)
    if refusal:
        print(f"REFUSED (fail-closed, nothing uploaded): {refusal}")
        print(f"  local={local_path}  repo_path={repo_path}  bytes={len(blob)}")
        return 5
    want = hashlib.sha1(b"blob %d\x00" % len(blob) + blob).hexdigest()

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
    for attempt in range(1, 4):
        st, after = call("GET", f"/repos/{REPO}/contents/{repo_path}?ref={BRANCH}")
        if isinstance(after, dict) and after.get("sha") == want:
            print("PROOF (git blob sha1 equality): BYTE-LEVEL MATCH")
            print(f"local bytes {len(blob)} | remote size {after.get('size')} | sha1 {want[:16]}")
            return 0
        print("attempt", attempt, "remote", str(after)[:80] if not isinstance(after, dict) else after.get("sha", "")[:10])
        time.sleep(3)
    print("MISMATCH after retries - do not claim the publish")
    return 4


if __name__ == "__main__":
    sys.exit(main())
