"""ORD-0500 r16: refuse to ship the page emitter with a %-format whose arity does not match.

Three hands of this order died on exactly this: a sentence template grew a placeholder, the argument
tuple did not, and the defect only appeared when the emitter ran -- which, after the readings chain had
already committed and pushed, meant a ref carrying an emitter that could not produce the very page it
was cut for.  Counting is cheap here and belongs in the door, not in the reviewer's hands.

Walks every `<string constant> % <args>` in the emitter.  `%s`/`%d`/`%f` in the template must equal the
number of arguments, except where an argument is itself a `%`-format (its own placeholders are already
satisfied by its own tuple).  Reports the file, the byte length, the number of placeholders and the
number of args for every call it can decide statically, and aborts on the first mismatch.

Exit 0 = every checkable call agrees.  `selftest` runs it against a deliberately broken sample.
"""
import ast
import json
import os
import re
import sys

PLACEHOLDER = re.compile(r"(?<!%)%[-+ #0-9,._]*[diouxXeEfFgGcrsa]")
LANE = r"D:/moodle/_qoder_phone_ord0485_20260930"


VALID = re.compile(r"%(%|[-+ #0-9,._]*[diouxXeEfFgGcrsa])")


def bad_specs(text):
    """Every `%` in the template that is not a conversion and not `%%`.

    A prose percent ("通过率 % 之几") is a runtime ValueError waiting to happen, and the emitter is
    full of CJK text where a percent sign reads like the start of a spec -- `% (` especially, since
    space is a legal flag and `(` is not a conversion, so Python gets as far as rejecting the character
    instead of catching my typo.
    """
    out, i = [], 0
    while i < len(text):
        if text[i] != "%":
            i += 1
            continue
        m = VALID.match(text, i)
        if m:
            i = m.end()
            continue
        out.append({"at": i, "around": text[i:i + 12]})
        i += 1
    return out


def check(path):
    src = open(path, encoding="utf-8").read()
    tree = ast.parse(src)
    rows, bad, uncountable, specs = [], [], [], []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.BinOp) and isinstance(node.op, ast.Mod)):
            continue
        left = node.left
        if not (isinstance(left, ast.Constant) and isinstance(left.value, str)):
            continue                      # template built at runtime: cannot count it here
        specs += [{"line": node.lineno, "file": path, **b} for b in bad_specs(left.value)]
        ph = len(PLACEHOLDER.findall(left.value))
        rhs = node.right
        if not isinstance(rhs, ast.Tuple):
            # one expression feeding N slots (`"%s %s" % kv` over .items(), a dict, a regex match):
            # its arity is decided at runtime, so counting it here would only manufacture reds
            uncountable.append({"line": node.lineno, "placeholders": ph,
                                "template": left.value[:60]})
            continue
        args = rhs.elts
        nested = [a for a in args if isinstance(a, ast.BinOp) and isinstance(a.op, ast.Mod)]
        if nested:
            continue                        # its own arity is checked as its own node
        rows.append({"line": node.lineno, "placeholders": ph, "args": len(args)})
        if ph != len(args):
            bad.append({"line": node.lineno, "placeholders": ph, "args": len(args),
                        "template": left.value[:90]})
    return {"file": os.path.relpath(path, LANE).replace("\\", "/"), "bytes": len(src.encode("utf-8")),
            "calls_checked": len(rows), "single_expression_args": len(uncountable),
            "mismatched": bad, "invalid_specs": specs,
            "verdict": "GREEN" if not bad and not specs else "RED"}


def selftest():
    """Prove the lint is not vacuous: a wrong arity and a prose percent must both come back RED by line,
    and a correct call must come back GREEN (a ruler that rejects everything is as useless as one that
    rejects nothing)."""
    samples = [("run/fmtlint_selftest_broken.py", "A = print\nA(\"two slots %s and %s\" % (1,))\n",
                "RED", 2, "mismatched"),
               ("run/fmtlint_selftest_spec.py",
                "A = print\nA(\"pass rate 80 % (of them red)\" % (1,))\n", "RED", 2, "invalid_specs"),
               ("run/fmtlint_selftest_ok.py", "A = print\nA(\"one slot %s\" % (1,))\n",
                "GREEN", None, "mismatched")]
    rows = []
    for name, body, want, line, key in samples:
        path = os.path.join(LANE, name)
        open(path, "w", encoding="utf-8").write(body)
        out = check(path)
        os.remove(path)
        found = out[key]
        ok = out["verdict"] == want and (line is None or any(m.get("line") == line for m in found))
        rows.append({"sample": name, "expected": "%s via %s" % (want, key), "got": out["verdict"],
                     "matched_line": line, "hits": len(found), "verdict": "PASS" if ok else "FAIL"})
    passed = sum(1 for r in rows if r["verdict"] == "PASS")
    return {"samples": rows, "ran_on": "; ".join(r["sample"] for r in rows),
            "expected": "2 红 1 绿，且都按行号对上", "got": "%d/%d 对上" % (passed, len(rows)),
            "verdict": "PASS" if passed == len(rows) else "FAIL"}


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        st = selftest()
        print("SELFTEST %s (%s)" % (st["verdict"], st["mismatched"]))
        return 0 if st["verdict"] == "PASS" else 1
    files = sys.argv[1:] or [os.path.join(LANE, "tools", "r10_block.py")]
    results, total_bad, total_specs = [], [], []
    for arg in files:
        out = check(arg)
        print("%s calls_checked=%d single_expression_args=%d mismatched=%d invalid_specs=%d "
              "verdict=%s" % (out["file"], out["calls_checked"], out["single_expression_args"],
                              len(out["mismatched"]), len(out["invalid_specs"]), out["verdict"]))
        for m in out["mismatched"]:
            print("   line %s: %d 个槽位 对 %d 枚参数 | %s" % (
                m["line"], m["placeholders"], m["args"], m["template"]))
        for s in out["invalid_specs"]:
            print("   line %s: 这个 `%%` 不是转义也不是槽位：`%s`" % (s["line"], s["around"]))
        total_bad += out["mismatched"]
        total_specs += out["invalid_specs"]
        results.append(out)
    st = selftest()
    receipt = {"tool": os.environ.get("FMTLINT_TOOL") or "fmt_lint_r15",
               "files": [r["file"] for r in results],
               "files_scanned": len(results),
               "calls_checked": sum(r["calls_checked"] for r in results),
               "single_expression_args": sum(r["single_expression_args"] for r in results),
               "mismatched": total_bad, "invalid_specs": total_specs,
               "verdict": "GREEN" if not total_bad and not total_specs else "RED",
               "selftest": st}
    dest = os.path.join(LANE, "evidence", os.environ.get("FMTLINT_OUT") or "fmt_lint_r14.json")
    json.dump(receipt, open(dest, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    print("selftest=%s (%s) WROTE %s" % (st["verdict"], st["got"], dest))
    if total_bad or total_specs or st["verdict"] != "PASS":
        raise SystemExit("ABORT_FORMAT_ARITY 槽位不对 %d 处、野 %% 号 %d 处、自检 %s" % (
            len(total_bad), len(total_specs), st["verdict"]))
    print("fmt lint GREEN")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
