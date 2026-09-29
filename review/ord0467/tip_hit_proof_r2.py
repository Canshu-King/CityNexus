"""ORD-0467 r2 -- prove what the tip holds and what this branch removes, without a second checkout.

The claim being measured is narrow: at the tip, the credential gate finds two product-path literals,
and this branch fixes exactly one of them (the V13 site). The other belongs to another order.

Why no full tip export: this branch differs from the tip in a known list of source files, so every
hit the tip can have outside those files the branch would have too. Materialising just the changed
files at the tip's blobs, and scanning them with the same helper the gate uses, is therefore enough
to compare the two generations -- and it avoids a second 8k-file worktree on a busy disk.
"""
import json
import pathlib
import shutil
import re
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8")
WT = pathlib.Path("D:/moodle/_qoder_q_ord0427_20260929/wt")
OUT = pathlib.Path("D:/moodle/_qoder_q_ord0467_20260929")
REF = "review/Q-ord0467-v13-contract-enum-r2"
sys.path.insert(0, str(WT / "backend"))
from app.security import credential_literals as CL  # noqa: E402


def git(*a):
    return subprocess.run(["git", "-C", str(WT)] + list(a), capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout.strip()


TIP = git("ls-remote", "--refs", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
REF_SHA = git("ls-remote", "--refs", "origin", "refs/heads/%s" % REF).split()[0]
BRANCH_TIP = git("merge-base", TIP, REF_SHA)
changed = [f for f in git("diff", "--name-only", TIP, REF_SHA, "--", "backend", "contracts",
                          "frontend", "tools").splitlines()
           if not f.startswith("review/")]

root = OUT / "tip_slices"
shutil.rmtree(str(root), ignore_errors=True)
root.mkdir(parents=True, exist_ok=True)
for f in changed:
    body = subprocess.run(["git", "-C", str(WT), "show", "%s:%s" % (TIP, f)], capture_output=True,
                          text=True, encoding="utf-8").stdout
    dst = root / f
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(body, encoding="utf-8", newline="\n")

tip_hits = [h for h in CL.find_literals(changed, root) if h["in_product_path"]]
branch_report = CL.scan(WT)
branch_hits = [h for h in branch_report["live"] if h["in_product_path"]]

members = set(re.findall(r"^\s*-\s*(V13_[A-Z0-9]+)\s*$", (WT / "contracts/openapi.yaml").read_text(encoding="utf-8"), re.M))


def brief(h):
    return {"path": h["path"], "line": h["line"], "pattern": h["pattern"],
            "position_fp": h["position_fp"], "length": h["length"],
            "is_member_of_the_contract_enum": h["token_fp"] in {CL.token_fp(m) for m in members}}


result = {"tip": TIP, "branch_ref": REF, "branch_tip": REF_SHA, "fork_point": BRANCH_TIP,
          "source_files_this_branch_changes": changed,
          "tip_product_path_hits": [brief(h) for h in tip_hits],
          "branch_product_path_hits": [brief(h) for h in branch_hits],
          "branch_contract_named_positions": branch_report["contract_named_positions"],
          "branch_verdict": branch_report["verdict"]}
(OUT / "tip_vs_branch_hits_r2.json").write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                                                encoding="utf-8", newline="\n")
print(json.dumps(result, ensure_ascii=False, indent=1))
if BRANCH_TIP != TIP:
    print("NOTE: the tip moved past my fork point %s -- rebase again before quoting these numbers" % BRANCH_TIP[:12])
