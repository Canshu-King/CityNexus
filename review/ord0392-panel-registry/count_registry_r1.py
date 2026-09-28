#!/usr/bin/env python
"""ORD-0392 · the two cells the commander asked for, computed by one command against any rev.

  table entries      -- how many mount declarations the registry holds, per surface and in total
  shell traversals   -- how many times the shell still has to be opened to render a panel
                        (`renderPanels(` call sites), plus what it still mounts itself

Reads `git show <rev>:<path>`, so the identical command runs against the authority line, against the
previous candidate and against this one, with no working-tree state involved.

Line by line, comment lines dropped.  An earlier cut of this instrument counted the phrase inside an
explanatory comment and a `route === "agent"` ternary argument, and reported two leftover route
mounts in a shell that holds none -- which is the difference between a measurement and a guess.
"""
import re
import subprocess
import sys

REG = "frontend/src/app/v8PanelRegistry.tsx"
SHELL = "frontend/src/app/V8Experience.tsx"
TABLES = ("routePanels", "tripsTabPanels", "authoritativePanels", "hubAnchorPanels")
NL = chr(10)
COMMENT = re.compile(r"^\s*(//|/\*|\*)")
ROUTE_IF = re.compile(r'\{route === "[^"]+" &&')
DIRECT_MOUNT = re.compile(r"^\s{4,12}<[A-Z]\w*(Panel|Workbench|Composer|Scanner|Explorer"
                          r"|Recovery|Comparison|Detail|Itinerary)\b")


def show(rev, path):
    r = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else None


def analyse(rev):
    reg = show(rev, REG)
    shell = show(rev, SHELL)
    out = {"rev": rev, "registry_exists": reg is not None, "tables": {}, "total_entries": 0}
    if reg:
        marks = [(m.group(1), m.start()) for m in
                 re.finditer(r"export const (\w+): V8PanelEntry<[^>]+>\[\] =", reg)]
        for idx, (name, start) in enumerate(marks):
            stop = marks[idx + 1][1] if idx + 1 < len(marks) else len(reg)
            ids = re.findall(r'^\s{4}id:\s*"([^"]+)"', reg[start:stop], flags=re.M)
            out["tables"][name] = {"entries": len(ids), "ids": ids}
            out["total_entries"] += len(ids)
        for name in TABLES:
            out["tables"].setdefault(name, {"entries": 0, "ids": []})
    if shell:
        every = shell.split(NL)
        code = [(i + 1, l) for i, l in enumerate(every) if not COMMENT.match(l)]
        out["shell_traversals"] = sum(l.count("renderPanels(") for _n, l in code)
        out["shell_route_if_sites"] = [(n, l.strip()[:80]) for n, l in code if ROUTE_IF.search(l)]
        out["shell_route_ifs"] = len(out["shell_route_if_sites"])
        out["shell_direct_panel_sites"] = [(n, l.strip()[:70]) for n, l in code if DIRECT_MOUNT.match(l)]
        out["shell_direct_panel_mounts"] = len(out["shell_direct_panel_sites"])
        out["shell_lines"] = len(every)
    return out


if __name__ == "__main__":
    import json
    for rev in sys.argv[1:]:
        print(json.dumps(analyse(rev), ensure_ascii=False))
