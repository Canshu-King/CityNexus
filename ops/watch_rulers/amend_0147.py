import io
L=r"D:\moodle\CITYNEXUS_AGENT_CONTROL.md"
t=io.open(L,encoding="utf-8",newline="").read()
b=io.open(r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\block_wizard_verified.md",encoding="utf-8",newline="\n").read().strip("\n")+"\n"
A="## ORDERS（收件箱：worker 每完成一个动作、每开始下一个动作之前先读这里）"
assert "\r\n" not in t and t.count(A)==1 and A not in b and t.count(b.splitlines()[0][:40])==0
i=t.index(A); ins="\n"+b; new=t[:i]+ins+t[i:]
assert new[:i]+new[i+len(ins):]==t
note="｜**ACCEPTED / REPRODUCED@01:4x（双向实测：缺项 ⇒ aria-disabled+describedby 具名提示+跳转并聚焦字段；填齐 ⇒ 按钮恢复正常）；我 01:1x 四条门全满足；预览现为 `index-DCeYs7jw.js`**"
for oid in ("ORD-0135",):
    j=new.index("- id: "+oid); k=new.index("\n  status: ", j); end=new.index("\n", k+1)
    orig=new[k+1:end]; assert new.count(orig)==1 and note[:16] not in new
    t2=new.replace(orig, orig+note, 1); assert t2.replace(orig+note, orig, 1)==new
    new=t2
io.open(L,"w",encoding="utf-8",newline="").write(new)
rb=io.open(L,encoding="utf-8",newline="").read()
print("bytes",len(rb.encode()),"| 0135 marked:", note[:16] in rb, "| anchor:", rb.count(A)==1)
