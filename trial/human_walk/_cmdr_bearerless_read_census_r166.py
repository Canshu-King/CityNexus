"""Inventory every private-journey read in the backend suite that never passes a credential.

The shift proved one cause family (401 on a bearer-less read) explains at least sixteen reds, so the
question for the repair order is scope, not theory.  This walks every test file's syntax tree and
lists each client.get/client.post whose URL is a private journey door and that carries no headers
argument at all.  It counts only what the parser actually finds and prints the denominator next to it.
"""

import ast
import io
import os
import sys

TESTS = r"D:\moodle\_cmdr_rescue_v3_1022\backend\tests"
PRIVATE_MARKERS = (
    "/experience",
    "/events",
    "/offline-snapshot",
    "/member-side-quests",
    "/group-presence",
    "/journeys/",
)
GETTERS = ("get", "post", "put", "patch", "delete")


def private(url):
    return isinstance(url, str) and "/api/v1/journeys/" in url


def url_text_of(node):
    """Join the literal fragments of a plain string or an f-string argument."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(str(part.value) for part in node.values if isinstance(part, ast.Constant))
    return ""


def scan_file(path, relative):
    source = io.open(path, encoding="utf-8", errors="replace").read()
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        return [("PARSE-ERROR", relative, 0, str(exc))]
    found = []

    class Walk(ast.NodeVisitor):
        def visit_Call(self, node):
            func = node.func
            url_text = url_text_of(node.args[0]) if node.args else ""
            if (
                isinstance(func, ast.Attribute)
                and func.attr in GETTERS
                and isinstance(func.value, ast.Name)
                and func.value.id == "client"
                and private(url_text)
            ):
                method = func.attr
                keyword_names = {kw.arg for kw in node.keywords}
                if "headers" not in keyword_names:
                    found.append((method, relative, node.lineno, url_text[:80]))
            self.generic_visit(node)

    Walk().visit(tree)
    return found


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    files = []
    for root, _dirs, names in os.walk(TESTS):
        for name in sorted(names):
            if name.startswith("test_") and name.endswith(".py"):
                files.append(os.path.join(root, name))
    hits = []
    parse_errors = []
    for path in sorted(files):
        relative = os.path.relpath(path, TESTS).replace("\\", "/")
        for entry in scan_file(path, relative):
            if entry[0] == "PARSE-ERROR":
                parse_errors.append(entry)
            else:
                hits.append(entry)
    per_file = {}
    for _method, relative, _line, _url in hits:
        per_file[relative] = per_file.get(relative, 0) + 1
    # Positive control: this shift already measured that this exact call is bearer-less and answers
    # 401, so a census that cannot see it is blind, not empty.
    control = ("get", "test_r64_member_side_quest.py", 1840)
    if not any((m, f, ln) == control for m, f, ln, _u in hits):
        print("ABORT control site tests/%s:%d is a known bearer-less read and the census missed it"
              % (control[1], control[2]))
        return 7
    print("CONTROL_SITE_SEEN tests/%s:%d" % (control[1], control[2]))
    print("TEST_FILES_PARSED %d" % len(files))
    print("PARSE_ERRORS %d" % len(parse_errors))
    for entry in parse_errors:
        print("  %s %s" % (entry[1], entry[3]))
    print("PRIVATE_CALLS_WITHOUT_HEADERS %d" % len(hits))
    print("FILES_INVOLVED %d" % len(per_file))
    for relative, count in sorted(per_file.items(), key=lambda item: (-item[1], item[0])):
        print("  %3d  tests/%s" % (count, relative))
    print("TOP CALL SITES")
    for method, relative, line, url in sorted(hits, key=lambda item: (item[1], item[2]))[:20]:
        print("  tests/%s:%d %s %s" % (relative, line, method.upper(), url))
    return 0


if __name__ == "__main__":
    sys.exit(main())
