# -*- coding: utf-8 -*-
"""门牌号 ORD-0573 第四批的文本不变尺：改前八枚双臂原文 vs 改后字典解析值，逐字节对拍，两语各四枚。

与 r4 同一套，只多认一种英文臂收尾（对象字段那形以 `",` 结束）。改前基线不是我抄的：从枝尖
659e08de67 那代组件字节里正则现取；解析值是把改后的字典与一枚探针一起 esbuild 打包后 node 真跑、
走产品自己那枚非钩子出口 dictionaryCopy 取回来的。字典那一层还分两次判：存进去的字节必须等于源码
里摘下来的字节，解码后渲染出的文字必须等于当年渲染的那串——带 \" 的那一枚只有第二层会红。
任一枚不合就退三；打包或运行返回码非零退四并贴 stderr，绝不拿坏尺报文本差。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_menpaaihao_0558")
TIP = "ba118336b94f11c6a81e2157dcda8d764a51c50a"
COMP = "frontend/src/features/planning/PlanWithAiSheet.tsx"
KEYS = [
    ("plan.baselineUnavailableBody", "无法确认本次是否生成了新方案"),
    ("plan.noPlansProducedBody", "服务器说这次没排出可行方案"),
    ("plan.assistantUnreachableBody", "规划助手这次没能连上"),
    ("plan.couldNotFinishBody", "这次没能生成方案。你的行程没有被改动"),
]
ESBUILD = "D:/moodle/CityNexus/frontend/node_modules/esbuild/bin/esbuild"
OUT = ROOT / "review/门牌号-0573/text_identity_r6.txt"
DICT_SRC = (ROOT / "frontend/src/i18n/LocaleContext.tsx").read_text(encoding="utf-8")
EN_TAILS = (r'(?:\)\}|\})$', r',$', r'}$')

log: list[str] = []


def git_show(path: str) -> str:
    return subprocess.run(["git", "-C", "D:/moodle/CityNexus", "show", f"{TIP}:{path}"],
                          capture_output=True, text=True, encoding="utf-8").stdout


def js_decode(inner: str) -> str:
    out, i = [], 0
    while i < len(inner):
        c = inner[i]
        if c == "\\" and i + 1 < len(inner):
            nxt = inner[i + 1]
            out.append({'"': '"', "'": "'", "\\": "\\", "/": "/", "n": "\n", "t": "\t"}.get(nxt, nxt))
            i += 2
            continue
        out.append(c)
        i += 1
    return "".join(out)


def arms_from_tip(probe: str) -> tuple[str, str]:
    src = git_show(COMP).split("\n")
    hits = [i for i, l in enumerate(src) if probe in l and l.strip().startswith("? ")]
    assert len(hits) == 1, (probe, len(hits))
    zh_line, en_line = src[hits[0]], src[hits[0] + 1]
    zh = re.match(r'^\s*\? "((?:[^"\\]|\\.)*)"$', zh_line)
    en = None
    for tail in EN_TAILS:
        en = re.match(r'^\s*: "((?:[^"\\]|\\.)*)"' + tail, en_line)
        if en:
            break
    assert zh and en, (zh_line[:40], en_line[:40])
    return zh.group(1), en.group(1)


probe_ts = ROOT / "review/门牌号-0573/_text_identity_probe.ts"
wanted = ", ".join('"%s"' % k for k, _ in KEYS)
probe_ts.write_text(
    "import { dictionaryCopy } from '../../frontend/src/i18n/LocaleContext';\n"
    "const keys = [" + wanted + "];\n"
    "for (const k of keys) {\n"
    "  console.log('EN|' + k + '|' + dictionaryCopy('en' as never, k));\n"
    "  console.log('ZH|' + k + '|' + dictionaryCopy('zh-CN' as never, k));\n"
    "}\n",
    encoding="utf-8", newline="\n",
)
bundled = ROOT / "review/门牌号-0573/_text_identity.cjs"
b = subprocess.run(["node", ESBUILD, str(probe_ts), "--bundle", "--platform=node", "--format=cjs",
                    "--outfile=" + str(bundled)], capture_output=True, text=True, encoding="utf-8", errors="replace")
log.append("bundle_rc=%d" % b.returncode)
run = subprocess.run(["node", str(bundled)], capture_output=True, text=True, encoding="utf-8", errors="replace")
log.append("run_rc=%d" % run.returncode)
if b.returncode != 0 or run.returncode != 0:
    log.append("尺坏了不是文本变了，先看这两段：")
    log.append("BUNDLE_STDERR " + (b.stderr or b.stdout or "")[:900])
    log.append("RUN_STDERR " + (run.stderr or run.stdout or "")[:900])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(log) + "\n", encoding="utf-8", newline="")
    print("\n".join(log))
    raise SystemExit(4)
resolved: dict[str, dict[str, str]] = {}
for line in run.stdout.split("\n"):
    if line.count("|") == 2:
        arm, key, val = line.split("|", 2)
        resolved.setdefault(key, {})[arm] = val
bundled.unlink(missing_ok=True)
probe_ts.unlink(missing_ok=True)


def dict_raw(key: str, arm: str) -> str:
    hits = re.findall(r'^[ \t]*"%s": "((?:[^"\\]|\\.)*)",?$' % re.escape(key), DICT_SRC, re.M)
    want = 0 if arm == "EN" else 1
    return hits[want] if len(hits) > want else "（字典里不足两臂）"


bad = 0
for key, probe in KEYS:
    tip_zh, tip_en = arms_from_tip(probe)
    got = resolved.get(key, {})
    for arm, raw_src in (("ZH", tip_zh), ("EN", tip_en)):
        stored = dict_raw(key, arm)
        want = js_decode(raw_src)
        have = got.get(arm)
        copied = stored == raw_src
        renders = have == want
        bad += 0 if (copied and renders) else 1
        log.append("%s %s 源%d 存%d 解%d 现%d %s%s" % (
            key, arm, len(raw_src), len(stored), len(want), len(have or ""),
            "存字节同" if copied else "存字节不同", "/渲染同" if renders else "/渲染不同"))
        if not (copied and renders):
            log.append("  源（未解码）：%s" % raw_src[:80])
            log.append("  字典存的：%s" % stored[:80])
            log.append("  解出来的：%s" % (have or "")[:80])
log.append("VERDICT %s（不合 %d 臂）" % ("两语四枚：存字节与渲染文字都逐字节同" if bad == 0 else "有不合", bad))
OUT.write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
print("\n".join(log))
raise SystemExit(0 if bad == 0 else 3)
