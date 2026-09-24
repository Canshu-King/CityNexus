"""One-shot patch: a round's legs must each carry the three *distinct* fifth-state shapes.

The first version of the round receipt asked only `len(mut) >= 3`. Round 1 satisfied that with two distinct
shapes plus a duplicate re-run of one of them, so a round that never measured the not-JSON shape under the
mutant built could still print ROUND_GREEN. Counting rows is not counting shapes.
"""
import ast
import pathlib

p = pathlib.Path(r"D:\moodle\_qoder_harness_ord0254\tools\ord0271b_round_receipt.py")
t = p.read_text(encoding="utf-8")
before = t

t = t.replace('''        "control_three_shapes_present": len(ctl) == 3,''',
              '''        "control_three_distinct_shapes": {s["shape"] for s in ctl} == SHAPES,''', 1)
t = t.replace('''        "mutant_three_shapes_present": len(mut) >= 3,''',
              '''        "mutant_three_distinct_shapes": {s["shape"] for s in mut} >= SHAPES,''', 1)
t = t.replace('CONTROL_SOURCE_SHA256 = "3472430ee46810bdef0f5b3e53cca88cbfeb9a4a5385760c165032a9974d5c5d"',
              'CONTROL_SOURCE_SHA256 = "3472430ee46810bdef0f5b3e53cca88cbfeb9a4a5385760c165032a9974d5c5d"\n'
              '# the fifth state is three readings, not one: HTML, an empty body, and a body that is not JSON.\n'
              '# A round that measured only two of them under the mutant built is not a round, however many rows\n'
              '# its capture happens to hold - a duplicate re-run of one shape must not fill the third seat.\n'
              'SHAPES = {"200_html", "200_empty", "200_not_json"}', 1)
t = t.replace('''        "dedicated_carrier_red_only_on_new_clause": len(car_rows) == 3 and all(''',
              '''        "dedicated_carrier_red_only_on_new_clause": len(car_rows) == len(ctl) and all(''', 1)

assert t != before and "SHAPES" in t and ">= SHAPES" in t
assert "len(mut) >= 3" not in t and "len(ctl) == 3" not in t
ast.parse(t)
p.write_bytes(t.encode("utf-8"))
print("patched; bytes", len(t.encode("utf-8")))
