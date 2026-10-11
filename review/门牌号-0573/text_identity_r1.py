# -*- coding: utf-8 -*-
"""门牌号 ORD-0573 的文本不变尺：改前三臂原文 vs 改后字典解析值，逐字节对拍，两语各三枚。

原文不是我抄的：从权威尖 3085e1c05c 的那枚组件字节里用正则现取；解析值不是我读的：把改后的
LocaleContext 与一段小探针一起 esbuild 打包后 node 真跑，走产品自己那枚非钩子出口 dictionaryCopy。
两臂任一枚逐字节不等就退三，一条都不放过。
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path("D:/moodle/_qoder_menpaaihao_0558")
TIP = "3085e1c05c54d4d9fdb55cfd01b7dd664b93c28c"
COMP = "frontend/src/features/planning/PlanWithAiSheet.tsx"
KEYS = [
    ("planai.aiCredentialNotConfigured", "这台服务没有配置 AI 凭据"),
    ("planai.aiSwitchedOffByOperator", "这台服务的 AI 开关处于关闭状态"),
    ("planai.aiStatusUnreadable", "读不到 AI 状态（状态接口没有应答）"),
]
ESBUILD = "D:/moodle/CityNexus/frontend/node_modules/esbuild/bin/esbuild"
OUT = ROOT / "review/门牌号-0573/text_identity_r1.txt"

log: list[str] = []


def git_show(path: str) -> str:
    return subprocess.run(["git", "-C", "D:/moodle/CityNexus", "show", f"{TIP}:{path}"],
                          capture_output=True, text=True, encoding="utf-8").stdout


def arms_from_tip(probe: str) -> tuple[str, str]:
    src = git_show(COMP).split("\n")
    hits = [i for i, l in enumerate(src) if probe in l and l.strip().startswith("? ")]
    assert len(hits) == 1, (probe, len(hits))
    zh_line, en_line = src[hits[0]], src[hits[0] + 1]
    zh = re.match(r'^\s*\? "((?:[^"\\]|\\.)*)"$', zh_line)
    en = re.match(r'^\s*: "((?:[^"\\]|\\.)*)"\)\}$', en_line)
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
    log.append("BUNDLE_STDERR " + (b.stderr or b.stdout or "")[:600])
    log.append("RUN_STDERR " + (run.stderr or run.stdout or "")[:600])
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

bad = 0
for key, probe in KEYS:
    tip_zh, tip_en = arms_from_tip(probe)
    got = resolved.get(key, {})
    for arm, want in (("ZH", tip_zh), ("EN", tip_en)):
        have = got.get(arm)
        same = have == want
        bad += 0 if same else 1
        log.append("%s %s 长度 原%d 现%d 逐字节%s" % (key, arm, len(want), len(have or ""), "相同" if same else "不同"))
        if not same:
            log.append("  原：%s" % want[:90])
            log.append("  现：%s" % (have or "")[:90])
log.append("VERDICT %s（不等 %d 枚）" % ("两语三枚逐字节全同" if bad == 0 else "有不等", bad))
OUT.write_text("\n".join(log) + "\n", encoding="utf-8", newline="\n")
print("\n".join(log))
raise SystemExit(0 if bad == 0 else 3)
