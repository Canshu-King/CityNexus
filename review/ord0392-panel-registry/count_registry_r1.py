#!/usr/bin/env python
"""ORD-0392 · the two cells the commander asked for, computed by one command against any rev.

  table entries   -- how many mount declarations the registry actually holds, per surface
  shell traversals -- how many times the shell still has to be opened to render a panel
                     (`renderPanels(` call sites) and how many `{route === "…" && …}` blocks it
                     still holds of its own

Reads `git show <rev>:<path>`, so the same command runs against the line, against the previous
candidate and against this one without any working-tree state.
"""
import re
import subprocess
import sys

REG = "frontend/src/app/v8PanelRegistry.tsx"
SHELL = "frontend/src/app/V8Experience.tsx"
TABLES = ("routePanels", "tripsTabPanels", "authoritativePanels", "hubAnchorPanels")


def show(rev, path):
    r = subprocess.run(["git", "show", f"{rev}:{path}"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace")
    return r.stdout if r.returncode == 0 else None


def analyse(rev):
    reg = show(rev, REG)
    shell = show(rev, SHELL)
    out = {"rev": rev, "registry_exists": reg is not None, "tables": {}, "total_entries": 0}
    if reg:
        # split the file on the exported table declarations, then count `id:` entries inside each
        marks = [(m.group(1), m.start()) for m in
                 re.finditer(r"export const (\w+): V8PanelEntry<[^>]+>\[\] =", reg)]
        for idx, (name, start) in enumerate(marks):
            stop = marks[idx + 1][1] if idx + 1 < len(marks) else len(reg)
            body = reg[start:stop]
            ids = re.findall(r'^\s{4}id:\s*"([^"]+)"', body, flags=re.M)
            out["tables"][name] = {"entries": len(ids), "ids": ids}
            out["total_entries"] += len(ids)
        for name in TABLES:
            out["tables"].setdefault(name, {"entries": 0, "ids": []})
    if shell:
        out["shell_traversals"] = len(re.findall(r"renderPanels\(", shell))
        out["shell_route_ifs"] = len(re.findall(r'\{route === "', shell))
        out["shell_lines"] = shell.count("\n") + 1
        out["shell_direct_panel_mounts"] = len(
            re.findall(r"^\s{4,8}<([A-Z]\w+Panel|[A-Z]\w+Workbench|[A-Z]\w+Composer|"
                       r"StayExplorer|HotelsPanel|LiveRecovery|PlanComparison|ActivityDetail|"
                       r"TripItinerary|TwinPanel|ControlTowerPanel|PretripChecklistPanel|"
                       r"DestinationPreparationPanel|RealCityDiscoveryPanel|BookingArtifactScanner|"
                       r"JourneyInboxWorkbench|RecoveryRequiredPanel|V1[0-9]\w+Panel)\b",
                       shell, flags=re.M))
    return out


if __name__ == "__main__":
    import json
    for rev in sys.argv[1:]:
        print(json.dumps(analyse(rev), ensure_ascii=False))
