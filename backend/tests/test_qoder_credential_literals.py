"""commander 2026-09-22 13:4x 安全事故的常驻门 · **凭据字面量不得进入受版本控制的任何路径**。

背景（账本 10008 块）：真 key 的**原文**被提交进 `qoder-handoff/qoder_xiaomi_truth_hardening_v6.patch`
（约 6348 行，一行以 `+` 开头），并由 `b12f24f` 推送到了远端分支；`13377d3` 做了工作副本脱敏，
但**历史与已推送的旧对象抹不掉** —— 唯一有效处置是用户轮换那把 key。

本门要抓的正是那次漏掉的形状：**补丁里套补丁**（`.patch` 文件里 `+` 开头的行携带字面量）。
判据是形状扫描（前缀 + 长度区间 + 高熵体），并排除明显占位串。

**读法**：只报**位置与形状**（文件:行、长度、字符类别），**绝不打印原文或前缀**
（账本既有禁令；指认用 `sha256[:12]`）。
"""

from __future__ import annotations

import hashlib
import math
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


def find_credential_shapes(text: str) -> list[tuple[int, str, int]]:
    """返回 (行号, 命中的模式名, token 长度)。**不返回 token 本身。**"""

    hits: list[tuple[int, str, int]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        for pattern in CREDENTIAL_PATTERNS:
            for match in pattern.finditer(line):
                token = match.group(0)
                if looks_like_placeholder(token):
                    continue
                if shannon_entropy(token) < MIN_ENTROPY_BITS_PER_CHAR:
                    continue
                hits.append((number, pattern.pattern[:12], len(token)))
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


def scan_paths(paths: Iterable[str]) -> list[str]:
    """扫描给定路径，返回**位置+形状**（不含原文）。"""

    offenders: list[str] = []
    for rel in paths:
        path = REPO / rel
        if not path.is_file():
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for number, pattern_name, length in find_credential_shapes(text):
            # 只报位置与形状；指认用 sha256[:12] 指纹，不印原文
            digest = hashlib.sha256(f"{rel}:{number}".encode("utf-8")).hexdigest()[:12]
            offenders.append(f"{rel}:{number} 形状={pattern_name}… 长度={length} 指纹={digest}")
    return offenders


# ======================================================================================
# 1 · 受版本控制的路径里不得有凭据字面量（含 `.patch` 里套补丁的形状）
# ======================================================================================
def test_1_no_credential_literal_in_any_versioned_path():
    paths = tracked_files()
    assert paths, "SETUP 失败：受版本控制路径清单为空 ⇒ 这条门没有分母，不许报绿"
    offenders = scan_paths(paths)
    assert not offenders, (
        f"期望：受版本控制的 {len(paths)} 个路径里没有凭据字面量"
        "（**含 `*.patch` 里 `+` 开头那种套补丁的形状** —— 2026-09-22 就是这么漏的）；"
        f"实际 {len(offenders)} 处（只给位置与形状，不给原文）：{offenders}"
    )


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


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
