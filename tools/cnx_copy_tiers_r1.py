#!/usr/bin/env python
"""Copy-register gate for frontend/src/i18n/LocaleContext.tsx.

Three gated claims plus one honest remainder report, all derived from measured
bytes rather than asserted:

  REGISTER_PARITY  a key may not speak two registers at once: an English
                   "Couldn't ..." paired with a Chinese "××失败" is the drift
                   this batch removes. Pi Travel ships that drift itself
                   (65% of its failure copy reads "Couldn't" in English while
                   92% stays "失败/无法" in Chinese), so it is a defect to
                   avoid, not a target to copy.
  NO_GROWTH        the Chinese side of a touched key must not gain a single
                   character. Two screens here were bitten by a control that
                   grew out of its hit area, so re-wording may not become
                   re-sizing.
  NOT_PINNED       no touched key may still be quoted verbatim by an e2e
                   literal. This batch edits copy only and edits no
                   assertion, so anything an e2e still pins must be skipped.
  REMAINDER        counts what is left unfixed. Reported, never gated, so a
                   green run is not mistaken for "finished".

--mutant injects one defect per gated claim; each must be caught or the ruler
itself is the defect.
"""
import argparse
import re
import sys
from pathlib import Path

KEY_RE = re.compile(r'^\s*"([A-Za-z0-9._-]+)"\s*:\s*"(.*)"\s*,?\s*$')
EN_SOFT = re.compile(r"couldn'?t|can'?t|unable", re.I)
EN_HARD = re.compile(r"\bfailed\b|\bfailure\b", re.I)
ZH_HARD = re.compile(r"失败|发生了错误")
ZH_SOFT = re.compile(r"没能|未能|请再试|稍后再试")


def dicts(path):
    """Parse the language blocks of LocaleContext into {lang: {key:(val,line)}}."""
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    marks = [i for i, ln in enumerate(lines) if re.match(r"^const (en|zhCN): Dict", ln)]
    if len(marks) < 2:
        raise SystemExit(f"FATAL expected `en` and `zhCN` Dict blocks in {path}, found {len(marks)}")
    out = {}
    for idx, start in enumerate(marks):
        lang = re.match(r"^const (\w+):", lines[start]).group(1)
        stop = marks[idx + 1] if idx + 1 < len(marks) else len(lines)
        table = {}
        for i in range(start, stop):
            m = KEY_RE.match(lines[i].rstrip("\r"))
            if m:
                table.setdefault(m.group(1), (m.group(2), i + 1))
        out[lang] = table
    return out


def e2e_corpus(root):
    """[(display path, text)] for every spec file, so a hit can name its line."""
    parts = []
    for p in sorted(Path(root).rglob("*")):
        if p.is_file() and p.suffix in {".ts", ".cjs", ".js", ".mjs"}:
            parts.append((p.name, p.read_text(encoding="utf-8", errors="replace")))
    return parts


CALL_RE = re.compile(r'(?:toContainText|toHaveText|getByText)\s*\(\s*(?:"([^"\n]{2,140})"|/([^/\n]{2,140})/([a-z]*))')
NAME_RE = re.compile(r'(?<![A-Za-z_])name\s*:\s*(?:"([^"\n]{2,140})"|/([^/\n]{2,140})/([a-z]*))')


def assertion_patterns(corpus):
    """Pull out every text assertion in the suite as (source, kind, matcher).

    Two shapes only: a direct text call (toContainText / toHaveText /
    getByText) and a `name:` option on a role query. Group numbering is fixed
    per pattern -- 1 literal, 2 regex body, 3 flags -- because a shared
    alternation silently renumbered itself and quietly matched nothing.
    """
    out = []
    for fname, text in corpus:
        for lineno, line in enumerate(text.split("\n"), 1):
            for rx, kind_hint in ((CALL_RE, "text call"), (NAME_RE, "role name")):
                for m in rx.finditer(line):
                    lit, reg, flags = m.group(1), m.group(2), m.group(3) or ""
                    src = f"{fname}:{lineno}"
                    if lit:
                        out.append((src, f"literal/{kind_hint}", ("lit", lit)))
                    elif reg:
                        try:
                            compiled = re.compile(reg, re.I if "i" in flags else 0)
                        except re.error:
                            continue
                        out.append((src, f"regex/{kind_hint}", ("re", compiled)))
    return out


def matches(pat, value):
    kind, body = pat
    if kind == "lit":
        return body.lower() in value.lower()
    return bool(body.search(value))


def diff_keys(bas, aft):
    """[(key, lang)] where the value actually changed between two parses."""
    out = []
    for lang in ("en", "zhCN"):
        for k, (v, _ln) in aft.get(lang, {}).items():
            old = bas.get(lang, {}).get(k)
            if old is not None and old[0] != v:
                out.append((k, lang))
    return out


def audit(after_path, base_path, e2e_dir):
    aft = dicts(after_path)
    bas = dicts(base_path) if base_path else aft
    corpus = e2e_corpus(e2e_dir) if e2e_dir else ""
    findings = []

    # ---- C1 register parity ------------------------------------------------
    shared = sorted(set(aft["en"]) & set(aft["zhCN"]))
    clashes, agreed = [], 0
    for k in shared:
        en, enl = aft["en"][k]
        zh, zhl = aft["zhCN"][k]
        bad = (EN_SOFT.search(en) and ZH_HARD.search(zh)) or (ZH_SOFT.search(zh) and EN_HARD.search(en))
        if bad:
            clashes.append(f"{k} @line {enl}/{zhl}: en={en[:34]!r} zh={zh[:22]!r}")
        else:
            agreed += 1
    findings.append(("REGISTER_PARITY",
                     f"{len(shared)} bilingual keys: {agreed} agree, {len(clashes)} clash",
                     not clashes, " || ".join(clashes[:4]) or "none"))

    # ---- C2 growth guard ---------------------------------------------------
    changed = diff_keys(bas, aft)
    zh_grew, en_over = [], []
    for k, lang in changed:
        before = bas[lang][k][0]
        after = aft[lang][k][0]
        if lang == "zhCN" and len(after) > len(before):
            zh_grew.append(f"{k} {len(before)}->{len(after)}")
        if lang == "en" and len(after) > len(before) + 8:
            en_over.append(f"{k} {len(before)}->{len(after)} cap {len(before) + 8}")
    findings.append(("NO_GROWTH",
                     f"{len(changed)} values changed; zh gained chars: {len(zh_grew)}, en over +8: {len(en_over)}",
                     not zh_grew and not en_over,
                     " || ".join((zh_grew + en_over)[:4]) or "every Chinese rewrite is the same length or shorter"))

    # ---- C3 assertion simulation ------------------------------------------
    # Checking whether a whole i18n value appears in the e2e corpus is too
    # weak: an assertion can quote a fragment ("toContainText(/失败/)",
    # getByRole({name: "Couldn't"})) and still lose its target when the copy
    # moves. So instead of pattern-matching the corpus, run the assertions:
    # for every text assertion in the suite, does it match the OLD value and
    # stop matching the NEW one? That is exactly the shape of a gate this
    # batch would break, and it is measured, not assumed.
    touched = sorted({k for k, _ in changed})
    patterns = assertion_patterns(corpus) if corpus else []
    broken = []
    for k in touched:
        for lang in ("en", "zhCN"):
            old = bas[lang].get(k, ("", 0))[0]
            new = aft[lang].get(k, ("", 0))[0]
            if not old:
                continue
            for src, kind, pat in patterns:
                if matches(pat, old) and not matches(pat, new):
                    broken.append(f"{k}[{lang}] {src}: {kind} matched the old copy and no longer matches")
    findings.append(("ASSERTIONS_STILL_HIT",
                     f"{len(touched)} keys edited against {len(patterns)} e2e text assertions; "
                     f"{len(broken)} would lose their target",
                     not broken, " || ".join(broken[:4]) or "every assertion that hit these values still hits the new ones"))

    # ---- C4 remainder (measured, not gated) --------------------------------
    now_en = sum(1 for v, _ in aft["en"].values() if EN_HARD.search(v))
    now_zh = sum(1 for v, _ in aft["zhCN"].values() if ZH_HARD.search(v))
    was_en = sum(1 for v, _ in bas["en"].values() if EN_HARD.search(v))
    was_zh = sum(1 for v, _ in bas["zhCN"].values() if ZH_HARD.search(v))
    findings.append(("REMAINDER_REPORT",
                     f"en hard words {was_en}->{now_en} | zh hard words {was_zh}->{now_zh} (not gated)",
                     True, "left visible on purpose: green here does not mean the file is finished"))
    return findings


def mutants(src_text, workdir, base_path, e2e_dir):
    """One injected defect per gated claim."""
    cases = []
    # K1: re-introduce a register clash on a key this batch fixed
    k1 = src_text.replace('"没能确认。"', '"确认失败。"')
    cases.append(("K1_register_clash", k1))
    # K2: lengthen the Chinese side of a touched key
    k2 = src_text.replace('"没能加载行程记忆。"', '"没能加载您之前保存下来的行程记忆内容。"')
    cases.append(("K2_zh_grew", k2))
    # K3: touch a key that an e2e still quotes verbatim
    k3 = src_text.replace('"My trip and preferences"', '"Your trips and what you like"')
    cases.append(("K3_pinned_key_touched", k3))
    out = []
    for label, mutated in cases:
        if mutated == src_text:
            out.append((label, "mutation did not apply -- nothing was handed to the ruler", False))
            continue
        p = Path(workdir) / f"_mut_{label}.tsx"
        p.write_text(mutated, encoding="utf-8", newline="\n")
        try:
            caught = sorted(n for n, _, ok, _ in audit(str(p), base_path, e2e_dir) if not ok)
        finally:
            p.unlink(missing_ok=True)
        out.append((label, ("caught by " + ",".join(caught)) if caught else "NOT CAUGHT", bool(caught)))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--i18n", required=True)
    ap.add_argument("--baseline")
    ap.add_argument("--e2e")
    ap.add_argument("--mutant", action="store_true")
    a = ap.parse_args()

    rc = 0
    print(f"== cnx_copy_tiers_r1  i18n={a.i18n}  baseline={a.baseline or 'self'}  e2e={a.e2e or 'none'}")
    for name, measure, ok, detail in audit(a.i18n, a.baseline, a.e2e):
        print(f"  [{'MET' if ok else 'VIOLATION'}] {name:17s} {measure}")
        print(f"          detail: {detail}")
        rc |= 0 if ok else 1
    if a.mutant:
        if not (a.baseline and a.e2e):
            print("  --mutant needs --baseline and --e2e; skipping instead of reporting a clean self-test")
            return rc or 1
        print("  -- ruler self-test: each injected defect must be caught --")
        for label, detail, ok in mutants(Path(a.i18n).read_text(encoding="utf-8"),
                                         Path(a.i18n).parent, a.baseline, a.e2e):
            print(f"  [{'MET' if ok else 'VIOLATION'}] {label:24s} {detail}")
            rc |= 0 if ok else 1
    print(f"exit={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
