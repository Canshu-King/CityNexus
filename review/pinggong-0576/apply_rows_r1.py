# -*- coding: utf-8 -*-
"""JSON 驱动的应用器（唯一事实源 = 铸出来的 rows JSON，不再手打串）：
1) 断言产品与字典两枚文件的字节仍等于 rows JSON 那枚尖上的 blob（不同代就 ABORT 先合尖）；
2) 逐枚把 `? "…" : "…"` 换成 t("键")，行号与全文命中次数都从 JSON 断言；
3) 新键两侧同序追加在 en 与 zh-CN 两块尾部；插入点断言不在未闭合 /* 里，键名断言不重复；
4) 落盘后回读：该行取词键在位、该族硬编码中文残留零枚、两侧各多出期望枚数的键行。"""
import json
import subprocess
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
SPEC = json.load(open(sys.argv[1], encoding="utf-8"))
TREE = sys.argv[2] if len(sys.argv) > 2 else "D:/moodle/_qoder_pinggong_0576"
REPO = "D:/moodle/_qoder_integration_20260919"
PROD_REL = SPEC["file"]
DICT_REL = "frontend/src/i18n/LocaleContext.tsx"
TIP = SPEC["tip"]


def die(msg):
    raise SystemExit("ABORT " + msg)


def blob_of(path):
    out = subprocess.run(["git", "hash-object", path], capture_output=True, text=True)
    if out.returncode != 0:
        die("hash-object failed %s" % out.stderr.strip())
    return out.stdout.strip()


def tip_blob(rel):
    out = subprocess.run(["git", "rev-parse", "%s:%s" % (TIP, rel)],
                         cwd=REPO, capture_output=True, text=True)
    if out.returncode != 0:
        die("tip blob lookup failed %s" % out.stderr.strip())
    return out.stdout.strip()


def read(path):
    with open(path, encoding="utf-8", newline="") as handle:
        return handle.read()


def write(path, text):
    with open(path, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)


prod_path = TREE + "/" + PROD_REL
dict_path = TREE + "/" + DICT_REL
for rel, path in ((PROD_REL, prod_path), (DICT_REL, dict_path)):
    want, got = tip_blob(rel), blob_of(path)
    if got != want:
        die("%s tree blob %s != tip blob %s —— 枝不在这代，先合尖再重跑" % (rel, got, want))

prod = read(prod_path)
dict_text = read(dict_path)
rows = SPEC["rows"]

ternary_hits = {}
for row in rows:
    ternary_hits[row["ternary"]] = ternary_hits.get(row["ternary"], 0) + 1
for ternary, count in ternary_hits.items():
    if prod.count(ternary) != count:
        die("ternary %r hits %d, expected %d" % (ternary[:60], prod.count(ternary), count))

lines = prod.split("\n")
for row in rows:
    if row["ternary"] not in lines[row["tip_line"] - 1]:
        die("line %d does not carry %r (reads %s)"
            % (row["tip_line"], row["ternary"][:50], lines[row["tip_line"] - 1].strip()[:90]))

keys = []
for row in rows:
    if row["key"] not in keys:
        keys.append(row["key"])
for key in keys:
    if dict_text.count('"%s":' % key):
        die("key %s already defined in the tree dictionary" % key)

ternary_to_key = {}
for row in rows:
    ternary_to_key.setdefault(row["ternary"], row["key"])
new_prod = prod
for ternary, key in ternary_to_key.items():
    new_prod = new_prod.replace(ternary, 't("%s")' % key)

new_lines = new_prod.split("\n")
for row in rows:
    if 't("%s")' % row["key"] not in new_lines[row["tip_line"] - 1]:
        die("after edit line %d does not read t(%s)" % (row["tip_line"], row["key"]))
for row in rows:
    if row["zh"] in new_prod:
        die("hardcoded zh of %s still present after edit" % row["key"])


def block_tail(text, head_marker):
    head = text.index(head_marker)
    return head, text.index("\n};", head)


en_head, en_end = block_tail(dict_text, "const en: Dict = {")
zh_head, zh_end = block_tail(dict_text, "const zhCN: Dict = {")


def assert_comment_free(text, index, label):
    if text.count("/*", 0, index) - text.count("*/", 0, index):
        die("insertion point %s inside an unterminated block comment" % label)


assert_comment_free(dict_text, en_end, "en tail")
assert_comment_free(dict_text, zh_end, "zh tail")

value_by_key = {row["key"]: (row["zh"], row["en"]) for row in rows}
en_block = "".join('  "%s": "%s",\n' % (key, value_by_key[key][1]) for key in keys)
zh_block = "".join('  "%s": "%s",\n' % (key, value_by_key[key][0]) for key in keys)
merged = dict_text[:en_end] + "\n" + en_block.rstrip("\n") + dict_text[en_end:]
zh_end2 = merged.index("\n};", merged.index("const zhCN: Dict = {"))
assert_comment_free(merged, zh_end2, "zh tail after en insert")
merged = merged[:zh_end2] + "\n" + zh_block.rstrip("\n") + merged[zh_end2:]

write(prod_path, new_prod)
write(dict_path, merged)

check_prod = read(prod_path)
check_dict = read(dict_path)
merged_lines = check_dict.split("\n")
print("APPLIED file %s tip %s rows %d keys %d" % (PROD_REL, TIP[:12], len(rows), len(keys)))
print("PRODUCT_BLOB %s" % blob_of(prod_path))
print("DICT_BLOB %s" % blob_of(dict_path))
def line_of(text, index):
    return 1 + text.count("\n", 0, index)


print("EN_BLOCK %d..%d  ZH_BLOCK %d..%d"
      % (line_of(check_dict, check_dict.index("const en: Dict = {")),
         line_of(check_dict, check_dict.index("\n};", check_dict.index("const en: Dict = {"))),
         line_of(check_dict, check_dict.index("const zhCN: Dict = {")),
         line_of(check_dict, check_dict.index("\n};", check_dict.index("const zhCN: Dict = {")))))
for key in keys:
    hits = [index + 1 for index, text in enumerate(merged_lines) if '"%s":' % key in text]
    if len(hits) != 2:
        die("key %s defined %d times, expected 2 (en + zh)" % (key, len(hits)))
    print("  %s\tdef_lines %s" % (key, hits))
for row in rows:
    print("  after %d\t%s" % (row["tip_line"], check_prod.split("\n")[row["tip_line"] - 1].strip()[:110]))
