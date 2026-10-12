# ORD-0585 mover: five dictionary keys (four new families) plus the three lib files that
# stop carrying the words inline. Every check runs in memory against the base tip and
# nothing is written unless all of them pass.
import io
import json
import os
import re
import subprocess
import sys

TREE = r"D:/moodle/_qoder_jianpanggong_0555"
BASE = "70da925d886199bd367478069fd428ca870a8a98"
DICTF = "frontend/src/i18n/LocaleContext.tsx"
FILES = {
    "keyless": "frontend/src/lib/keylessWriteDeadline.ts",
    "write": "frontend/src/lib/writeDeadline.ts",
    "clock": "frontend/src/lib/sceneClock.ts",
}
ANCHOR = '  "live.confirmedAffected": '

ROWS = [
    ("live.evidence.serverWordUnexplained",
     "服务器报的是 {state}，我们不替它解释",
     "the server reported {state}; we do not interpret it"),
    ("recover.writeDeadline.title",
     "这台设备等到 {seconds} 秒就停了",
     "This device stopped waiting after {seconds} s"),
    ("recover.writeDeadline.body",
     "服务端没有在这段时间内回答，所以这一笔的结果是未知的——不是「没有发生」。",
     "The server did not answer in that time, so the outcome of this write is unknown -- not \\\"did not happen\\\"."),
    ("recover.writeDeadline.retryGuidance",
     "请先刷新核对再决定是否重试；同一把幂等键重试是补问同一笔，不会生成第二份。",
     "Refresh and check before deciding to retry; retrying with the same idempotency key re-asks the same write instead of creating a second one."),
    ("copilot.keyless.writeUnknown",
     "{method} {path} -- 这台设备等到 {seconds} 秒就停下来了。这一笔的结果未知，不是没发生：请求已经发出去了，服务器可能还在做。也不能靠同一把键补问：这条路线不认幂等键，它没有收下这把键，没有可回读的凭条。",
     "{method} {path} -- 这台设备等到 {seconds} 秒就停下来了。这一笔的结果未知，不是没发生：请求已经发出去了，服务器可能还在做。也不能靠同一把键补问：这条路线不认幂等键，它没有收下这把键，没有可回读的凭条。"),
]
KEYS = [r[0] for r in ROWS]

EDITS = {
    "keyless": [
        ('export const KEYLESS_WRITE_DEADLINE_MS = 60_000;',
         'import { dictionaryText } from "../i18n/LocaleContext";\n\nexport const KEYLESS_WRITE_DEADLINE_MS = 60_000;'),
        ('''  return {
    text:
      `${method} ${path} -- 这台设备等到 ${seconds} 秒就停下来了。` +
      `这一笔的结果未知，不是没发生：请求已经发出去了，服务器可能还在做。` +
      `也不能靠同一把键补问：这条路线不认幂等键，它没有收下这把键，没有可回读的凭条。`,
    from: "device" as const,''',
         '''  /* This leg has no locale in its signature -- the only caller (features/planning/
     aiGenerationRun.ts) hands it the request, not the screen -- so both dictionary arms carry
     the one string these screens read before the port, and nothing here picks a language. */
  return {
    text: dictionaryText("zh-CN", "copilot.keyless.writeUnknown", { method, path, seconds }),
    from: "device" as const,'''),
    ],
    "write": [
        ('export const CLIENT_WRITE_DEADLINE_MS = 60_000;',
         'import { dictionaryCopy, dictionaryText } from "../i18n/LocaleContext";\n\nexport const CLIENT_WRITE_DEADLINE_MS = 60_000;'),
        ('''  return zh
    ? {
        title: `这台设备等到 ${seconds} 秒就停了`,
        body:
          "服务端没有在这段时间内回答，所以这一笔的结果是未知的——不是「没有发生」。" +
          "请先刷新核对再决定是否重试；同一把幂等键重试是补问同一笔，不会生成第二份。",
        seconds,
      }
    : {
        title: `This device stopped waiting after ${seconds} s`,
        body:
          "The server did not answer in that time, so the outcome of this write is unknown -- not " +
          '"did not happen". Refresh and check before deciding to retry; retrying with the same ' +
          "idempotency key re-asks the same write instead of creating a second one.",
        seconds,
      };''',
         '''  const locale = zh ? "zh-CN" : "en";
  return {
    title: dictionaryText(locale, "recover.writeDeadline.title", { seconds }),
    body:
      dictionaryCopy(locale, "recover.writeDeadline.body") +
      (zh ? "" : " ") +
      dictionaryCopy(locale, "recover.writeDeadline.retryGuidance"),
    seconds,
  };'''),
    ],
    "clock": [
        ('import { useQuery, type QueryClient } from "@tanstack/react-query";',
         'import { useQuery, type QueryClient } from "@tanstack/react-query";\nimport { dictionaryText } from "../i18n/LocaleContext";'),
        ('  return zh ? `服务器报的是 ${state}，我们不替它解释` : `the server reported ${state}; we do not interpret it`;',
         '  return dictionaryText(zh ? "zh-CN" : "en", "live.evidence.serverWordUnexplained", { state });'),
    ],
}

ENTRY_RE = re.compile(r'^  "([A-Za-z0-9._]+)": "(.*)",$')


def die(msg):
    sys.stdout.write("ABORT (nothing written) :: " + msg + "\n")
    sys.exit(1)


def show(path):
    return subprocess.check_output(["git", "-C", TREE, "show", "%s:%s" % (BASE, path)]).decode("utf-8")


def load(path):
    with io.open(os.path.join(TREE, path.replace("/", os.sep)), encoding="utf-8", newline="") as fh:
        return fh.read()


def save(path, text):
    with io.open(os.path.join(TREE, path.replace("/", os.sep)), "w", encoding="utf-8", newline="") as fh:
        fh.write(text)


def arm_spans(lines):
    out = {}
    for name, marker in (("en", "const en: Dict = {"), ("zh", "const zhCN: Dict = {")):
        start = lines.index(marker)
        end = start
        while lines[end] != "};":
            end += 1
        out[name] = (start, end)
    return out


def key_values(lines, span):
    d = {}
    for i in range(span[0] + 1, span[1]):
        m = ENTRY_RE.match(lines[i])
        if m:
            d[m.group(1)] = m.group(2)
    return d


def main():
    dict_text = load(DICTF)
    if dict_text != show(DICTF):
        die("字典页现读与基准尖不同值，先重切再动手")
    base_lines = dict_text.split("\n")
    spans = arm_spans(base_lines)
    base_kv = dict((n, key_values(base_lines, s)) for n, s in spans.items())
    for k in KEYS:
        for n in ("en", "zh"):
            if k in base_kv[n]:
                die("键名已存在：%s 在 %s 侧" % (k, n))
    gap_base = set(base_kv["en"]) ^ set(base_kv["zh"])
    if sum(1 for l in base_lines if l.startswith(ANCHOR)) != 2:
        die("锚不唯一")

    new_lines = list(base_lines)
    for name in ("zh", "en"):
        start, end = spans[name]
        out = []
        for i in range(start + 1, end):
            out.append(new_lines[i])
            if new_lines[i].startswith(ANCHOR):
                out.extend(['  "%s": "%s",' % (k, zh if name == "zh" else en) for k, zh, en in ROWS])
        new_lines[start + 1:end] = out
    new_text = "\n".join(new_lines)
    nl = new_text.split("\n")
    nspans = arm_spans(nl)
    nkv = dict((n, key_values(nl, s)) for n, s in nspans.items())

    if (set(nkv["en"]) ^ set(nkv["zh"])) != gap_base:
        die("两侧键集差变了")
    for k, zh, en in ROWS:
        if nkv["zh"].get(k) != zh or nkv["en"].get(k) != en:
            die("回读不成：%s" % k)
    for n in ("en", "zh"):
        for k, v in base_kv[n].items():
            if nkv[n].get(k) != v:
                die("既有键被动过：%s 在 %s" % (k, n))
    added_en = [k for k in nkv["en"] if k not in base_kv["en"]]
    added_zh = [k for k in nkv["zh"] if k not in base_kv["zh"]]
    if sorted(added_en) != sorted(KEYS) or added_en != added_zh:
        die("新增集合或顺序不对：%s / %s" % (added_en, added_zh))

    rebuilt = {}
    reads = {}
    for f, pairs in EDITS.items():
        text = load(FILES[f])
        if text != show(FILES[f]):
            die("%s 现读与基准尖不同值" % f)
        for old, new in pairs:
            if text.count(old) != 1:
                die("%s 锚命中 %d 次 :: %s" % (f, text.count(old), old.split("\n")[0][:60]))
            text = text.replace(old, new, 1)
        for k in KEYS:
            n = text.count('"%s"' % k)
            if n > 1:
                die("%s 在 %s 里被读 %d 次" % (k, f, n))
            reads[k] = reads.get(k, 0) + n
        rebuilt[FILES[f]] = text
    for k in KEYS:
        if reads.get(k) != 1:
            die("%s 在三枚文件里共被读 %d 次" % (k, reads.get(k, 0)))

    def cjk_lines(text):
        n = 0
        in_block = False
        for line in text.split("\n"):
            s = line.strip()
            if in_block:
                if "*/" in s:
                    in_block = False
                continue
            if s.startswith("/*"):
                if "*/" not in s:
                    in_block = True
                continue
            if s.startswith(("//", "*", "*/")):
                continue
            for lit in re.findall(r'["`]([^"`]*)["`]', line):
                if re.search(u'[一-鿿]', lit):
                    n += 1
                    break
        return n
    # sceneClock.ts keeps its paired-locale table by order, so the expected residue differs:
    # eight table rows stay, the one display string outside the table goes
    expect_cjk = {FILES["keyless"]: (3, 0), FILES["write"]: (3, 0), FILES["clock"]: (9, 8)}
    joined = {}
    for f, text in rebuilt.items():
        got = (cjk_lines(show(f)), cjk_lines(text))
        if got != expect_cjk[f]:
            die("%s 带汉字的行 %d 降到 %d，预期 %s" % (f.split("/")[-1], got[0], got[1], expect_cjk[f]))
        joined[f] = text

    save(DICTF, new_text)
    for path, text in joined.items():
        save(path, text)
    out = dict(base=BASE, keys=KEYS,
               dict_lines=dict((n, dict((k, [i for i, l in enumerate(nl, 1)
                                            if l.startswith('  "%s": ' % k)]) for k in KEYS))
                               for n in ("en", "zh")),
               files=[FILES[k] for k in ("keyless", "write", "clock")])
    save("frontend/scripts/i18n_0585_move_evidence_r1.json", json.dumps(out, ensure_ascii=False, indent=1))
    sys.stdout.write("MOVED keys=%d dict=%s files=%d\n" % (len(KEYS), {k: v for k, v in out["dict_lines"]["en"].items()}, len(joined)))


main()
