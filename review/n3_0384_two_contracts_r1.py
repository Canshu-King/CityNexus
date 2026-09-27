#!/usr/bin/env python3
"""ORD-0384 -- ask BOTH OpenAPI artifacts whether a field is declared, before calling it un-anchored.

The re-scoped order says an item may appear only if its field has a contract anchor. The repo carries two
artifacts that do not know about each other: the hand-written `contracts/openapi.yaml`, and the document
FastAPI generates from the routes at runtime. Reading only the first is exactly the mistake this order
was re-scoped because of -- concluding "the server cannot answer X" from one document. So this measures
each candidate field against both, and records where each answer came from.

The generated document is produced in-process from an export of the working tree's commit
(`git archive` + `app.openapi()`), not from the phone chain: :4781 answers `/openapi.json` with the SPA
shell and :4782 refuses with 401, and neither runs this commit anyway. No server is started, no database
is written -- the throwaway URL exists only so importing the app cannot reach a shared file.
"""
import hashlib
import io
import json
import os
import re
import subprocess
import sys

WT = r"D:/moodle/_qoder_n3_ord0357"
REPO = r"D:/moodle/CityNexus"
VENV_PY = os.path.join(REPO, ".venv", "Scripts", "python.exe")
HAND = os.path.join(WT, "contracts", "openapi.yaml")
EV = os.path.join(WT, "review", "evidence", "ord0384")
ROOT = r"D:/moodle/_qoder_n3_ord0384_openapi"
FIELDS = ["feasibility_failures", "requires_user_decision", "stay_budget", "selected_option_id",
          "reservations", "commitments", "offline_ready", "arrival_anchor", "departure_anchor",
          "active_plan"]


def sh(cmd, timeout=900, cwd=None, env=None):
    p = subprocess.run(cmd, shell=isinstance(cmd, str), capture_output=True, text=True,
                       errors="replace", timeout=timeout, cwd=cwd, env=env)
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def hand_property_line(name):
    lines = io.open(HAND, encoding="utf-8").read().splitlines()
    pat = re.compile(r"(^|[{,\s])" + re.escape(name) + r"\s*:")
    for n, line in enumerate(lines, 1):
        if pat.search(line):
            return n, line.strip()[:110]
    prose = [n for n, line in enumerate(lines, 1) if name in line]
    return None, {"prose_only_lines": prose[:10], "prose_only_count": len(prose)}


def generated_key_paths(doc, name):
    """Every JSON-pointer path at which `name` appears as an object KEY in the generated document."""
    hits = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in node.items():
                if k == name:
                    hits.append(path + "/" + k)
                walk(v, path + "/" + k)
        elif isinstance(node, list):
            for i, v in enumerate(node):
                walk(v, "%s/%d" % (path, i))

    walk(doc, "")
    return hits


def main():
    head = subprocess.run(["git", "-C", WT, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    if os.path.isdir(ROOT):
        sh(["cmd", "/c", "rmdir", "/s", "/q", ROOT.replace("/", "\\")])
    os.makedirs(ROOT, exist_ok=True)
    rc, err = sh('git -C "%s" archive %s backend data contracts tools scripts agent-mcp | tar -x -C "%s"'
                 % (REPO, head, ROOT))
    assert rc == 0 and os.path.isdir(os.path.join(ROOT, "backend", "app")), "archive failed: " + err[:200]
    env = dict(os.environ)
    for k in [k for k in list(env) if re.search(r"(API_KEY|AUTH_TOKEN|SECRET)$|^OPENAI_|^DEEPSEEK_", k)]:
        env.pop(k, None)
    env.update({"CITYNEXUS_AI_ENABLED": "false",
                "CITYNEXUS_DATABASE_URL": "sqlite:///" + os.path.join(ROOT, "throwaway_never_written.db").replace("\\", "/"),
                "PYTHONPATH": ROOT.replace("\\", "/"),
                "HTTP_PROXY": "", "HTTPS_PROXY": "", "NO_PROXY": "*"})
    script = ("import json,sys;sys.path.insert(0,r'%s\\backend');"
              "from app.main import app;"
              "io=open(r'%s','w',encoding='utf-8');io.write(json.dumps(app.openapi()));io.close();"
              "print('GENERATED_OK')") % (ROOT, os.path.join(ROOT, "generated_openapi.json"))
    rc, out = sh([VENV_PY, "-c", script], timeout=600, cwd=os.path.join(ROOT, "backend"), env=env)
    gpath = os.path.join(ROOT, "generated_openapi.json")
    assert rc == 0 and os.path.isfile(gpath), "app.openapi() failed: " + out[-400:]
    gbytes = io.open(gpath, "rb").read()
    doc = json.loads(gbytes.decode("utf-8"))
    io.open(os.path.join(EV, "generated_openapi.json"), "wb").write(gbytes)

    rows = []
    for f in FIELDS:
        hl, hd = hand_property_line(f)
        paths = generated_key_paths(doc, f)
        rows.append({"field": f,
                     "hand_declared": hl is not None, "hand_line": hl, "hand_declaration": hd,
                     "generated_declared": len(paths) > 0,
                     "generated_paths": paths[:6], "generated_path_count": len(paths)})
    hand_yes = [r["field"] for r in rows if r["hand_declared"]]
    gen_yes = [r["field"] for r in rows if r["generated_declared"]]
    out = {"generated_by": os.path.basename(__file__), "order": "ORD-0384", "commit": head,
           "hand_contract_sha256": hashlib.sha256(io.open(HAND, "rb").read()).hexdigest(),
           "generated_bytes": len(gbytes),
           "generated_sha256": hashlib.sha256(gbytes).hexdigest(),
           "generated_saved_as": "review/evidence/ord0384/generated_openapi.json",
           "generated_path_count_total": len((doc.get("paths") or {})),
           "fields": rows,
           "declared_in_hand": hand_yes, "declared_in_generated": gen_yes,
           "declared_in_either": sorted(set(hand_yes) | set(gen_yes)),
           "declared_in_neither": sorted(set(FIELDS) - set(hand_yes) - set(gen_yes))}
    p = os.path.join(EV, "two_contracts_r1.json")
    io.open(p, "w", encoding="utf-8").write(json.dumps(out, ensure_ascii=False, indent=1) + "\n")
    for r in rows:
        print("%-24s hand=%-5s %-6s generated=%-5s %s" % (
            r["field"], r["hand_declared"], "L%s" % r["hand_line"] if r["hand_line"] else "-",
            r["generated_declared"], (r["generated_paths"][0][:66] if r["generated_paths"] else "")))
    print("declared in either: %s" % ", ".join(out["declared_in_either"]))
    print("declared in neither: %s" % ", ".join(out["declared_in_neither"]))
    print("READING " + p.replace("\\", "/"))
    sh(["cmd", "/c", "rmdir", "/s", "/q", ROOT.replace("/", "\\")])
    return 0


if __name__ == "__main__":
    sys.exit(main())
