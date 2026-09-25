"""Add the 03:32 artefacts to the block's coordinate line and restate the shipping count from the branch."""
import ast
import pathlib

p = pathlib.Path('D:/moodle/HJ-P3_evidence/p4_deliver.py')
s = p.read_text(encoding='utf-8')
old = ("         f'`{P312}/instruments/p4_served_now.py` `{B(P312 + \"/instruments/p4_served_now.py\")}`。')")
new = ("         f'`{P312}/instruments/p4_served_now.py` `{B(P312 + \"/instruments/p4_served_now.py\")}` · '\n"
       "         f'`{P312}/{G2P}` `{B(P312 + \"/\" + G2P)}` · '\n"
       "         f'`{P312}/instruments/p4_m3_bind_gen2.py` '\n"
       "         f'`{B(P312 + \"/instruments/p4_m3_bind_gen2.py\")}` · '\n"
       "         f'`{P312}/instruments/p4_ship_any.py` `{B(P312 + \"/instruments/p4_ship_any.py\")}`。')")
assert s.count(old) == 1
s = s.replace(old, new)
p.write_text(s, encoding='utf-8')
ast.parse(s)
print('PATCHED + PARSES')
