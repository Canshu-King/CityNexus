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
  COMPONENT_FALLBACK  (ORD-0370, needs --src) the three claims above read only
                   LocaleContext, so a component that invents its own sentence
                   in a `??` slot walks past every one of them. This face reads
                   the components: tier A is a language branch sitting in that
                   slot (`?? (zh ? "…" : "…")`), tier B is a bare literal there,
                   which a Chinese device is shown as English. Shape only: this
                   face never claims the bytes reached a screen.
  CORPUS_GATE      (ORD-0370) a named --e2e path that is not a directory used
                   to read 0 assertions and still print MET. Refusing that is
                   the only way the first four claims can be trusted from a
                   transcript; it can make ASSERTIONS_STILL_HIT redder, never
                   quieter.

--mutant injects one defect per gated claim; each must be caught or the ruler
itself is the defect.
"""
import argparse
import re
import sys
import tempfile
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


# --------------------------------------------------------------------------
# COMPONENT_FALLBACK face (ORD-0370)
# --------------------------------------------------------------------------
DQ = r'"((?:[^"\\\n]|\\.)*)"'
SQ = r"'((?:[^'\\\n]|\\.)*)'"
STR = r"(?:" + DQ + r"|" + SQ + r")"
# tier A: a language branch parked in a `??` slot -- `?? (zh ? "..." : "...")`,
# with or without the parentheses. The condition is captured so it can be
# checked: an unrelated ternary that merely sits after a `??` in the same line
# (`(contentType ?? "").includes("html") ? "html" : "not_json"`) is a media-type
# label handed to an Error, not a language branch, and counting it as one would
# teach people to distrust every hit this face reports.
A_RE = re.compile(r"\?\?\s*\(?\s*([^?:;{}]{0,60}?)\?\s*" + STR + r"\s*:\s*" + STR)
LOCALE_TEST = re.compile(r"\b(zh|zhCN|zh_cn|isZh|locale|language|lang|chinese|simplified|hans)\b")
# tier B: a bare literal in that slot.
B_RE = re.compile(r"\?\?\s*" + STR)
# denominator only: any inline bilingual pair, wherever it sits.
PAIR_RE = re.compile(r"\?\s*" + STR + r"\s*:\s*" + STR)
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
SCREAMING = re.compile(r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$")
HTTPISH = re.compile(r"^\dxx$|^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$")


def _pick(groups, first, second):
    for i in (first, second):
        if groups[i - 1] is not None:
            return groups[i - 1]
    return None


def _is_copy(lit):
    """Is this literal candidate user-facing copy rather than a machine token?

    Every exclusion names the evidence it fired on: a filter that only reports
    a number cannot be audited for quietly silencing the stock.
    """
    if lit.strip() == "":
        return False, "empty"
    if CJK_RE.search(lit):
        return False, "CJK inside (tier-A shape, not a bare English fallback)"
    if SCREAMING.match(lit.strip()):
        return False, "SCREAMING_SNAKE enum value"
    if HTTPISH.match(lit.strip()):
        return False, "http method / status-class token"
    return True, "copy"


def slot_shape(line, upto):
    """What construct the `??` sits in, read from the text before it on the line.

    This is a SHAPE hint and is reported as one: it never removes a hit from the
    count, because "this cannot render" is exactly the kind of claim a text
    ruler is not entitled to make. It exists so a reader can triage the stock
    without re-opening 78 files.
    """
    head = line[:upto]
    if re.search(r"\bdata-[A-Za-z-]+\s*=\s*\{", head):
        return "data-attr"
    if re.search(r"\b(aria-[A-Za-z-]+|title|placeholder|alt|label)\s*=\s*\{", head):
        return "a11y-or-tooltip"
    if re.search(r"\bkey\s*=\s*\{", head):
        return "react-key"
    if re.search(r"\b(set[A-Z]\w*|useState|useState<[^>]*>)\s*\(\s*", head):
        return "state-write"
    if "`" in head and re.search(r"\w+\s*=\s*\$\{", head):
        return "telemetry-string"
    if re.search(r"\w+\s*:\s*[^=]*$", head) and not re.search(r"[<>{}]", head[-40:]):
        return "js-value"
    if re.search(r"[<>]\s*[^<>]*$", head) or re.search(r"\{\s*[A-Za-z_.$\[\]?'\"()]*\s*$", head):
        return "jsx-or-expr"
    return "other"


def fallback_hits(text, name):
    """[(tier, file, line, literal, why)] for one file's text.

    A `??` that ends a line and a fallback that opens the next line are one
    expression, not two, so the pair is read as a joined window; the hit is
    still attributed to the line carrying the literal.
    """
    lines = text.split("\n")
    hits = []
    seen = set()
    for i, line in enumerate(lines):
        if line.strip().startswith(("//", "*")):
            continue
        prev = lines[i - 1].rstrip() if i > 0 else ""
        windows = [(line, i + 1)]
        if prev.endswith("??"):
            windows.append((prev + " " + line, i + 1))
        for window, at in windows:
            for rx, tier in ((A_RE, "A"), (B_RE, "B")):
                for m in rx.finditer(window):
                    shape = slot_shape(window, m.start())
                    if tier == "A":
                        cond = m.group(1) or ""
                        lits = (_pick(m.groups(), 2, 3), _pick(m.groups(), 4, 5))
                        if not LOCALE_TEST.search(cond):
                            for lit in lits:
                                if lit is not None:
                                    _tally(hits, seen, "A", name, at, lit,
                                           (False, "not a language branch: condition %r names no locale" % cond.strip()[:40]),
                                           shape)
                            continue
                        for lit in lits:
                            if lit is None:
                                continue
                            _tally(hits, seen, "A", name, at, lit, _is_copy(lit), shape)
                    else:
                        lit = _pick(m.groups(), 1, 2)
                        if lit is None:
                            continue
                        _tally(hits, seen, "B", name, at, lit, _is_copy(lit), shape)
    return hits


def _tally(hits, seen, tier, name, at, lit, verdict, shape="other"):
    key = (name, at, lit)
    if key in seen:
        return
    seen.add(key)
    found, why = verdict
    hits.append((tier if found else tier + "-skipped", name, at, lit,
                 "language branch in a ?? slot" if tier == "A" and found else
                 ("bare literal in a ?? slot" if tier == "B" and found else why),
                 shape))


def scan_tree(src_dir):
    hits, pairs, files = [], 0, 0
    for p in sorted(Path(src_dir).rglob("*")):
        if p.suffix not in {".ts", ".tsx"} or "node_modules" in p.parts:
            continue
        files += 1
        text = p.read_text(encoding="utf-8", errors="replace")
        hits += fallback_hits(text, str(p))
        pairs += len(PAIR_RE.findall(text))
    return hits, pairs, files


def component_fallback(src_dir):
    """The gated claim plus its denominator, both computed from the tree."""
    from collections import Counter
    hits, pairs, files = scan_tree(src_dir)
    tier_a = [h for h in hits if h[0] == "A"]
    tier_b = [h for h in hits if h[0] == "B"]
    skipped = [h for h in hits if h[0].endswith("-skipped")]
    bad = tier_a + tier_b
    detail = " || ".join("%s %s:%d %r" % (t, f, ln, lit) for t, f, ln, lit, _, _s in bad[:3]) \
        or "no hardcoded fallback copy left in a ?? slot"
    # The breakdown counts every hit, so no bucket can hide stock from the claim.
    shapes = Counter(h[5] for h in bad)
    shape_txt = ", ".join("%s=%d" % (k, v) for k, v in sorted(shapes.items(), key=lambda kv: -kv[1]))
    measure = ("%d files scanned: tier A (language branch in the slot) %d, tier B (bare literal) %d, "
               "excluded as machine tokens %d; inline bilingual pairs anywhere = %d "
               "(denominator only -- most are legitimate inline pairs, NOT a defect count)"
               % (files, len(tier_a), len(tier_b), len(skipped), pairs))
    return ("COMPONENT_FALLBACK",
            measure,
            not bad,
            "shape of the %d hit(s) by slot: %s. This breakdown removes nothing -- it is a triage "
            "hint, and 'data-attr' here means the ?? sits inside a data-* attribute on this line, "
            "which a text ruler cannot prove never renders. Detail: " % (len(bad), shape_txt) + detail)


def fallback_mutants():
    """Four arms: two must be caught, two must stay quiet.

    The quiet arms are what prove the machine-token filter is load-bearing -- a
    ruler that flags everything is indistinguishable from one that flags nothing.
    """
    clean = '  setActionState(copyFor(attribution, zh).body ?? t("agent.stopFailed"));\n'
    tier_a = '  setActionState(copyFor(attribution, zh).body ?? (zh ? "停止失败" : "Stop failed"));\n'
    tier_b = '  setActionState(copyFor(attribution, zh).body ?? "Stop failed");\n'
    enum_ok = '  const code = (await r.json()).error_code ?? "SERVER_UNAVAILABLE";\n'
    multiline = '  const raw = body?.detail ??\n    (zh ? "暂时无法接受。" : "Could not accept.");\n'
    # A real shape from this tree (api/citynexus.ts:691): a media-type label that
    # merely sits after a `??` on the same line. Counting it would be a false
    # positive, and this arm is what proves the locale test is load-bearing.
    media = '      emptyAnswer ? "empty" : (contentType ?? "").includes("html") ? "html" : "not_json",\n'
    arms = [("K4a_dictionary_read_quiet", clean, 0),
            ("K4b_tier_A_language_branch", tier_a, 1),
            ("K4c_tier_B_bare_literal", tier_b, 1),
            ("K4d_machine_token_quiet", enum_ok, 0),
            ("K4e_split_across_lines", multiline, 1),
            ("K4i_media_type_ternary_quiet", media, 0)]
    out = []
    for label, source, expect in arms:
        got = [h for h in fallback_hits(source, label) if not h[0].endswith("-skipped")]
        if expect and not got:
            out.append((label, "NOT CAUGHT -- source %r produced 0 hits" % source.strip()[:64], False))
        elif expect and len(got) < expect:
            out.append((label, "PARTIAL -- %d hit(s), wanted >=%d" % (len(got), expect), False))
        elif not expect and got:
            out.append((label, "FALSE POSITIVE -- flagged %r" % got[0][3], False))
        else:
            out.append((label, "%d hit(s) as expected" % len(got), True))
    return out


def audit(after_path, base_path, e2e_dir, src_dir=None):
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
    #
    # Corpus gate (ORD-0370, added because it can only make this arm redder): a
    # named --e2e path that is not a directory yields zero assertions, and zero
    # assertions lets the claim pass while reading nothing. Measured on this box
    # with the pre-ORD-0370 ruler: `--e2e frontend/src/../../e2e` (which is
    # `<repo>/e2e`, and does not exist) read "0 e2e text assertions" and printed
    # MET, where the correct path read 213. The path was simply wrong; nothing
    # about `..` handling is implicated -- a `..` spelling that does resolve is
    # checked by K4g and still passes.
    if e2e_dir and not Path(e2e_dir).is_dir():
        findings.append(("ASSERTIONS_STILL_HIT",
                         f"e2e directory {e2e_dir!r} is not a readable directory; 0 assertions read",
                         False,
                         "REFUSED: an unreadable --e2e makes this claim vacuous, so it is not a pass. "
                         "Pass the directory as a resolved path."))
    else:
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

    # ---- C5 component-side hardcoded fallbacks (ORD-0370) --------------------
    # Gated: a hit is a defect whether or not the dictionaries are clean, and
    # the stock here is real, so a first run over an unfixed tree is expected to
    # report VIOLATION with its count. Without --src nothing was read, which is
    # reported as NOT_RUN rather than as a pass.
    findings.append(coverage_finding(after_path))
    if src_dir:
        findings.append(component_fallback(src_dir))
    else:
        findings.append(("COMPONENT_FALLBACK_NOT_RUN",
                         "no component was read (pass --src frontend/src to enable this face)",
                         True, "NOT_RUN is not a pass: hardcoded fallback copy was never measured"))
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


def corpus_guard_mutants(i18n_path, base_path, e2e_dir):
    """The corpus gate's own proof: a path that is not a directory must be
    refused, and two spellings that do resolve must still pass -- otherwise the
    gate is noise that teaches people to ignore it."""
    import os
    bogus = os.path.join(e2e_dir, "_definitely_not_a_directory_")
    dotdot = os.path.join(e2e_dir, os.pardir, "src", os.pardir, "e2e")
    arms = [("K4f_e2e_path_not_a_dir", bogus, False),
            ("K4g_dotdot_spelling_resolves", dotdot, True),
            ("K4h_plain_path_resolves", e2e_dir, True)]
    out = []
    for label, probe, want_met in arms:
        verdicts = {n: ok for n, _, ok, _ in audit(i18n_path, base_path, probe)}
        got = verdicts.get("ASSERTIONS_STILL_HIT")
        if got is None:
            out.append((label, "no ASSERTIONS_STILL_HIT verdict was produced at all", False))
        elif got != want_met:
            out.append((label, "%r gave %s, wanted %s" % (probe, "MET" if got else "VIOLATION",
                                                           "MET" if want_met else "VIOLATION"), False))
        else:
            out.append((label, "%r -> %s as expected" % (probe, "MET" if got else "VIOLATION"), True))
    return out


def wrapped_value_keys(path):
    """Keys the single-line KEY_RE cannot see: `"key":` with the value next line.

    Reported, never folded into the four dictionary claims, because widening
    that parser mid-batch would move the ground under verdicts already issued
    against it. What it does move is the meaning of a green REGISTER_PARITY:
    every key listed here was not read by it.
    """
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    marks = [i for i, ln in enumerate(lines) if re.match(r"^const (en|zhCN): Dict", ln)]
    out = {}
    for idx, start in enumerate(marks):
        lang = re.match(r"^const (\w+):", lines[start]).group(1)
        stop = marks[idx + 1] if idx + 1 < len(marks) else len(lines)
        for i in range(start, stop):
            m = re.match(r'^\s*"([A-Za-z0-9._-]+)"\s*:\s*$', lines[i].rstrip("\r"))
            if m:
                out.setdefault(lang, []).append((m.group(1), i + 1))
    return out


def coverage_finding(i18n_path):
    wrapped = wrapped_value_keys(i18n_path)
    en_missing = [k for k, _ in wrapped.get("en", [])]
    zh_missing = [k for k, _ in wrapped.get("zhCN", [])]
    n = len(set(en_missing) | set(zh_missing))
    return ("DICTIONARY_COVERAGE_REPORT",
            "%d key row(s) written with the value on the next line, invisible to the four "
            "dictionary claims (en %d, zhCN %d)" % (n, len(en_missing), len(zh_missing)),
            True,
            "not gated on purpose: a green REGISTER_PARITY below is not a claim about these keys. "
            "First five: " + ", ".join("%s@%d" % (k, ln) for k, ln in
                                       (wrapped.get("en", []) + wrapped.get("zhCN", []))[:5]))


def coverage_mutant(i18n_path):
    """Prove the coverage arm counts a wrapped row that REGISTER_PARITY cannot see.

    The injected pair is a live register clash (en `Couldn't …` against a Chinese
    ××失败) written in the wrapped style. If REGISTER_PARITY stayed green while
    DICTIONARY_COVERAGE_REPORT did not move, the coverage arm would be decoration.
    """
    text = Path(i18n_path).read_text(encoding="utf-8")
    en_anchor = '  "agent.sendError": "Copilot could not reach CityNexus.",\n'
    zh_anchor = '  "agent.sendError": "Copilot 暂时没能连上 CityNexus。",\n'
    mutated = text.replace(en_anchor, en_anchor + '  "zz.coverageProbe":\n    "Couldn\'t probe this.",\n')
    mutated = mutated.replace(zh_anchor, zh_anchor + '  "zz.coverageProbe": "探测失败。",\n')
    if mutated == text or "zz.coverageProbe" not in mutated:
        return ("K5_wrapped_row_counted", "injection did not land -- nothing was handed to the arm", False)
    probe_path = None
    counted = parity_blind = False
    wrapped_before = wrapped_after = -1
    try:
        with tempfile.NamedTemporaryFile("w", suffix=".tsx", delete=False, encoding="utf-8", newline="\n") as fh:
            fh.write(mutated)
            probe_path = fh.name
        after = dicts(probe_path)
        clash = "zz.coverageProbe" in (set(after["en"]) & set(after["zhCN"]))
        wrapped_before = sum(len(v) for v in wrapped_value_keys(i18n_path).values())
        wrapped_after = sum(len(v) for v in wrapped_value_keys(probe_path).values())
        counted = wrapped_after == wrapped_before + 1
        parity_blind = not clash
    finally:
        if probe_path:
            Path(probe_path).unlink(missing_ok=True)
    if counted and parity_blind:
        return ("K5_wrapped_row_counted",
                "the clash was written where REGISTER_PARITY cannot reach it, and the coverage arm "
                "counted it (%d -> %d wrapped rows)" % (wrapped_before, wrapped_after), True)
    return ("K5_wrapped_row_counted",
            "counted=%s parity_blind=%s (before=%d after=%d)" % (counted, parity_blind, wrapped_before, wrapped_after), False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--i18n", required=True)
    ap.add_argument("--baseline")
    ap.add_argument("--e2e")
    ap.add_argument("--src", help="frontend/src, for the COMPONENT_FALLBACK face")
    ap.add_argument("--list-fallbacks", action="store_true",
                    help="print every COMPONENT_FALLBACK hit as path:line, not just three")
    ap.add_argument("--mutant", action="store_true")
    a = ap.parse_args()

    rc = 0
    print(f"== cnx_copy_tiers_r1  i18n={a.i18n}  baseline={a.baseline or 'self'}  "
          f"e2e={a.e2e or 'none'}  src={a.src or 'none'}")
    for name, measure, ok, detail in audit(a.i18n, a.baseline, a.e2e, a.src):
        state = "MET" if ok else "VIOLATION"
        if name.endswith("_NOT_RUN"):
            state = "NOT_RUN"
        print(f"  [{state:9s}] {name:24s} {measure}")
        print(f"          detail: {detail}")
        rc |= 0 if ok else 1
    if a.src and a.list_fallbacks:
        hits, _pairs, _files = scan_tree(a.src)
        for tier in ("A", "B"):
            rows = [h for h in hits if h[0] == tier]
            print(f"  -- tier {tier}: {len(rows)} hit(s) --")
            for t, f, ln, lit, why, shape in sorted(rows, key=lambda r: (r[1], r[2])):
                print(f"     {t} [{shape:16s}] {f}:{ln} {lit!r}  <- {why}")
    if a.mutant:
        if not (a.baseline and a.e2e):
            print("  --mutant needs --baseline and --e2e; skipping instead of reporting a clean self-test")
            return rc or 1
        print("  -- ruler self-test: each injected defect must be caught --")
        for label, detail, ok in mutants(Path(a.i18n).read_text(encoding="utf-8"),
                                         Path(a.i18n).parent, a.baseline, a.e2e):
            print(f"  [{'MET' if ok else 'VIOLATION'}] {label:24s} {detail}")
            rc |= 0 if ok else 1
        print("  -- COMPONENT_FALLBACK self-test: injected copy must be caught, machine tokens must stay quiet --")
        for label, detail, ok in fallback_mutants():
            print(f"  [{'MET' if ok else 'VIOLATION'}] {label:24s} {detail}")
            rc |= 0 if ok else 1
        print("  -- e2e corpus gate self-test: a non-directory must be refused, a real one must pass --")
        for label, detail, ok in corpus_guard_mutants(a.i18n, a.baseline, a.e2e):
            print(f"  [{'MET' if ok else 'VIOLATION'}] {label:24s} {detail}")
            rc |= 0 if ok else 1
        print("  -- dictionary coverage self-test --")
        label, detail, ok = coverage_mutant(a.i18n)
        print(f"  [{'MET' if ok else 'VIOLATION'}] {label:24s} {detail}")
        rc |= 0 if ok else 1
    print(f"exit={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
