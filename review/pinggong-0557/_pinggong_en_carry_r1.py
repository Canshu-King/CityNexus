import io, sys

P = r"D:/moodle/_qoder_pinggong_0557_dict/frontend/src/i18n/LocaleContext.tsx"
KEY = "main.unnamedCommitmentServerGaveNoName"
VAL = "未命名承诺 · 服务器没给名字"
AFTER = '  "main.evidenceUnavailable": "evidence unavailable",'

lines = io.open(P, encoding="utf-8").read().split("\n")
en_from = next(i for i, s in enumerate(lines) if s.startswith("const en: Dict = {"))
en_to = next(i for i, s in enumerate(lines[en_from + 1:], en_from + 1) if s == "};")
anchor = [i for i in range(en_from, en_to) if lines[i] == AFTER]
if len(anchor) != 1:
    sys.exit("ABORT en-block anchor hits=%d" % len(anchor))
already = [i for i in range(en_from, en_to) if lines[i].startswith('  "%s":' % KEY)]
if already:
    sys.exit("ABORT key already in en block at %d" % (already[0] + 1))
lines[anchor[0] + 1:anchor[0] + 1] = ['  "%s": "%s",' % (KEY, VAL)]
io.open(P, "w", encoding="utf-8", newline="\n").write("\n".join(lines))
print("en_block_line=%d" % (anchor[0] + 2))
