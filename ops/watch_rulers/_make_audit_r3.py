"""Build audit_closure_coordinates_r3.py from r2 by appending the coordinates cited since 05:3x.

Only two edits are allowed: the CLAIMS tuple grows, and the docstring says which run this is.
Everything else stays byte-identical so a reviewer can diff r2 -> r3 and see only new pins.
"""
import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

SRC = "audit_closure_coordinates_r2.py"
DST = "audit_closure_coordinates_r3.py"

NEW = (
    ('    ("evidence/ord0272-k8-f/verifier_derivation_d2305848.json", '
     '"709f9c8f99314a6b1ce5096e5ee3008b884f3c85", 6211, "0272 K8 two-cell derivation (lane E)"),\n'),
    ('    ("evidence/ord0269-0273-gate-v6-e713510/commander_samegen_0269_0273_45b0a5e_d2305848.json", '
     '"bd12f1fb08833b98ebd93b83d0a0fa94773bce9d", 3499, "0269/0273 same-generation gate rerun (lane E)"),\n'),
    ('    ("evidence/ord0269-0273-gate-v7-45b0a5e/arms-v6-aef5765.json", '
     '"af2150a0e8097edd7e1be2c4a720f9e660f60b2a", 22591, "lane D arms (delivered as 16-hex prefix, resolved here)"),\n'),
    ('    ("evidence/ord0269-0273-gate-v7-45b0a5e/gate-round-5b549be-with-landing-groups.json", '
     '"31eb62fb634a57450b90dbcfebf392f9725e7ed5", 20772, "lane D gate round + landing groups"),\n'),
    ('    ("evidence/ord0269-0273-gate-v7-45b0a5e/manifest-5b549be.json", '
     '"e2bca6c975a95dcf6972463851ddcc11bda31d0c", 2997, "lane D manifest"),\n'),
)

src = io.open(SRC, encoding="utf-8", newline="").read()
marker = '    ("evidence/ord0279x-hjp3-run/O0279X-2504_readings.json", "24a6a384e357449c7cc8f4de4a0f1d9b2759da63", 9483, "ORD-0279-X readings"),\n'
assert src.count(marker) == 1, "anchor count %d" % src.count(marker)
out = src.replace(marker, marker + "".join(NEW), 1)
assert out != src
io.open(DST, "w", encoding="utf-8", newline="").write(out)

# prove: only the 5 new lines differ, and the new file parses
import ast
ast.parse(out)
old_lines = src.splitlines()
new_lines = out.splitlines()
added = [l for l in new_lines if l not in old_lines]
removed = [l for l in old_lines if l not in new_lines]
print("wrote", DST, "bytes", len(out.encode("utf-8")))
print("added lines:", len(added), "removed lines:", len(removed))
for l in added:
    print("  +", l[:70])
assert len(added) == 5 and not removed, "unexpected diff"
ns = {}
exec (compile(out.split("def main()")[0], "r3-head", "exec"), ns)
print("claims in r3:", len(ns["CLAIMS"]))
