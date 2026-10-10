"""Prove the landing recipe by A/B/C, not by assertion.

The writer's coordinate bolt (ledger_insert_after.py:94-109) carries an unresolvable 40-hex value ONLY when
BOTH conjuncts hold: (1) the value's OWN line matches the non-retrievable disclosure pattern, and
(2) the value's OWN paragraph (consecutive non-blank lines) also holds a coordinate that really resolves.
Three model blocks isolate the two conjuncts, each run through BOTH real arms:
  GOOD        declared + same-paragraph resolvable coordinate  -> must WOULD-LAND
  BAD_NODECL  no declaration, same-paragraph coordinate        -> must WOULD-ABORT
  BAD_NOPARA  declared, but the coordinate sits in another paragraph -> must WOULD-ABORT
If any arm reads the wrong way, the recipe is not proven and must not be relayed.
"""
import io
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bolt_replica as BR

TIP_REF = "refs/heads/mirror/integration-frontend-apple-pass1"
COUNT_LINE = ("计数都在同一行带坐标：`backend/app/main.py:2999` 有 1 条 undelete 路由；"
              "`green_stuck.py:33` 报 findings=0；本块首行是 1 个 `### ` 标题。")


def tip():
    r = subprocess.run(["git", "-c", "http.proxy=", "-c", "https.proxy=", "-C", r"D:\moodle\CityNexus",
                        "ls-remote", "origin", TIP_REF], capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=180)
    parts = (r.stdout or "").split()
    if not parts or not re.match(r"^[0-9a-f]{40}$", parts[0]):
        raise SystemExit("ABORT: no tip from ls-remote, cannot build a resolvable coordinate: %r" % (parts,))
    return parts[0]


def local_sha1(path):
    import hashlib
    return hashlib.sha1(io.open(path, "rb").read()).hexdigest()


def build(t, sha, mode):
    """mode: good | nodecl | nopara"""
    if mode == "nodecl":
        # the wording map used at 0404/0447: calls a local file's hash a "blob" and says nothing about
        # retrievability - which is exactly what the disclosure pattern does NOT match.
        sha_line = "机器读数 `gauge.json`，blob `" + sha + "`"
    else:
        sha_line = ("本机量具输出：`gauge.json` 的文件内容 sha1 `" + sha +
                    "`（本地字节重算，不是 git 对象）")
    tip_line = "可读的真对象：权威尖 `" + t + "`（`git ls-remote origin " + TIP_REF + "` 回读）"
    name = {"good": "GOOD", "nodecl": "BAD-NODECL", "nopara": "BAD-NOPARA"}[mode]
    head = "### RECIPE-SELFTEST lane patrol · " + name + " · 2026-09-28 1931"
    if mode == "nopara":
        body = [head, "", sha_line, "", tip_line, "", COUNT_LINE, ""]
    else:
        body = [head, "", tip_line, sha_line, "", COUNT_LINE, ""]
    return "\n".join(body) + "\n"


def main():
    t = tip()
    src = os.path.join(HERE, "_recipe_selftest.py")
    sh = local_sha1(src)
    print("control: tip=%s resolves=%s ; the content-hash value is the real sha1 of %s (%d B) = %s"
          % (t[:12], BR.resolves(t), os.path.basename(src), os.path.getsize(src), sh[:12]))
    want = {"good": False, "nodecl": True, "nopara": True}
    paths = {}
    ok = True
    for mode in ("good", "nodecl", "nopara"):
        p = os.path.join(HERE, "_recipe_%s.md" % mode)
        io.open(p, "w", encoding="utf-8", newline="\n").write(build(t, sh, mode))
        paths[mode] = p
        q43, aborts, carried, ntok = BR.evaluate(p)
        door = subprocess.run([BR.PY, BR.RULER, "--text", p, "--expect-clean"], capture_output=True, timeout=600)
        verdict = "WOULD-ABORT" if aborts else "WOULD-LAND"
        must_abort = want[mode]
        agrees = (bool(aborts) == must_abort) and q43 == "GREEN"
        print("  %-9s %-16s q43=%s(rc %d) tokens=%d carried=%d aborts=%d -> %-11s expected=%s %s"
              % (mode, os.path.basename(p), q43, door.returncode, ntok, len(carried), len(aborts), verdict,
                 "ABORT" if must_abort else "LAND", "OK" if agrees else "MISMATCH"))
        for ln, tok, dec, anc in aborts:
            print("            L%d %s declared=%s anchored=%s" % (ln, tok[:12], dec, anc))
        ok = ok and agrees
    print("RESULT: %s" % ("RECIPE PROVEN - both conjuncts are load-bearing and the good form lands"
                          if ok else "NOT PROVEN - do not relay this recipe"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
