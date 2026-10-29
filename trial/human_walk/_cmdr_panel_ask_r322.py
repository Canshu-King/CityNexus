"""bw322: from "the frontend asks" to "a panel the traveller can open asks" - the gap §14.33 left open.

bw318 proved a hand-written frontend file builds each of these paths, but most of those files are
frontend/src/api/citynexus.ts, the shared API layer: naming it says nothing about a screen.  This ruler
walks one more hop - the function that builds the path, who imports or calls that function, and whether
that caller is a panel the registry mounts - and keeps three answers apart:

  ON_A_MOUNTED_PANEL   some file that uses the function is referenced by app/v8PanelRegistry.tsx
  USED_OFF_PANEL       a component uses it, but the registry never mentions that component
  SHARED_API_ONLY      only the shared api layer mentions the function - no component yet
  NO_USER_FOUND        nothing outside the defining file mentions the function

Rows come from bw318 through that ruler's own regex, and the row count must equal bw318's published
caller_found, so this cannot quietly describe a different set than the ruler above it.
"""

import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "trial", "human_walk"))

import _cmdr_button_reachability_r318 as reach  # noqa: E402
import _cmdr_write_block_366_r320 as writer  # noqa: E402  (owns the row regex bw318's rows are read with)

BW318 = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                     "bw318-which-of-these-has-a-button.txt")
RECEIPT = os.path.join(ROOT, "trial", "results", "20261026_gozero",
                       "bw322-which-panel-asks.txt")
REGISTRY_REL = "frontend/src/app/v8PanelRegistry.tsx"
FUNCTION_ROW = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)"                      # named function
    r"|^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::[^=]*)?=>"
    r"|^\s{2,}(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::[^{]*)?\{\s*$"           # method signature
    r"|^\s{2,}(\w+)\s*:\s*(?:async\s*)?\([^)]*\)\s*=>")                      # arrow method


def tally():
    text = io.open(BW318, encoding="utf-8", errors="replace").read()
    match = re.search(r"TALLY caller_found=(\d+) no_caller=(\d+) total=(\d+)", text)
    if not match:
        raise SystemExit("ABORT bw318 publishes no readable TALLY")
    return dict(zip(("caller", "none", "total"), (int(value) for value in match.groups())))


def caller_rows():
    lines = io.open(BW318, encoding="utf-8", errors="replace").read().split("\n")
    rows = []
    for index, line in enumerate(lines):
        match = writer.ROW.match(line)
        if not match or not match.group(5).startswith("CALLER_FOUND"):
            continue
        following = next((row for row in lines[index + 1:index + 5]
                          if re.search(r"frontend/\S+?:\d+", row)), "")
        found = re.search(r"(frontend/\S+?):(\d+)", following)
        if not found:
            raise SystemExit("ABORT row %s claims a caller but no coordinate is readable"
                             % match.group(1))
        rows.append({"rank": int(match.group(1)), "url": match.group(2),
                     "backend": match.group(3), "terms": match.group(4),
                     "file": found.group(1), "line": int(found.group(2))})
    return rows


def function_at(files, rel, line):
    text = dict(files).get(rel)
    if text is None:
        raise SystemExit("ABORT the caller file is not in the scanned set: %s" % rel)
    rows = text.split("\n")
    for index in range(min(line, len(rows)) - 1, -1, -1):
        match = FUNCTION_ROW.match(rows[index])
        if match:
            return next(group for group in match.groups() if group)
    return ""


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    published = tally()
    files = list(reach.source_files())
    prepared = [(rel, text, text.split("\n")) for rel, text in files]
    registry = dict(files).get(REGISTRY_REL)
    if registry is None:
        raise SystemExit("ABORT the panel registry is not in the scanned set")
    rows = caller_rows()
    out = ["WHICH PANEL ASKS bw322",
           "SAME-SOURCE CHECK caller rows read from bw318 = %d, matching its published TALLY "
           "caller_found=%d (total %d)" % (len(rows), published["caller"], published["total"])]
    if len(rows) != published["caller"]:
        out.append("ABORT %d caller rows against a published caller_found of %d"
                   % (len(rows), published["caller"]))
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 7

    counts = {"ON_A_MOUNTED_PANEL": 0, "USED_OFF_PANEL": 0, "SHARED_API_ONLY": 0,
              "NO_USER_FOUND": 0}
    seen_names = []
    for row in rows:
        name = function_at(files, row["file"], row["line"])
        if name:
            seen_names.append(name)
        if not name:
            out.append("%2d. %s  (caller %s:%d) NO_FUNCTION_AROUND_THIS_LINE"
                       % (row["rank"], row["url"], row["file"], row["line"]))
            counts["NO_USER_FOUND"] += 1
            continue
        pattern = re.compile(r"\b%s\b" % re.escape(name))
        users = []
        for rel, text, rows_of_file in prepared:
            if rel == row["file"] or not pattern.search(text):
                continue
            users.append((rel, next((index + 1 for index, cell in enumerate(rows_of_file)
                                     if pattern.search(cell)), 0)))
        # the shared api layer is a legitimate user but says nothing about a screen: only files that
        # could be a panel are tested against the registry, and the registry is matched on the module
        # path (features/execution/LiveRecovery), not a bare word that comments could also carry
        panel_candidates = [item for item in users if not item[0].startswith("frontend/src/api/")]
        mounted = [item for item in panel_candidates
                   if item[0].split("src/", 1)[-1].rsplit(".", 1)[0] in registry]
        if mounted:
            verdict = "ON_A_MOUNTED_PANEL"
        elif panel_candidates:
            verdict = "USED_OFF_PANEL"
        elif users:
            verdict = "SHARED_API_ONLY"
        else:
            verdict = "NO_USER_FOUND"
        counts[verdict] += 1
        out.append("%2d. %s  函数 %s（%s:%d）→ %s，使用者 %d 处（其中可成面板的 %d 处）"
                   % (row["rank"], row["url"], name, row["file"], row["line"], verdict, len(users),
                      len(panel_candidates)))
        shown = mounted if mounted else users
        for rel, line_no in shown[:2]:
            out.append("      %s:%d%s" % (rel, line_no,
                                          "  ← 注册表引用此文件" if rel in [m[0] for m in mounted]
                                          else ""))
    out.append("TALLY on_a_mounted_panel=%d used_off_panel=%d shared_api_only=%d no_user_found=%d "
               "rows=%d"
               % (counts["ON_A_MOUNTED_PANEL"], counts["USED_OFF_PANEL"], counts["SHARED_API_ONLY"],
                  counts["NO_USER_FOUND"], len(rows)))
    if sum(counts.values()) != len(rows):
        out.append("ABORT the verdicts do not cover every row")
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 8
    most = max(seen_names, key=seen_names.count) if seen_names else ""
    repeated = seen_names.count(most) if seen_names else 0
    out.append("NAME_UNIQUENESS %d of %d resolved rows name %r - %s"
               % (repeated, len(seen_names), most,
                  "SUSPECT: the ruler matched an enclosing object rather than the method, so the "
                  "panel verdicts above cannot be trusted until this is fixed"
                  if seen_names and repeated * 2 > len(seen_names)
                  else "the rows name distinct callables, so a panel verdict rides on a real function"))
    out.append("REGISTRY %s read from the same scan as bw318 (%d frontend files)"
               % (REGISTRY_REL, len(files)))
    probe = [rel for rel, text in files if re.search(r"\b__cmdr_no_such_function__\b", text)]
    out.append("NEGATIVE_CONTROL the same whole-word search run against a name nobody defines "
               "returns %d files (%s)"
               % (len(probe), "CLEAN - the ruler does not invent users" if not probe
                  else "the ruler matched, which is wrong"))
    out.append("COUNTING_RULE a user is a scanned file other than the defining file that mentions the "
                "function name as a whole word; only non-api users are tested against the registry, and "
                "a file counts as mounted when its module path appears in the registry source")
    out.append("COVERAGE_LIMIT a registry entry is not proof a traveller opens that panel, and a "
                "whole-word mention is not proof of a call - comments and re-exports count. "
                "This narrows which screens could show the sentence; it does not replace walking one.")
    io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
    for line in out:
        print(line)
    print("WROTE %s" % RECEIPT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
