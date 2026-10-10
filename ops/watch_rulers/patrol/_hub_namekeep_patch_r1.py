# -*- coding: utf-8 -*-
"""修一处会毁掉花名的行为：不带 --name 的再 join，会把已登记的花名冲回 id。

实测依据（10-04 11:12，不是推测）：
    join 之前 name = '打更人·值守'
    跑 `bus.py join --id qoder:42d1a6fa`（不带 --name，车道重启后就是这么用的）
    join 之后 name = 'qoder:42d1a6fa'
花名的单一来源是名册；只要 join 会重置它，板子、光荣榜、耻辱墙明天就会重新变成一排 hex 串，
而"认不得谁是谁"正是主人今天提出来要解决的问题。

改法：register 里没给 name 时**保留上一份**（除非上一份就等于 id，即从未登记过名字）。
顺手给 selftest_bus.py 加一正一反两枚断言，免得下次有人"顺手改回去"。
"""
import ast
import io

NL = chr(10)
HUB = u"D:/moodle/agent_bus/bus_hub.py"
ST = u"D:/moodle/agent_bus/selftest_bus.py"

s = io.open(HUB, encoding="utf-8", errors="replace").read()
old = u'''    st["agents"][aid] = {"name": b.get("name") or aid, "transport": aid.split(":")[0],'''
new = u'''    prev_name = str((prev or {}).get("name") or "")
    # 没带 --name 的再 join（车道重启后最常见的一形）**不许把花名冲回 id**；
    # 上一份名字若本来就等于 id（从没登记过），才退回 id。
    keep = prev_name if prev_name and prev_name != aid else aid
    st["agents"][aid] = {"name": b.get("name") or keep, "transport": aid.split(":")[0],'''
assert s.count(old) == 1, "找不到 register 里那行赋值"
s = s.replace(old, new, 1)
ast.parse(s)
io.open(HUB, "w", encoding="utf-8", newline=NL).write(s)
print("HUB_NAME_KEEP_PATCHED AST_OK")

t = io.open(ST, encoding="utf-8", errors="replace").read()
probe = u'''    # —— 花名保真（10-04 11:1x 加的实测格）——
    tag_id = u"qoder:nametagprobe%d" % int(time.time() % 100000)
    st_http("POST", "/agents", {"id": tag_id, "name": u"临时工·小探"})
    ags = json.loads(st_http("GET", "/agents")[2].decode("utf-8", "replace"))
    checks["nametag_saved_on_register"] = ags.get(tag_id, {}).get("name") == u"临时工·小探"
    # 再 join 一次、不带 name：这是车道重启后的真实动作，过去会把花名冲回 id
    subprocess.run([sys.executable, os.path.join(HERE, "bus.py"), "join", "--id", tag_id],
                   capture_output=True, cwd=HERE, timeout=120)
    ags2 = json.loads(st_http("GET", "/agents")[2].decode("utf-8", "replace"))
    checks["nametag_survives_bare_join"] = ags2.get(tag_id, {}).get("name") == u"临时工·小探"
    say(u"花名保真：注册=%s 裸 join 后=%s（两向都要真）" % (
        ags.get(tag_id, {}).get("name"), ags2.get(tag_id, {}).get("name")))

'''
anchor = u"    say(u\"=== "
idx = t.rindex(anchor)
t2 = t[:idx] + probe + t[idx:]
ast.parse(t2)
io.open(ST, "w", encoding="utf-8", newline=NL).write(t2)
print("SELFTEST_TWO_CASES_ADDED AST_OK")
