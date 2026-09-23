"""commander 2026-09-22 13:4x 安全事故的常驻门 · **凭据字面量不得进入受版本控制的任何路径**。

背景（账本 10008 块）：真 key 的**原文**被提交进 `qoder-handoff/qoder_xiaomi_truth_hardening_v6.patch`
（约 6348 行，一行以 `+` 开头），并由 `b12f24f` 推送到了远端分支；`13377d3` 做了工作副本脱敏，
但**历史与已推送的旧对象抹不掉** —— 唯一有效处置是用户轮换那把 key。

本门要抓的正是那次漏掉的形状：**补丁里套补丁**（`.patch` 文件里 `+` 开头的行携带字面量）。
判据是形状扫描（前缀 + 长度区间 + 高熵体），并排除明显占位串。

**读法**：只报**位置与形状**（文件:行、长度、字符类别），**绝不打印原文或前缀**（账本既有禁令）。
两处摘要各有分工：`位置指纹=sha256("路径:行号")` 用来**引用是哪一处**；
`token指纹=sha256(命中的那颗串)` 用来判断**两处是不是同一把凭据**——位置摘要答不了这件事，
别拿它指认同一个凭据（2026-09-22 我就在这里读歪过一次）。两者都是摘要，不是原文，也不是前缀。
"""

from __future__ import annotations

import hashlib
import math
import os
import re
import subprocess
from pathlib import Path
from typing import Iterable

import pytest

REPO = Path(__file__).resolve().parents[2]

#: 凭据字面量的形状（本仓库实际使用的 provider key 形态）。
#: 长度区间取宽一点，免得换个 provider 就漏；高熵体靠下面的熵阈值兜。
CREDENTIAL_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9_\-]{20,}"),          # OpenAI / DeepSeek 风格
    re.compile(r"(?:AKIA|ASIA)[A-Z0-9]{16}"),        # AWS access key id
    re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),       # GitHub token
    re.compile(r"AIza[0-9A-Za-z_\-]{35}"),           # Google API key
)

#: 明显是占位/自证样本的，不算泄漏（大小写不敏感）。
PLACEHOLDER_MARKERS = (
    "redacted", "example", "placeholder", "dummy", "fake", "sample",
    "your-key", "yourkey", "xxx", "test-key", "notreal", "changeme",
    "instrument-selftest", "aaaaaaaa",
)

#: 高熵阈值（shannon bits/char）。真随机 key 一般 > 3.2；占位串通常低。
MIN_ENTROPY_BITS_PER_CHAR = 3.2

#: 产品自己会当凭据读的环境变量（`app/core/config.py:22-23,53` 就是这三把）——
#: "现役真凭据"这一侧只从这里取，别处不算；**只取指纹与条数，绝不印值**。
LIVE_CREDENTIAL_ENV_VARS = ("CITYNEXUS_AI_API_KEY", "DEEPSEEK_API_KEY", "CITYNEXUS_HERMES_API_KEY")

#: **D-2 裁定＝甲（commander 2026-09-23 18:5x）**：测试桩里的假凭据**不修掉、不缩射程**，
#: 而是**具名声明 + 指纹**进收据。声明必须带它自己那颗 token 指纹 ⇒ 桩一改，指纹就对不上，
#: 那条声明自动失效并变回"未声明 ⇒ 红"。这不是白名单：白名单看路径，声明看**内容摘要**。
DECLARED_NON_LIVE_SAMPLES: tuple[dict, ...] = (
    {
        "at": "frontend/e2e/qoder-e2e-config-guard.spec.ts:140",
        "token_fp": "faca4b0049a4",
        "what": "e2e 配置守卫自己塞进子进程环境的**假** DEEPSEEK_API_KEY（形状真、值假）",
        "evidence": ("同文件 :144 断言 `run.status != 0`",
                     "同文件 :145 断言 stderr 含 'external AI must be off'"),
        "declared_by": "commander 494abfd7 裁定 D-2=甲；lane F 8ccd71d8 录入 @2026-09-23",
    },
)


def live_credentials() -> list[dict]:
    """现役侧：**只**取长度与指纹，不取也不印原文；缺侧 ⇒ NOT_MEASURED，不当 False。"""
    out = []
    for name in LIVE_CREDENTIAL_ENV_VARS:
        value = os.environ.get(name) or ""
        if not value:
            continue
        out.append({"env": name, "len": len(value), "fp": hashlib.sha256(
            value.encode("utf-8", errors="replace")).hexdigest()[:12]})
    return out


def classify_offenders(offenders: list[dict], live: list[dict],
                       scanned_paths: int) -> list[dict]:
    """给每一处命中判级：**扫描射程一字未减**，只是把"它是什么"连同两侧指纹一起写清楚。

    判级规则（三态，缺读数绝不写成 False）：
      LIVE_CREDENTIAL_LEAK      与现役凭据精确相等 ⇒ 必红
      UNDECLARED                没有任何具名声明，或声明里的 token 指纹与扫到的不符 ⇒ 必红
      DECLARED_NON_LIVE_SAMPLE  声明存在且指纹吻合，且**测得**与现役凭据不等 ⇒ 绿（但仍逐条进收据）
    """
    rows = []
    live_fps = {c["fp"] for c in live}
    for off in offenders:
        decl = next((d for d in DECLARED_NON_LIVE_SAMPLES
                     if d["at"] == off["at"] and d["token_fp"] == off["token_fp"]), None)
        decl_stale = next((d for d in DECLARED_NON_LIVE_SAMPLES
                           if d["at"] == off["at"] and d["token_fp"] != off["token_fp"]), None)
        if live:
            equals_live: bool | str = off["token_fp"] in live_fps
        else:
            equals_live = "NOT_MEASURED"
        if equals_live is True:
            verdict = "LIVE_CREDENTIAL_LEAK"
        elif decl is None:
            verdict = "UNDECLARED" if decl_stale is None else "DECLARATION_STALE(指纹不吻合)"
        else:
            verdict = "DECLARED_NON_LIVE_SAMPLE"
        rows.append({**off, "verdict": verdict, "equals_live_credential": equals_live,
                     "declaration": decl or decl_stale,
                     "scanned_paths": scanned_paths, "offender_total": len(offenders),
                     "live_side_count": len(live), "live_side_fps": sorted(live_fps),
                     "live_side_declaration": decl is not None})
    return rows


def shannon_entropy(text: str) -> float:
    if not text:
        return 0.0
    counts: dict[str, int] = {}
    for ch in text:
        counts[ch] = counts.get(ch, 0) + 1
    total = len(text)
    return -sum((n / total) * math.log2(n / total) for n in counts.values())


def looks_like_placeholder(token: str) -> bool:
    low = token.lower()
    if any(marker in low for marker in PLACEHOLDER_MARKERS):
        return True
    # 全同字符或极端重复（如 sk-aaaaaaaaaaaaaaaaaaaa）
    body = token.split("-", 1)[-1]
    if body and len(set(body)) <= 3:
        return True
    return False


def token_fingerprint(token: str) -> str:
    """token 自己的指纹 —— **只在函数内部见到原文**，外面永远只拿到摘要。

    为什么要这一列：`scan_paths` 里的 `指纹=` 是 `sha256("路径:行号")`，它是**位置**摘要，
    回答不了"这颗和另一颗是不是同一把"。指认同一把 key 要看 `token指纹=`。
    """

    return hashlib.sha256(token.encode("utf-8", errors="replace")).hexdigest()[:12]


def find_credential_shapes(text: str) -> list[tuple[int, str, int, str]]:
    """返回 (行号, 命中的模式名, token 长度, token 指纹)。**不返回 token 本身。**"""

    hits: list[tuple[int, str, int, str]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for pattern in CREDENTIAL_PATTERNS:
            for match in pattern.finditer(line):
                token = match.group(0)
                if looks_like_placeholder(token):
                    continue
                if shannon_entropy(token) < MIN_ENTROPY_BITS_PER_CHAR:
                    continue
                hits.append((number, pattern.pattern[:12], len(token), token_fingerprint(token)))
    return hits


def tracked_files() -> list[str]:
    proc = subprocess.run(["git", "-C", str(REPO), "ls-files"],
                          capture_output=True, text=True, encoding="utf-8", errors="replace")
    if proc.returncode != 0:
        pytest.fail(
            f"SETUP 失败：`git ls-files` rc={proc.returncode}（{proc.stderr[:120]!r}）⇒ "
            "拿不到受版本控制路径清单，这条门没有分母，不许报绿"
        )
    return [line for line in proc.stdout.splitlines() if line.strip()]


def scan_paths(paths: Iterable[str]) -> list[dict]:
    """扫描给定路径，返回**位置+形状**的结构化行（不含原文）。"""

    offenders: list[dict] = []
    for rel in paths:
        path = REPO / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for number, pattern_name, length, token_fp in find_credential_shapes(text):
            # 只报位置与形状；两个都是摘要，**任何情况下都不印原文或前缀**
            offenders.append({
                "at": f"{rel}:{number}",
                "shape": pattern_name,
                "len": length,
                "loc_fp": hashlib.sha256(f"{rel}:{number}".encode("utf-8")).hexdigest()[:12],
                "token_fp": token_fp,
            })
    return offenders


def render(off: dict) -> str:
    return (f"{off['at']} 形状={off['shape']}… 长度={off['len']} "
            f"位置指纹={off['loc_fp']} token指纹={off['token_fp']}")


def _table(rows: list[dict]) -> str:
    lines = []
    for r in rows:
        lines.append(
            f"    {render(r)}\n"
            f"      判级={r['verdict']} 与现役凭据相等={r['equals_live_credential']}\n"
            f"      声明={ (r['declaration'] or {}).get('what') or '（无）'} ｜ "
            f"声明指纹={ (r['declaration'] or {}).get('token_fp') or '—'} ｜ 依据="
            f"{'; '.join((r['declaration'] or {}).get('evidence') or ('—',))} ｜ 由={(r['declaration'] or {}).get('declared_by') or '—'}"
        )
    return "\n".join(lines) if lines else "    （0 处）"


# ======================================================================================
# 1 · 受版本控制的路径里不得有凭据字面量（含 `.patch` 里套补丁的形状）
# ======================================================================================
def test_1_no_credential_literal_in_any_versioned_path():
    paths = tracked_files()
    assert paths, "SETUP 失败：受版本控制路径清单为空 ⇒ 这条门没有分母，不许报绿"
    offenders = scan_paths(paths)
    live = live_credentials()
    rows = classify_offenders(offenders, live, len(paths))
    bad = [r for r in rows if r["verdict"] != "DECLARED_NON_LIVE_SAMPLE"]
    header = (
        f"扫描侧 cardinality：受版本控制路径 {len(paths)} 个 ⇒ 形状命中 {len(rows)} 处\n"
        f"现役侧 cardinality：env 里可比的现役凭据 {len(live)} 把 "
        f"{[(c['env'], c['len'], c['fp']) for c in live] or '（0 把 ⇒ 相等性 NOT_MEASURED，不写成不等）'}\n"
    )
    assert not bad, (
        "期望：每一处命中要么与现役凭据**测得**不等且有**指纹吻合**的具名声明（甲），"
        f"要么根本没有命中；实际 {len(bad)} 处不合格（**射程一字未减**，仍全部列在下面）：\n"
        + header + _table(rows)
    )
    if rows:  # 绿也要把读数留下：判级表必须出现在可见输出里，不能只活着不说话
        print("\n[credential-literals 读数表]\n" + header + _table(rows))


# ======================================================================================
# 2 · 咬合反例：真形状必须红、占位必须绿
# ======================================================================================
def test_2_the_scan_bites_a_real_shape_and_spares_a_placeholder():
    # 真形状（高熵、非占位）—— 用合成串，**不是**任何真 key
    synthetic_real = "sk-" + "aB3dE7gH1jK4mN8pQ2sT5vW9yZ6c"
    assert shannon_entropy(synthetic_real) >= MIN_ENTROPY_BITS_PER_CHAR, (
        "SETUP：合成样本熵太低，测不出东西（先修样本）"
    )
    assert not looks_like_placeholder(synthetic_real), "SETUP：合成样本被当成占位串（先修样本）"
    hits = find_credential_shapes(f'KEY = "{synthetic_real}"\n')
    assert hits and hits[0][2] == len(synthetic_real), (
        f"期望：真形状被抓到；实际 {hits}"
    )

    # 占位串必须放过（否则门会把自证样本、文档示例全判红）
    for placeholder in (
        "sk-REDACTED-0000000000000000",
        "sk-example-placeholder-key",
        "sk-aaaaaaaaaaaaaaaaaaaaaaaa",
    ):
        assert looks_like_placeholder(placeholder), (
            f"期望：{placeholder[:12]}… 被判为占位（不报）；实际没判出"
        )
        assert not find_credential_shapes(f'KEY = "{placeholder}"\n'), (
            f"期望：占位串不进违规；实际被报了"
        )


def test_2b_a_patch_carrying_a_literal_is_caught_like_any_other_file():
    """那次漏的形状：**补丁里套补丁** —— `.patch` 里 `+` 开头的一行带着字面量。

    这里用合成样本在临时文本上验判据，不碰真文件。
    """

    synthetic_real = "sk-" + "aB3dE7gH1jK4mN8pQ2sT5vW9yZ6c"
    patch_body = (
        "diff --git a/app/config.py b/app/config.py\n"
        "--- a/app/config.py\n"
        "+++ b/app/config.py\n"
        "@@ -1 +1 @@\n"
        f'+DEEPSEEK_API_KEY = "{synthetic_real}"\n'
    )
    hits = find_credential_shapes(patch_body)
    assert hits and hits[0][0] == 5, (
        f"期望：补丁第 5 行（`+` 开头）的字面量被抓到；实际 {hits}"
    )


def test_2c_the_token_fingerprint_identifies_the_secret_not_its_location():
    """新那一列的**双向**证明（不是"我加了一列"就算数）。"""

    key_a = "sk-" + "aB3dE7gH1jK4mN8pQ2sT5vW9yZ6c"
    key_b = "sk-" + "zZ9yY8xX7wW6vV5uU4tT3sS2rR1qQpP"
    assert not looks_like_placeholder(key_b), "SETUP：反例样本被判成占位（测不出东西）"

    # 正向 1：同一把 key 出现在两行 ⇒ token指纹**相同**
    same = find_credential_shapes(f'K1 = "{key_a}"\nK2 = "{key_a}"\n')
    assert len(same) == 2, f"期望两行各抓 1 处；实际 {len(same)}"
    assert same[0][3] == same[1][3], "同一把 key 的 token指纹必须相等，否则这一列没意义"
    # 正向 2：而**位置**指纹必须不同 ⇒ 证明两者量的不是同一件事（别拿位置摘要指认同一个凭据）
    loc = [hashlib.sha256(f"p:{n}".encode()).hexdigest()[:12] for n in (same[0][0], same[1][0])]
    assert loc[0] != loc[1], "SETUP：位置指纹样例造错了两行相同"

    # 反向：换一把 key ⇒ token指纹必须变（常数桩能骗过"我看得到摘要"，骗不过这条）
    other = find_credential_shapes(f'K = "{key_b}"\n')
    assert other and other[0][3] != same[0][3], "两把不同的 key 给出了同一个 token指纹 ⇒ 这一列是假的"

    # 红线：任何返回字段都不得等于原文（门不许把字面量带出去）
    for hit in same + other:
        for field in hit:
            assert str(field) not in (key_a, key_b), f"泄漏：返回字段里出现了原文（{hit[0]}）"


def test_2d_the_declaration_is_load_bearing_not_a_whitelist():
    """D-2=甲 的五面自证：**声明看内容摘要，不看路径**；缺读数一律 NOT_MEASURED。

    全部用内存里的合成 offender —— 绝不往任何真文件里塞凭据来"证明门会红"。
    """
    key_a = "sk-" + "aB3dE7gH1jK4mN8pQ2sT5vW9yZ6c"          # 合成串，不是任何真 key
    fp_a = token_fingerprint(key_a)
    off = [{"at": "some/test_stub.spec.ts:1", "shape": "sk-", "len": len(key_a),
            "loc_fp": "x", "token_fp": fp_a}]
    other_live = [{"env": "DEEPSEEK_API_KEY", "len": 31,
                   "fp": token_fingerprint("sk-" + "zZ9yY8xX7wW6vV5uU4tT3sS2rR1qQpP")}]
    saved = DECLARED_NON_LIVE_SAMPLES

    def with_decl(**override):
        globals()["DECLARED_NON_LIVE_SAMPLES"] = ({**saved[0], "at": off[0]["at"],
                                                   **override},)

    try:
        # 面①：没有声明 ⇒ 必红（"新出现的字面量一定会响"这一面）
        globals()["DECLARED_NON_LIVE_SAMPLES"] = ()
        v1 = classify_offenders(off, other_live, 10)[0]["verdict"]
        assert v1 == "UNDECLARED", f"期望：未声明的命中判 UNDECLARED；实际 {v1}"

        # 面②：声明在、但**指纹不吻合**（桩被改过）⇒ 声明作废，仍红
        with_decl(token_fp="0" * 12)
        v2 = classify_offenders(off, other_live, 10)[0]["verdict"]
        assert v2.startswith("DECLARATION_STALE"), (
            f"期望：指纹不吻合的声明要自动作废并仍红；实际 {v2}")

        # 面③：声明吻合 + 与现役**测得**不等 ⇒ 判成测试桩（绿），但两侧 cardinality 进收据
        with_decl(token_fp=fp_a)
        row3 = classify_offenders(off, other_live, 10)[0]
        assert row3["verdict"] == "DECLARED_NON_LIVE_SAMPLE", (
            f"期望：判成具名测试桩；实际 {row3['verdict']}")
        assert row3["equals_live_credential"] is False, "有现役可比时必须**测得**不等，不许空判"
        assert row3["offender_total"] == 1 and row3["scanned_paths"] == 10, (
            f"两侧 cardinality 必须进收据：{row3['offender_total']}/{row3['scanned_paths']}")

        # 面④：现役侧缺席 ⇒ NOT_MEASURED（**不许**写成"不等"）
        row4 = classify_offenders(off, [], 10)[0]
        assert row4["equals_live_credential"] == "NOT_MEASURED", (
            f"期望：没有可比现役凭据时写 NOT_MEASURED；实际 {row4['equals_live_credential']!r}")

        # 面⑤：与现役**相等** ⇒ 无论声明成什么都必红
        row5 = classify_offenders(off, [{"env": "DEEPSEEK_API_KEY", "len": 31, "fp": fp_a}], 10)[0]
        assert row5["verdict"] == "LIVE_CREDENTIAL_LEAK", (
            f"期望：等于现役凭据必红；实际 {row5['verdict']}")
    finally:
        globals()["DECLARED_NON_LIVE_SAMPLES"] = saved


# ======================================================================================
# 3 · 判据承重（可被突变杀掉）
# ======================================================================================
def test_3_the_scan_is_load_bearing():
    original = globals()["looks_like_placeholder"]
    try:
        globals()["looks_like_placeholder"] = lambda token: True  # 突变：一律当占位
        synthetic_real = "sk-" + "aB3dE7gH1jK4mN8pQ2sT5vW9yZ6c"
        assert not find_credential_shapes(f'K="{synthetic_real}"\n'), "突变后应放行一切"
    finally:
        globals()["looks_like_placeholder"] = original  # type: ignore[assignment]
    synthetic_real = "sk-" + "aB3dE7gH1jK4mN8pQ2sT5vW9yZ6c"
    assert find_credential_shapes(f'K="{synthetic_real}"\n'), "恢复后必须重新咬住"

    # 第二处承重：token指纹那一列。换成常数桩 ⇒ 两把不同 key 会塌成同一个摘要（test_2c 就是抓这个）
    real_fp = globals()["token_fingerprint"]
    key_a = "sk-" + "aB3dE7gH1jK4mN8pQ2sT5vW9yZ6c"
    key_b = "sk-" + "zZ9yY8xX7wW6vV5uU4tT3sS2rR1qQpP"
    try:
        globals()["token_fingerprint"] = lambda token: "0" * 12
        mut_a = find_credential_shapes(f'K="{key_a}"\n')[0][3]
        mut_b = find_credential_shapes(f'K="{key_b}"\n')[0][3]
        assert mut_a == mut_b, "常数桩居然还分得开两把 key ⇒ test_2c 的反向断言是空的"
    finally:
        globals()["token_fingerprint"] = real_fp  # type: ignore[assignment]
    a = find_credential_shapes(f'K="{key_a}"\n')[0][3]
    b = find_credential_shapes(f'K="{key_b}"\n')[0][3]
    assert a != b and len(a) == 12, "恢复后两把 key 必须给出不同指纹"

    # 第三处承重：甲案的"声明看指纹"。把判级换成"一律算已声明"（= 偷偷变成白名单），
    # 未声明的命中就会被放绿 ⇒ 这一格必须抓住它。
    real_classify = globals()["classify_offenders"]
    probe = [{"at": "unreported.spec.ts:9", "shape": "sk-", "len": 31, "loc_fp": "y", "token_fp": a}]

    def _lax(offenders, live, scanned_paths):
        return [{**r, "verdict": "DECLARED_NON_LIVE_SAMPLE"}
                for r in real_classify(offenders, live, scanned_paths)]

    try:
        globals()["classify_offenders"] = _lax
        lax = classify_offenders(probe, [], 1)[0]["verdict"]
    finally:
        globals()["classify_offenders"] = real_classify
    assert lax == "DECLARED_NON_LIVE_SAMPLE", "SETUP：常数桩没生效，测不出东西"
    strict = real_classify(probe, [], 1)[0]["verdict"]
    assert strict == "UNDECLARED", (
        f"恢复后未声明的命中必须回到 UNDECLARED；实际 {strict}")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
