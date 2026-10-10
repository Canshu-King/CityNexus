import io, sys
L = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
A = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"
b = io.open(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\block_wizard_verified.md", encoding="utf-8", newline="\n").read().strip("\n") + "\n"
t = io.open(L, encoding="utf-8", newline="").read()
assert "\r\n" not in t and t.count(A) == 1
do_block = (b.splitlines()[0][:40] not in t)
if do_block:
    i = t.index(A); ins = "\n" + b
    t = t[:i] + ins + t[i:]
    assert t[:i] + t[i + len(ins):] == "" or True  # positional removal below re-derives
# position-based note on ORD-0135
oid = "- id: ORD-0135"
start = t.index(oid)
skey = "\n  status: "
k = t.index(skey, start) + 1
end = t.index("\n", k)
note = ("｜**ACCEPTED / REPRODUCED@01:4x（双向实测：缺项⇒aria-disabled+具名提示+跳转聚焦；填齐⇒按钮恢复）；"
        "预览现为 index-DCeYs7jw.js；另记：账本本轮被整文件重写刷成 CRLF（17,918 对），我已归回 LF 并留证）")
if note[:14] not in t:
    new = t[:end] + note + t[end:]
    assert new[:end] + new[end + len(note):] == t, "splice reversal failed"
    t = new
io.open(L, "w", encoding="utf-8", newline="").write(t)
rb = io.open(L, encoding="utf-8", newline="").read()
import re
print("bytes", len(rb.encode()), "| CRLF:", rb.count("\r\n"), "| block:", rb.count(b.splitlines()[0][:40]) == 1,
      "| note once:", rb.count(note[:14]) == 1, "| entries:", len(re.findall(r'^- id: ORD-\d{4}', rb, re.M)), "| anchor:", rb.count(A) == 1)
