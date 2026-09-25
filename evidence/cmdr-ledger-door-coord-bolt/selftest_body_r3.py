"""Two-way self-test for the COORDINATE BOLT of ledger_insert_after.py (r4 behaviour).

The bolt refuses any 40-hex in a ledger block that does not resolve as a git object.  r4 adds exactly one
disclosure path: the value may be carried when the SAME line both (a) declares it non-retrievable in the
author's own words and (b) carries at least one coordinate that does resolve.

Discriminator, chosen so this selftest can never touch the shared ledger: the bolt runs BEFORE the ledger is
read or written, and every fixture is given an anchor string that does not exist in the ledger.  So
  rc == 9                      -> the bolt FIRED (refused)
  rc != 9 and "anchor not found" -> the bolt PASSED the block through
Both directions are asserted.  A fixture that is expected to be exempt must not merely avoid rc 9 - it must
reach the anchor check, which proves the whole bolt was walked.
"""
import hashlib
import io
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOOR = os.path.join(HERE, "ledger_insert_after.py")
REPO = "D:/moodle/CityNexus"
TMP = os.path.join(HERE, "_door_selftest_scratch")
os.makedirs(TMP, exist_ok=True)

FAKE = hashlib.sha1(b"never-committed-bytes-for-a-door-selftest").hexdigest()   # 40 hex, cannot resolve
ANCHOR = "ZZZ this anchor does not exist in the shared ledger ZZZ"


def resolves(h):
    return subprocess.run(["git", "-C", REPO, "cat-file", "-t", h],
                          capture_output=True, text=True).returncode == 0


def real_blob():
    """A coordinate this door can actually fetch - taken from an artifact published tonight."""
    p = os.path.join(HERE, "_suite_arm_selftest_r1.json")
    raw = io.open(p, "rb").read()
    return hashlib.sha1(b"blob %d\0" % len(raw) + raw).hexdigest()


# Fixtures carry NO bare numerals on purpose.  First run of this selftest proved why: the door's Q43 bolt runs
# BEFORE the coordinate bolt, so a fixture that trips Q43 gets rc 8 and never reaches the rule under test.  That
# ordering is itself a finding - a block can be refused for its numbers before anything looks at its hashes.
def fixtures(good):
    # Q43 answers NO_CLAIM_FOUND (rc 4) for a block that states nothing checkable, and the door treats any
    # non-zero as a refusal - a first run of this selftest died there.  So every fixture carries one honest,
    # satisfied claim line before the line under test: the gate must be awake in the fixture, not asleep.
    pre = u"### zz door selftest\n\n· 说明：本块是门自测件，被引件 3023 B 见 `%s`。\n\n" % good
    return {
        "exempt_p3_line45_verbatim": ("exempt", pre + u"· 原件本机字节未动，本地字节重算的 sha1 `%s`"
                                      u"（原件从未入 git，故意不可取回，所以它不是 blob 坐标），容器 blob `%s`。" % (FAKE, good)),
        "exempt_p3_line48_verbatim": ("exempt", pre + u"· 坐标：原件 = 本地字节重算的 sha1 `%s`（非 blob，不可 cat-file）"
                                      u" ／ 证明件（blob，架上可取）`%s`。" % (FAKE, good)),
        "fire_undeclared_same_value": ("fire", pre + u"证据件 `%s` 已上架。" % FAKE),
        "fire_declared_but_no_anchor_on_line": ("fire", pre + u"本地字节重算的 sha1 `%s`（原件从未入 git，故意不可取回）。" % FAKE),
        "fire_declared_anchor_in_OTHER_paragraph": ("fire", pre + u"锚点件 `%s`\n\n" % good
                                                    + u"另一段里孤零零写 `%s`（本地字节重算、故意不可取回）。" % FAKE),
        "exempt_s4_sha1_over_bytes_wording": ("exempt", pre + u"· 尺本体 blob `%s`；架上读出与本地副本的"
                                              u" sha1(over bytes) 同为 `%s`。" % (good, FAKE)),
        "exempt_s4_file_sha1_wording": ("exempt", pre + u"· 架上 blob `%s` 与文件 sha1 `%s` 不是一回事，"
                                        u"后者是我对字节直接算的。" % (good, FAKE)),
        "negative_control_the_word_blob_alone_does_not_refuse": ("exempt", pre + u"blob `%s` 可从架上取。" % good),
        "exempt_line_all_coordinates_resolve": ("exempt", pre + u"两件 `%s` 与 `%s` 均可 cat-file。" % (good, good)),
    }


def run(text):
    p = os.path.join(TMP, "block.md")
    io.open(p, "w", encoding="utf-8", newline="\n").write(text + "\n")
    r = subprocess.run([sys.executable, "-X", "utf8", DOOR, ANCHOR, p],
                       capture_output=True, text=True, timeout=600, encoding="utf-8", errors="replace")
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def main():
    good = real_blob()
    # Same reason the door fetches before it judges: a blob published minutes ago is not in this object store
    # yet.  Without this the selftest's own anchor reads as "unresolvable" - the exact false alarm that cost
    # two lanes a refused block at 00:45 / 00:59.
    subprocess.run(["git", "-C", REPO, "fetch", "origin", "+refs/heads/*:refs/remotes/origin/*", "--quiet"],
                   capture_output=True, timeout=900)
    assert resolves(good), "the selftest's own anchor coordinate must resolve: %s" % good
    checks, rows = {}, []
    for name, (kind, text) in sorted(fixtures(good).items()):
        rc, out = run(text)
        reached_anchor = "anchor not found" in out
        bolt_fired = rc == 9
        if kind == "exempt":
            checks[name] = (not bolt_fired) and reached_anchor
        else:
            checks[name] = bolt_fired and not reached_anchor
        rows.append({"fixture": name, "expect": kind, "rc": rc, "bolt_fired": bolt_fired,
                     "reached_anchor_check": reached_anchor,
                     "first_line": out.strip().splitlines()[0][:160] if out.strip() else ""})
    ok = all(checks.values())
    print(json.dumps({"door_blob": hashlib.sha1(b"blob %d\0" % len(io.open(DOOR, "rb").read())
                                                + io.open(DOOR, "rb").read()).hexdigest(),
                      "anchor_coordinate_used": good, "checks": checks,
                      "all_two_way_assertions_hold": ok, "rows": rows},
                     ensure_ascii=False, indent=1))
    return 0 if ok else 6


if __name__ == "__main__":
    sys.exit(main())
