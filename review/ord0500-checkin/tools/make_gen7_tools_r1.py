"""Derive the generation-7 instruments from the generation-5 ones.

Only names move: the tip, the two worktrees, the two mutant trees, the three faces and the order's
ref.  Keeping the measurement code byte-for-byte the same across generations is what lets a reader
compare the numbers instead of comparing the instruments.
"""
import os

SUBS = [
    ("gen5", "gen7"),
    ("TIP_822db3d9", "TIP_7862c6de"),
    ("O0500_R2", "O0500_R3"),
    ("wt13", "wt17"),
    ("wt10", "wt18"),
    ("mutgen5", "mutgen6"),
    ("wt9", "wt16"),
    ("faces/tip5", "faces/tip7"),
    ("faces/o0500_r2", "faces/o0500_r3"),
    ("faces/o0500_clientbool7", "faces/o0500_clientbool7"),
    ("faces/o0500_clientbool5", "faces/o0500_clientbool7"),
    ("822db3d9f07b9c7d535e12afbdeb3074dd94acb2", "7862c6de5565c02c20ec2dccaa9da18960603e06"),
    ("candidate_wt16", "candidate_wt16"),
]
SRC = ["gen5_build_r1.py", "gen5_stack_r1.py", "gen5_doors_r1.py", "gen5_ce1_r1.py",
       "gen5_ce1_proof_r1.py", "gen5_carrier_r1.py", "gen5_carrier_arms_r1.py",
       "gen5_sheets_r1.py", "gen5_slots_r1.py"]
LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for name in SRC:
    text = open(os.path.join(LANE, "tools", name), encoding="utf-8").read()
    for old, new in SUBS:
        text = text.replace(old, new)
    out = os.path.join(LANE, "tools", name.replace("gen5", "gen7"))
    open(out, "w", encoding="utf-8", newline="chr" and "\n").write(text)
    import ast
    try:
        ast.parse(text)
        print("%-34s PARSE_OK" % os.path.basename(out))
    except SyntaxError as exc:
        print("%-34s SYNTAX %s" % (os.path.basename(out), exc))
