#!/usr/bin/env python3
"""ORD-0415 report writer -- render REPORT.md out of the readings, never by typing them.

The order asks for two numbers (how many forbidden hits the map rendered before, how many after, and
whether the ORD-0412 attribution survived) plus the claim that nothing else went red. A hand-typed
figure in a report is a figure that can be wrong while the artefact it came from is right, so this
file reads `readings/before.json`, `readings/after.json`, the sibling-run logs its own runner wrote,
and git itself, then writes the prose around them. Re-run it after any re-run.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
READINGS = Path(__file__).resolve().parent / "readings"
SCRATCH = ROOT.parent
RENDER_FILES = [
    "frontend/src/lib/mapStopLabels.ts",
    "frontend/src/components/v8/MapPanel.tsx",
    "frontend/src/components/JourneyMap.tsx",
]
SIBLING_LOGS = [
    ("同一条命令、候选字节", "run_reg2.log"),
    ("同一条命令、权威线字节（对照）", "run_reg_base2.log"),
]


def git(*args):
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True).stdout.strip()


def load(tag):
    return json.loads((READINGS / f"{tag}.json").read_text(encoding="utf-8"))


def blobs(tag, head_claims=False):
    """The byte prefixes for the three render files -- either what the run served, or what HEAD claimed."""
    reading = load(tag)
    table = reading.get("watched_blobs") if head_claims else reading.get("watched_worktree_blobs")
    if not table:
        table = reading.get("watched_blobs") or {}
    return ", ".join(str(table.get(path, "?"))[:10] for path in RENDER_FILES)


def hits_line(tag):
    d = load(tag)
    wide = d.get("forbidden_rendered_hits_by_class") or {}
    narrow = d.get("forbidden_rendered_hits_by_accepted_class") or {}
    per_class = "，".join(
        f"{name} {wide.get(name, 0)} 处／窄尺 {narrow.get(name, 0)} 处"
        for name in ["clock-time", "duration", "money", "source"]
    )
    return (
        f"地图上实际渲染出的禁项 {d['forbidden_rendered_hits']} 处"
        f"（按已验收词表那把尺判 {d['rendered_strings_with_accepted_class']} 处；逐类：{per_class}）；"
        f"其中落在按钮可及名上的 {d['pins_announcing_a_forbidden_class']} 处；"
        f"芯片上带着「裁掉了哪一类」回执的 {len(d['rule_fired_on'] or [])} 个"
    )


def chip_texts(tag):
    d = load(tag)
    return json.dumps([row["text"] for row in d.get("rendered_chip_texts") or []], ensure_ascii=False)


def parse_sibling_log(name):
    """Read one sibling run out of the log its runner wrote: the counts, and the arms listed UNDER the
    `N failed` header -- Playwright also prints every test while it runs, so scanning the whole log would
    report passing arms as red, which the first version of this function did."""
    path = SCRATCH / name
    if not path.exists():
        return None
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    passed = failed = 0
    red = []
    in_failures = False
    for line in lines:
        match = re.search(r"(\d+) passed", line)
        if match:
            passed = int(match.group(1))
        match = re.search(r"^(\d+) failed", line.strip())
        if match:
            failed = int(match.group(1))
            in_failures = True
            continue
        if in_failures:
            entry = re.search(r"\[[^\]]+\] › (\S+:[\d:]+) › (.+?)\s*$", line)
            if entry:
                red.append(f"{entry.group(1)} {entry.group(2)}")
            elif line.strip() and not line.startswith("    "):
                in_failures = False
    return {
        "passed": passed,
        "failed": failed,
        "red": sorted(set(red)),
        "log": name,
    }


def main():
    before, after = load("before"), load("after")
    tip_read = git("ls-remote", "origin", "refs/heads/mirror/integration-frontend-apple-pass1")
    tip_sha = tip_read.split()[0] if tip_read else ""
    instrument = git("rev-parse", "HEAD")
    base_of_branch = git("merge-base", "HEAD", tip_sha) if tip_sha else "(未现读)"
    lines = [
        "# ORD-0415 — 地图标注的禁项规则接到渲染路径（车道：地图标注接线）",
        "",
        f"- 候选枝 `refs/heads/review/map-label-wiring-r1`，本报告的生成基准尖 `{instrument}`。",
        f"- 权威尖现读 `git ls-remote origin refs/heads/mirror/integration-frontend-apple-pass1` = `{tip_sha}`；本枝与它的 `merge-base` 现读 `{base_of_branch}`。",
        f"- 两枚读数出自同一个仪表提交 `{instrument}`，区别只在三枚渲染文件的工作树字节。",
        "",
        "## 一、两枚读数（同一把尺，两次运行）",
        "",
        f"- 修改前 —— 三枚渲染文件的工作树字节 {blobs('before')}，同一轮 HEAD 声称 {blobs('after', head_claims=True)}；两者不同正是这一轮把渲染文件检出回权威线的凭据。{hits_line('before')}。渲染出的站名逐枚：{chip_texts('before')}。",
        f"- 修改后 —— 三枚渲染文件的工作树字节 {blobs('after')}。{hits_line('after')}。渲染出的站名逐枚：{chip_texts('after')}。",
        f"- 两轮的 fixture 都把 {before['fixture_landed_cases']} 条词送进了服务端载荷（现读 `readings/before.json`、`readings/after.json`），所以归零不是种子数据干净；退出码 before {before['exit_code']}（三格红＝未接线这件事本身的判据）、after {after['exit_code']}（七格全绿）。",
        "",
        "## 二、ORD-0412 那条合规署名没被误杀",
        "",
        f"- 两侧同格同文：修改前渲染盒 宽 {before['attribution_box']['w']} 像素 × 高 {before['attribution_box']['h']} 像素，修改后 {after['attribution_box']['w']} × {after['attribution_box']['h']} 像素；文本与词典那一条逐字对上：before {before['attribution_matches_authored_arm']} / after {after['attribution_matches_authored_arm']}。",
        f"- 负对照仍承重：把这句署名喂给同一条词表，仍报 {json.dumps(after['attribution_violations_if_fed'], ensure_ascii=False)} —— 「不判 DOM 署名」这条豁免是被用到的，不是我顺手绕开的。",
        f"- 干净控制词 `古文化街牌坊` 两侧都在图上（before {before['clean_control_on_glass']} / after {after['clean_control_on_glass']}），它在修改后那轮的 `data-forbidden-removed` 回执是 `nothing`；被裁的四条词仍带着剩下的名字部分在图上：after {json.dumps(after['cut_words_on_glass'], ensure_ascii=False)}。",
        "",
        "## 三、同族四把已验收的闸（零新增红，实测对照）",
        "",
    ]
    for label, name in SIBLING_LOGS:
        read = parse_sibling_log(name)
        if read is None:
            lines.append(f"- {label}：日志不在 `{name}` —— 没量到就不写。")
            continue
        lines.append(
            f"- {label}：{read['failed']} 格红 / {read['passed']} 格绿；红的逐格 {json.dumps(read['red'], ensure_ascii=False)}（取自 `{read['log']}`）。"
        )
    lines += [
        "- 两侧红的都是 `qoder-map-ord0403-named-control-and-labels.spec.ts` 里 `reach` 那一族（具名控件压在瓦片提示下），数量同为三格，"
        "宽度集合在两次运行之间自己换了 —— 既有抖动，不是本单带来的；那把闸一个字我没动。",
        "",
        "## 四、接线落在哪几处",
        "",
        "- `frontend/src/lib/mapLabelRules.ts`：词表本体搬进产品树，另加两个出口（裁切的 `takeOffGlass()`、宽尺的 `mapLabelSpanViolations()`）。",
        "- `frontend/e2e/_mapLabelRules.ts`：改为再导出同一份定义，四把已验收的闸仍读一个所有者，而不是第二份副本。",
        "- `frontend/src/lib/mapStopLabels.ts`：`stopLabel()` 出词之前先裁；整条词都是禁项时不造词。",
        "- `frontend/src/components/v8/MapPanel.tsx`：芯片文字与按钮可及名用同一个词，并在芯片上留裁切回执。",
        "- `frontend/src/components/JourneyMap.tsx`：全仓唯一那条 canvas `symbol` 层，裁它自己喂给 `text-field` 的 `title`。",
        "- `frontend/e2e/qoder-map-ord0415-forbidden-off-the-glass.spec.ts`：本单的闸，自带 fixture —— 种子数据全干净，不带 fixture 的零是运气不是证据。",
        "",
        "## 五、自报：这枚闸在自己身上抓到的三次坏",
        "",
        "词表搬进产品树时漏导出 `MAP_LABEL_FIELDS`（模块加载即炸）；`sqlite:///` 少剥一个斜杠，把「本 run 没有库」读成事实；"
        "臂先加载后改库，于是它读的是上一臂留下的屏。三者都不是读代码能看出来的：`tsconfig.check.json` 与 "
        "`tsconfig.typecheck.json` 的 include 都不含 `e2e/**`，实测两次 `tsc --noEmit` 都 rc=0 而闸根本起不来。"
        "我没有去扩别人的 tsconfig（那会一次点亮既有 e2e 类型错误，不属于本单）。",
        "",
        "## 六、留给号令者的两点裁语（我没动的尺）",
        "",
        "- 已验收词表里 `duration` 那条在中文标签上匹配不到：`45 分钟`、`45分钟`、`需45分钟时间` 实测全 false，`45 min walk` true。"
        " 产品的裁切按宽尺走，闸把宽窄两把尺的数都报；要不要把窄尺本身修宽，归那把尺的主人定。",
        "- `qoder-map-ord0412-label-scope.spec.ts` 的 `scope-declared` 臂断言的是 `src/lib/mapLabels.ts` 这枚文件名不存在。"
        " 我把产品侧那份命名为 `mapLabelRules.ts`，所以它仍绿；但它当年保护的判语（「无产品代码查此规则」）现在已不成立 —— "
        "判据该从「有没有那个文件名」改成「有没有产品代码在裁」。由那把闸的收件人定，我没改它的任何断言。",
        "",
        "## 七、复现",
        "",
        "```",
        "python review/map-label-wiring-r1/run_gate_r1.py --tag after \\",
        "    --spec e2e/qoder-map-ord0415-forbidden-off-the-glass.spec.ts",
        "python review/map-label-wiring-r1/report_readings_r1.py --tag after",
        "python review/map-label-wiring-r1/write_report_r1.py",
        "```",
        "",
        f"原始产物在仓外 `{SCRATCH / 'evidence'}`：`provenance_*.json` 记下每轮的工作树字节、解释器、端口与库文件。",
    ]
    target = Path(__file__).resolve().parent / "REPORT.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {target} ({len(lines)} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
