"""Build test_publisher_placeholder_value_scan_r3.py from the r2 source.

Why a generator file instead of an inline shell edit: the previous attempt lost a level of backslash
escaping through JSON/shell, so `\\n` and `\\x00` arrived already-interpreted and produced a real newline
and a NUL byte inside string literals in the generated instrument.  Raw strings here, and an `ast.parse`
plus a NUL scan before anything is written.
"""
import ast
import io

SRC = "test_publisher_placeholder_value_scan.py"
DST = "test_publisher_placeholder_value_scan_r3.py"

src = io.open(SRC, encoding="utf-8", newline="\n").read()

old_const = r'''HERE = os.path.dirname(os.path.abspath(__file__))
PUBLISHER = os.path.join(HERE, "publish_evidence.py")
MY_INSTRUMENT = os.path.join(HERE, "test_ord0275_publisher_guard_r3.py")
THIS_FILE = os.path.join(HERE, "test_publisher_placeholder_value_scan.py")'''

new_const = r'''HERE = os.path.dirname(os.path.abspath(__file__))
PUBLISHER = os.path.join(HERE, "publish_evidence.py")
# r3 (rule GENERATION_TRANSFER_BY_CITED_BLOB_EQUALITY_V1, arbiter Q24=1 @2026-09-25T04:0x+08): the sibling
# instrument is pinned by its 40-hex BLOB and fetched by that coordinate, never by filename.  r2 read
# `test_ord0275_publisher_guard_r3.py` BY NAME; when that file's bytes legitimately changed at 02:01 the
# cell went RED on a stale premise that nobody had touched - a name is not a coordinate.
SUBJECT_INSTRUMENT_BLOB = "be0978863fbd76f19de7350d6e889b7bf8d38010"
SUBJECT_PUBLISHED_AS = "live_checks/test_ord0275_publisher_guard_r5.py"
TOKEN_FILE = r"D:\moodle\_qoder_recovery_20260919\.api_tok_20260920"
THIS_FILE = os.path.abspath(__file__)


def blob_sha_of(raw):
    return hashlib.sha1(b"blob %d\x00" % len(raw) + raw).hexdigest()


def fetch_blob(sha):
    """Read a published blob back out of GitHub and prove it by recomputed sha1.

    Returns None when it cannot be resolved or does not match; callers fail CLOSED.  This is the same
    discipline the 0271-A DEBT-3 cold run uses: a local path is not a coordinate.
    """
    import base64
    import json
    import urllib.request
    try:
        tok = io.open(TOKEN_FILE, encoding="utf-8").read().strip()
        req = urllib.request.Request(
            "https://api.github.com/repos/Canshu-King/CityNexus/git/blobs/" + sha,
            headers={"Authorization": "Bearer " + tok, "Accept": "application/vnd.github+json",
                     "User-Agent": "cnx-cmdr-scan-r3"})
        with urllib.request.urlopen(req, timeout=120) as r:
            meta = json.loads(r.read().decode("utf-8"))
        raw = base64.b64decode(meta["content"].replace("\n", ""))
    except Exception:
        return None
    return raw if blob_sha_of(raw) == sha else None'''

assert src.count(old_const) == 1, "constant anchor"
src = src.replace(old_const, new_const, 1)

start = src.index(r"    # ---- S10 an instrument")
end = src.index(r"    # ---- S18 THIS instrument")
new_s10 = r'''    # ---- S10 (r3): the pinned instrument is ACCEPTED as it ships and REFUSED the moment a
    #      credential-shaped literal is embedded in those same bytes.  Both sides derive from the pinned
    #      published blob, so this cannot be satisfied by a stale file on someone's disk, and it is not a
    #      relabel either: the before-rule is reported next to the after-rule.
    subject = fetch_blob(SUBJECT_INSTRUMENT_BLOB)
    if subject is None:
        check("S10_pinned_instrument_accepted_clean_and_refused_once_a_literal_is_embedded", False,
              {"error": "pinned subject blob could not be read back - NOT MEASURED (fail CLOSED)",
               "pinned_blob": SUBJECT_INSTRUMENT_BLOB, "published_as": SUBJECT_PUBLISHED_AS})
    else:
        tampered = subject + ("\n" + 'API_TOKEN = "%s"' % CANARY).encode() + b"\n"
        clean_v = verdict(base, subject)
        tampered_v = verdict(base, tampered)
        refusal = base["_content_refusal"](tampered)
        check("S10_pinned_instrument_accepted_clean_and_refused_once_a_literal_is_embedded",
              clean_v == GREEN and tampered_v == RED,
              {"pinned_blob": blob_sha_of(subject), "bytes": len(subject),
               "published_as": SUBJECT_PUBLISHED_AS,
               "clean_verdict": clean_v, "tampered_verdict": tampered_v,
               "before_rule_on_tampered": old_line_scope(base, tampered),
               "rule_hit": rule_hit(refusal),
               "meaning": "the tightening did not open the block layer: bytes that name a credential-shaped "
                          "value are refused wherever they live, while a compliant instrument - this pinned "
                          "one and S18's own source - stays publishable"})

'''
src = src[:start] + new_s10 + src[end:]

old_out = '"publisher_placeholder_value_scan_r2_selftest.json"'
assert src.count(old_out) == 1, "receipt path anchor"
src = src.replace(old_out, '"publisher_placeholder_value_scan_r3_selftest.json"', 1)

raw = src.encode("utf-8")
assert b"\x00" not in raw, "generated source contains a NUL byte"
ast.parse(src)
io.open(DST, "w", encoding="utf-8", newline="\n").write(src)
print("wrote", DST, len(raw), "B; syntax OK; NUL-free")
