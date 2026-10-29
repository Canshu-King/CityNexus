"""bw302: of the 333 English refusals, how many sit on a route a traveller can actually hit?

bw293 counted the sentences; the count alone cannot be handed to the operator as a screen problem,
because the same bucket mixes three very different surfaces: a FastAPI route a traveller's click can
reach, an Agent-tool path only the assistant walks, and an internal helper.  This ruler separates them
by what decorates the function holding each raise: any @app.get/post/put/patch/delete binding makes it
route-reachable, a module under backend/app/agent or an agent_* function is the assistant's surface,
and everything else is internal.

Named assertion, so a mis-bucketed sheet cannot pass: the known sentence raised at backend/app/main.py
must land in ROUTE_REACHABLE, and the census must still show a non-empty INTERNAL bucket - if every
raise were called route-reachable the classification would be doing nothing.
"""

import ast
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
APP = os.path.join(ROOT, "backend", "app")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw302-which-surface-says-it-in-english.txt")
KNOWN_SENTENCE = "Trip Studio requires an active plan"
HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options")
CODE_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)+\b")
WORD_RE = re.compile(r"[A-Za-z][A-Za-z']{2,}")


def classify(text):
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


def route_paths(func):
    """Return the URL paths this function is bound to as an HTTP route, if any."""
    paths = []
    for decorator in func.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        target = decorator.func
        if isinstance(target, ast.Attribute) and target.attr in HTTP_METHODS:
            owner = target.value
            owner_name = getattr(owner, "id", None) or getattr(owner, "attr", None)
            if owner_name in ("app", "router") and decorator.args:
                first = decorator.args[0]
                if isinstance(first, ast.Constant) and isinstance(first.value, str):
                    # keep which object carried the binding, so an APIRouter route reads differently
                    paths.append("%s %s" % (owner_name, first.value))
    return paths


def detail_text(call):
    args = list(call.args)
    candidate = args[1] if len(args) >= 2 else next(
        (kw.value for kw in call.keywords if getattr(kw, "arg", None) == "detail"), None)
    if isinstance(candidate, ast.Constant) and isinstance(candidate.value, str):
        return candidate.value
    if isinstance(candidate, ast.JoinedStr):
        return ast.unparse(candidate)
    return None


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    rows = []
    for base, _dirs, names in os.walk(APP):
        for name in sorted(names):
            if not name.endswith(".py"):
                continue
            path = os.path.join(base, name)
            rel = os.path.relpath(path, ROOT).replace("\\", "/")
            source = io.open(path, encoding="utf-8", errors="replace").read()
            tree = ast.parse(source)
            funcs = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            # a private helper reached only through a routed function still lands on a traveller's
            # screen, so the module is consulted as a second level; the two levels are reported apart
            module_bound = [path for func in funcs for path in route_paths(func)]
            module_is_agent = rel.endswith(os.path.join("app", "agent", "gateway.py")) or (
                os.sep + "agent" + os.sep) in path
            # walk functions so each raise inherits the surface of the function holding it
            for func in funcs:
                bound = route_paths(func)
                for node in ast.walk(func):
                    if not isinstance(node, ast.Call):
                        continue
                    fname = getattr(node.func, "id", None) or getattr(node.func, "attr", None)
                    if fname != "HTTPException":
                        continue
                    text = detail_text(node)
                    if text is None:
                        continue
                    if bound:
                        surface, via = "ROUTE_REACHABLE", "route_decorator"
                    elif module_bound:
                        surface, via = "ROUTE_REACHABLE", "same_module_has_routes"
                    elif module_is_agent or func.name.startswith("agent_"):
                        surface, via = "AGENT_SURFACE", "agent_module"
                    else:
                        surface, via = "INTERNAL", "no_route_found"
                    rows.append({"path": rel, "line": node.lineno, "kind": classify(text),
                                 "surface": surface, "via": via,
                                 "routes": bound, "module_route_count": len(module_bound),
                                 "func": func.name,
                                 "text": text[:120]})
            # raises outside any function body are reported as a coverage limit, not silently counted

    english = [r for r in rows if r["kind"] == "ENGLISH_SENTENCE"]
    surfaces = {}
    via_counts = {}
    for row in english:
        surfaces[row["surface"]] = surfaces.get(row["surface"], 0) + 1
        if row["surface"] == "ROUTE_REACHABLE":
            via_counts[row["via"]] = via_counts.get(row["via"], 0) + 1

    known = [r for r in rows if KNOWN_SENTENCE in r["text"]]
    if not known:
        print("ABORT the known traveller-facing sentence is not in the census at all")
        return 7
    if not all(r["surface"] == "ROUTE_REACHABLE" for r in known):
        print("ABORT the known sentence read as %s, so route binding is not being detected"
              % sorted({r["surface"] for r in known}))
        return 7
    if not surfaces.get("INTERNAL"):
        print("ABORT nothing landed in INTERNAL - the classifier is calling everything a route")
        return 7

    out = ["WHICH SURFACE SAYS IT IN ENGLISH bw302",
           "DENOMINATOR this census reads %d raises (only inside function bodies, and only where the "
           "detail is literal text); bw293 read 1187 because it also walks module level and lambdas "
           "and records details built at runtime. The two are not the same denominator and the "
           "residual has not been reconciled raise by raise - see "
           "trial/results/20261026_gozero/bw293-bare-english-refusals.txt:3" % len(rows),
           "ENGLISH SENTENCES %d split by surface: %s"
           % (len(english), ", ".join("%s=%d" % (k, surfaces[k]) for k in sorted(surfaces))),
           "ROUTE-REACHABLE SPLIT by how the binding was found: %s"
           % ", ".join("%s=%d" % (key, via_counts[key]) for key in sorted(via_counts)),
           "NAMED CONTROL %r -> %s at %s:%d via %s%s"
           % (KNOWN_SENTENCE, known[0]["surface"], known[0]["path"], known[0]["line"],
              known[0]["via"],
              (" (bound to %s)" % ", ".join(known[0]["routes"])) if known[0]["routes"] else
              (" - the helper itself has no decorator; its module carries %d routes, so no single URL "
               "is claimed for it" % known[0]["module_route_count"])),
           "ROUTE-REACHABLE ENGLISH SENTENCES BY FILE",
           ]
    by_file = {}
    for row in english:
        if row["surface"] == "ROUTE_REACHABLE":
            by_file.setdefault(row["path"], []).append(row)
    for path in sorted(by_file, key=lambda key: (-len(by_file[key]), key)):
        out.append("  %s  %d sentences on real routes" % (path, len(by_file[path])))
        for row in by_file[path][:8]:
            out.append("      %s:%d  in %s bound to %s | %s"
                       % (row["path"], row["line"], row["func"], "|".join(row["routes"])[:60],
                          row["text"][:70]))
    out.append("AGENT-SURFACE ENGLISH SENTENCES (the assistant walks these, not a traveller)")
    agent_rows = [r for r in english if r["surface"] == "AGENT_SURFACE"]
    for row in agent_rows[:10]:
        out.append("      %s:%d  in %s | %s" % (row["path"], row["line"], row["func"],
                                                row["text"][:70]))
    out.append("  AGENT_SURFACE total %d" % len(agent_rows))
    out.append("INTERNAL (no HTTP binding found on the holding function)")
    internal = [r for r in english if r["surface"] == "INTERNAL"]
    for row in internal[:10]:
        out.append("      %s:%d  in %s | %s" % (row["path"], row["line"], row["func"],
                                                row["text"][:70]))
    out.append("  INTERNAL total %d" % len(internal))
    out.append("COVERAGE_LIMIT the surface is decided inside one module: a helper called by a route in "
               "the same file counts as reachable (level same_module_has_routes), but a helper living "
               "in another module and called only from a route stays INTERNAL, and raises outside any "
               "function body are not enumerated. So INTERNAL is an upper bound on 'no traveller "
               "reaches it', not a proof.")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for row in out:
        print(row)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
