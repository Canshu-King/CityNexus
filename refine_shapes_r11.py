"""Fourth cut of the ORD-0424 shapes: precision rules the third cut's measurement demanded, and the
escape discipline its own generator needed.

The third cut hit 15 of the 22 pinned strings and 772 tier-C hits over 96 files at once - a face that
calls three quarters of a screen a defect gets muted by its next reader, which is the failure this
tool's own comments already warn about. Measured causes, each now a checkable rule:

  * `> ... <` is not an element boundary by itself: `Promise<Response>` and `useState<ReadState>({`
    produced 61 fake "element text" hits in .ts files alone. The opening is parsed as a tag - it may
    not sit flush against an identifier (a generic does) and a non-self-closing one must have a
    matching `</name>` after it (a comparison operator does not). Element text is only looked for in
    .tsx, where JSX exists at all.
  * a single lowercase token is not prose: `not_json`, `?proposal_id=`, `zh-CN` and `en-GB` were
    counted as sentences. Two words separated by a space are required, with named vetoes for BCP-47
    tags, snake_case tokens and query fragments.
  * a label is still copy: `CHANGED`, `PROTECTED`, `Baseline evidence` are element text in the
    inventory, so the single-word allowance stays for the element shape and is dropped for ternary and
    `useState` branches, where a one-word branch is a machine value.

Escape note, because it cost a run: this generator's payload is written into a raw string that is
then written into the tool verbatim, so a regex here needs ONE backslash. The previous revision doubled
them (`\\?\\s*`), which the tool then compiled as "optional literal backslash", and the doubled
quote escapes made the generated file unparseable. Quoting is done through QUOTE_CHARS instead of a
backslash inside a quote.
"""
import ast
import io
import os

WORK = r"D:\moodle\_qoder_lane_S4_0926\work\ord0424"
BOLT = os.path.join(WORK, "bolt_shapes_r2.py")

START = "JSX_OPEN_TAG = re.compile("
FALLBACK_START = "JSX_TEXT_RE = re.compile("
END = "    return out"

BLOCK = r'''JSX_OPEN_TAG = re.compile(r"(?<![A-Za-z0-9_$)\]])<([A-Za-z][\w.-]*)((?:[^<>/]|\s)*?)(/?)>")
JSX_TEXT_STOP = re.compile(r"[<>]")
QUOTE_CHARS = '"' + "'"
# Both branches of a ternary are read, because the false branch is where this tree keeps its English:
# `{explicit.length ? explicit.join(" . ") : "No explicit preferences"}` is one of the pinned 22 and
# a rule that only reads the branch after `?` never sees it.
TERN_TRUE = re.compile(r"(?<![:?])\?\s*(?:" + STR + r"|`[^`\n]{6,}`)")
TERN_FALSE = re.compile(r"(?<![:?])\?[^?:;\n]{1,120}?\s*:\s*(?:" + STR + r"|`[^`\n]{6,}`)")
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
        head = re.match(r"`([^`$]*)", s)
        return head.group(1).strip() if head else s.strip("`")
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
        for m in JSX_OPEN_TAG.finditer(text):
            tag, selfclosing = m.group(1), m.group(3)
            body = text[m.end():]
            if not selfclosing and ("</" + tag) not in body:
                continue
            stop = JSX_TEXT_STOP.search(body)
            if not stop:
                continue
            frag = " ".join(body[:stop.start()].split())
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
                lit = unquote(m.group(1))
                if not copy_candidate(lit, allow_single_label=False):
                    continue
                push(shape, i + 1, lit, starts[i] + m.start(1))
    return out'''


def main():
    s = io.open(BOLT, encoding="utf-8").read()
    i = s.index(START) if START in s else s.index(FALLBACK_START)
    j = s.index(END, i) + len(END)
    s = s[:i] + BLOCK + s[j:]
    for needle in ("def copy_candidate", "def unquote", "def seed_strings", "def exclusion_verdict",
                   "def new_shape_hits"):
        assert s.count(needle) == 1, (needle, s.count(needle))
    for needle in ("JSX_OPEN_TAG", "TERN_FALSE", "LOCALE_TAG", "MACHINE_ONLY_IN_NULLISH",
                   "QUOTE_CHARS"):
        assert s.count(needle) >= 2, (needle, s.count(needle))
    assert "JSX_TEXT_RE" not in s, "the loose angle-bracket rule is still referenced"
    ast.parse(s)
    io.open(BOLT, "w", encoding="utf-8", newline="\n").write(s)
    print("shapes block replaced in the generator:", len(s.encode("utf-8")), "B")


if __name__ == "__main__":
    main()
