"""Regression arm: sceneClock.ts reads its nine traveller words from the shared
dictionary instead of carrying two languages inline.

MUTUALLY_EXCLUSIVE_VARIANT: 把两枚源文件回退到现尖字节的独立副本上跑本臂必须红。

用法：`python i18n_scene_clock_arm_r1.py [tree_root]`
tree_root 缺省为本臂所在树；指到一份回退副本（例如同代基线树）时应咬红。
冻结期望在 i18n_scene_clock_expect.json，那九个值由生成器从现尖字节抄出，非手打。
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BS = chr(96)
CJK = re.compile(r"[一-鿿]")
DQ = r'"((?:[^"\\\n]|\\.)*)"'
TPL = BS + r"((?:[^\n]|\\.)*)" + BS
STR = r"(?:" + DQ + r"|" + TPL + r")"
PAIR = re.compile(r"\?\s*" + STR + r"\s*:\s*" + STR, re.S)
KEY_RE = re.compile(r'^\s*"([A-Za-z0-9._-]+)"\s*:\s*"(.*)"\s*,?\s*$')

CLOCK = "lib/sceneClock.ts"
DICT = "i18n/LocaleContext.tsx"
PANEL = "SimulationPanel.tsx"

if len(sys.argv) > 1:
    SRC = Path(sys.argv[1]).resolve() / "frontend" / "src"
else:
    SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"

EXPECT = json.loads(
    (Path(__file__).resolve().parent / "i18n_scene_clock_expect.json").read_text(encoding="utf-8")
)


def find(rel: str) -> Path:
    for root in SRC.rglob(rel):
        return root
    raise SystemExit("missing %s under %s" % (rel, SRC))


def read(rel: str) -> str:
    return find(rel).read_text(encoding="utf-8")


def dict_blocks(text: str):
    """{lang: {key: (value, line)}} -- same block split the copy gate uses."""
    lines = text.split("\n")
    marks = [i for i, ln in enumerate(lines) if re.match(r"^const (en|zhCN): Dict", ln)]
    if len(marks) != 2:
        raise SystemExit("expected 2 Dict blocks, found %d" % len(marks))
    out = {}
    for idx, start in enumerate(marks):
        lang = re.match(r"^const (\w+):", lines[start]).group(1)
        stop = marks[idx + 1] if idx + 1 < len(marks) else len(lines)
        table = {}
        for i in range(start, stop):
            m = KEY_RE.match(lines[i].rstrip("\r"))
            if m:
                table.setdefault(m.group(1), (m.group(2), i + 1))
        out[lang] = table
    return out


def cjk_pairs(text: str):
    hits = []
    for m in PAIR.finditer(text):
        a = m.group(1) if m.group(1) is not None else m.group(2)
        b = m.group(3) if m.group(3) is not None else m.group(4)
        if (CJK.search(a or "") and not CJK.search(b or "")) or (
            CJK.search(b or "") and not CJK.search(a or "")
        ):
            hits.append((text.count("\n", 0, m.start()) + 1, a, b))
    return hits


def main() -> int:
    clock = read(CLOCK)
    panel = read(PANEL)
    blocks = dict_blocks(read(DICT))
    en, zh = blocks["en"], blocks["zhCN"]
    checks: list[tuple[str, bool, str]] = []

    def ck(name: str, ok: bool, detail: str = "") -> None:
        checks.append((name, bool(ok), detail))

    # 1. 本件的覆盖面：屏上那些字不再以两种语言并排写在这枚模块里
    left = cjk_pairs(clock)
    ck("sceneClock 内联双语归零", not left, "剩 %d 处%s" % (len(left), (" 首处行 " + str(left[0][0])) if left else ""))

    # 2-3. 九枚键两臂齐，且逐字等于冻结期望（期望由生成器抄自现尖字节）
    missing_en = [k for k in EXPECT if k not in en]
    missing_zh = [k for k in EXPECT if k not in zh]
    ck("en 臂不缺键", not missing_en, "缺 %s" % (missing_en or "无"))
    ck("zhCN 臂不缺键", not missing_zh, "缺 %s" % (missing_zh or "无"))
    drift = []
    for k, want in EXPECT.items():
        if k in en and en[k][0] != want["en"]:
            drift.append("%s en@%d" % (k, en[k][1]))
        if k in zh and zh[k][0] != want["zh"]:
            drift.append("%s zh@%d" % (k, zh[k][1]))
    ck("九枚值逐字等于现尖上屏字", not drift, "改动了 %s" % (drift or "无"))

    # 4. 组件确实逐枚问到这些键，且没有别的模块替它抄句子
    asked = set(re.findall(r't\("(clock\.[A-Za-z.]+)"', clock))
    ck("九枚键都被模块自己问到", asked == set(EXPECT), "问到 %d 枚" % len(asked))
    ck("zh: boolean 形制在本文件归零", "zh: boolean" not in clock, "读自 %s" % CLOCK)
    ck("两枚函数改接收词函数", clock.count("t: Say): string {") == 2, "形制 `t: Say): string {` 现读 %d 次" % clock.count("t: Say): string {"))

    # 5. 插值契约：占位符两边同集，调用处把服务器原值转成字符串（保住旧的 null 读法）
    ph = re.compile(r"\{(\w+)\}")
    mismatch = [
        k
        for k in EXPECT
        if ph.findall(en[k][0] if k in en else "") != ph.findall(zh[k][0] if k in zh else "")
    ]
    ck("占位符两臂同集", not mismatch, "不同集 %s" % (mismatch or "无"))
    ck(
        "unknown 那枚把 state 转成字符串",
        't("clock.evidence.unknown", { state: String(state) })' in clock,
        "旧写法 `${state}` 对 null 输出 `null`，String() 保住这条",
    )

    # 6. 消费面：只有模拟舞台问这两枚函数，签名改动不漏任何调用者
    consumers = []
    for p in SRC.rglob("*.ts*"):
        if p.name in (CLOCK.split("/")[-1],):
            continue
        body = p.read_text(encoding="utf-8", errors="replace")
        if re.search(r"\b(basisWord|evidenceWord)\(", body):
            consumers.append(p.name)
    ck("调用者只有模拟舞台", set(consumers) == {PANEL}, "现读调用者 %s" % (sorted(set(consumers)) or "无"))
    ck(
        "舞台两处传的是 t",
        panel.count("?? null, t)") == 2 and "?? null, zh)" not in panel,
        "`?? null, t)` 现读 %d 处，`?? null, zh)` 现读 %d 处" % (panel.count("?? null, t)"), panel.count("?? null, zh)")),
    )
    ck("舞台引入了 useT", "import { useLocale, useT }" in panel and "const t = useT();" in panel, "读自 %s" % PANEL)

    # 7. 反控：本件不收的形制必须还活着（它们不是文案，或属别车道的面）
    keep = [
        ('if (!iso) return "' + chr(8212) + '";', "缺席标记：两臂同字，不是双语对"),
        ("demo/scene failed (", "日志串"),
        ("SCENE_ENVELOPE_UNRECOGNISED", "机器码"),
        ("SCENE_READ_FAILED", "机器码"),
        ("Sliced, never parsed", "sceneInstant 的说明注释"),
    ]
    for probe, why in keep:
        ck("反控存活 %s" % probe[:26], probe in clock, why)
    ck(
        '反控存活：舞台自己的 "收起舞台" 未被本件改动',
        'zh ? "收起舞台" : "Close the stage"' in panel,
        "那六处属 SimulationPanel 这一格，本件只换两处取词参数",
    )
    stage_pairs = [n for n, _a, _b in cjk_pairs(panel)]
    ck("舞台的内联双语数目未被本件改动", len(stage_pairs) == 23, "现读 %d 处（现尖同尺读数 23）" % len(stage_pairs))

    width = max(len(n) for n, _o, _d in checks)
    bad = 0
    for name, ok, detail in checks:
        print("%s %-*s %s" % ("OK  " if ok else "FAIL", width, name, detail))
        bad += 0 if ok else 1
    print("checks=%d failed=%d" % (len(checks), bad))
    return 0 if bad == 0 else 1


sys.exit(main())
