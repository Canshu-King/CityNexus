"""Refuse a commit that carries a real credential. r2 -- r1 could not tell a secret from source code.

r1 (trial/human_walk/_staged_secret_gate_r1.py) greps staged text files for the AMap key value AND for the bare
words "Authorization" / "Bearer ".  The first marker is right; the other two are not: an API client has to write
`Authorization: `Bearer ${bearer}`` to work at all, so r1 refused RevolutionFirstLook.tsx for six lines that were
already in HEAD (git diff --cached showed 0 added marker lines).  A gate that cries wolf on normal product code
gets walked around, which is worse than no gate -- so r2 keeps the fatal rules and states them precisely:

  FATAL 1  the AMap key value itself (read from the process env, never printed);
  FATAL 2  a JWT-shaped literal (eyJ....) or a quoted 20+ char literal assigned right after an
           Authorization/Bearer header name -- i.e. a credential pasted into source.  The marker must be a
           whole word and the value must follow a ':' or '=', because the first cut of this rule flagged
           `import { readTravelerBearer } from "../../lib/travelerSession"` as a leak;
  FATAL 3  a private key block.

Informational: a header built from a variable -- counted and named, so a reviewer sees the auth surface without
the gate pretending the word "Bearer" is a leak.

--selftest proves the three fatal arms bite on planted samples and the clean shape passes.  Run it after any edit.
Exit 1 = do not commit.
"""
import os
import re
import subprocess
import sys

KEY = (os.environ.get("CITYNEXUS_AMAP_WEB_KEY") or "").strip()
TOKEN_AFTER_HEADER = re.compile(r"(?:Authorization|\bBearer\b)[^\n]{0,20}?[:=]\s*['\"]([A-Za-z0-9_\-\+]{20,})['\"]")
JWT = re.compile(r"eyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{6,}")
PRIVATE_KEY = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")
HEADER_SHAPE = re.compile(r"Authorization|Bearer ")


def verdict(text):
    """Return (fatal_reasons, info_count) for one file's text."""
    fatal = []
    if KEY and KEY in text:
        fatal.append("AMAP_KEY_VALUE")
    for match in TOKEN_AFTER_HEADER.finditer(text):
        fatal.append("TOKEN_LITERAL_AFTER_HEADER")
    if JWT.search(text):
        fatal.append("JWT_LITERAL")
    if PRIVATE_KEY.search(text):
        fatal.append("PRIVATE_KEY_BLOCK")
    return fatal, len(HEADER_SHAPE.findall(text))


def main():
    if "--selftest" in sys.argv:
        # Fixtures are assembled at runtime, because a file that carries a literal credential-shaped string is
        # exactly what this gate refuses -- including itself.  verdict() still sees the finished shapes.
        token = "abc123DEF456" + "ghi789JKL012"
        jwt = "eyJhbGciOiJIUzI1NiJ9" + "." + "eyJzdWIiOiIxMjM0NTY3ODkwIn0" + "." + "abcdefghijklmnopqrstuvwxyz"
        priv = "-----BEGIN " + "RSA PRIVATE KEY" + "-----\nAAAA"
        cases = [
            ("key value", "x = '%s'" % KEY if KEY else "x = 'FAKE32CHARKEYVALUE0000000000000000'", True),
            ("token literal", "headers = { Authorization: \"" + token + "\" }", True),
            ("jwt literal", "const t = '" + jwt + "';", True),
            ("private key", priv, True),
            ("clean template", "headers: { Authorization: `Bearer ${bearer}`, Accept: \"application/json\" },", False),
            ("clean reader", "const b = readTravelerBearer(); if (!b) return;", False),
            # the two shapes that made the first r2 cut cry wolf on real product code: an import whose module
            # path is 25 chars, and a header assembled by concatenation.
            ("import path", "import { readTravelerBearer, subscribeTravelerBearer } from \"../../lib/travelerSession\";", False),
            ("concat header", "const h = { Authorization: \"Bearer \" + token };", False),
        ]
        bad = 0
        for name, text, want_fatal in cases:
            fatal, info = verdict(text)
            got_fatal = bool(fatal)
            ok = got_fatal == want_fatal
            bad += 0 if ok else 1
            print("SELFTEST %-16s want_fatal=%-5s got_fatal=%-5s reasons=%s header_shape_hits=%d %s"
                  % (name, want_fatal, got_fatal, fatal or "[]", info, "OK" if ok else "WRONG"))
        print("SELFTEST cases=%d wrong=%d key_env_present=%s" % (len(cases), bad, bool(KEY)))
        return 1 if bad else 0

    files = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True).stdout.split()
    scanned = refused = 0
    for path in files:
        if path.lower().endswith((".png", ".jpg", ".jpeg", ".ico", ".woff", ".woff2", ".db", ".sqlite")):
            continue
        try:
            with open(path, "rb") as handle:
                text = handle.read().decode("utf-8", "replace")
        except OSError as error:
            print("UNREADABLE", path, type(error).__name__)
            refused += 1
            continue
        scanned += 1
        fatal, info = verdict(text)
        for reason in fatal:
            print("REFUSE", path, "reason=", reason)
            refused += 1
        if info and not fatal:
            print("info", path, "auth_header_lines_shape=%d (built from a variable, no literal credential)" % info)
    print("staged_text_files_scanned=%d key_env_present=%s refused=%d" % (scanned, bool(KEY), refused))
    if refused:
        return 1
    print("PASS no literal credential in staged text")
    return 0


if __name__ == "__main__":
    sys.exit(main())
