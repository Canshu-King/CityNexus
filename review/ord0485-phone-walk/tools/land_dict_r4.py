"""ORD-0485 -r3 -- land the four word-table rows on the live tip's own bytes.

The recut rule (CMDR 15:12, restated 00:13): base = the tip read now by `git ls-remote`, and my four
entries go onto that generation's actual dictionary bytes without overwriting anyone else's line.
Each anchor is asserted to match exactly once *before* any write, so a moved neighbourhood aborts
the landing instead of silently inserting into the wrong table.
"""
import re
import sys

PATH = sys.argv[1]
src = open(PATH, encoding="utf-8", newline="").read()
lines = src.split("\n")


def one(pattern):
    hits = [i for i, line in enumerate(lines) if re.match(pattern, line)]
    if len(hits) != 1:
        raise SystemExit("ABORT_ANCHOR_NOT_UNIQUE %s -> %r" % (pattern, hits[:6]))
    return hits[0]


anchors = {
    "poiImport.channelLocal": {
        "after_en": r'^\s*"poiImport\.channelNote": "Local parser; no third-party reading service\.",$',
        "after_zh": r'^\s*"poiImport\.channelNote": "本地解析器；不接第三方读取服务。",$',
    },
    "exec.state.notStarted": {
        "after_en": r'^\s*"exec\.state\.skipped": "SKIPPED",$',
        "after_zh": r'^\s*"exec\.state\.skipped": "已跳过",$',
    },
}
values = {"poiImport.channelLocal": ("Local channel", "本地通道"),
          "exec.state.notStarted": ("NOT STARTED", "未开始")}

for key, already_missing in (("poiImport.channelLocal", True), ("exec.state.notStarted", True)):
    present = [i for i, line in enumerate(lines) if re.match(r'^\s*"%s":' % re.escape(key), line)]
    if present:
        raise SystemExit("ABORT_KEY_ALREADY_LANDED %s at %r" % (key, present))

edits = []
for key, spec in anchors.items():
    en_at = one(spec["after_en"]) + 1
    zh_at = one(spec["after_zh"]) + 1
    en, zh = values[key]
    edits.append((en_at, '  "%s": "%s",' % (key, en)))
    edits.append((zh_at, '  "%s": "%s",' % (key, zh)))

for at, text in sorted(edits, reverse=True):
    lines.insert(at, text)

open(PATH, "w", encoding="utf-8", newline="").write("\n".join(lines))
raw = open(PATH, "rb").read()
print("LANDED file=%s bytes=%d CR=%d LF=%d" % (PATH, len(raw), raw.count(b"\r"), raw.count(b"\n")))
for key in values:
    hits = [i + 1 for i, line in enumerate(raw.decode("utf-8").split("\n"))
            if re.match(r'^\s*"%s":' % re.escape(key), line)]
    print("KEY %s lines=%s" % (key, hits))
