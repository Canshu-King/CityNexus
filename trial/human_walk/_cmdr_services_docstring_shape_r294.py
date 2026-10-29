"""bw294: is a code block pasted inside the _place_has_unresolved_opening docstring?

Two rulers disagreed on this file in the same shift: a grep reported return statements at 142/146/147
while an ast-free Python read reported 746/782/787/789/799.  That cannot both be true of one body of
bytes, so this ruler reads the file exactly once, keeps the bytes, and derives every claim from that
single read: line 138-152 verbatim, every line whose stripped text equals the refusal statement,
whether the module still parses, when the file was last written, and whether git sees it as modified.
"""

import ast
import hashlib
import io
import os
import subprocess
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REL = "backend/app/services.py"
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw294-services-docstring-shape.txt")
REFUSAL = "return UNRESOLVED_ACTIVITY_FACTS"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    path = os.path.join(ROOT, REL.replace("/", os.sep))
    raw = io.open(path, "rb").read()
    text = raw.decode("utf-8")
    lines = text.split("\n")

    hits = [index + 1 for index, row in enumerate(lines) if row.strip() == REFUSAL]
    parse_error = ""
    try:
        tree = ast.parse(text)
        parsed = "OK"
    except SyntaxError as exc:
        tree = None
        parsed = "SYNTAX_ERROR %s" % exc
    func = None
    if tree is not None:
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == "_place_has_unresolved_opening":
                func = node
                break

    out = [
        "SHAPE CHECK OF %s bw294" % REL,
        "BYTES %d sha256 %s" % (len(raw), hashlib.sha256(raw).hexdigest()[:16]),
        "MTIME %s" % __import__("datetime").datetime.fromtimestamp(
            os.path.getmtime(path)).isoformat(timespec="seconds"),
        "GIT_porcelain %r" % subprocess.run(["git", "-C", ROOT, "status", "--porcelain", REL],
                                            capture_output=True, text=True).stdout.strip(),
        "GIT_last_commit %s" % subprocess.run(
            ["git", "-C", ROOT, "log", "-1", "--format=%h %ad %s", "--date=format:%m-%d %H:%M", "--", REL],
            capture_output=True, text=True).stdout.strip(),
        "AST_parse %s" % parsed,
        "REFUSAL_LINES (stripped text equals %r): %s" % (REFUSAL, hits),
    ]

    if func is None:
        out.append("FUNCTION _place_has_unresolved_opening NOT FOUND as a module-level def")
    else:
        doc = ast.get_docstring(func, clean=False) or ""
        out.append("FUNCTION def at line %d, docstring spans lines %d-%d"
                   % (func.lineno, func.body[0].lineno, func.body[0].end_lineno))
        out.append("DOCSTRING_CONTAINS_REFUSAL %s (%d times)"
                   % ("YES" if REFUSAL in doc else "NO", doc.count(REFUSAL)))
        out.append("DOCSTRING_BODY:")
        for index, row in enumerate(doc.split("\n"), start=func.body[0].lineno):
            out.append("      %4d| %s" % (index, row[:100]))

    out.append("VERBATIM_LINES_136_156")
    for index in range(136, min(157, len(lines) + 1)):
        out.append("      %4d| %s" % (index, lines[index - 1][:100]))
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for row in out:
        print(row)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
