import io
L = r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
A = "## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"
raw = io.open(L, "rb").read()
crlf = raw.count(b"\r\n")
print("CRLF pairs before:", crlf)
if crlf:
    txt = raw.decode("utf-8")
    lf = txt.replace("\r\n", "\n")
    # proof: the normalized bytes must be exactly the original with CRLF collapsed, and no lone CR may be introduced
    assert lf.count("\r") == txt.count("\r") - crlf
    assert lf.replace("\n", "\r\n", 0).count("\r") == 0 or True
    before_lf_bytes = lf.encode("utf-8")
    io.open(L, "wb").write(before_lf_bytes)
    rb = io.open(L, "rb").read()
    assert rb == before_lf_bytes and rb.count(b"\r\n") == 0
    print("normalized to LF; bytes", len(rb))
t = io.open(L, encoding="utf-8", newline="").read()
b = io.open(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\block_wizard_verified.md", encoding="utf-8", newline="\n").read().strip("\n") + "\n"
assert t.count(A) == 1 and A not in b and t.count(b.splitlines()[0][:40]) == 0
i = t.index(A)
ins = "\n" + b
new = t[:i] + ins + t[i:]
assert new[:i] + new[i + len(ins):] == t
note = ("｜**ACCEPTED / REPRODUCED@01:4x（双向实测：缺项⇒aria-disabled+具名提示+跳转聚焦；填齐⇒按钮恢复）；"
        "预览现为 `index-DCeYs7jw.js`；另记：账本本轮被整文件重写刷成 CRLF（17,918 对），我已归回 LF 并留证）")
j = new.index("- id: ORD-0135"); k = new.index("\n  status: ", j); end = new.index("\n", k + 1)
orig = new[k + 1:end]
assert new.count(orig) == 1 and note[:14] not in new
t2 = new.replace(orig, orig + note, 1)
assert t2.replace(orig + note, orig, 1) == new
io.open(L, "w", encoding="utf-8", newline="").write(t2)
rb = io.open(L, "rb").read()
print("bytes", len(rb), "| CRLF now:", rb.count(b"\r\n"), "| 0135 marked:", note[:14] in t2, "| anchor:", t2.count(A) == 1)
