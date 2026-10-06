"""ORD-0553 r19 -- re-bind: the authority tip moved, so say which of my readings still hold and which are stale.

This lane's blocks all pinned one generation (b2fccfdf...).  The tip has moved to a new sha, and two of the
files my readings cite changed with it.  Rather than let a stale reading look current, this instrument:

  * reads the live tip and records the new pin;
  * for every file my recent blocks cite, compares old-pin blob to new-tip blob (equality is a fact, not
    an inference);
  * re-runs the r16 key-reference scan at the new tip (the four `exec.mark*` keys);
  * re-runs the r17-style reachability graph at the new tip, from the app entry, on a fresh export of the
    new tree -- because the graph's answer depends on files that moved;
  * re-runs the r2 status-vocabulary ruler (this lane's own landed gate) at the new tip, with no server;
  * names, explicitly, which earlier readings are bound to the old generation's *runtime* (screen walks,
    censuses) and are therefore NOT re-measured here.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"
REFS = r"D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
REPO = r"D:/moodle/CityNexus"
OLD = io.open(os.path.join(R1, "_tip_r11.txt"), encoding="utf-8").read().strip()
NPX = r"C:/Program Files/nodejs/npx.cmd"
NM = r"D:/moodle/CityNexus/frontend/node_modules"
EXPORT = os.path.join(R1, "tipfull_r19")
CONFIG_SRC = os.path.join(R1, "cmdra_0553_r15_noserver.config.ts")
CITED = [
    "backend/app/main.py", "backend/app/schemas.py", "backend/app/demo_scene.py",
    "frontend/src/i18n/LocaleContext.tsx", "frontend/src/lib/displayVocabulary.ts",
    "frontend/src/features/execution/V12StatePrimitives.tsx",
    "frontend/src/features/execution/V12AuthoritativeJourneyPanel.tsx",
    "frontend/src/features/studio/V12TripStudioPanel.tsx",
    "frontend/src/main.tsx", "frontend/src/app/V8Experience.tsx",
    "frontend/e2e/v13-authoritative-integrity.spec.ts",
    "frontend/e2e/qoder-45d25bfb-authoritative-status-vocabulary-r1.spec.ts",
]
KEYS = ["exec.markEnRoute", "exec.markArrived", "exec.markInProgress", "exec.markCompleted"]


def sh(cmd, cwd, timeout=900, shell=False):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, shell=shell)
    return p.returncode, (p.stdout or ""), (p.stderr or "")


report = {"instrument": "cmdra_0553_rebind_r19", "old_pin": OLD, "new_pin": None,
          "cited_files": {}, "mark_key_refs_at_new_tip": {}, "reachability_at_new_tip": {},
          "own_ruler_at_new_tip": {}, "stale_by_generation": [], "arms": []}

rc, out, _err = sh(["git", "-C", REPO, "ls-remote", "origin",
                    "refs/heads/mirror/integration-frontend-apple-pass1"], cwd=R1, timeout=180)
live = out.split()[0] if rc == 0 and out.split() else None
report["new_pin"] = live
if not live or len(live) != 40:
    raise SystemExit("ABORT cannot read the live tip; refusing to re-bind on a guess")
if live == OLD:
    raise SystemExit("ABORT the tip has not moved -- re-binding is not this round's work")
rc, _o, _e = sh(["git", "-C", REPO, "fetch", "origin",
                 "refs/heads/mirror/integration-frontend-apple-pass1"], cwd=R1, timeout=600)
rc, out, _e = sh(["git", "-C", REPO, "cat-file", "-t", live], cwd=R1, timeout=60)
if (out or "").strip() != "commit":
    raise SystemExit("ABORT the new tip is not in the local object store; refusing to read it from a guess")

for f in CITED:
    rc, a, _e = sh(["git", "-C", REPO, "rev-parse", "%s:%s" % (OLD, f)], cwd=R1, timeout=60)
    rc2, b, _e = sh(["git", "-C", REPO, "rev-parse", "%s:%s" % (live, f)], cwd=R1, timeout=60)
    a, b = a.strip(), b.strip()
    report["cited_files"][f] = {"old": a, "new": b, "same": bool(a) and a == b}

for k in KEYS:
    rc, out, _e = sh(["git", "-C", REPO, "grep", "-n", '"%s"' % k, live, "--", "frontend/src"],
                     cwd=R1, timeout=300)
    hits = [l for l in out.splitlines() if "i18n/LocaleContext.tsx" not in l]
    report["mark_key_refs_at_new_tip"][k] = {"refs_outside_dictionary": len(hits),
                                             "sites": [l.split(":", 1)[0] for l in hits][:3]}

# fresh export of the new tree (only what the graph and the ruler read; optional files are dropped if the
# new tip does not carry them -- a pathspec that matches nothing aborts the whole archive)
WANT = ["backend/app/schemas.py", "frontend/src", "frontend/e2e", "frontend/package.json", "frontend/tsconfig.json"]
present = []
for p in WANT:
    rc, out, _e = sh(["git", "-C", REPO, "cat-file", "-e", "%s:%s" % (live, p)], cwd=R1, timeout=60)
    if rc == 0:
        present.append(p)
report["exported_paths"] = present
if os.path.isdir(EXPORT):
    shutil.rmtree(EXPORT)
os.makedirs(EXPORT)
rc, out, err = sh('git -C "%s" archive %s %s | tar -x -C "%s"'
                  % (REPO.replace("\\", "/"), live, " ".join(present), EXPORT.replace("\\", "/")),
                  cwd=R1, timeout=900, shell=True)
if rc != 0 or not os.path.exists(os.path.join(EXPORT, "backend", "app", "schemas.py")):
    raise SystemExit("ABORT export of the new tip failed: %s" % err[-200:])

# r17-style graph at the new tip: are the two fallback-calling components still only stories-imported?
SRC = os.path.join(EXPORT, "frontend", "src")
ENTRY = os.path.join(SRC, "main.tsx")
graph, real = {}, {}
for root, _d, names in os.walk(SRC):
    for n in names:
        if n.endswith((".ts", ".tsx")):
            p = os.path.join(root, n)
            real[os.path.normcase(p)] = p
            t = io.open(p, encoding="utf-8", errors="replace").read()
            deps = set()
            for m in re.finditer(r'(?:from\s+|import\()"(\.[^"]+)"', t):
                tgt = os.path.normpath(os.path.join(os.path.dirname(p), m.group(1)))
                for cand in (tgt + ".tsx", tgt + ".ts", tgt + os.sep + "index.ts", tgt + os.sep + "index.tsx"):
                    if os.path.exists(cand):
                        deps.add(os.path.normcase(cand))
                        break
            graph[os.path.normcase(p)] = deps
seen, stack = set(), [os.path.normcase(ENTRY)]
while stack:
    cur = stack.pop()
    if cur not in seen:
        seen.add(cur)
        stack.extend(graph.get(cur, ()))
reachable = {os.path.relpath(real[k], EXPORT).replace("\\", "/") for k in seen if k in real}
imp = {}
for root, _d, names in os.walk(SRC):
    for n in names:
        if not n.endswith((".ts", ".tsx")):
            continue
        p = os.path.join(root, n)
        t = io.open(p, encoding="utf-8", errors="replace").read()
        for m in re.finditer(r'import\s*\{([^}]*)\}\s*from\s*"([^"]*V12StatePrimitives)"', t):
            taken = [x.strip() for x in m.group(1).split(",") if x.strip()]
            rel = os.path.relpath(p, EXPORT).replace("\\", "/")
            imp[rel] = {"names": taken, "reachable": rel in reachable}
report["reachability_at_new_tip"] = {
    "files_reachable": len(reachable),
    "shell_reachable": "frontend/src/app/V8Experience.tsx" in reachable,
    "importers_of_the_state_primitives_module": imp,
    "ActivityCard_imported_by_reachable_file": any(
        "ActivityCard" in v["names"] and v["reachable"] for v in imp.values()),
    "LiveJourney_imported_by_reachable_file": any(
        "LiveJourney" in v["names"] and v["reachable"] for v in imp.values()),
}

# this lane's own landed ruler, at the new tip, with no server
link = os.path.join(EXPORT, "frontend", "node_modules")
if not os.path.exists(link):
    sh('cmd /c mklink /J "%s" "%s"' % (link.replace("/", "\\"), NM.replace("/", "\\")), cwd=R1, timeout=120, shell=True)
cfg = os.path.join(EXPORT, "frontend", "_r19_noserver.config.ts")
shutil.copyfile(CONFIG_SRC, cfg)
ev = os.path.join(R1, "_evidence", "r19_own_ruler_at_new_tip.json")
env = dict(os.environ)
env["CMDRA_R15_ROOT"] = os.path.join(EXPORT, "frontend", "e2e")
env["CMDRA_R15_OUT"] = os.path.join(EXPORT, "_r19_out")
env["CITYNEXUS_STATUSQ_EVIDENCE"] = ev
env["CITYNEXUS_STATUSQ_RUN"] = "r19-new-tip"
for k in ("DEEPSEEK_API_KEY", "CITYNEXUS_AI_API_KEY"):
    env.pop(k, None)
p = subprocess.run([NPX, "playwright", "test", "--config", cfg], cwd=os.path.join(EXPORT, "frontend"),
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, env=env)
out = (p.stdout or "") + (p.stderr or "")
mp = re.search(r"(\d+) passed", out)
mf = re.search(r"(\d+) failed", out)
report["own_ruler_at_new_tip"] = {"rc": p.returncode, "passed": int(mp.group(1)) if mp else 0,
                                  "failed": int(mf.group(1)) if mf else 0,
                                  "evidence_written": os.path.exists(ev)}
report["stale_by_generation"] = [
    "r11 census and r13 screen walks: runtime readings taken against the previous generation's bundle "
    "(entry index-DLbc3Q3N.js); this round does NOT re-walk them, so they speak for the old pin only",
]

# the three copy-words another lane reworded between the two pins: old value, new value, and whether the
# old value's words were in the old census's token table (so that table no longer describes the tip)
REWORDED = ["bookings.stayEvidence", "inbox.multimodal", "inbox.authoritativeMemory"]


def value_at(sha, key):
    rc, out, _e = sh(["git", "-C", REPO, "show", "%s:frontend/src/i18n/LocaleContext.tsx" % sha],
                     cwd=R1, timeout=300)
    m = re.search(r'"%s":\s*"([^"]*)"' % re.escape(key), out)
    return m.group(1) if m else None


walk = json.load(io.open(os.path.join(R1, "_evidence", "r11_walk_en_49881.json"), encoding="utf-8"))
old_tokens = set()
for _route, v in walk["perRoute"].items():
    for h in v.get("hits", []):
        if h.get("token"):
            old_tokens.add(h["token"])
report["reworded_copy_words"] = []
for key in REWORDED:
    ov, nv = value_at(OLD, key), value_at(live, key)
    report["reworded_copy_words"].append({
        "key": key, "old_value": ov, "new_value": nv, "changed": ov != nv,
        "old_value_words_in_old_census": sorted({w for w in re.findall(r"[A-Z]{4,}", ov or "")
                                                 if w in old_tokens}),
    })
report["own_census_token_table_is_stale_for"] = [k["key"] for k in report["reworded_copy_words"]
                                                 if k["changed"]]


def arm(ident, ok, observed):
    report["arms"].append({"id": ident, "verdict": "PASS" if ok else "FAIL", "observed": observed})


unchanged = [f for f, v in report["cited_files"].items() if v["same"]]
changed = [f for f, v in report["cited_files"].items() if not v["same"]]
arm("the_rebind_runs_on_a_sha_that_exists_locally", live != OLD and bool(live),
    "old pin %s -> new pin %s" % (OLD[:12], live[:12]))
arm("the_cited_file_table_names_what_moved", len(changed) >= 1 and len(unchanged) >= 1,
    "unchanged %d, changed %d: %s" % (len(unchanged), len(changed), json.dumps(changed, ensure_ascii=False)))
arm("the_four_mark_keys_keep_their_reference_shape",
    [report["mark_key_refs_at_new_tip"][k]["refs_outside_dictionary"] for k in KEYS] == [0, 0, 1, 0],
    json.dumps({k: report["mark_key_refs_at_new_tip"][k]["refs_outside_dictionary"] for k in KEYS}))
arm("the_reachability_graph_at_the_new_tip_still_sees_the_shell",
    report["reachability_at_new_tip"]["shell_reachable"],
    "%d files reachable; shell reachable=%s" % (report["reachability_at_new_tip"]["files_reachable"],
                                                report["reachability_at_new_tip"]["shell_reachable"]))
arm("the_two_fallback_components_are_still_stories_only",
    not report["reachability_at_new_tip"]["ActivityCard_imported_by_reachable_file"]
    and not report["reachability_at_new_tip"]["LiveJourney_imported_by_reachable_file"],
    "importers %s" % json.dumps(report["reachability_at_new_tip"]["importers_of_the_state_primitives_module"],
                                ensure_ascii=False)[:300])
arm("my_own_landed_ruler_is_still_green_at_the_new_tip",
    report["own_ruler_at_new_tip"]["rc"] == 0 and report["own_ruler_at_new_tip"]["failed"] == 0
    and report["own_ruler_at_new_tip"]["passed"] >= 4,
    "ruler at the new tip: rc=%s passed=%s failed=%s" % (
        report["own_ruler_at_new_tip"]["rc"], report["own_ruler_at_new_tip"]["passed"],
        report["own_ruler_at_new_tip"]["failed"]))
arm("the_reworded_copy_words_are_measured_against_the_old_census",
    all(k["changed"] for k in report["reworded_copy_words"]),
    "reworded by another lane between the two pins: %s" % json.dumps(
        {k["key"]: (k["old_value"], k["new_value"]) for k in report["reworded_copy_words"]},
        ensure_ascii=False))

red = [a["id"] for a in report["arms"] if a["verdict"] == "FAIL"]
report["verdict"] = "GREEN" if not red else "RED"
report["red_arms"] = red
path = os.path.join(R1, "_evidence", "r19_rebind.json")
io.open(path, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1))
print(json.dumps({k: report[k] for k in ("verdict", "red_arms", "arms", "old_pin", "new_pin",
                                         "reachability_at_new_tip", "own_ruler_at_new_tip",
                                         "stale_by_generation")}, ensure_ascii=False, indent=1))
print("changed files:", json.dumps(changed, ensure_ascii=False))
print("WROTE", path)
