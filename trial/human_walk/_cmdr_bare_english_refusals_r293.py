"""bw293: how many refusals hand the traveller a bare English sentence?

Section 14.27 found one by walking: pressing accept with no plan chosen answers 409 with the literal
"Trip Studio requires an active plan" (backend/app/main.py), and the only message_key attached is the
generic request.conflict, so the screen has no Chinese phrase waiting for it.  One example is an
anecdote.  This ruler counts the family.

Method: parse every module under backend/app with ast, take the second positional argument of each
HTTPException(...) raise, and classify the literal text (f-strings are unparsed back to source, so an
interpolated code prefix still reads as a code).  Three buckets: a bare internal CODE, an ENGLISH
SENTENCE a person can read on screen, and MIXED where a code and a sentence are welded together.

Named assertions, because a census that cannot see the known example is not a census: the ruler must
place "Trip Studio requires an active plan" in ENGLISH_SENTENCE and "TRIP_STUDIO_BASE_PLAN_STALE" in
CODE_ONLY, or it aborts instead of publishing a number.  Read-only: nothing here changes a byte.
"""

import ast
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(ROOT, "backend", "app")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw293-bare-english-refusals.txt")

CODE_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z']{2,}")
KNOWN_SENTENCE = "Trip Studio requires an active plan"
KNOWN_CODE = "TRIP_STUDIO_BASE_PLAN_STALE"


def classify(text: str) -> str:
    stripped = text.strip()
    has_code = bool(CODE_RE.search(stripped))
    words = [token for token in WORD_RE.findall(stripped) if not token.isupper()]
    if has_code and len(words) >= 3:
        return "MIXED"
    if has_code:
        return "CODE_ONLY"
    if len(words) >= 3:
        return "ENGLISH_SENTENCE"
    return "OTHER"


def message_of(node: ast.Call) -> str | None:
    """Return the literal detail argument of an HTTPException(...) call."""
    args = list(node.args)
    if len(args) >= 2:
        candidate = args[1]
    elif any(getattr(keyword, "arg", None) == "detail" for keyword in node.keywords):
        candidate = next(keyword.value for keyword in node.keywords
                         if getattr(keyword, "arg", None) == "detail")
    else:
        return None
    if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str):
        return candidate.value
    if isinstance(candidate, ast.JoinedStr):
        return ast.unparse(candidate)
    return None


def detail_shape(node: ast.Call) -> str:
    """Does the payload carry a message_key a client could localise, or only prose?"""
    for candidate in list(node.args[1:]) + [
        keyword.value for keyword in node.keywords
        if getattr(keyword, "arg", None) in ("detail", "message")
    ]:
        if isinstance(candidate, ast.Dict):
            keys = {ast.unparse(item) for item in candidate.keys if item is not None}
            if "message_key" in keys:
                return "WITH_MESSAGE_KEY"
            return "DICT_NO_MESSAGE_KEY"
        if isinstance(candidate, (ast.Constant, ast.JoinedStr)):
            return "PLAIN_STRING"
    return "UNKNOWN_SHAPE"


def scan() -> tuple[list[dict], dict]:
    rows = []
    files = []
    for base, _dirs, names in os.walk(APP):
        for name in sorted(names):
            if name.endswith(".py"):
                files.append(os.path.join(base, name))
    for path in files:
        source = io.open(path, encoding="utf-8", errors="replace").read()
        try:
            tree = ast.parse(source)
        except SyntaxError as exc:
            raise SystemExit("ABORT cannot parse %s: %s" % (path, exc))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            if name != "HTTPException":
                continue
            text = message_of(node)
            shape = detail_shape(node)
            if text is None:
                rows.append({"path": os.path.relpath(path, ROOT).replace("\\", "/"),
                             "line": node.lineno, "kind": "NOT_LITERAL", "shape": shape,
                             "text": ""})
                continue
            rows.append({"path": os.path.relpath(path, ROOT).replace("\\", "/"),
                         "line": node.lineno, "kind": classify(text), "shape": shape,
                         "text": text[:150]})
    return rows, {"files": len(files)}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows, meta = scan()
    counts = {}
    for row in rows:
        counts[row["kind"]] = counts.get(row["kind"], 0) + 1

    # named assertions - the census must see the known example, or it proves nothing
    known_sentence = [r for r in rows if KNOWN_SENTENCE in r["text"]]
    known_code = [r for r in rows if KNOWN_CODE == r["text"]]
    if not known_sentence:
        print("ABORT the census cannot find the known English sentence at all")
        return 7
    if any(r["kind"] != "ENGLISH_SENTENCE" for r in known_sentence):
        print("ABORT the known English sentence classified as %s"
              % sorted({r["kind"] for r in known_sentence}))
        return 7
    if not known_code:
        print("ABORT the census cannot find the known internal code at all")
        return 7
    if any(r["kind"] != "CODE_ONLY" for r in known_code):
        print("ABORT the known internal code classified as %s"
              % sorted({r["kind"] for r in known_code}))
        return 7

    shapes = {}
    for row in rows:
        shapes[row["shape"]] = shapes.get(row["shape"], 0) + 1
    english_plain = [r for r in rows if r["kind"] == "ENGLISH_SENTENCE"
                     and r["shape"] == "PLAIN_STRING"]
    english_keyed = [r for r in rows if r["kind"] == "ENGLISH_SENTENCE"
                     and r["shape"] == "WITH_MESSAGE_KEY"]
    if not shapes.get("PLAIN_STRING") or not shapes.get("WITH_MESSAGE_KEY"):
        print("ABORT the payload-shape arm only ever saw one bucket: %s" % shapes)
        return 7
    by_file = {}
    for row in rows:
        if row["kind"] == "ENGLISH_SENTENCE":
            by_file.setdefault(row["path"], []).append(row)
    lines = [
        "BARE ENGLISH REFUSALS HANDED TO A TRAVELLER bw293",
        "SCOPE every module under backend/app (files=%d), parsed with ast, read-only"
        % meta["files"],
        "HTTPException RAISES FOUND %d (this is the denominator)" % len(rows),
        "BUCKETS %s" % ", ".join("%s=%d" % (key, counts[key]) for key in sorted(counts)),
        "NAMED CONTROLS",
        "  %r -> %s at %s:%d" % (KNOWN_SENTENCE, known_sentence[0]["kind"],
                                 known_sentence[0]["path"], known_sentence[0]["line"]),
        "  %r -> %s at %s:%d" % (KNOWN_CODE, known_code[0]["kind"],
                                 known_code[0]["path"], known_code[0]["line"]),
        "ENGLISH SENTENCES BY FILE (every row carries its own coordinate)",
    ]
    for path in sorted(by_file, key=lambda key: (-len(by_file[key]), key)):
        lines.append("  %s  %d sentences" % (path, len(by_file[path])))
        for row in by_file[path][:6]:
            lines.append("      %s:%d  %s" % (row["path"], row["line"], row["text"][:110]))
    lines.append("MIXED CODE-PLUS-SENTENCE ROWS")
    for row in [r for r in rows if r["kind"] == "MIXED"][:12]:
        lines.append("  %s:%d  %s" % (row["path"], row["line"], row["text"][:110]))
    lines.append("NOT_LITERAL (message built at runtime, invisible to a static census)")
    for row in [r for r in rows if r["kind"] == "NOT_LITERAL"][:10]:
        lines.append("  %s:%d" % (row["path"], row["line"]))
    lines.append("COVERAGE_LIMIT the census reads the raise site only; it cannot say which of these "
                 "a traveller can actually reach, and it does not see messages built by a helper.")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(lines) + "\n")
    for line in lines:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
