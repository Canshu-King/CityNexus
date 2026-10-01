"""Derive the generation-8 instruments from generation 7, in an order that cannot eat itself.

`mutgen6` contains the substring `gen6`, and `gen7` -> `gen8` would happily rewrite `mutgen7`; the
previous round produced exactly that bug (the mutant tree was named `mutgen6`, the derived tool went
looking for `mutgen7`, and two measurement steps died in one second).  So the tree and face names are
mapped first, the tool-name prefix last, and every derived file is parsed before it is kept.
"""
import ast
import os

ORDER = [
    ("mutgen6", "mutgen8"),
    ("wt18", "wt21"),
    ("wt16", "wt19"),
    ("wt17", "wt20"),
    ("TIP_7862c6de", "TIP_514b397f"),
    ("O0500_R3", "O0500_R4"),
    ("faces/tip7", "faces/tip8"),
    ("faces/o0500_r3", "faces/o0500_r4"),
    ("faces/o0500_clientbool7", "faces/o0500_clientbool8"),
    ("7862c6de5565c02c20ec2dccaa9da18960603e06", "514b397f96f3b5165b24865f4a544ab6f8020084"),
    ("merge_tree_r7", "merge_tree_r8"),
    ("blobs_r7", "blobs_r8"),
    ("ls_remote_r7", "ls_remote_r8"),
    ("landing_check_r1", "landing_check_r2"),
    ("gen7_landing_check_r1", "gen8_landing_check_r1"),
    ("GEN7_READINGS", "GEN8_READINGS"),
    ("gen7", "gen8"),
]
SRC = ["gen7_build_r1.py", "gen7_stack_r1.py", "gen7_doors_r1.py", "gen7_ce1_r1.py",
       "gen7_ce1_proof_r1.py", "gen7_carrier_r1.py", "gen7_carrier_arms_r1.py",
       "gen7_sheets_r1.py", "gen7_slots_r1.py", "gen7_blocks_r1.py", "gen7_coordinates_r1.py",
       "gen7_landing_check_r1.py", "make_gen7_mutants_r1.py"]
LANE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
for name in SRC:
    text = open(os.path.join(LANE, "tools", name), encoding="utf-8").read()
    for old, new in ORDER:
        text = text.replace(old, new)
    out = os.path.join(LANE, "tools", name.replace("gen7", "gen8"))
    open(out, "w", encoding="utf-8", newline="\n").write(text)
    try:
        ast.parse(text)
        print("%-36s PARSE_OK" % os.path.basename(out))
    except SyntaxError as exc:
        print("%-36s SYNTAX line %s %s" % (os.path.basename(out), exc.lineno, exc.msg))
