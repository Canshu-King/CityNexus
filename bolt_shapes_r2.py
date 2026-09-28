'''Bolt the three new shapes onto the HARDCODED_FALLBACK face (ORD-0424).

The published face anchors on `??` alone: A_RE is `?? ... ? "x" : "y"` and B_RE is `?? "x"`. The 22
strings pinned in evidence/cmdr-ord0419-20260929-0051/ord0419_inventory_r1.json (blob
353d1c4f96945de517cacf1ef1c8856345d812f8) are, by that file's own counts, 14 JSX_TEXT, 6 TERNARY, 1
TERNARY_TEMPLATE and 1 DEFAULT - none of which passes a `??`. That is why the face reported
`TwinPanel.tsx` zero times at tip 8a7665be while ten of the 22 live in that file.

Three rules of construction, so the old reading keeps its meaning:
  * the `??` face is not touched - its regexes, tier letters and exclusions stay exactly as published,
    so "the hits are still there" is a diff against a file rather than a claim;
  * exclusions are asked per shape and the reason that fired is reported. Element text is read by a
    traveller by definition, so the machine-token veto that belongs in a `??` slot (a `?? "CHANGED"`
    is an enum value handed on) does not veto `<div>CHANGED</div>`;
  * brand words and seed names are excluded against files in the tree being scanned, and the excluded
    string travels with the file, offset and rule that fired. Nothing is silenced by a name only.

The generator assembles its insert from single-quoted pieces: the target file contains both triple
quote forms, and one nested docstring is how the previous draft of this script died.
'''
import ast
import io
import os

TOOLS = r"D:\moodle\_qoder_cmdr_ref_20260921\tools"
SRC = os.path.join(TOOLS, "cnx_copy_tiers_r1.py")
DST = os.path.join(TOOLS, "cnx_copy_tiers_r2.py")

MODULE_LEVEL = r'''
# --------------------------------------------------------------------------
# ORD-0424: the three shapes the `??` anchor cannot see
# --------------------------------------------------------------------------
#   JSX_TEXT_NODE   `<h3>Capability needs</h3>`. No quote at all: the string is element text, so it
#                   reaches a screen whether or not a language branch guards the neighbours.
#   TERNARY_BRANCH  `zh ? a : "Stated; confirmation needed by the traveller"`. A bare literal chosen
#                   by a condition that need not name a locale - `? "policy unavailable" : ...`
#                   branches on data availability and still paints English on a Chinese screen.
#   STATE_DEFAULT   `useState("I prefer quiet indoor culture...")`, generic form included, because it
#                   is what the traveller reads before any response arrives.
# A template literal in one of those places is the same defect (TERNARY_TEMPLATE in the inventory),
# so the backtick arm is opened and only its fixed text is taken as the string.
#
# The `??` face above is untouched: its two regexes, its tier letters and its exclusions are exactly
# as published, so a reader can diff today's reading against
# evidence/cmdr-ord0419-20260929-0051/ord0370_tierface_at_tip_8a7665be_r1.txt
# (blob 4765e5f8053fa078e04cff05a549568d5cb06ea6) and see that nothing was re-decided. These shapes
# only ever ADD hits, in a tier of their own.

# A JSX text block is anything between a closing `>` and the next `<` that is not markup, a brace
# (that would be an expression, handled by the other arms) or a quote. Newlines are allowed:
# `Refresh recovery` sits on its own line inside a <button>, and a per-line scan hands it nothing.
# An open tag's attribute run may contain a BRACE with an arrow inside it
# (`<button onClick={() => void refresh()}>Refresh recovery</button>`), and a plain `[^<>]` class
# stops at that arrow's `>`. The first version therefore read `void refresh()}` as the element text
# and never saw `Refresh recovery` at all - one of the two rows still missing at the inventory.
# Braces are allowed as units, one level deep, and the whole run stays BOUNDED.
JSX_BRACE = r"(?:\{(?:[^{}]|\{[^{}]{0,120}\}){0,200}\})"
JSX_OPEN_TAG = re.compile(r"(?<![A-Za-z0-9_$)\]])<([A-Za-z][\w.-]*)"
                          r"((?:" + r"[^<>{}]" + r"|" + JSX_BRACE + r"){0,300}?)(/?)>")
JSX_TEXT_STOP = re.compile(r"[<>]")
QUOTE_CHARS = '"' + "'"
# Both branches of a ternary are read, because the false branch is where this tree keeps its English:
# `{explicit.length ? explicit.join(" . ") : "No explicit preferences"}` is one of the pinned 22 and
# a rule that only reads the branch after `?` never sees it.
TERN_TRUE = re.compile(r"(?<![:?])\?\s*(?:" + STR + r"|(`[^`\n]{6,}`))")
TERN_FALSE = re.compile(r"(?<![:?])\?[^?:;\n]{1,120}?\s*:\s*(?:" + STR + r"|(`[^`\n]{6,}`))")


def first_group(m):
    """The literal this match captured, whichever alternative fired.

    `STR` is `(?:DQ|SQ)`, so a double-quoted arm fills group 1, a single-quoted arm fills group 2 and
    a template arm fills group 3. Reading `group(1)` unconditionally returned None for every template,
    and `(lit or "")` turned that into a silent skip - which is how the pinned row
    `${hard.length} hard need(s) remain explicit and are never learned.` stayed invisible.
    """
    for g in m.groups():
        if g is not None:
            return g
    return None
STATE_DEFAULT = re.compile(r"\buseState\s*(?:<[^<>{]{0,80}>)?\s*\(\s*(" + STR + r")")
WORD_RE = re.compile(r"[A-Za-z]{2,}")
PUNCT_ONLY = re.compile(r"^[\s\-.,;:|/一-鿿·→✓×()*#\[\]{}<>\u3001\u3002]*$")
COPY_SINGLE = re.compile(r"^[A-Z][A-Za-z]{2,}$|^[A-Z][A-Z0-9]{2,}$")
# Named vetoes, each one a shape that text alone can prove is not a sentence
LOCALE_TAG = re.compile(r"^[a-z]{2}([_-][A-Za-z]{2,4}){0,2}$")
SNAKE_TOKEN = re.compile(r"^[a-z][a-z0-9]*(_[a-z0-9]+)+$")
QUERY_FRAGMENT = re.compile(r"[?&=]")


def unquote(lit):
    """The literal as the traveller would read it, without its delimiters.

    A report that prints `"\\"No learned signals\\"" ` makes every comparison downstream fragile, and
    fragility in a ruler is how a miss gets mistaken for a pass.
    """
    s = (lit or "").strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in QUOTE_CHARS:
        return s[1:-1]
    if s.startswith("`"):
        # the fixed text of a template is whatever survives after every `${...}` hole is removed;
        # taking the head instead of the longest piece loses the whole tail of
        # `${hard.length} hard need(s) remain explicit and are never learned.` - a pinned row
        parts = re.split(r"\$\{[^{}]*\}", s[1:].split("`")[0])
        parts = [x.strip() for x in parts if x.strip()]
        return max(parts, key=len) if parts else ""
    return s


def copy_candidate(frag, allow_single_label=True):
    """Is this fragment a sentence or a label at all, before any exclusion is asked?

    Two words separated by a space, or - for element text only - one word that reads as a label
    (`CHANGED`, `PROTECTED`). A separator, an arrow, a number, a locale tag, a snake_case token or a
    query fragment is not something a traveller reads as prose: it never enters the candidate set, and
    is therefore not counted as an exclusion either. Exclusions are reserved for strings that WOULD be
    hits and are let go by a named rule, which is the only kind a reader can audit.
    """
    s = (frag or "").strip()
    if not s or PUNCT_ONLY.match(s):
        return False
    if LOCALE_TAG.match(s) or SNAKE_TOKEN.match(s):
        return False
    if QUERY_FRAGMENT.search(s):
        return False
    if len(WORD_RE.findall(s)) >= 2 and re.search(r"[A-Za-z]\s+\S*[A-Za-z]", s):
        return True
    if allow_single_label and COPY_SINGLE.match(s):
        return True
    return False


# Exclusions are asked PER SHAPE. `?? "CHANGED"` is an enum value handed to a screen, which the
# published veto is right to call a machine token; `<div>CHANGED</div>` is a label somebody wrote for
# the traveller to read. Same string, different shape, different answer - and the reason that fired is
# what gets reported, never a silent drop.
MACHINE_ONLY_IN_NULLISH = ("SCREAMING_SNAKE enum value",)


def _shape_verdict(shape, lit):
    found, why = _is_copy(lit)
    if found:
        found, why = localisable(lit)
    if not found and shape != "NULLISH" and why in MACHINE_ONLY_IN_NULLISH:
        found, why = True, ("copy: element text is read as it is rendered (the machine-token veto "
                           "belongs to a ?? slot, not to this shape)")
    return found, why


def seed_strings(data_dir):
    """Every name the demo data can put on a screen, read from the tree being scanned.

    `Tech Art Center` is seed content, not a missing translation: no dictionary key makes it Chinese
    and the data is the same on both arms. The exclusion may only fire on a string literally present in
    this directory, and the file plus the offset travel with the report.
    """
    if not data_dir or not os.path.isdir(data_dir):
        return {}
    names = {}

    def add(v, p, off):
        v = v.strip()
        if len(v) >= 3 and re.search(r"[A-Za-z]", v) and not CJK_RE.search(v):
            names.setdefault(v, []).append((p.replace(BS, "/"), off))

    for root, _dirs, files in os.walk(data_dir):
        for f in sorted(files):
            if not f.endswith(".json"):
                continue
            p = os.path.join(root, f)
            try:
                txt = io.open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for m in re.finditer(r'"(?:name|title|label|display_name)"\s*:\s*"([^"\n]{3,80})"', txt):
                add(m.group(1), p, m.start(1))
            for m in re.finditer(r'"(?:names|cities|pois)"\s*:\s*\[([^\]]{0,4000})\]', txt):
                for q in re.finditer(r'"([^"\n]{3,80})"', m.group(1)):
                    add(q.group(1), p, q.start(1))
    return names


BS = "\\"


# The brand vocabulary is a product decision, not a translation gap: the name reads the same on both
# arms. It is excluded BY NAME from this list and printed with the count, so a reader can disagree
# with the list instead of discovering a silent filter.
BRAND_WORDS = ("CityNexus Copilot", "Copilot", "CN / AI")


def exclusion_verdict(lit, seeds):
    stripped = lit.strip()
    for b in BRAND_WORDS:
        if stripped == b or stripped.startswith(b + " ") or stripped.endswith(" " + b):
            return "brand vocabulary (%r in BRAND_WORDS, same on both arms)" % b
    if stripped in seeds:
        where = seeds[stripped][0]
        return "seed data names this verbatim: %s at offset %d" % (where[0], where[1])
    return None


def new_shape_hits(text, name, lines, starts, seeds):
    """[(tier, file, line, literal, why, shape, render tier, slot)] for the three shapes.

    Tier C = a shape the published face cannot reach at all. The letter stays new on purpose: an old
    reading cannot be compared against a mixed bucket, so the count of newly visible hits is readable
    without re-deriving which ones used to be invisible.
    """
    out = []
    seen = set()

    def line_of(off):
        lo, hi = 0, len(starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if starts[mid] <= off:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1

    def push(shape, at, lit, abs_off):
        lit = (lit or "").strip()
        if not lit:
            return
        key = (name, at, lit)
        if key in seen:
            return
        seen.add(key)
        found, why = _shape_verdict(shape, lit)
        slot, in_lang = ("OTHER", False)
        if found:
            exc = exclusion_verdict(lit, seeds)
            if exc:
                found, why = False, exc
        if found:
            slot, in_lang = render_pos(text, abs_off)
            if shape == "JSX_TEXT_NODE":
                # the element parse IS the render proof here: text between a real open tag and the
                # next `<` is painted by React whatever the brace scanner makes of the rest of a line
                # that may hold four hundred characters of markup
                slot, in_lang = ("JSX_CHILD", in_lang)
        out.append((("C" if found else "C-skipped"), name, at, lit, "%s: %s" % (shape, why),
                    "jsx-text" if shape == "JSX_TEXT_NODE" else shape.lower(),
                    render_tier(slot, in_lang, lit) if found else 3, slot))

    # ---- element text, read as tags rather than as angle brackets ----
    if name.endswith(".tsx"):
        # `{/* … */}` is a comment, not something a traveller reads. It is masked to SPACES rather
        # than removed so every offset still lands on the same line, and the arm K8i is what proves
        # the mask holds: the first version reported the comment's own English prose as element text.
        scanned = re.sub(r"\{/\*.*?\*/\}", lambda mm: " " * len(mm.group(0)), text, flags=re.S)
        for m in JSX_OPEN_TAG.finditer(scanned):
            tag, selfclosing = m.group(1), bool(m.group(3))
            # searched by offset, never by slicing, and the attribute run is BOUNDED at 300 chars:
            # the unbounded lazy form `(?:[^<>/]|\s)*?` was not merely slow, it made one file
            # (frontend/src/app/V8Experience.tsx) unfinishable inside ten minutes
            if not selfclosing and scanned.find("</" + tag, m.end()) < 0:
                continue
            stop = JSX_TEXT_STOP.search(scanned, m.end())
            if not stop:
                continue
            frag = " ".join(scanned[m.end():stop.start()].split())
            if not copy_candidate(frag, allow_single_label=True):
                continue
            at = line_of(m.end())
            if lines[at - 1].strip().startswith(("//", "*", "/*")):
                continue
            push("JSX_TEXT_NODE", at, frag, m.end())

    # ---- ternary branches and useState defaults, read per line ----
    for i, line in enumerate(lines):
        if line.strip().startswith(("//", "*", "/*")):
            continue
        for rx, shape in ((TERN_TRUE, "TERNARY_BRANCH"), (TERN_FALSE, "TERNARY_BRANCH"),
                          (STATE_DEFAULT, "STATE_DEFAULT")):
            for m in rx.finditer(line):
                # one word in a branch is a machine value (`? "empty"`, `? "html" : "not_json"`),
                # which is exactly what the published face's K4i arm exists to keep quiet
                lit = unquote(first_group(m) or "")
                if not copy_candidate(lit, allow_single_label=False):
                    continue
                push(shape, i + 1, lit, starts[i] + (m.start(1) if m.start(1) >= 0 else m.start()))
    return out
'''

BODY_PREAMBLE = (
    "def fallback_hits(text, name, lines=None, starts=None, seeds=None):\n"
    '    """[(tier, file, line, literal, why, shape, render tier, slot)] for one file.\n\n'
    "    `lines` / `starts` are the caller's line offsets, computed once when absent; `seeds` is the\n"
    "    tree's own seed-name index, and an empty index excludes nothing. A `??` that ends a line and a\n"
    "    fallback that opens the next line are one expression, not two, so the pair is read as a joined\n"
    "    window; the hit is still attributed to the line carrying the literal.\n"
    '    """\n'
    "    if lines is None:\n"
    '        lines = text.split("\\n")\n'
    "    if starts is None:\n"
    "        starts = []\n"
    "        off = 0\n"
    "        for ln in lines:\n"
    "            starts.append(off)\n"
    "            off += len(ln) + 1\n"
    "    if seeds is None:\n"
    "        seeds = {}\n"
    "    hits = []\n"
    "    seen = set()\n"
)

OLD_BODY_HEAD = (
    'def fallback_hits(text, name):\n'
    '    """[(tier, file, line, literal, why, slot, render tier)] for one file\'s text.\n'
    '\n'
    '    A `??` that ends a line and a fallback that opens the next line are one\n'
    '    expression, not two, so the pair is read as a joined window; the hit is\n'
    '    still attributed to the line carrying the literal. The render tier is\n'
    '    computed from an absolute offset into the file, because deciding whether a\n'
    '    value lands in element text needs the braces around it, not the line.\n'
    '    """\n'
    '    lines = text.split("\\n")\n'
    '    starts = []\n'
    '    off = 0\n'
    '    for ln in lines:\n'
    '        starts.append(off)\n'
    '        off += len(ln) + 1\n'
    '    hits = []\n'
    '    seen = set()\n'
)

OLD_SCAN_TREE = (
    "def scan_tree(src_dir):\n"
    "    hits, pairs, files = [], 0, 0\n"
    '    for p in sorted(Path(src_dir).rglob("*")):\n'
    '        if p.suffix not in {".ts", ".tsx"} or "node_modules" in p.parts:\n'
    "            continue\n"
    "        files += 1\n"
    '        text = p.read_text(encoding="utf-8", errors="replace")\n'
    "        hits += fallback_hits(text, str(p))\n"
    "        pairs += len(PAIR_RE.findall(text))\n"
    "    return hits, pairs, files\n"
)

NEW_SCAN_TREE = (
    "def scan_tree(src_dir, data_dir=None):\n"
    '    """`data_dir` is the scanned tree\'s own seed directory; None excludes nothing."""\n'
    "    hits, pairs, files = [], 0, 0\n"
    "    seeds = seed_strings(data_dir)\n"
    '    for p in sorted(Path(src_dir).rglob("*")):\n'
    '        if p.suffix not in {".ts", ".tsx"} or "node_modules" in p.parts:\n'
    "            continue\n"
    "        files += 1\n"
    '        text = p.read_text(encoding="utf-8", errors="replace")\n'
    '        lines = text.split("\\n")\n'
    "        starts, off = [], 0\n"
    "        for ln in lines:\n"
    "            starts.append(off)\n"
    "            off += len(ln) + 1\n"
    "        hits += fallback_hits(text, str(p), lines, starts, seeds)\n"
    "        pairs += len(PAIR_RE.findall(text))\n"
    "    return hits, pairs, files\n"
)

APPEND_LOOP = (
    '                        _tally(hits, seen, "B", name, at, lit, _is_copy(lit), shape, slot, in_lang)\n'
    "    return hits\n"
)
APPEND_LOOP_NEW = (
    '                        _tally(hits, seen, "B", name, at, lit, _is_copy(lit), shape, slot, in_lang)\n'
    "    hits += new_shape_hits(text, name, lines, starts, seeds)\n"
    "    return hits\n"
)


def main():
    s = io.open(SRC, encoding="utf-8").read()
    assert s.count(OLD_BODY_HEAD) == 1, s.count(OLD_BODY_HEAD)
    s = s.replace(OLD_BODY_HEAD, BODY_PREAMBLE, 1)
    assert s.count(OLD_SCAN_TREE) == 1, s.count(OLD_SCAN_TREE)
    s = s.replace(OLD_SCAN_TREE, NEW_SCAN_TREE, 1)
    assert s.count(APPEND_LOOP) == 1, s.count(APPEND_LOOP)
    s = s.replace(APPEND_LOOP, APPEND_LOOP_NEW, 1)

    anchor = "def fallback_hits(text, name, lines=None"
    assert s.count(anchor) == 1
    s = s.replace(anchor, MODULE_LEVEL.strip() + "\n\n\n" + anchor, 1)

    io.open(DST, "w", encoding="utf-8", newline="\n").write(s)
    ast.parse(s)
    print("wrote", DST, len(s.encode("utf-8")), "B  ast.parse ok")


if __name__ == "__main__":
    main()
