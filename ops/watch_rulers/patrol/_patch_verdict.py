import io, ast
p = "_night_verdict_r1.py"
t = io.open(p, encoding="utf-8", newline="").read()
a = "        last_txt = None\n        caps = 0\n"
assert a in t
t = t.replace(a, "        last_txt = None\n        caps = 0\n        last_cap = None\n", 1)
b = "                if e >= day0:\n                    caps += 1\n                last_rec = \"cap\"\n"
assert b in t
t = t.replace(b, "                if e >= day0:\n                    caps += 1\n                    if last_cap is None or e > last_cap:\n                        last_cap = e\n                last_rec = \"cap\"\n", 1)
c = "        rows.append((nick, sid8, last_txt, caps, last_rec, blocks))\n    rows.sort(key=lambda r: -(r[2] or 0))\n    for nick, sid8, lt, caps, lr, blocks in rows:\n        print(\"   %-8s %-8s 末次产出 %s｜今日撞闸 %2d 次｜末条 %s\" % (\n            nick, sid8, time.strftime(\"%H:%M:%S\", time.localtime(lt)) if lt else \"—\",\n            caps, (\"额度回话\" if lr == \"cap\" else (\"有产出\" if lr else \"无\"))))"
assert c in t
d = "        rows.append((nick, sid8, last_txt, caps, last_rec, blocks, last_cap))\n    rows.sort(key=lambda r: -(r[2] or 0))\n    for nick, sid8, lt, caps, lr, blocks, lcap in rows:\n        print(\"   %-8s %-8s 末次产出 %s｜今日撞闸 %2d 次｜最后一次额度回话 %s｜末条 %s\" % (\n            nick, sid8, time.strftime(\"%H:%M:%S\", time.localtime(lt)) if lt else \"—\",\n            caps,\n            time.strftime(\"%H:%M:%S\", time.localtime(lcap)) if lcap else \"—\",\n            (\"额度回话\" if lr == \"cap\" else (\"有产出\" if lr else \"无\"))))"
t = t.replace(c, d, 1)
io.open(p, "w", encoding="utf-8", newline="").write(t)
ast.parse(io.open(p, encoding="utf-8").read())
print("AST OK：加了『最后一次额度回话』一列")
