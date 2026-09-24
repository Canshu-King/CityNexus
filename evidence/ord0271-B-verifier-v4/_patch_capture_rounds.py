"""One-shot patch: make the capture builder take a round number instead of round 1."""
import ast
import pathlib

p = pathlib.Path(r"D:\moodle\_qoder_harness_ord0254\tools\build_0271b_capture.py")
t = p.read_text(encoding="utf-8")

t = t.replace('''"""ORD-0271-B: assemble the round-1 fifth-state capture from what the instruments wrote, not from what I saw.''',
              '''"""ORD-0271-B: assemble one round's fifth-state capture from what the instruments wrote, not from what I saw.

Usage: python build_0271b_capture.py [round-number]   ->   ord0271b_capture_round<N>.json''', 1)

t = t.replace("def readings() -> list[dict]:\n    p = BASE",
              "def readings(PASSES: dict) -> list[dict]:\n    p = BASE", 1)
t = t.replace("def main() -> int:\n    sys.stdout.reconfigure",
              "def main() -> int:\n    sys.stdout.reconfigure", 1)
t = t.replace("    kept, rejected, skipped = readings()",
              "    round_no = int(sys.argv[1]) if len(sys.argv) > 1 else 1\n"
              "    PASSES = passes_for(round_no)\n"
              "    kept, rejected, skipped = readings(PASSES)", 1)
t = t.replace('    shapes = {"control1": [], "mutant1": []}',
              '    shapes = {f"control{round_no}": [], f"mutant{round_no}": []}', 1)
t = t.replace('    for gen in shapes:\n        shapes[gen].sort(key=lambda s: s["shape"])',
              '    for gen in shapes:\n        shapes[gen].sort(key=lambda s: s["shape"])\n'
              '    cgen, mgen = f"control{round_no}", f"mutant{round_no}"', 1)
t = t.replace('           "subject": "runtime readings for the fifth state on candidate c79e2b4f: control build and the "\n'
              '                      "single-variable UNKNOWN_FAILURE mutant of the same build, same face, same instrument",',
              '           "round": round_no,\n'
              '           "subject": "runtime readings for the fifth state on candidate c79e2b4f: control build and the "\n'
              '                      "single-variable UNKNOWN_FAILURE mutant of the same build, same face, same instrument",', 1)
t = t.replace('           "cells": {"S5_invalid_response": {"shapes": shapes["control1"]},\n'
              '                     "S5_invalid_response_mutant": {"shapes": shapes["mutant1"]}},',
              '           "cells": {"S5_invalid_response": {"shapes": shapes[cgen]},\n'
              '                     "S5_invalid_response_mutant": {"shapes": shapes[mgen]}},', 1)
t = t.replace('                      "control_shapes": len(shapes["control1"]), "mutant_shapes": len(shapes["mutant1"]),',
              '                      "control_shapes": len(shapes[cgen]), "mutant_shapes": len(shapes[mgen]),', 1)
t = t.replace('    p = BASE / "ord0271b_capture_round1.json"',
              '    p = BASE / f"ord0271b_capture_round{round_no}.json"', 1)
t = t.replace('                                         for s in shapes["control1"]],',
              '                                         for s in shapes[cgen]],', 1)
t = t.replace('                                        for s in shapes["mutant1"]],',
              '                                        for s in shapes[mgen]],', 1)

assert "shapes[\"control1\"]" not in t, "leftover control1 reference"
assert "readings(PASSES)" in t and "passes_for(round_no)" in t
ast.parse(t)
p.write_bytes(t.encode("utf-8"))
print("patched; bytes", len(t.encode("utf-8")))
