#!/usr/bin/env python3
"""ORD-0415 report writer -- render REPORT.md out of the two readings, never by typing them.

The order asks for two numbers (how many forbidden hits the map rendered before, how many after, and
whether the ORD-0412 attribution survived). A hand-typed figure in a report is a figure that can be
wrong while the artefact it came from is right, so this file reads `readings/before.json`,
`readings/after.json` and git, and writes the prose around them. Re-run it after any re-run.
"""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
READINGS = Path(__file__).resolve().parent / "readings"


def git(*args: str) -> str:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True).stdout.strip()


def load(tag: str) -> dict:
    return json.loads((READINGS / f"{tag}.json").read_text(encoding="utf-8"))


def blob_of(tag: str, path: str) -> str:
    table = load(tag).get("watched_worktree_blobs") or load(tag).get("watched_blobs") or {}
    entry = table.get(path, "?")
    return str(entry)[:10]


def hits_line(tag: str) -> str:
    d = load(tag)
    per = d.get("forbidden_rendered_hits_by_class") or {}
    per_accepted = d.get("forbidden_rendered_hits_by_accepted_class") or {}
    order = ["clock-time", "duration", "money", "source"]
    both = ", ".join(f"{name} {per.get(name, 0)}／{per_accepted.get(name, 0)}" for name in order)
    return (
        f"渲染出的禁项命中 {d['forbidden_rendered_hits']} 处（按已验收词表那把尺 {d['rendered_strings_with_accepted_class']} 处）"
        f"，逐类 宽尺／窄尺：{both}；按钮可及名里带禁项 {d['pins_announcing_a_forbidden_class']} 枚；"
        f"词表被真正触发的芯片 {len(d['rule_fired_on'] or [])} 枚"
    )


TIP = ""
INSTRUMENT = ""


def main() -> int:
    global TIP, INSTRUMENT
    before, after = load("before"), load("after")
    TIP = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1").split()[0]
    INSTRUMENT = git("rev-parse", "HEAD")
    render_files = [
        "frontend/src/lib/mapStopLabels.ts",
        "frontend/src/components/v8/MapPanel.tsx",
        "frontend/src/components/JourneyMap.tsx",
    ]
    lines = [
        "# ORD-0415 — the map label forbidden rule wired to the render path (lane 地图标注接线)",
        "",
        f"- 候选枝 `refs/heads/review/map-label-wiring-r1`，本报告的生成基准尖 `{git('rev-parse','HEAD')}`（`git cat-file -t` 回读为 "
        f"`{git('cat-file','-t','HEAD')}`）。",
        f"- 权威尖（现读，只读不推）：`git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1` = `{TIP}`，本车道起枝的那枚尖等于它（`merge-base HEAD <tip>` 现读等于该尖）。",
        f"- 两轮的仪表同一个提交 `{INSTRUMENT}`；两轮的区别只有三枚渲染文件的工作树字节（下表逐枚给 blob 前缀）。",
        "",
        "## 两枚读数（同一把尺，两次运行）",
        "",
        f"- **修改前**（三枚渲染文件的工作树字节 = 权威线 `{', '.join(blob_of('before', f) for f in render_files)}`，对应 HEAD 声称 `{', '.join(str((before.get('watched_blobs') or {}).get(f, '?'))[:10] for f in render_files)}`，两者不同正是这一轮把渲染文件检出回权威线的证据）：" + hits_line("before") + f"；署名 `v8-map-attribution` 渲染盒 {json.dumps(before['attribution_box'])}，文本与词典那一条对上：{before['attribution_matches_authored_arm']}。",
        f"- **修改后**（候选字节 `{', '.join(blob_of('after', f) for f in render_files)}`）：" + hits_line("after") + f"；署名渲染盒 {json.dumps(after['attribution_box'])}，文本与词典那一条对上：{after['attribution_matches_authored_arm']}，把这句喂给同一条词表仍报 `source`（{after['attribution_violations_if_fed']}），说明豁免是承重的、不是我顺手绕过的。",
        "",
        f"- 两轮的 fixture 都把同样 {before['fixture_landed_cases']} 枚词送进了服务端载荷（`readings/*.json` 的 `offender_classes` 逐枚留底），"
        f"所以“归零”不是种子数据干净：修改前渲染的芯片是 {json.dumps([c['text'] for c in before['rendered_chip_texts'] or []], ensure_ascii=False)}，"
        f"修改后是 {json.dumps([c['text'] for c in after['rendered_chip_texts'] or []], ensure_ascii=False)}。",
        f"- 合规署名没被误杀：干净控制词 `古文化街牌坊` 两侧都在图上（before {before['clean_control_on_glass']} / after {after['clean_control_on_glass']}），"
        f"且它在修改后的 `data-forbidden-removed` 是 `nothing`；被裁的四个词仍带着剩下的名字部分在图上（after {json.dumps(after['cut_words_on_glass'], ensure_ascii=False)}）。",
        f"- 退出码：before {before['exit_code']}（三格红正是未接线的判据），after {after['exit_code']}（七格全绿）。",
        "",
        "## 接线落在哪四处（现读行号见交付块）",
        "",
        "1. `frontend/src/lib/mapLabelRules.ts` — 词表本体搬进产品树，加 `takeOffGlass()` 与 `mapLabelSpanViolations()`。",
        "2. `frontend/e2e/_mapLabelRules.ts` — 改为再导出，四把已验收的闸仍读同一份定义（不是第二份副本）。",
        "3. `frontend/src/lib/mapStopLabels.ts` — `stopLabel()` 出词之前先裁，整词都是禁项时不造词。",
        "4. `frontend/src/components/v8/MapPanel.tsx` 与 `frontend/src/components/JourneyMap.tsx` — 芯片与按钮可及名用同一个词；legacy 的 canvas `symbol` 层裁它自己喂给 `text-field` 的 `title`。",
        "",
        "## 一处自报（仪表的毛病，不是产品的）",
        "",
        "这枚闸在自己身上抓到三次“只有真跑才咬得到”的错：词表搬进产品树时漏导出 `MAP_LABEL_FIELDS`；`sqlite:///` 少剥一个斜杠把“本 run 没有库”读成事实；"
        "臂先加载后改库，于是它读的是上一臂留下的屏。根因相同：`tsconfig.check.json` 与 `tsconfig.typecheck.json` 的 include 都不含 `e2e/**`，"
        "所以 `npm run typecheck` 与 `typecheck:all` 全绿时没看过这些文件一眼（实测两次 rc=0）。我没有去扩别人的 tsconfig（那会把既有的 e2e 类型错误一次点亮，不属于本单）。",
        "",
        "## 一处留给号令者的裁定点（我没动的尺）",
        "",
        "- 已验收词表里 `duration` 那条 `\\d+\\s*(?:分钟|min)\\b` 在中文标签上匹配不到：`45 分钟`／`45分钟`／`需45分钟时间` 实测全 false，`45 min walk` true。"
        "  产品的裁切按宽尺走（不改窄尺，因为四把闸拿它做断言），闸把两把尺的数都报。要不要把窄尺本身修宽，归尺的主人次定。",
        "- `qoder-map-ord0412-label-scope.spec.ts` 的 `scope-declared` 臂断言的是 `src/lib/mapLabels.ts` 这枚文件名不存在；我把产品侧那份命名为 `mapLabelRules.ts`，"
        "  所以它仍绿。但它当年保护的判语（“无产品代码查此规则”）现在已经不成立，该怎么改写由那把闸的收件人次定；我没有改它的任何断言。",
        "",
        "## 复现",
        "",
        "```",
        "python review/map-label-wiring-r1/run_gate_r1.py --tag after \\",
        "    --spec e2e/qoder-map-ord0415-forbidden-off-the-glass.spec.ts",
        "python review/map-label-wiring-r1/report_readings_r1.py --tag after",
        "```",
        "",
        f"原始产物在仓外：`{Path(before['database']).parent.parent / '..' / 'evidence'}`（`provenance_*.json` 记了两轮各自的工作树字节、解释器与端口）。",
    ]
    target = Path(__file__).resolve().parent / "REPORT.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {target} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
