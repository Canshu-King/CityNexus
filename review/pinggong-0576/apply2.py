# -*- coding: utf-8 -*-
"""批二起的应用器：按 offset 从后往前替换，跨行切片整段收掉，改后逐枚现读回报新行号。
  1) 断言工作树里两枚文件的字节 == 规格里那一代（不同代先合尖）；
  2) 每枚切片先断言命中次数与起始行，再按 offset 降序整段换成 t("键")；
  3) 新键两侧同序追加在 en 与 zh-CN 尾部，插入点断言不在未闭合 /* 里、键名断言不重复；
  4) 落盘后回读：该族硬编码中文残留零枚、每枚键两侧各一枚、并现读报出改后行号。"""
import json
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SPEC = json.load(open(sys.argv[1], encoding="utf-8"))
TREE = sys.argv[2] if len(sys.argv) > 2 else "D:/moodle/_qoder_pinggong_0576"
REPO = "D:/moodle/_qoder_integration_20260919"
PROD_REL = SPEC["file"]
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
GEN = SPEC["gen"]


def die(msg):
    raise SystemExit("ABORT " + msg)


def blob_of(path):
    out = subprocess.run(["git", "hash-object", path], capture_output=True, text=True)
    if out.returncode != 0:
        die("hash-object failed %s" % out.stderr.strip())
    return out.stdout.strip()


def gen_blob(rel):
    out = subprocess.run(["git", "rev-parse", "%s:%s" % (GEN, rel)],
                         cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        die("gen blob lookup failed %s" % out.stderr.strip())
    return out.stdout.strip()


def read(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


def line_of(text, index):
    return 1 + text.count("\n", 0, index)


prod_path = TREE + "/" + PROD_REL
dict_path = TREE + "/" + DICT_REL
for rel, path in ((PROD_REL, prod_path), (DICT_REL, dict_path)):
    if blob_of(path) != gen_blob(rel):
        die("%s tree blob %s != generation blob %s —— 先合尖再重跑" % (rel, blob_of(path), gen_blob(rel)))

prod = read(prod_path)
dict_text = read(dict_path)
rows = SPEC["rows"]

slices = {}
for row in rows:
    slices[row["ternary"]] = slices.get(row["ternary"], 0) + 1
for ternary, count in slices.items():
    if prod.count(ternary) != count:
        die("slice %r hits %d, expected %d" % (ternary[:60], prod.count(ternary), count))

for row in rows:
    if line_of(prod, row["start"]) != row["start_line"]:
        die("offset %d now reads line %d, spec says %d —— 代变了，重铸规格"
            % (row["start"], line_of(prod, row["start"]), row["start_line"]))
    if prod[row["start"]:row["start"] + len(row["ternary"])] != row["ternary"]:
        die("slice at offset %d does not match the spec" % row["start"])

keys = []
for row in rows:
    if row["key"] not in keys:
        keys.append(row["key"])
for key in keys:
    if dict_text.count('"%s":' % key):
        die("key %s already defined in the tree dictionary" % key)

new_prod = prod
for row in sorted(rows, key=lambda r: -r["start"]):
    new_prod = new_prod[:row["start"]] + 't("%s")' % row["key"] + new_prod[row["start"] + len(row["ternary"]):]

for row in rows:
    if prod.count(row["zh"]) and row["zh"] in new_prod:
        die("hardcoded zh of %s still present after edit" % row["key"])
for key in keys:
    want = sum(1 for row in rows if row["key"] == key)
    got = new_prod.count('t("%s")' % key)
    if got != want:
        die("key %s called %d times after edit, expected %d" % (key, got, want))


def block_tail(text, marker):
    head = text.index(marker)
    return head, text.index("\n};", head)


_, en_end = block_tail(dict_text, "const en: Dict = {")
_, zh_end = block_tail(dict_text, "const zhCN: Dict = {")
for index, label in ((en_end, "en tail"), (zh_end, "zh tail")):
    if dict_text.count("/*", 0, index) - dict_text.count("*/", 0, index):
        die("insertion point %s inside an unterminated block comment" % label)

value_by_key = {row["key"]: (row["zh"], row["en"]) for row in rows}
en_block = "".join('  "%s": "%s",\n' % (key, value_by_key[key][1]) for key in keys)
zh_block = "".join('  "%s": "%s",\n' % (key, value_by_key[key][0]) for key in keys)
merged = dict_text[:en_end] + "\n" + en_block.rstrip("\n") + dict_text[en_end:]
zh_end2 = merged.index("\n};", merged.index("const zhCN: Dict = {"))
if merged.count("/*", 0, zh_end2) - merged.count("*/", 0, zh_end2):
    die("zh insertion point after en insert sits in a comment")
merged = merged[:zh_end2] + "\n" + zh_block.rstrip("\n") + merged[zh_end2:]

write(prod_path, new_prod)
write(dict_path, merged)

check_prod = read(prod_path)
check_dict = read(dict_path)
dict_lines = check_dict.split("\n")
print("APPLIED gen %s family %s rows %d keys %d" % (GEN[:12], SPEC["family"], len(rows), len(keys)))
print("PRODUCT_BLOB %s" % blob_of(prod_path))
print("DICT_BLOB %s" % blob_of(dict_path))
for key in keys:
    hits = [index + 1 for index, text in enumerate(dict_lines) if '"%s":' % key in text]
    if len(hits) != 2:
        die("key %s defined %d times, expected 2 (en + zh)" % (key, len(hits)))
    print("  KEY %s en=%d zh=%d" % (key, hits[0], hits[1]))
prod_lines = check_prod.split("\n")
for row in rows:
    offset = check_prod.index('t("%s")' % row["key"])
    where = [index + 1 for index, text in enumerate(prod_lines) if 't("%s")' % row["key"] in text]
    print("  CALL %s at lines %s (改前 %d-%d)" % (row["key"], where, row["start_line"], row["end_line"]))
