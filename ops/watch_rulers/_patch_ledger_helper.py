import io
import sys

p = "ledger_insert_after.py"
lines = io.open(p, encoding="utf-8", newline="\n").read().split("\n")
out = []
changed = 0
for ln in lines:
    if ln.strip() == 'for _h in sorted(set(_re.findall(r"\\b[0-9a-f]{40}\\b", raw))):':
        out.append('        _raw = io.open(block_file, encoding="utf-8", newline="\\n").read()')
        out.append('        for _h in sorted(set(_re.findall(r"\\b[0-9a-f]{40}\\b", _raw))):')
        changed += 1
    elif ln.strip() == 'print("       do")':
        out.append(ln.replace('print("       do")',
                              'print("       if it still fails, the coordinate itself is wrong - fix it, do not bypass.")'))
        changed += 1
    else:
        out.append(ln)
io.open(p, "w", encoding="utf-8", newline="\n").write("\n".join(out))
import ast
ast.parse("\n".join(out))
print("edits applied:", changed, "| lint ok")
