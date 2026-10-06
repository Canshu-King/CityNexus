import io, ast
p = "_quota_roster_r1.py"
t = io.open(p, encoding="utf-8", newline="").read()
old = """        age = (now - os.path.getmtime(p)) / 60.0
        if last and "daily usage limit" in last:
            capped.append((nick, sid8, age))
        elif age < 8:
            writing.append((nick, sid8, age))
        else:
            quiet.append((nick, sid8, age))"""
assert old in t
new = """        age = (now - os.path.getmtime(p)) / 60.0
        # 21:19 学到：mtime 静默不等于停下——尾条若是 tool_use/tool_result/thinking，
        # 那是**正在跑一个长工具**（构建、套件），敲它只是打断。所以静默那档再分两类。
        kinds = last_kinds(blob)
        if last and "daily usage limit" in last:
            capped.append((nick, sid8, age))
        elif age < 8:
            writing.append((nick, sid8, age))
        else:
            quiet.append((nick, sid8, age, kinds))"""
t = t.replace(old, new)
helper = '''def last_kinds(blob):
    """最后一条 assistant/user 记录里装的是什么：text（说人话）还是工具块（在跑东西）。"""
    rows = [l.strip() for l in blob.split(chr(10)) if l.strip().startswith("{")]
    for line in reversed(rows[-40:]):
        try:
            o = json.loads(line)
        except Exception:
            continue
        if o.get("type") not in ("user", "assistant"):
            continue
        c = (o.get("message") or {}).get("content")
        if isinstance(c, list):
            ks = set(x.get("type", "") for x in c if isinstance(x, dict))
            if ks:
                return "+".join(sorted(ks))
    return "?"


'''
t = t.replace("def main():", helper + "def main():", 1)
t = t.replace('        print("   静默非闸：" + "、".join("%s(%.0f分)" % (x[0], x[2]) for x in sorted(quiet, key=lambda y: -y[2])))',
              '        print("   静默非闸：" + "、".join("%s(%.0f分｜尾条 %s)" % (x[0], x[2], x[3] if len(x) > 3 else "?") for x in sorted(quiet, key=lambda y: -y[2])))')
io.open(p, "w", encoding="utf-8", newline="").write(t)
ast.parse(io.open(p, encoding="utf-8").read())
print("AST OK")
