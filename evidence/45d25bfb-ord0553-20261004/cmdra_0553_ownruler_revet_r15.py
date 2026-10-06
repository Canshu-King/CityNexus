"""ORD-0553 r15 -- does the ruler this lane landed in r2 still hold on today's tip, and does it bite?

Two runs, one instrument:

  clean    the ruler is executed against a full export of the current authority tip, through a config that
           starts no server (the ruler reads five source files and starts nothing).
  mutant   the same ruler against a tree that differs in ONE line -- the en wording of EN_ROUTE put back to
           the enum's own printed form ("EN ROUTE"), which is the defect the ruler exists for.  A ruler that
           stays green here is a rubber stamp, so this run must fail.

Both trees are mine, in my directory, and `node_modules` is a junction into the repo's -- never copied, and
never removed recursively.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

R1 = r"D:/moodle/_qoder_cmdra_ord0553_20261003"
TIP_DIR = os.path.join(R1, "tipfull_b2fccfdf")
MUT_DIR = os.path.join(R1, "_r15_mutant")
NM = r"D:/moodle/CityNexus/frontend/node_modules"
CONFIG_SRC = os.path.join(R1, "cmdra_0553_r15_noserver.config.ts")
SPEC_REL = "frontend/e2e/qoder-45d25bfb-authoritative-status-vocabulary-r1.spec.ts"
READ_FILES = ["backend/app/schemas.py", "frontend/src/features/execution/V12StatePrimitives.tsx",
              "frontend/src/i18n/LocaleContext.tsx", "frontend/src/lib/displayVocabulary.ts",
              "frontend/src/features/execution/V12AuthoritativeJourneyPanel.tsx"]
NODE = r"C:/Program Files/nodejs/node.exe"
NPX = r"C:/Program Files/nodejs/npx.cmd"


def sh(cmd, cwd, timeout=900):
    p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", timeout=timeout, shell=isinstance(cmd, str))
    return p.returncode, (p.stdout or ""), (p.stderr or "")


def junction(link, target):
    if os.path.exists(link):
        return "exists"
    rc, out, err = sh('cmd /c mklink /J "%s" "%s"' % (link.replace("/", "\\"), target.replace("/", "\\")),
                      cwd=R1)
    return "made" if rc == 0 else "FAILED %s %s" % (out[-80:], err[-80:])


def build_mutant():
    if os.path.isdir(MUT_DIR):
        shutil.rmtree(MUT_DIR)  # my own scratch tree, contains no junction yet
    # package.json / tsconfig travel with the tree: without them the .ts spec is loaded as CJS and the
    # mutant never runs -- a red caused by the rig, which is exactly what this arm must not report.
    extra = ["frontend/package.json", "frontend/tsconfig.json"]
    for rel in READ_FILES + [SPEC_REL] + extra:
        src = os.path.join(TIP_DIR, rel.replace("/", os.sep))
        if not os.path.exists(src):
            if rel in extra:
                continue
            raise SystemExit("ABORT missing in the tip export: %s" % rel)
        dst = os.path.join(MUT_DIR, rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copyfile(src, dst)
    i18n = os.path.join(MUT_DIR, "frontend", "src", "i18n", "LocaleContext.tsx")
    text = io.open(i18n, encoding="utf-8").read()
    before = text
    text = text.replace('"exec.state.enRoute": "On the way"', '"exec.state.enRoute": "EN ROUTE"', 1)
    if text == before:
        raise SystemExit("ABORT the mutant could not be made: the en wording line was not found")
    io.open(i18n, "w", encoding="utf-8", newline="\n").write(text)
    os.makedirs(os.path.join(MUT_DIR, "frontend", "e2e"), exist_ok=True)
    return "one line changed: exec.state.enRoute en wording -> the enum's printed form"


def run_tree(root, tag, evidence_path):
    # The config has to live next to the junctioned node_modules: playwright resolves its own import
    # ("@playwright/test") from the config file's directory, and the export root has none.
    cfg = os.path.join(root, "frontend", "_r15_noserver.config.ts")
    shutil.copyfile(CONFIG_SRC, cfg)
    env = dict(os.environ)
    env["CMDRA_R15_ROOT"] = os.path.join(root, "frontend", "e2e")
    env["CMDRA_R15_OUT"] = os.path.join(root, "_r15_out")
    env["CITYNEXUS_STATUSQ_EVIDENCE"] = evidence_path
    env["CITYNEXUS_STATUSQ_RUN"] = tag
    env.pop("DEEPSEEK_API_KEY", None)
    env.pop("CITYNEXUS_AI_API_KEY", None)
    p = subprocess.run([NPX, "playwright", "test", "--config", cfg], cwd=os.path.join(root, "frontend"),
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=900, env=env)
    out = (p.stdout or "") + (p.stderr or "")
    passed = re.search(r"(\d+) passed", out)
    failed = re.search(r"(\d+) failed", out)
    return {"tag": tag, "rc": p.returncode, "passed": int(passed.group(1)) if passed else 0,
            "failed": int(failed.group(1)) if failed else 0, "tail": out[-700:],
            "evidence_written": os.path.exists(evidence_path)}


report = {"instrument": "cmdra_0553_ownruler_revet_r15",
          "node_modules_junctions": {}, "runs": [], "arms": []}
report["node_modules_junctions"]["tip_export"] = junction(os.path.join(TIP_DIR, "frontend", "node_modules"), NM)
report["mutant_note"] = build_mutant()
report["node_modules_junctions"]["mutant"] = junction(os.path.join(MUT_DIR, "frontend", "node_modules"), NM)

clean = run_tree(TIP_DIR, "clean-at-tip", os.path.join(R1, "_evidence", "r15_ruler_at_tip.json"))
mut = run_tree(MUT_DIR, "mutant-enum-wording", os.path.join(R1, "_evidence", "r15_ruler_mutant.json"))
report["runs"] = [clean, mut]


def arm(ident, ok, observed):
    report["arms"].append({"id": ident, "verdict": "PASS" if ok else "FAIL", "observed": observed})


arm("the_landed_ruler_still_passes_on_todays_tip",
    clean["rc"] == 0 and clean["passed"] >= 4 and clean["failed"] == 0,
    "clean run: rc=%s passed=%s failed=%s" % (clean["rc"], clean["passed"], clean["failed"]))
arm("the_ruler_goes_red_when_the_wording_is_put_back_to_the_enum",
    mut["rc"] != 0 and mut["failed"] >= 1,
    "mutant run: rc=%s passed=%s failed=%s" % (mut["rc"], mut["passed"], mut["failed"]))
arm("both_runs_actually_read_a_live_surface",
    clean["evidence_written"] and mut["evidence_written"],
    "each run wrote its own reading file: clean=%s mutant=%s" % (
        clean["evidence_written"], mut["evidence_written"]))

red = [a["id"] for a in report["arms"] if a["verdict"] == "FAIL"]
report["verdict"] = "GREEN" if not red else "RED"
report["red_arms"] = red
path = os.path.join(R1, "_evidence", "r15_ownruler_revet.json")
io.open(path, "w", encoding="utf-8").write(json.dumps(report, ensure_ascii=False, indent=1))
print(json.dumps({k: report[k] for k in ("verdict", "red_arms", "arms", "node_modules_junctions")},
                 ensure_ascii=False, indent=1))
print("clean tail:", clean["tail"][-260:].replace("\n", " | "))
print("mutant tail:", mut["tail"][-260:].replace("\n", " | "))
print("WROTE", path)
