"""ORD-0461 r3: carry only this order's lines into the generated client.

The generated file is not this lane's to re-take wholesale (that is ORD-0508).  So the delta is built by
generating the client twice -- once from the tip's contract and once from the contract with this order's
one line added -- and applying only the difference between the two generations to the tip's file.
Everything the tip already had, including whatever drift another lane left in it, stays untouched.
"""
import io
import os
import subprocess
import sys

WT = "D:/moodle/_qoder_rel_ord0461_wt"
WK = "D:/moodle/_qoder_rel_ord0461_wk"
TIP = "d7c08d1293835adc7b2628f7100263066d610322"
NODE = "node.exe" if os.name == "nt" else "node"
CLI = "node_modules/openapi-typescript/bin/cli.js"


def git(*args):
    p = subprocess.run(["git", "-C", WT] + list(args), capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    assert p.returncode == 0, (args, p.stderr[:200])
    return p.stdout


def generate(contract_path, out_path):
    r = subprocess.run([NODE, CLI, contract_path, "-o", out_path], cwd=WT + "/frontend",
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, r.stderr[:300]
    return io.open(out_path, encoding="utf-8").read()


# 1. the tip's contract and the tip's generated client, both taken out of git
tip_contract = git("show", "%s:contracts/openapi.yaml" % TIP)
io.open(WK + "/r3_tip_contract.yaml", "w", encoding="utf-8", newline="\n").write(tip_contract)
tip_client = git("show", "%s:frontend/src/generated/api.ts" % TIP)
io.open(WK + "/r3_tip_client.ts", "w", encoding="utf-8", newline="\n").write(tip_client)

# 2. generate from each contract into the same tool version
a = generate(WK + "/r3_tip_contract.yaml", WK + "/r3_gen_A.ts")
b = generate("../contracts/openapi.yaml", WK + "/r3_gen_B.ts")  # the worktree file = tip + my line

diff_ab = subprocess.run([NODE, "-e", ""], capture_output=True)  # touch nothing
lines_a, lines_b = a.splitlines(), b.splitlines()
import difflib
patch = [l for l in difflib.unified_diff(lines_a, lines_b, "A", "B", lineterm="", n=3)]
added = [l[1:] for l in patch if l.startswith("+") and not l.startswith("+++")]
removed = [l[1:] for l in patch if l.startswith("-") and not l.startswith("---")]
print("generation_delta added=%d removed=%d" % (len(added), len(removed)))
for l in added:
    print("  + %s" % l.strip()[:120])
for l in removed:
    print("  - %s" % l.strip()[:120])
assert added, "the contract edit produced no client line -- it would not be carried"
assert "MEMBER_EXPIRY_IN_PAST" in " ".join(added), "my reason code is not in the client delta"

# 3. apply exactly that delta to the tip's client, by line identity, not by regenerating
out_lines, skip_next = [], 0
removed_set = [l.strip() for l in removed]
src = tip_client.splitlines(keepends=True)
i = 0
applied_add = 0
while i < len(src):
    line = src[i]
    if line.strip() in removed_set and removed_set:
        # replace the removed anchor line with the added block once
        if skip_next == 0:
            for new in added:
                out_lines.append(new + "\n")
            applied_add = len(added)
            skip_next = 1
            i += 1
            continue
    out_lines.append(line)
    i += 1
assert applied_add == len(added), "delta was not applied"
io.open(WT + "/frontend/src/generated/api.ts", "w", encoding="utf-8", newline="\n").write(
    "".join(out_lines))

after = io.open(WT + "/frontend/src/generated/api.ts", encoding="utf-8").read()
print("client_vs_tip added=%d removed=%d" % (
    len([l for l in difflib.unified_diff(tip_client.splitlines(), after.splitlines(), n=0)
         if l.startswith("+") and not l.startswith("+++")]),
    len([l for l in difflib.unified_diff(tip_client.splitlines(), after.splitlines(), n=0)
         if l.startswith("-") and not l.startswith("---")]),
))
