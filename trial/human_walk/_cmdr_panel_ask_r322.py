"""bw322: from "the frontend asks" to "a panel the traveller can open asks" - the gap §14.33 left open.

bw318 proved a hand-written frontend file builds each of these paths, but most of those files are
frontend/src/api/citynexus.ts, the shared API layer: naming it says nothing about a screen.  This ruler
walks one more hop - the function that builds the path, who imports or calls that function, and whether
that caller is a panel the registry mounts - and keeps five answers apart:

  ON_A_MOUNTED_PANEL   the registry imports and renders a component that builds or uses the function
  USED_BY_APP_SHELL    only a file under app/ uses it and the registry renders none of them
  USED_OFF_PANEL       a component uses it, but the registry never imports and renders that component
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
NAMED_IMPORT = re.compile(r"""import\s*\{([^}]*)\}\s*from\s*["']([^"']+)["']""")
LAZY_IMPORT = re.compile(r"""import\(\s*["']([^"']+)["']\s*\)""")
JSX_TAG = re.compile(r"<\s*([A-Z]\w*)")
FUNCTION_ROW = re.compile(
    r"^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)"                      # named function
    r"|^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s*)?\([^)]*\)\s*(?::[^=]*)?=>"
    r"|^\s{2,}(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::[^{]*)?\{\s*$"           # method signature
    r"|^\s{2,}(\w+)\s*:\s*(?:async\s*)?\([^)]*\)\s*=>")                      # arrow method


def module_key(rel):
    """frontend/src/features/execution/LiveRecovery.tsx -> features/execution/LiveRecovery."""
    return rel.split("src/", 1)[-1].rsplit(".", 1)[0]


def registry_panels(registry):
    """Module paths the registry both imports and renders as a component - as opposed to ones it only
    names in prose, or imports as a helper.

    v1 substring-matched the whole registry source and so counted app/V8Experience.tsx, which appears
    only inside a docstring, as a mounted panel.  v2 required any import edge, which then would have
    called the shared api layer a panel too.  Both filters are needed: the module must arrive through an
    import and leave through JSX, which is what a traveller can actually be shown.
    """
    names_by_module = {}

    def bind(spec, name):
        if not spec.startswith("."):
            return
        resolved = os.path.normpath(os.path.join("frontend/src/app", spec)).replace("\\", "/")
        if resolved.startswith("frontend/src/"):
            names_by_module.setdefault(resolved.split("src/", 1)[-1], set()).add(name)

    for group, spec in NAMED_IMPORT.findall(registry):
        for cell in group.split(","):
            local = cell.split(" as ")[-1].strip()
            if local:
                bind(spec, local)
    for spec in LAZY_IMPORT.findall(registry):
        bind(spec, spec.rsplit("/", 1)[-1])
    rendered = set(JSX_TAG.findall(registry))
    mounted = {key for key, names in names_by_module.items() if names & rendered}
    return mounted, names_by_module, rendered


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
    mounted_keys, imported_modules, rendered_tags = registry_panels(registry)
    if not mounted_keys:
        raise SystemExit("ABORT the registry produced no imported-and-rendered module, so every row "
                         "would read off-panel - the mount test is broken, not the code")
    rows = caller_rows()
    out = ["WHICH PANEL ASKS bw322",
           "SAME-SOURCE CHECK caller rows read from bw318 = %d, matching its published TALLY "
           "caller_found=%d (total %d)" % (len(rows), published["caller"], published["total"])]
    if len(rows) != published["caller"]:
        out.append("ABORT %d caller rows against a published caller_found of %d"
                   % (len(rows), published["caller"]))
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 7

    counts = {"ON_A_MOUNTED_PANEL": 0, "USED_BY_APP_SHELL": 0, "USED_OFF_PANEL": 0,
              "SHARED_API_ONLY": 0, "NO_USER_FOUND": 0}
    seen_names = []
    rows_by_file = {}
    keys_considered = set()
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
        # the shared api layer is a legitimate user but says nothing about a screen, and the registry is
        # the mount table rather than a screen of its own, so neither is tested as a panel candidate
        panel_candidates = [item for item in users
                            if not item[0].startswith("frontend/src/api/") and item[0] != REGISTRY_REL]
        keys_considered |= {module_key(rel) for rel, _ in panel_candidates}
        keys_considered.add(module_key(row["file"]))
        mounted = [item for item in panel_candidates if module_key(item[0]) in mounted_keys]
        # a row whose building file is itself a registry-rendered component needs no importer to prove
        # a screen: the component is what the traveller is shown
        self_mounted = module_key(row["file"]) in mounted_keys
        shell = [item for item in panel_candidates if item[0].startswith("frontend/src/app/")]
        if mounted or self_mounted:
            verdict = "ON_A_MOUNTED_PANEL"
            for rel in ([row["file"]] if self_mounted else []) + [r for r, _ in mounted]:
                rows_by_file[rel] = rows_by_file.get(rel, 0) + 1
        elif shell:
            verdict = "USED_BY_APP_SHELL"
        elif panel_candidates:
            verdict = "USED_OFF_PANEL"
        elif users:
            verdict = "SHARED_API_ONLY"
        else:
            verdict = "NO_USER_FOUND"
        counts[verdict] += 1
        out.append("%2d. %s  函数 %s（%s:%d）→ %s，使用者 %d 处（其中可成面板的 %d 处）%s"
                   % (row["rank"], row["url"], name, row["file"], row["line"], verdict, len(users),
                      len(panel_candidates),
                      "；此行构建的文件本身就被注册表渲染" if self_mounted else ""))
        shown = ([(row["file"], row["line"])] if self_mounted else []) + (mounted or users)
        for rel, line_no in shown[:2]:
            out.append("      %s:%d%s" % (rel, line_no,
                                          "  ← 注册表 import 并渲染此模块"
                                          if module_key(rel) in mounted_keys else ""))
    out.append("TALLY on_a_mounted_panel=%d used_by_app_shell=%d used_off_panel=%d "
               "shared_api_only=%d no_user_found=%d rows=%d"
               % (counts["ON_A_MOUNTED_PANEL"], counts["USED_BY_APP_SHELL"], counts["USED_OFF_PANEL"],
                  counts["SHARED_API_ONLY"], counts["NO_USER_FOUND"], len(rows)))
    if sum(counts.values()) != len(rows):
        out.append("ABORT the verdicts do not cover every row")
        io.open(RECEIPT, "w", encoding="utf-8", newline="\n").write("\n".join(out) + "\n")
        return 8
    top = sorted(rows_by_file.items(), key=lambda item: -item[1])
    out.append("MOUNTED_CONCENTRATION %d mounted rows rest on %d distinct file(s): %s - "
               "read the screens off this line, not off the row count"
               % (counts["ON_A_MOUNTED_PANEL"], len(top),
                  ", ".join("%s=%d" % (rel, hits) for rel, hits in top)))
    not_rendered = sorted(key for key in imported_modules if key not in mounted_keys)
    comment_only = sorted(key for key in keys_considered
                          if key not in mounted_keys and key in registry)
    out.append("MOUNT_TABLE the registry imports %d module(s) and renders %d of them as a component: %s"
               % (len(imported_modules), len(mounted_keys), ", ".join(sorted(mounted_keys))))
    out.append("REGISTRY_MATCH %d module(s) are imported but never rendered (%s) and %d module name(s) "
               "our rows touch appear in the registry text without an import edge (%s); neither counts as "
               "a panel - v1 counted the second kind, v2 would have counted the first"
               % (len(not_rendered), ", ".join(not_rendered) or "none", len(comment_only),
                  ", ".join(comment_only) or "none"))
    out.append("REVISION this ruler was published three times and the count moved: v1 called any text in "
               "the registry a mount and read 16, v2 required an import edge but ignored components the "
               "registry renders themselves and read 12, this one requires import plus JSX and also "
               "accepts a building file that is itself mounted, reading %d. v1's receipt is committed at "
               "e329db4b2c; v2 never left the working tree. The moving number is the point: the answer "
               "depends on how strictly 'mounted panel' is defined, so the definition is printed above."
               % counts["ON_A_MOUNTED_PANEL"])
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
                "function name as a whole word; the api layer and the registry itself are users but not "
                "screens; a file is on a panel only when the registry both imports its module path and "
                "renders it as a JSX component; a row whose own building file passes that test is "
                "mounted without needing an importer; a user under app/ that fails the test is the shell")
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
