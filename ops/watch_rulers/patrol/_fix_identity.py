import hashlib, io, os, subprocess, time, urllib.request as U, json, ssl
LC = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks"
HERE = os.path.dirname(os.path.abspath(__file__))
raw = io.open(os.path.join(LC, "CLOSING_LINE.txt"), "rb").read()
assert len(raw) == 83 and hashlib.sha1(raw).hexdigest() == "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
CLOSING = raw.decode("utf-8").strip()
p = os.path.join(LC, "ui_exposure_taint_ast_r7b.cjs")
b = io.open(p, "rb").read()
blob = hashlib.sha1(b"blob %d" % len(b) + b"\x00" + b).hexdigest()
gitblob = subprocess.run(["git", "hash-object", p], capture_output=True, text=True).stdout.strip()
pin = next(l for l in io.open(os.path.join(LC, "preflight_and_land_r5.py"), encoding="utf-8", errors="replace") if "EXPOSURE_RULER_BLOB" in l).strip()
size = os.path.getsize(p)
b2 = []
b2.append(u"**勘误（新帖，不改 %s）：那条落地包里的尺身份我印成了空白，还把'一致'当结论写了——现在给可回读的值。**" % "5891063450")
b2.append(u"")
b2.append(u"- 空白的原因：我用 `python -c \"...%%s...\"` 嵌套引号算 sha1，子进程直接失败返回空串，我没回读就发了帖。这是我的错，和今天 15:0x 那次'引用了命令没产出的坐标'同一类。")
b2.append(u"- 正确身份（21:16 现读，两种通道同枚）：`git hash-object live_checks/ui_exposure_taint_ast_r7b.cjs` = `%s`；按门自己的算法 `sha1(b\"blob %%d\0\" + 文件字节)`（`preflight_and_land_r5.py:138`）= `%s`。文件 %d 字节。" % (gitblob, blob, size))
b2.append(u"- 门钉的那枚：`%s` ⇒ 与上面两枚**逐字相同**，这次是真的比过。所以那条帖里的曝光面读数仍成立（跑的就是这枚尺），只是我当时没把坐标印出来。" % pin)
b2.append(u"- 口径顺带钉住：`本机字节 sha1` 与 `git blob id` 不是一回事（前者不含 `blob <len>\0` 头），我上一条帖里写的\"本机字节 sha1\"这个词也用错了；门取的是后者。" )
b2.append(u"")
b2.append(u"边界：只读（文件字节、门源码、git hash-object）。0 次写账本、0 次代插、0 次落地、0 次动权威线、0 次改别人的文件。")
out = os.path.join(HERE, "_bus_identity_fix.md")
io.open(out, "w", encoding="utf-8", newline="\n").write("\n".join(b2).rstrip() + "\n" + CLOSING + "\n")
print("写好 %d B｜git=%s｜算法=%s｜同枚=%s" % (os.path.getsize(out), gitblob[:12], blob[:12], gitblob == blob))
r = subprocess.run([r"D:\moodle\CityNexus\.venv\Scripts\python.exe", os.path.join(LC, "bus_post.py"), out],
                   capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=600,
                   env=dict(os.environ, PYTHONIOENCODING="utf-8", HTTP_PROXY="", HTTPS_PROXY=""))
print(((r.stdout or "") + (r.stderr or "")).strip()[:400])
