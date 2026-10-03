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
  HARDCODED_FALLBACK  (ORD-0370, needs --src; dispatched under this name, an
                   earlier cut of this file called it COMPONENT_FALLBACK) the
                   three claims above read only LocaleContext, so a component
                   that invents its own sentence in a `??` slot walks past every
                   one of them. This face reads the components: tier A is a
                   language branch sitting in that slot (`?? (zh ? "…" : "…")`),
                   tier B is a bare literal there, which a Chinese device is
                   shown as English. Shape only: this face never claims the
                   bytes reached a screen.
  RENDERED         (ORD-0370, needs --src) a key can match register, grow nothing,
                   be quoted by no assertion and still never reach a traveller,
                   because no component ever asks for it. Measured, not assumed:
                   every key is looked up as a quoted string across the
                   non-dictionary sources, and the denominator -- how many files
                   that scan actually read -- travels with the count, as does the
                   number of dictionary files skipped, so a copy of the
                   dictionary elsewhere cannot quietly double every site.
                   THE GATE IS ASYMMETRIC ON PURPOSE. A stock row nothing reads
                   is an unharmless-bytes-only problem: it is dead copy, not a
                   runtime defect, so it is listed and never gated -- gating it
                   would hold this batch hostage to ORD-0323's decision to route
                   the inbox failures through copyFor(). A key *this run*
                   introduced or reworded that nothing asks for is churn: the
                   ruler could not previously tell polish-progress from
                   polish-nothing, and now it can.
                   Keys under a concatenated prefix (`t("nav." + item.key)`) are
                   covered dynamically and are excluded from the zero-use claim;
                   without that rule one prefix would report 28 false deaths.
  CORPUS_GATE      (ORD-0370) a named --e2e path that is not a directory used
                   to read 0 assertions and still print MET. Refusing that is
                   the only way the first four claims can be trusted from a
                   transcript; it can make ASSERTIONS_STILL_HIT redder, never
                   quieter.

  RENDER_TIERS   (ORD-0370b, needs --src) splits the hits above by where the value
                   actually goes, and gates on one thing only: no tier-1 hit may
                   remain. The vocabulary, and what each slot is licensed to claim:
                     JSX_CHILD      element text. The enclosing `{` opens straight
                                    after a `>`. PROVEN render slot.
                     ATTR_VISIBLE   `title=` / `placeholder=` / `alt=` / `label=`.
                                    The browser paints it. PROVEN render slot.
                     ATTR_ANNOUNCED `aria-*=`. Reaches a screen reader, not the eye:
                                    undetermined for this order's purpose.
                     DATA_ATTR      `data-*=`. UNDETERMINED, deliberately never
                                    excluded: a stylesheet can print it with
                                    attr(), a reviewer reads it in devtools, and a
                                    text ruler that called it dead would be
                                    asserting something it has not measured.
                     REACT_KEY      `key={`. The one slot this face may state cannot
                                    render: React consumes key to reconcile and
                                    never emits it into the DOM.
                     STATE_WRITE / TELEMETRY_STRING / JS_VALUE / OTHER / ATTR_OTHER
                                    undetermined -- reaching a screen depends on who
                                    reads the field, which text cannot settle.
                   A tier-1 hit additionally requires that no language branch guards
                   it: `{zh ? (x ?? "甲") : (x ?? "乙")}` sits in element text but a
                   Chinese screen takes the Chinese arm, so it is tier 2. A nested
                   template interpolation is also tier 2: collecting it means
                   rewriting the sentence around it, which is a different order.
                   Tiers 2 and 3 can never turn this cell green-by-laundering: the
                   gate reads tier 1 alone, and the counts of all three are printed.

A face that did not run prints NOT_RUN, never MET: an absent --src or --e2e is
not evidence of anything.

--mutant injects one defect per gated claim; each must be caught or the ruler
itself is the defect. Several arms are the other kind: they require the ruler
to stay quiet, because a ruler that flags everything passes as one that works.
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
# HARDCODED_FALLBACK face (ORD-0370)
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


LANG_ARM = re.compile(r"\b(?:zh|isZh|isChinese|zhCN|locale|language|lang)\b[^{};]{0,60}\?", re.I)
ATTR_NAME = re.compile(r'([A-Za-z_][\w-]*)\s*=\s*\{?\s*$')


def render_pos(text, abs_off):
    """Where the value of this expression actually goes, as far as text can show.

    Returns (slot, in_lang_arm). The slot vocabulary and what each one licenses is
    in this file's docstring; the short version of the rule that matters:

      JSX_CHILD      the enclosing `{` opens right after a `>` -> the value is
                     element text. A render slot.
      ATTR_VISIBLE   `title=` / `placeholder=` / `alt=` -> shown by the browser.
      ATTR_ANNOUNCED `aria-*=` -> reaches an assistive reader, not the eye.
      DATA_ATTR      `data-*=` -> NOT licensed as "cannot render". A stylesheet
                     can print it with attr(), and a reviewer can. It is
                     undetermined, never excluded.
      REACT_KEY      `key={` -> the only slot this face may assert cannot render:
                     React consumes key to reconcile and never emits it to the DOM.
      everything else: undetermined (state writes, telemetry strings, object
                     fields, and anything the text does not settle).
    """
    head = text[:abs_off]
    line_start = head.rfind("\n") + 1
    line_head = text[line_start:abs_off]
    in_lang = bool(LANG_ARM.search(line_head)) or bool(
        LANG_ARM.search(text[max(0, abs_off - 700):abs_off][-700:]))
    # innermost unmatched `{` before the hit
    depth = 0
    open_at = -1
    for i in range(len(head) - 1, -1, -1):
        ch = head[i]
        if ch == "}":
            depth += 1
        elif ch == "{":
            if depth == 0:
                open_at = i
                break
            depth -= 1
    if open_at >= 0:
        before = head[:open_at].rstrip()
        m = ATTR_NAME.search(head[:open_at].rstrip() + " ")
        attr = m.group(1).lower() if m else ""
        last = before[-1] if before else ""
        # `>` closes a JSX open tag, so a `{` right after it is element text -- but
        # `=>` also ends in `>`, and that one opens a function body, not a screen.
        arrow = before.endswith("=>")
        if last == ">" and not arrow:
            return ("JSX_CHILD", in_lang)
        # `{` preceded by plain text is also element text: `<small>→ {x ?? "…"}</small>`.
        # The guard is that nothing code-like sits between the nearest `>` and this
        # `{`, and `$` is excluded on purpose (`${` opens a template interpolation,
        # which is a string being assembled, not a place a value is painted).
        # Without the `>`-to-`{` gap rule this branch claimed an `if (...) {` block
        # was element text -- measured on frontend/src/features/recovery/
        # RecoveryRequiredPanel.tsx, where the enclosing brace is a control block.
        gt = before.rfind(">")
        gap = before[gt + 1:] if gt >= 0 else ""
        if (last and last not in "=(,)[]:;{}<>+-*/%&|^!~?\"$%" and not attr
                and gt >= 0 and not re.search(r"[(){};=,?]|=>", gap)):
            return ("JSX_CHILD", in_lang)
        if attr.startswith("data-"):
            return ("DATA_ATTR", in_lang)
        if attr.startswith("aria-"):
            return ("ATTR_ANNOUNCED", in_lang)
        if attr in ("title", "placeholder", "alt", "label"):
            return ("ATTR_VISIBLE", in_lang)
        if attr == "key":
            return ("REACT_KEY", in_lang)
        if attr:
            return ("ATTR_OTHER", in_lang)
    low = line_head
    if re.search(r"\bkey\s*=\s*\{", low):
        return ("REACT_KEY", in_lang)
    if re.search(r"\bdata-[A-Za-z-]+\s*=\s*\{", low):
        return ("DATA_ATTR", in_lang)
    if re.search(r"\baria-[A-Za-z-]+\s*=\s*\{", low):
        return ("ATTR_ANNOUNCED", in_lang)
    if re.search(r"\b(aria-[A-Za-z-]+|title|placeholder|alt|label)\s*=\s*\{", low):
        return ("ATTR_VISIBLE", in_lang)
    if re.search(r"\bset[A-Z]\w*\s*\(\s*", low):
        return ("STATE_WRITE", in_lang)
    if "`" in low and re.search(r"\w+\s*=\s*\$\{", low):
        return ("TELEMETRY_STRING", in_lang)
    if re.search(r"\w+\s*:\s*[^=]*$", low) and not re.search(r"[<>{}]", low[-40:]):
        return ("JS_VALUE", in_lang)
    return ("OTHER", in_lang)


TIER1_SLOTS = {"JSX_CHILD", "ATTR_VISIBLE"}
CANNOT_RENDER = {"REACT_KEY"}
# A literal only has something to localise if it carries a letter. `—` sitting in
# element text is a render slot and no language branch guards it, but no dictionary
# key can make an em dash read better in Chinese, and calling it tier 1 would keep
# this cell red forever and teach people to mute it. A dotted identifier
# (`agent.intentUnknown`) or a bare key prefix (`nav.`) is a name handed to t(),
# not copy, so it is not tier 1 either.
LETTER = re.compile(r"[A-Za-z一-鿿]")
KEYISH = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*(\.[A-Za-z0-9_-]+)*\.?$")
KEYISH_DOTTED = re.compile(r"^[a-z][A-Za-z0-9_-]*(\.[A-Za-z0-9_-]+)+\.?$|^[a-z]+\.$")


def localisable(lit):
    """Does this literal carry anything a language could change?"""
    if not LETTER.search(lit):
        return False, "no letter: locale-neutral symbol"
    if KEYISH_DOTTED.match(lit.strip()):
        return False, "dotted identifier / key prefix, not copy"
    return True, "carries language"


def render_tier(slot, in_lang, lit=""):
    """1 = the value lands in a render slot, no language branch guards it, and the
    text carries a language to mistranslate. A Chinese screen is being handed this.
    3 = text proves it cannot reach a screen. 2 = everything this face cannot settle.
    """
    if slot in CANNOT_RENDER:
        return 3
    ok_localisable, _why = localisable(lit)
    if slot in TIER1_SLOTS and not in_lang and ok_localisable:
        return 1
    return 2


def slot_shape(line, upto):
    """What construct the `??` sits in, read from the text before it on the line.

    Kept for the older reporting; `render_pos` is the version that reasons about
    braces and a wider context, and the tiers come from it.
    """
    head = line[:upto]
    p, _lang = render_pos(head, len(head))
    return {"JSX_CHILD": "jsx-or-expr", "DATA_ATTR": "data-attr",
            "ATTR_ANNOUNCED": "a11y-or-tooltip", "ATTR_VISIBLE": "a11y-or-tooltip",
            "REACT_KEY": "react-key", "ATTR_OTHER": "other",
            "STATE_WRITE": "state-write", "TELEMETRY_STRING": "telemetry-string",
            "JS_VALUE": "js-value", "OTHER": "other"}[p]



def fallback_hits(text, name):
    """[(tier, file, line, literal, why, slot, render tier)] for one file's text.

    A `??` that ends a line and a fallback that opens the next line are one
    expression, not two, so the pair is read as a joined window; the hit is
    still attributed to the line carrying the literal. The render tier is
    computed from an absolute offset into the file, because deciding whether a
    value lands in element text needs the braces around it, not the line.
    """
    lines = text.split("\n")
    starts = []
    off = 0
    for ln in lines:
        starts.append(off)
        off += len(ln) + 1
    hits = []
    seen = set()
    for i, line in enumerate(lines):
        if line.strip().startswith(("//", "*")):
            continue
        prev = lines[i - 1].rstrip() if i > 0 else ""
        windows = [(line, i + 1, starts[i])]
        if prev.endswith("??") and i > 0:
            windows.append((prev + " " + line, i + 1, starts[i - 1]))
        for window, at, base in windows:
            for rx, tier in ((A_RE, "A"), (B_RE, "B")):
                for m in rx.finditer(window):
                    # map the match back to an absolute offset in the file
                    if window is line or len(window) == len(line):
                        abs_off = starts[i] + m.start()
                    else:
                        abs_off = (starts[i - 1] + m.start() if m.start() <= len(prev)
                                   else starts[i] + m.start() - len(prev) - 1)
                    slot, in_lang = render_pos(text, abs_off)
                    shape = slot_shape(window, m.start())
                    if tier == "A":
                        cond = m.group(1) or ""
                        lits = (_pick(m.groups(), 2, 3), _pick(m.groups(), 4, 5))
                        if not LOCALE_TEST.search(cond):
                            for lit in lits:
                                if lit is not None:
                                    _tally(hits, seen, "A", name, at, lit,
                                           (False, "not a language branch: condition %r names no locale" % cond.strip()[:40]),
                                           shape, slot, in_lang)
                            continue
                        for lit in lits:
                            if lit is None:
                                continue
                            _tally(hits, seen, "A", name, at, lit, _is_copy(lit), shape, slot, in_lang)
                    else:
                        lit = _pick(m.groups(), 1, 2)
                        if lit is None:
                            continue
                        _tally(hits, seen, "B", name, at, lit, _is_copy(lit), shape, slot, in_lang)
    return hits


def _tally(hits, seen, tier, name, at, lit, verdict, shape="other", slot="OTHER", in_lang=False):
    key = (name, at, lit)
    if key in seen:
        return
    seen.add(key)
    found, why = verdict
    hits.append((tier if found else tier + "-skipped", name, at, lit,
                 "language branch in a ?? slot" if tier == "A" and found else
                 ("bare literal in a ?? slot" if tier == "B" and found else why),
                 shape, render_tier(slot, in_lang, lit), slot))


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
    detail = " || ".join("%s %s:%d %r" % (t, f, ln, lit) for t, f, ln, lit, _, _s, _r, _sl in bad[:3]) \
        or "no hardcoded fallback copy left in a ?? slot"
    # The breakdown counts every hit, so no bucket can hide stock from the claim.
    shapes = Counter(h[5] for h in bad)
    shape_txt = ", ".join("%s=%d" % (k, v) for k, v in sorted(shapes.items(), key=lambda kv: -kv[1]))
    measure = ("%d files scanned: tier A (language branch in the slot) %d, tier B (bare literal) %d, "
               "excluded as machine tokens %d; inline bilingual pairs anywhere = %d "
               "(denominator only -- most are legitimate inline pairs, NOT a defect count)"
               % (files, len(tier_a), len(tier_b), len(skipped), pairs))
    return ("HARDCODED_FALLBACK",
            measure,
            not bad,
            "shape of the %d hit(s) by slot: %s. This breakdown removes nothing -- it is a triage "
            "hint, and 'data-attr' here means the ?? sits inside a data-* attribute on this line, "
            "which a text ruler cannot prove never renders. Detail: " % (len(bad), shape_txt) + detail)


def render_tiers_finding(src_dir):
    """RENDER_TIERS: of the hits, how many can be proven to reach a screen.

    Gated on one thing only: no tier-1 hit may remain uncollected. Tiers 2 and 3
    never move this cell, because "undetermined" is not "harmless" and the face
    must not be allowed to launder a hit into tier 2 to go green.
    """
    hits, _pairs, files = scan_tree(src_dir)
    live = [h for h in hits if h[0] in ("A", "B")]
    by = {1: [], 2: [], 3: []}
    for h in live:
        by[h[6]].append(h)
    t1 = by[1]
    return ("RENDER_TIERS",
            "%d hits over %d files by render tier: tier 1 (proven render slot, no language branch "
            "guarding it) %d, tier 2 (this face cannot settle it) %d, tier 3 (text proves it cannot "
            "reach a screen -- key={}) %d"
            % (len(live), files, len(by[1]), len(by[2]), len(by[3])),
            not t1,
            "tier 1 is the actionable set and is gated; tier 2 stays listed because calling it "
            "safe would be the lie -- data-* in particular is never asserted unable to render. "
            "Tier 1: %s" % ([("%s:%d %r" % (h[1], h[2], h[3])) for h in t1[:6]] or "empty"))


def render_tier_mutants():
    """Teeth for the tiering: one arm per claim the tiering makes."""
    cases = [
        ("K7a_jsx_child_is_tier1",
         '  return <p className="x">{row.title ?? "not reported"}</p>;\n', 1, "JSX_CHILD"),
        ("K7c_data_attr_is_undetermined",
         '  return <div data-outcome={row.kind ?? "unknown"} />;\n', 2, "DATA_ATTR"),
        ("K7d_react_key_cannot_render",
         '  return <li key={row.id ?? "unknown"}>x</li>;\n', 3, "REACT_KEY"),
        ("K7e_placeholder_is_visible",
         '  return <input placeholder={hint ?? "type here"} />;\n', 1, "ATTR_VISIBLE"),
        # the rule that keeps a bilingual sentence out of tier 1: the value is in
        # element text, but a `zh` guard means a Chinese screen takes the other arm
        ("K7f_jsx_child_behind_lang_guard",
         '  return <p>{zh ? (row.title ?? "未知") : (row.title ?? "unknown")}</p>;\n', 2, "JSX_CHILD"),
        # a nested template interpolation is element text but not a whole copy
        # slot: collecting it means rewriting the sentence around it, so tier 2
        ("K7g_template_interpolation_undetermined",
         '  return <p>{zh ? `标题 ${x ?? "未知"}` : `title ${x ?? "unknown"}`}</p>;\n', 2, "OTHER"),
        # an em dash in element text has no language to mistranslate; treating it as
        # actionable would keep the cell red forever and invite people to mute it
        ("K7h_symbol_in_jsx_child_not_actionable",
         '  return <p>{row.value ?? "—"}</p>;\n', 2, "JSX_CHILD"),
        # a dotted name is an argument to t(), not copy
        ("K7i_dotted_key_not_copy",
         '  return <p>{label ?? "agent.intentUnknown"}</p>;\n', 2, "JSX_CHILD"),
        # the shape that bit this ruler once: a control block's `{` is not element
        # text, and a state setter's argument only reaches a screen if some JSX
        # later reads that state -- which text cannot settle
        ("K7j_control_block_is_not_jsx_child",
         '  async function go(): Promise<void> {\n'
         '    if (!r.ok) {\n'
         '      setMessage(\n        body?.detail ??\n'
         '          "No alternative plan could be generated.",\n      );\n    }\n  }\n',
         2, "OTHER"),
    ]
    out = []
    for label, source, want_tier, want_slot in cases:
        hits = [h for h in fallback_hits(source, label) if not h[0].endswith("-skipped")]
        if not hits:
            out.append((label, "no hit at all from %r" % source.strip()[:60], False))
            continue
        got = hits[0][6]
        slot = hits[0][7]
        if got != want_tier or slot != want_slot:
            out.append((label, "tier=%d slot=%s, wanted tier=%d slot=%s" % (got, slot, want_tier, want_slot), False))
        else:
            out.append((label, "tier %d via %s as expected" % (got, slot), True))
    return out


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
    findings.extend(shape_findings(after_path, src_dir))
    if src_dir:
        findings.append(component_fallback(src_dir))
        findings.append(render_tiers_finding(src_dir))
        findings.append(rendered_finding(after_path, base_path, src_dir))
    else:
        findings.append(("HARDCODED_FALLBACK_NOT_RUN",
                         "no component was read (pass --src frontend/src to enable this face)",
                         True, "NOT_RUN is not a pass: hardcoded fallback copy was never measured"))
        findings.append(("RENDERED_NOT_RUN",
                         "no component was read (pass --src frontend/src to enable this face)",
                         True, "NOT_RUN is not a pass: whether any component asks for these keys "
                         "was never measured, so no key here has a proven use site"))
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


def rendered_uses(src_dir, dict_names):
    """{key: [sites]} for every quoted reference outside the dictionary.

    Dictionary is `frontend/src/i18n/LocaleContext.tsx`, excluded by name
    because every key appears there once per language block. A copy of the
    dictionary anywhere else would inflate every count, so the number of files
    skipped is returned alongside and a reader can see it.
    """
    uses = {k: [] for k in dict_names}
    scanned = 0
    skipped = 0
    for p in sorted(Path(src_dir).rglob("*")):
        if p.suffix not in {".ts", ".tsx"} or "node_modules" in p.parts:
            continue
        if p.name == "LocaleContext.tsx":
            skipped += 1
            continue
        scanned += 1
        rel = str(p)
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            for q in ('"', "'"):
                for m in re.finditer(re.escape(q) + r"([A-Za-z0-9._-]+)" + re.escape(q), line):
                    k = m.group(1)
                    if k in uses:
                        uses[k].append("%s:%d" % (rel, n))
    return uses, scanned, skipped


DYN_RE = re.compile(r'"([A-Za-z0-9_-]+\.)"\s*\+')


def dynamic_prefixes(src_dir):
    """{prefix: [sites]} for keys built by concatenation, e.g. `t("nav." + item.key)`.

    Without this, every key under a concatenated prefix reads as zero-use and
    the face cries wolf: in this tree one prefix covers 28 dictionary keys that
    are in fact asked for at runtime.
    """
    out = {}
    for p in sorted(Path(src_dir).rglob("*")):
        if p.suffix not in {".ts", ".tsx"} or "node_modules" in p.parts or p.name == "LocaleContext.tsx":
            continue
        for n, line in enumerate(p.read_text(encoding="utf-8", errors="replace").split("\n"), 1):
            for m in DYN_RE.finditer(line):
                # the group already carries the trailing dot; appending one made
                # every prefix match fail and turned 28 live keys into false deaths
                out.setdefault(m.group(1), []).append("%s:%d" % (p, n))
    return out


def rendered_data(after_path, base_path, src_dir):
    """Everything the RENDERED cell reports, computed once so the face and the
    per-key listing can never disagree about a count."""
    aft = dicts(after_path)
    bas = dicts(base_path) if base_path else aft
    parsed = set(aft["en"]) | set(aft["zhCN"])
    names = sorted(parsed)
    wrapped = wrapped_value_keys(after_path)
    wrapped_names = sorted({k for lang in ("en", "zhCN") for k, _ in wrapped.get(lang, [])})
    names = sorted(set(names) | set(wrapped_names))
    uses, scanned, skipped = rendered_uses(src_dir, names)
    dyn = dynamic_prefixes(src_dir)

    def is_dynamic(k):
        return any(k.startswith(p) for p in dyn)

    zero = [k for k in names if not uses.get(k)]
    # The baseline's key set has to be assembled the same way as this run's, or a
    # row that merely wraps its value onto the next line looks brand-new. Caught
    # by control arm K6b, which was green-by-design and went red: `push.`
    # capDependencyMissingHelp is wrapped in both blocks at the baseline and was
    # being counted as introduced, inflating the touched-key count by one.
    base_keys = set()
    for lang in ("en", "zhCN"):
        base_keys |= set(bas.get(lang, {}))
        if base_path:
            base_keys |= {k for k, _ in wrapped_value_keys(base_path).get(lang, [])}
    added = [k for k in names if k not in base_keys]
    changed = sorted({k for k, _ in diff_keys(bas, aft)})
    introduced = sorted(set(added) | set(changed))
    return dict(names=names, parsed=len(parsed), wrapped=wrapped_names,
                only_wrapped=[k for k in wrapped_names if k not in parsed],
                uses=uses,
                scanned=scanned, skipped=skipped, dyn=dyn, is_dynamic=is_dynamic,
                zero=zero, zero_static=[k for k in zero if not is_dynamic(k)],
                zero_dynamic=[k for k in zero if is_dynamic(k)],
                added=added, changed=changed, introduced=introduced)


def rendered_finding(after_path, base_path, src_dir):
    """The RENDERED cell: does any component ever ask for this key?

    Gated for keys this run introduced or reworded; reported-only for stock.
    """
    d = rendered_data(after_path, base_path, src_dir)
    churn = [k for k in d["introduced"] if k in d["zero_static"]]
    sites_txt = "; ".join("%s=%d %s" % (k, len(d["uses"][k]), d["uses"][k][0])
                          for k in d["introduced"] if d["uses"][k])
    stock = d["zero_static"]
    return ("RENDERED",
            "%d distinct key names (%d readable by the single-line parser; %d rows carry their value "
            "on the next line and %d of those keys are reachable only through the wrapped scan) "
            "against %d non-dictionary files (%d dictionary files skipped); zero-use %d, of which %d "
            "sit under a concatenated prefix %s and are covered dynamically; keys introduced or "
            "reworded by this run: %d, gated offenders: %d"
            % (len(d["names"]), d["parsed"], len(d["wrapped"]), len(d["only_wrapped"]),
               d["scanned"], d["skipped"],
               len(d["zero"]), len(d["zero_dynamic"]), sorted(d["dyn"]) or "none",
               len(d["introduced"]), len(churn)),
            not churn,
            "stock zero-use rows are harmless bytes, not a runtime defect, so they are listed and "
            "not gated; a key THIS run touched that nothing asks for is churn, so it is gated. "
            "Gated: %s. Stock, not gated (first 8 of %d): %s. Use sites of touched keys: %s"
            % (churn or "none", len(stock), stock[:8] or "none", sites_txt or "none"))


def rendered_mutants(after_path, base_path, src_dir):
    """Three arms: unread new key caught, read new key quiet, stock zeros never gated."""
    out = []
    text = Path(after_path).read_text(encoding="utf-8")
    en_anchor = '  "agent.sendError": "Copilot could not reach CityNexus.",\n'
    zh_anchor = '  "agent.sendError": "Copilot 暂时没能连上 CityNexus。",\n'
    if en_anchor not in text or zh_anchor not in text:
        return [("K6_rendered_arms", "anchors absent from %s -- nothing was injected" % after_path, False)]
    with tempfile.TemporaryDirectory() as td:
        dict_path = Path(td) / "LocaleContext.tsx"
        dict_path.write_text(
            text.replace(en_anchor, en_anchor + '  "zz.renderProbe": "Probe sentence.",\n')
                .replace(zh_anchor, zh_anchor + '  "zz.renderProbe": "探针句。",\n'),
            encoding="utf-8", newline="\n")
        probe_keys = "zz.renderProbe"
        # A: introduced this run, asked for by nobody
        src_a = Path(td) / "a"
        src_a.mkdir()
        (src_a / "LocaleContext.tsx").write_text("export const x = 1;\n", encoding="utf-8", newline="\n")
        (src_a / "Widget.tsx").write_text('  return <p>{t("agent.sendError")}</p>;\n',
                                          encoding="utf-8", newline="\n")
        fa = rendered_finding(str(dict_path), after_path, str(src_a))
        out.append(("K6a_new_key_unread",
                    "verdict %s on %s" % ("MET" if fa[2] else "VIOLATION", probe_keys), not fa[2]))
        # B: same key, one component asks for it -> must stay quiet
        (src_a / "Widget.tsx").write_text('  return <p>{t("zz.renderProbe")}</p>;\n',
                                          encoding="utf-8", newline="\n")
        fb = rendered_finding(str(dict_path), after_path, str(src_a))
        out.append(("K6b_new_key_read_quiet",
                    "verdict %s with one use site" % ("MET" if fb[2] else "VIOLATION"), fb[2]))
    # C: stock zeros must be listed, never gated -- the real tree at the real baseline
    fc = rendered_finding(base_path or after_path, base_path or after_path, src_dir)
    listed = "Stock (not gated): none" not in fc[3]
    out.append(("K6c_stock_zeros_not_gated",
                "verdict %s while listing stock zeros: %s" % ("MET" if fc[2] else "VIOLATION",
                                                              "yes" if listed else "no"),
                fc[2] and listed))
    return out


# --------------------------------------------------------------------------
# COPY HONESTY LADDER (ORD-0381) -- six tiers taken from the Pi Travel string
# corpus (D:/moodle/_apk_analysis_pi_travel/PI_TRAVEL_APK_ANALYSIS.md section 4).
# The source's own numbering is ①..⑥ where ① is the bilingual-register tier;
# the dispatch renumbers its list 1..3 = source ②③ and keeps ④⑤⑥ in place, so
# every tier below is named by the SOURCE numeral and the dispatch number is
# mapped in the printed header.
#
# Every vocabulary is printed by --ladder. A count without its matcher is not a
# measurement, it is an opinion, and the point of this file is that the copy
# claims become checkable.
# --------------------------------------------------------------------------
VALUE_ROW = re.compile(r'^\s*"([A-Za-z0-9._-]+)"\s*:\s*(?:"((?:[^"\\]|\\.)*)"\s*,?\s*)?$')


def dicts_full(path):
    """{lang: {key: (value, line)}} reading BOTH dictionary row shapes.

    `dicts()` sees only rows whose value sits on the key's line, and this file
    already reports 12 rows that wrap their value onto the next. A ladder count
    computed over the single-line subset would be a ratio over a denominator the
    file does not have, so this parser is the one the ladder uses.
    """
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    marks = [i for i, ln in enumerate(lines) if re.match(r"^const (en|zhCN): Dict", ln)]
    if len(marks) < 2:
        raise SystemExit("FATAL expected `en` and `zhCN` Dict blocks in %s" % path)
    out = {}
    for idx, start in enumerate(marks):
        lang = re.match(r"^const (\w+):", lines[start]).group(1)
        stop = marks[idx + 1] if idx + 1 < len(marks) else len(lines)
        table = {}
        for i in range(start, stop):
            m = VALUE_ROW.match(lines[i].rstrip("\r"))
            if not m:
                continue
            key, val = m.group(1), m.group(2)
            if val is None:
                # wrapped: the value is on the next non-comment line
                j = i + 1
                while j < stop and lines[j].strip().startswith(("/*", "*", "//")):
                    j += 1
                vm = re.match(r'^\s*"((?:[^"\\]|\\.)*)"\s*,?\s*$', lines[j].rstrip("\r")) if j < stop else None
                val = vm.group(1) if vm else ""
            table.setdefault(key, (val, i + 1))
        out[lang] = table
    return out


LADDER = {
    # tier: (subject detector over the merged text, satisfaction detector, what
    # satisfaction means in one line)
    "①register": (
        re.compile(r"失败|无法|没能|未能|couldn'?t|can'?t|unable|could not", re.I),
        re.compile(r"没能|未能|请再试|稍后再试|couldn'?t|can'?t|unable|could not", re.I),
        "failure copy speaks the agreed register in BOTH languages (ORD-0367's rule)"),
    "②provenance": (
        re.compile(r"\bAI\b|智能|生成|Copilot|assistant|generated", re.I),
        re.compile(r"由 ?AI|AI ?生成|Generated|仅供参考|for reference|Sources|参考来源|来源", re.I),
        "AI-produced copy names its origin, and a mixed origin is admitted"),
    "③destructive": (
        re.compile(r"删除|移除|取消|替换|覆盖|撤销|delete|remove|cancel|replace|discard|overwrite", re.I),
        re.compile(r"整个|全部|全局|your entire|all of|移入|待规划|保留|可恢复|回收|不会|仍|never|retained|remain|undo|recovered|最多|上限", re.I),
        "the consequence names its scope, a destination, or a retention limit"),
    "④empty-action": (
        re.compile(r"^\s*(暂无|没有|尚未|空空|这里没|现在没)|^\s*(No |Nothing|None|empty|There is no)", re.I),
        re.compile(r"试试|来|添加|创建|选择|打开|重试|查看|开始|填写|点|告诉|\b(add|create|pick|choose|open|try|start|select|switch|tell|browse|enter|record)\b", re.I),
        "an empty state offers the next action, not just the absence"),
    "⑤metric-shape": (
        re.compile(r"\{n\}|个|处|条|段|次"),
        re.compile(r"·.*·|\b\d+ .+ .+ \d+", re.I),
        "counters show the shape that will be filled, e.g. 0 · 0 · 0"),
    "⑥estimate": (
        re.compile(r"Δ|cost|费用|时长|风险|risk|分钟|min\b|预估|参考价|est\b", re.I),
        re.compile(r"Est\.|预估|约|大约|approx|reference price|参考价|not .*run|没有.*跑|未跑", re.I),
        "a value that was estimated says so with a prefix; nothing uncomputed is promised"),
}
ACTION_SIBLING = re.compile(r"(Action|Cta|Hint|Empty|Add|Create|Retry)$")


def action_sibling(key, keys):
    """An empty state counts as honest if this same namespace also carries the
    action as its own label -- the shape CityNexus already uses (a status line
    plus a button). The sibling must share the key's own subject word, so a
    random `...Create` elsewhere in the namespace cannot silence a miss."""
    stem = key.split(".", 1)[1].lower() if "." in key else key.lower()
    for o in keys:
        if o == key or "." not in o or not o.startswith(key.split(".")[0] + "."):
            continue
        if not ACTION_SIBLING.search(o):
            continue
        os = o.split(".", 1)[1].lower()
        if os.startswith(stem) or stem in os:
            return o
    return None


def ladder_data(i18n_path, src_dir=None):
    """Per-tier population, satisfaction and misses, over both dictionaries."""
    d = dicts_full(i18n_path)
    keys = sorted(set(d["en"]) | set(d["zhCN"]))
    rows = {}
    shapes = shape_cells(i18n_path, src_dir)
    for tier, (subj, sat, meaning) in LADDER.items():
        gate = {"④empty-action": "EMPTY_ACTION", "⑥estimate": "ESTIMATE_PREFIX"}.get(tier)
        if gate:
            # one truth per tier: the printed row and the gated cell share a body
            s = shapes[gate]
            rows[tier] = dict(pop=s["pop"], ok=s["good"], miss=[(k,) for k in s["miss"]],
                              meaning=meaning + (" (read rows only)" if s["filtered"] else ""))
            continue
        ok, miss = [], []
        for k in keys:
            zh = d["zhCN"].get(k, ("", 0))[0]
            en = d["en"].get(k, ("", 0))[0]
            text = "%s %s" % (zh, en)
            if not subj.search(text):
                continue
            (ok if sat.search(text) else miss).append((k, zh, en))
        rows[tier] = dict(pop=len(ok) + len(miss), ok=[x[0] for x in ok], miss=miss, meaning=meaning)
    both = set(d["en"]) & set(d["zhCN"])
    ns = {}
    for k in keys:
        ns.setdefault(k.split(".")[0], 0)
        ns[k.split(".")[0]] += 1
    wrapped = sum(len(v) for v in dicts_all_wrapped_rows(i18n_path).values())
    return dict(d=d, keys=keys, both=len(both), rows=rows, ns=ns, single=dicts(i18n_path),
                wrapped=wrapped)


def dicts_all_wrapped_rows(path):
    """Rows whose value sits on the line after the key -- the single-line parser's
    blind spot, counted so a ladder denominator can be checked against it."""
    lines = Path(path).read_text(encoding="utf-8").split("\n")
    marks = [i for i, ln in enumerate(lines) if re.match(r"^const (en|zhCN): Dict", ln)]
    out = {}
    for idx, start in enumerate(marks):
        lang = re.match(r"^const (\w+):", lines[start]).group(1)
        stop = marks[idx + 1] if idx + 1 < len(marks) else len(lines)
        for i in range(start, stop):
            if re.match(r'^\s*"([A-Za-z0-9._-]+)"\s*:\s*$', lines[i].rstrip("\r")):
                out.setdefault(lang, []).append((re.match(r'^\s*"([A-Za-z0-9._-]+)"', lines[i]).group(1), i + 1))
    return out


def ladder_finding(i18n_path):
    """The measurement cell. Ungated: this reports where the copy stands, and the
    two tiers this order actually fixed are gated separately by EMPTY_ACTION and
    ESTIMATE_PREFIX below."""
    L = ladder_data(i18n_path)
    parts = []
    for tier in LADDER:
        r = L["rows"][tier]
        parts.append("%s %d/%d" % (tier, len(r["ok"]), r["pop"]))
    return ("LADDER_REPORT",
            "%d keys in the denominator (%d in both blocks, %d single-line-parseable, %d rows wrap their "
            "value onto the next line); satisfied/population per tier: %s"
            % (len(L["keys"]), L["both"], sum(len(v) for v in L["single"].values()), L["wrapped"],
               " | ".join(parts)),
            True,
            "not gated on purpose: a population found by a regex is not a promise the tier is met. "
            "The two tiers this order fixes are gated by their own cells. Misses are listed by "
            "--ladder. Namespaces scanned: %d." % len(L["ns"]))


def ladder_mutants():
    """One injected miss per adopted tier must be caught, and one honest line per
    tier must stay quiet."""
    cases = [
        ("K8a_empty_without_action_caught", "暂无行程。", "No trips.", "EMPTY_ACTION", False),
        ("K8b_empty_with_action_quiet", "暂无行程，创建一个看看。", "No trips yet. Add one to see it.", "EMPTY_ACTION", True),
        ("K8c_estimate_unmarked_caught", "影响 Δ 12 分钟", "Impact Δ 12 min", "ESTIMATE_PREFIX", False),
        ("K8d_estimate_marked_quiet", "预估影响 Δ 12 分钟", "Est. impact Δ 12 min", "ESTIMATE_PREFIX", True),
    ]
    out = []
    for label, zh, en, cell, want_pass in cases:
        ok = check_shape(cell, zh, en, {})[0]
        if ok == want_pass:
            out.append((label, "%s verdict as expected" % ("pass" if ok else "fail"), True))
        else:
            out.append((label, "%s verdict, wanted %s -- the shape is not the claim"
                        % ("pass" if ok else "fail", "pass" if want_pass else "fail"), False))
    return out


EMPTY_SUBJECT = re.compile(r"^\s*(暂无|没有|尚未|空空|这里没|现在没)|^\s*(No |Nothing|None\b|empty|There is no)", re.I)
EMPTY_ACTION = re.compile(r"试试|创建|添加|选择|打开|重试|查看|开始|填写|告诉|\b(add|create|pick|choose|open|try|start|select|switch|tell|browse|enter|record)\b", re.I)
# A line is estimate-shaped only when it both carries a value (a digit, a Δ, or a
# `{placeholder}`) AND is about a cost/time/risk figure. Without the second half
# this matcher claimed 「费用」/`Cost`, a bare label, owed an `Est.` prefix.
EST_SUBJECT = re.compile(r"Δ|\{[a-z_]+\}")
EST_ABOUT = re.compile(r"影响|impact|\brisk\b|风险|花费|费用|成本|时长|分钟|\bmin\b|参考价|\bcost\b|walk", re.I)
EST_MARK = re.compile(r"Est\.|预估|^约|约 ?\d|大约|approx|reference|未跑|没有.*跑|will not claim", re.I)


def check_shape(cell, zh, en, ctx=None):
    """The two adopted tiers, as one function so the gate, the listing and the
    counter-control arms cannot drift apart.

    Returns (passes, why). A value outside the tier's subject population passes
    vacuously, which is why every cell prints its population next to its verdict.
    """
    ctx = ctx or {}
    if cell == "EMPTY_ACTION":
        if not (EMPTY_SUBJECT.search(zh) or EMPTY_SUBJECT.search(en)):
            return True, "not an empty state"
        if "?" in zh + en or "？" in zh + en:
            return True, "not an empty state (it is a question)"
        if EMPTY_ACTION.search(zh) or EMPTY_ACTION.search(en):
            return True, "action named in the line"
        if ctx.get("sibling_action"):
            return True, "action lives in a sibling key %s" % ctx["sibling_action"]
        return False, "empty state with no action in the line and no action sibling"
    if cell == "ESTIMATE_PREFIX":
        joined = zh + " " + en
        if not ((EST_SUBJECT.search(zh) or EST_SUBJECT.search(en)) and EST_ABOUT.search(joined)):
            return True, "not an estimate-shaped value"
        if EST_MARK.search(zh) or EST_MARK.search(en):
            return True, "carries an estimate marker"
        return False, "states a computed quantity with no Est/约/预估 marker"
    raise AssertionError("no such shape %s" % cell)


def shape_cells(i18n_path, src_dir=None):
    """Run the two adopted shapes over both dictionaries.

    A tier describes what a traveller reads. A row no component ever asks for is
    not copy anyone can be dishonest AT, and it is already reported -- gated, for
    rows this run touched -- by RENDERED. So when --src is present the population
    is read rows and the unread ones are counted out loud; when --src is absent
    nothing is filtered and the cell says so rather than pretending."""
    d = dicts_full(i18n_path)
    keys = sorted(set(d["en"]) | set(d["zhCN"]))
    read = None
    if src_dir:
        uses, _scanned, _skipped = rendered_uses(src_dir, keys)
        read = {k for k in keys if uses.get(k)}
    out = {}
    for cell in ("EMPTY_ACTION", "ESTIMATE_PREFIX"):
        pop, miss, unread, good = 0, [], [], []
        for k in keys:
            zh = d["zhCN"].get(k, ("", 0))[0]
            en = d["en"].get(k, ("", 0))[0]
            sib = action_sibling(k, keys)
            ok, why = check_shape(cell, zh, en, {"sibling_action": sib})
            if why.startswith("not an empty state") or why == "not an estimate-shaped value":
                continue
            if read is not None and k not in read:
                # this tier's row, but no component reads it: RENDERED owns it
                unread.append(k)
                continue
            pop += 1
            (good if ok else miss).append(
                k if ok else "%s:%d %r / %r (%s)" % (k, d["zhCN"].get(k, ("", 0))[1], zh, en, why))
        out[cell] = dict(pop=pop, miss=miss, unread=unread, good=good, filtered=read is not None)
    return out


def shape_findings(i18n_path, src_dir=None):
    d = shape_cells(i18n_path, src_dir)
    findings = []
    for cell, label in (("EMPTY_ACTION", "LADDER_TIER④_EMPTY_ACTION"),
                        ("ESTIMATE_PREFIX", "LADDER_TIER⑥_ESTIMATE_PREFIX")):
        pop, miss, unread = d[cell]["pop"], d[cell]["miss"], d[cell]["unread"]
        filtered = d[cell]["filtered"]
        measure = ("%d read key(s) in this tier's population, %d miss the shape "
                   "(%d unread row(s) %s)"
                   % (pop, len(miss), len(unread),
                      "counted out, they belong to RENDERED" if filtered
                      else "NOT filtered: no --src"))
        detail = ("population and matcher are printed by --ladder; a miss is listed by key and "
                  "line. First three: %s" % (miss[:3] or "none"))
        findings.append((label, measure, not miss, detail))
    return findings


def print_ladder(i18n_path, src_dir=None):
    L = ladder_data(i18n_path, src_dir)
    print("  -- ORD-0381 copy honesty ladder --")
    print("     denominator: %d distinct keys (%d present in both blocks); %d rows are single-line-"
          "parseable by KEY_RE, %d rows wrap their value onto the next line and are counted here anyway"
          % (len(L["keys"]), L["both"], sum(len(v) for v in L["single"].values()), L["wrapped"]))
    print("     namespaces scanned: %d, largest: %s"
          % (len(L["ns"]), ", ".join("%s=%d" % kv for kv in sorted(L["ns"].items(), key=lambda x: -x[1])[:6])))
    for tier in LADDER:
        subj, sat, meaning = LADDER[tier]
        r = L["rows"][tier]
        print("     %-16s %-5d/%-5d  %s" % (tier, len(r["ok"]), r["pop"], meaning))
        print("                      subject=%s" % subj.pattern)
        print("                      satisfy=%s" % sat.pattern)
        if r["miss"]:
            # ④/⑥ hand back rendered strings, the rest hand back triples
            names = [(m if isinstance(m, str) else m[0]) for m in r["miss"]]
            print("                      misses (first 8 of %d): %s"
                  % (len(r["miss"]), ", ".join(n[:110] for n in names[:8])))
    for cell in ("EMPTY_ACTION", "ESTIMATE_PREFIX"):
        sc = shape_cells(i18n_path, src_dir)[cell]
        pop, miss, unread, filtered = sc["pop"], sc["miss"], sc["unread"], sc["filtered"]
        print("     gated %-16s read-population=%d missing=%d unread-excluded=%d%s"
              % (cell, pop, len(miss), len(unread), "" if filtered else " (no --src: NOT filtered)"))
        for m in miss[:10]:
            print("        ", m[:150])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--i18n", required=True)
    ap.add_argument("--baseline")
    ap.add_argument("--e2e")
    ap.add_argument("--src", help="frontend/src, for the HARDCODED_FALLBACK face")
    ap.add_argument("--ladder", action="store_true", help="print the ORD-0381 six-tier measurement with its matchers")
    ap.add_argument("--list-fallbacks", action="store_true",
                    help="print every HARDCODED_FALLBACK hit as path:line, not just three")
    ap.add_argument("--list-rendered", action="store_true",
                    help="print every key's non-dictionary use count and site, and the zero-use list")
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
            for t, f, ln, lit, why, shape, rtier, slot in sorted(rows, key=lambda r: (r[1], r[2])):
                print(f"     {t} T{rtier} [{slot:17s}] {f}:{ln} {lit!r}  <- {why}")
    if a.ladder:
        print_ladder(a.i18n, a.src)
    if a.src and a.list_rendered:
        d = rendered_data(a.i18n, a.baseline, a.src)
        print("  -- RENDERED per-key listing (denominator = %d non-dictionary files, %d dictionary "
              "files skipped) --" % (d["scanned"], d["skipped"]))
        print("     keys this run introduced or reworded: %d" % len(d["introduced"]))
        for k in d["introduced"]:
            print("       %-34s uses=%-3d %s" % (k, len(d["uses"][k]),
                                                 ", ".join(d["uses"][k][:3]) or "NO USE SITE"))
        print("     zero-use keys not covered by a dynamic prefix: %d" % len(d["zero_static"]))
        for k in d["zero_static"]:
            print("       %s" % k)
        print("     zero-use keys under a concatenated prefix (dynamic, so not a defect): %d"
              % len(d["zero_dynamic"]))
        for pfx, sites in sorted(d["dyn"].items()):
            n = len([k for k in d["zero_dynamic"] if k.startswith(pfx)])
            print("       prefix %-10s covers %-3d key(s), built at %s"
                  % (pfx, n, ", ".join(sites[:4])))
    if a.mutant:
        if not (a.baseline and a.e2e):
            print("  --mutant needs --baseline and --e2e; skipping instead of reporting a clean self-test")
            return rc or 1
        print("  -- ruler self-test: each injected defect must be caught --")
        for label, detail, ok in mutants(Path(a.i18n).read_text(encoding="utf-8"),
                                         Path(a.i18n).parent, a.baseline, a.e2e):
            print(f"  [{'MET' if ok else 'VIOLATION'}] {label:24s} {detail}")
            rc |= 0 if ok else 1
        print("  -- HARDCODED_FALLBACK self-test: injected copy must be caught, machine tokens must stay quiet --")
        for label, detail, ok in fallback_mutants():
            print(f"  [{'MET' if ok else 'VIOLATION'}] {label:24s} {detail}")
            rc |= 0 if ok else 1
        print("  -- ladder shape self-test: an injected miss must be caught, honest copy must stay quiet --")
        for label, detail, ok in ladder_mutants():
            print(f"  [{'MET' if ok else 'VIOLATION'}] {label:26s} {detail}")
            rc |= 0 if ok else 1
        print("  -- render-tier self-test: each tier claim needs its own arm --")
        for label, detail, ok in render_tier_mutants():
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
        if a.src:
            print("  -- RENDERED self-test: an unread new key must be caught, a read one and "
                  "the stock zeros must stay quiet --")
            for label, detail, ok in rendered_mutants(a.i18n, a.baseline, a.src):
                print(f"  [{'MET' if ok else 'VIOLATION'}] {label:24s} {detail}")
                rc |= 0 if ok else 1
        else:
            print("  [VIOLATION] K6_rendered_arms       --mutant without --src cannot test RENDERED; "
                  "refusing to report a self-test that never ran")
            rc |= 1
    print(f"exit={rc}")
    return rc


if __name__ == "__main__":
    sys.exit(main())
