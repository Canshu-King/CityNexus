"""Re-key design-tokens.css's dark blocks from the OS media query onto the root data-theme.

Ruling ④ needs a pinned System/Light/Dark choice to win over the operating system, and
`@media (prefers-color-scheme: dark)` cannot express "OS is light, traveller chose dark".
theme.ts always writes `:root[data-theme=...]`, so each wrapper is removed and every selector
inside it is prefixed.  One copy of each rule; no duplicated token table.

Comment-aware: an earlier revision of this script matched selectors with a regex that also
spanned `/* ... */` text and injected prefixes *inside* the explanatory comments, which are
the documentation other lanes read.  The invariants below now include a check that no prefix
ever lands inside a comment.
"""

import sys

PATH = "D:/moodle/_qoder_ui_overnight_20260920/frontend/src/design-tokens.css"
MARK = "@media (prefers-color-scheme: dark) {"
THEME = ':root[data-theme="dark"]'
TERMINATORS = set("};{")

original = open(PATH, encoding="utf-8", newline="").read()


def comment_spans(text):
    spans = []
    index = 0
    while True:
        start = text.find("/*", index)
        if start == -1:
            break
        end = text.find("*/", start + 2)
        end = len(text) if end == -1 else end + 2
        spans.append((start, end))
        index = end
    return spans


def masked(text):
    """A copy of `text` with comment characters replaced by spaces, so positions align."""
    out = list(text)
    for start, end in comment_spans(text):
        for index in range(start, min(end, len(out))):
            out[index] = " "
    return "".join(out)


def matching_brace(view, open_index):
    depth = 0
    index = open_index
    while index < len(view):
        if view[index] == "{":
            depth += 1
        elif view[index] == "}":
            depth -= 1
            if depth == 0:
                return index
        index += 1
    raise AssertionError("unbalanced braces")


def rekey_body(body):
    """Prefix every selector that governs a `{` inside a dark block's body.

    The selector is the last *code* segment before the brace: comments are cut out first,
    so a rule that follows a multi-line explanatory comment cannot be mistaken for one.
    """
    view = masked(body)
    spans = comment_spans(body)
    inserts = []
    for index, char in enumerate(view):
        if char != "{":
            continue
        end = index - 1
        while end >= 0 and view[end].isspace():
            end -= 1
        if end < 0 or view[end] in TERMINATORS:
            continue
        start = end
        while start >= 0 and view[start] not in TERMINATORS:
            start -= 1
        start += 1
        region = body[start : end + 1]
        region_view = view[start : end + 1]
        # Keep only code (non-comment) text, then take its trailing selector run.
        code_parts = []
        cursor = 0
        for c_start, c_end in spans:
            c_start = max(c_start - start, 0)
            c_end = min(c_end - start, len(region))
            if c_start >= c_end:
                continue
            if c_start > cursor:
                code_parts.append((cursor, c_start))
            cursor = max(cursor, c_end)
        if cursor < len(region):
            code_parts.append((cursor, len(region)))
        if not code_parts:
            continue
        last_start, last_end = code_parts[-1]
        selector_text = region[last_start:last_end].strip()
        if not selector_text:
            continue
        sel_from = start + last_start + (len(region[last_start:last_end]) - len(region[last_start:last_end].lstrip()))
        sel_to = sel_from + len(selector_text)
        parts = [part.strip() for part in selector_text.split(",") if part.strip()]
        rewritten = []
        for part in parts:
            if part in (":root", "html"):
                rewritten.append(THEME)
            elif part.startswith(":root") or part.startswith("html"):
                head = ":root" if part.startswith(":root") else "html"
                rewritten.append(THEME + part[len(head) :])
            else:
                rewritten.append(f"{THEME} {part}")
        inserts.append((sel_from, sel_to, ", ".join(rewritten)))
    if not inserts:
        return body
    pieces = []
    cursor = 0
    for start, end, text in sorted(inserts):
        pieces.append(body[cursor:start])
        pieces.append(text)
        cursor = end
    pieces.append(body[cursor:])
    return "".join(pieces)


pieces = []
cursor = 0
blocks = 0
while True:
    start = original.find(MARK, cursor)
    if start == -1:
        pieces.append(original[cursor:])
        break
    open_index = start + len(MARK) - 1
    close = matching_brace(masked(original), open_index)
    body = original[open_index + 1 : close]
    pieces.append(original[cursor:start])
    pieces.append(rekey_body(body))
    blocks += 1
    cursor = close + 1

new_text = "".join(pieces)

# --- invariants ---------------------------------------------------------------
old_open, old_close = original.count("{"), original.count("}")
new_open, new_close = new_text.count("{"), new_text.count("}")
if (old_open - new_open, old_close - new_close) != (blocks, blocks):
    sys.exit(
        f"REFUSED: expected to remove exactly {blocks} wrapper brace pairs, "
        f"removed {old_open - new_open}/{old_close - new_close}"
    )
if new_text.count(MARK):
    sys.exit("REFUSED: a dark media wrapper survived")
if new_text.count(THEME) < blocks:
    sys.exit("REFUSED: nothing was re-keyed")

# No declaration value may have changed: every innermost body in the original must still be
# present, byte for byte, in the result.
import re as _re

old_bodies = _re.findall(r"\{([^{}]*)\}", masked(original), _re.S)
new_bodies = _re.findall(r"\{([^{}]*)\}", masked(new_text), _re.S)
missing = [body for body in old_bodies if body not in new_bodies]
if missing:
    sys.exit(f"REFUSED: {len(missing)} declaration body(ies) changed, first: {missing[0][:80]!r}")
if len(new_bodies) != len(old_bodies):
    sys.exit(
        f"REFUSED: rule count changed ({len(old_bodies)} -> {len(new_bodies)}) "
        "beyond the removed wrappers"
    )

# The check the previous revision failed: a prefix must never appear inside a comment.
for start, end in comment_spans(new_text):
    if THEME in new_text[start:end]:
        sys.exit(
            "REFUSED: a theme prefix landed inside a comment at "
            + str(start)
            + ": "
            + new_text[start : start + 90].replace("\n", " ")
        )
# And comments themselves must be untouched, in order.
old_comments = [original[s:e] for s, e in comment_spans(original)]
new_comments = [new_text[s:e] for s, e in comment_spans(new_text)]
if old_comments != new_comments:
    changed = next(
        (i for i, (a, b) in enumerate(zip(old_comments, new_comments)) if a != b), len(new_comments)
    )
    sys.exit(f"REFUSED: comment #{changed} changed")

print(f"dark blocks re-keyed: {blocks}")
print(f"braces: {old_open}/{old_close} -> {new_open}/{new_close}")
print(f"comments preserved: {len(old_comments)}")
if "--dry-run" in sys.argv:
    sys.exit(0)
open(PATH, "w", encoding="utf-8", newline="").write(new_text)
print("written")
