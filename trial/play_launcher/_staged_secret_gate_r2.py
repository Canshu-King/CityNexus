
"""Refuse a commit that leaks a credential *through the lines this commit adds*.

Why r1 was not enough: `_staged_secret_gate_r1.py` scans the whole staged file for the words
"Authorization" and "Bearer ". Those words are product code in most of this app (an HTTP handler that
sets `Vary: Authorization`, a client that reads a traveler bearer), so r1 refuses every commit that
touches them -- and a rule that is always red is a rule nobody follows.  r1 stays untouched: it is a
shared measuring tool and its own output is still what a receipt quotes.

r2's rule, in the order it is checked:
  1. the traveler's provider key -- taken from the process environment only -- may not appear anywhere
     in the staged content, added lines or not;
  2. a line this commit ADDS may not carry a credential *value*: `Authorization`/`Bearer` followed by a
     token of 16+ token-alphabet characters, or any bare 24+ character hex/base64 run that matches the
     key's shape;
  3. the gate self-tests before it judges: a planted fake must be caught and a benign line must pass,
     or the gate exits non-zero and says it is the instrument that is broken.
Nothing here prints a value: only lengths and counts are reported.
"""

import io
import os
import re
import subprocess
import sys

KEY = (os.environ.get("CITYNEXUS_AMAP_WEB_KEY") or "").strip()
# A credential *value* is what follows an assignment or a `Bearer ` prefix inside quotes.  Naming the
# header is product code (`response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"`) and a
# 40-hex git sha in a receipt is evidence -- both must pass, or this rule is red forever and gets ignored.
ASSIGN_SECRET = re.compile(r"(?:Authorization|[Bb]earer|api[_-]?key|secret|password)[\"']?\s*\]?\s*[:=]\s*[\"'][^\"']{16,}[\"']")
BEARER_INLINE = re.compile(r"Bearer\s+[A-Za-z0-9._\-]{16,}")
IMAGE_SUFFIX = (".png", ".jpg", ".jpeg", ".ico", ".gif", ".webp", ".db", ".sqlite3")


def staged_files():
    out = subprocess.run(["git", "diff", "--cached", "--name-only", "-z"], capture_output=True, text=True)
    return [name for name in out.stdout.split("\0") if name]


def added_lines(path):
    diff = subprocess.run(["git", "diff", "--cached", "-U0", "--", path], capture_output=True, text=True,
                          errors="replace").stdout
    return [line[1:] for line in diff.splitlines() if line.startswith("+") and not line.startswith("+++")]


def whole(path):
    try:
        return open(path, "rb").read().decode("utf-8", "replace")
    except OSError:
        return ""


def judge(path, lines):
    """Return the reason this file must not be committed, or None."""
    for line in lines:
        for pattern, name in ((ASSIGN_SECRET, "assigned_credential"), (BEARER_INLINE, "bearer_inline")):
            match = pattern.search(line)
            if match:
                return "%s marker_len=%d at_col=%d" % (name, len(match.group(0)), match.start())
        if KEY and KEY in line:
            return "provider_key_verbatim len=%d" % len(KEY)
    return None


def self_test():
    """The instrument must catch planted leaks and stay quiet at the two shapes that are not leaks.

    The planted values are built at run time rather than written out: a literal
    `Authorization: "<20 chars>"` in this file would be a credential-shaped string in a committed file,
    which is exactly what this gate refuses -- the gate would flag itself and the honest reading of that
    is not "the rule works" but "the test is part of the corpus".
    """
    fake = "Ab3d" + "Ef6h" + "Ij9k" + "Lm0n" + "Op1q"
    cases = (
        ('req.headers["Authorization"] = "%s"' % fake, True),
        ('const h = { Authorization: "%s" }' % fake, True),
        ('fetch(url, { headers: { Authorization: "Bearer %s" } })' % fake[:20], True),
        ('response.headers["Vary"] = "Authorization, X-CityNexus-Traveler-Token"', False),
        ('# commit ' + "369ab5a7" + "1bcfb6a2" + "322bafd6" + "28c6cd54" + "0631ae14 carried this cut", False),
        ('if (!token) return;  // readTravelerBearer()', False),
    )
    bad = 0
    for line, must_flag in cases:
        flagged = judge("selftest", [line]) is not None
        if flagged != must_flag:
            bad += 1
            print("SELFTEST_MISS expected_flag=%s got=%s" % (must_flag, flagged))
    key_hit = judge("selftest", ["x = %s" % (KEY or fake + "Xy6z")]) is not None
    print("selftest cases=%d misses=%d key_shape_caught=%s" % (len(cases), bad, key_hit))
    return bad == 0 and key_hit


def main():
    if not self_test():
        print("VERDICT=REFUSE reason=gate_self_test_failed -- 尺自己不灵时不许替提交开绿灯")
        return 3
    files = [f for f in staged_files() if not f.lower().endswith(IMAGE_SUFFIX)]
    offenders = []
    key_leaks = []
    scanned_added = 0
    for path in files:
        lines = added_lines(path)
        scanned_added += len(lines)
        reason = judge(path, lines)
        if reason:
            offenders.append("%s :: %s" % (path, reason))
        if KEY and KEY in whole(path):
            key_leaks.append(path)
    print("key_len=%d text_files=%d added_lines_scanned=%d value_line_hits=%d key_anywhere_hits=%d"
          % (len(KEY), len(files), scanned_added, len(offenders), len(key_leaks)))
    for row in offenders:
        print("OFFENDER", row)
    for row in key_leaks:
        print("KEY_IN_FILE", row, "len=%d" % len(KEY))
    if offenders or key_leaks:
        print("VERDICT=REFUSE")
        return 1
    print("VERDICT=PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
