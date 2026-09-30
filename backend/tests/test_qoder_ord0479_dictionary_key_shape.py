"""ORD-0479 · 凭据尺不许把 i18n 查表的值读成凭据——判据是结构，不是词表、也不是申报。

号令者 01:3x 那块：现尖唯一那枚凭据红在 `backend/tests/test_qoder_ord0307_credential_gate.py:180`
（C07，断 hits_in_product_path == 0 得 1），命中的是 frontend/src/features/shared/SharedJourneyPanel.tsx:45
那张"拒绝码 ↔ 字典键"对照表里的值。要求写得很死：要结构判据，不要往占位词表塞词，也不要走申报通道
（那等于把尺的假阳性登记成真凭据）。

每格自己造输入（临时 root，自己的词典、自己的表），断言只用位置摘要与长度，绝不打印命中值；
正控与反控成对：真凭据形状仍红、形状像但结构不符仍红、词典读不到仍红。
H07 那一格反过来钉"两条禁路没被走"：把词表与申报表跟基座尖上的版本逐字节比。
"""
from __future__ import annotations

import hashlib
import re
import subprocess
from pathlib import Path

import pytest

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.security import credential_literals as CL  # noqa: E402

REPO = CL.REPO
BASE_TIP = "127ce7b05329eaa837701cdb93bdbc2e5d64e10f"
SITE = "frontend/src/features/shared/SharedJourneyPanel.tsx"
VALUE = "shared.refusedTokenUnknown"


def _git_show(rev: str, rel: str) -> str:
    """The file as that generation holds it, or a red that names the real reason."""

    r = subprocess.run(["git", "-C", str(REPO), "show", "%s:%s" % (rev, rel)],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    assert r.returncode == 0, "cannot read %s:%s in this checkout -- this cell is NOT_MEASURED, not green" % (rev, rel)
    assert r.stdout, "git show %s:%s produced no bytes" % (rev, rel)
    return r.stdout


def _write(root: Path, rel: str, text: str) -> str:
    dst = root / rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(text, encoding="utf-8", newline="\n")
    return rel


def _dict(tmp: Path, en: list[str], zh: list[str]) -> str:
    body = ("const en: Dict = {\n"
            + "".join('  "%s": "english %s",\n' % (k, k) for k in en)
            + "};\n\nconst zhCN: Dict = {\n"
            + "".join('  "%s": "中文 %s",\n' % (k, k) for k in zh)
            + "};\n")
    return _write(tmp, CL.I18N_SOURCE_REL, body)


def _table(tmp: Path, values: list[tuple[str, str]]) -> str:
    body = "const REFUSAL_KEY: Record<string, string> = {\n" + "".join(
        '  %s: "%s",\n' % (k, v) for k, v in values) + "};\n"
    return _write(tmp, "frontend/src/features/shared/panel.ts", body)


def _synthetic_key(seed: str) -> str:
    return "sk-" + hashlib.sha256(seed.encode()).hexdigest()[:28]


@pytest.fixture()
def tmp_root(tmp_path: Path) -> Path:
    """A dictionary with four translated keys; the tables below use three of them.

    The counts are deliberately unequal so a receipt that reports the wrong one cannot pass:
    `translation_lookup_table:3 entries, dictionary:4 keys` names the table and the vocabulary.
    """

    _dict(tmp_path, [VALUE, "shared.refusedRevoked", "shared.refusedExpired",
                     "shared.refusedUnused"],
          [VALUE, "shared.refusedRevoked", "shared.refusedExpired", "shared.refusedUnused"])
    return tmp_path


# ---------------------------------------------------------------- H01 真那一处：被结构赦免，且 C07 的断言成立
def test_H01_the_real_site_is_exempted_by_structure_not_by_a_word(tmp_root: Path) -> None:
    """整表都是"凭据形状的标签 ↔ 两本词典都认得的键"，三处命中全靠结构赦免。

    标签逐枚都带 token，是因为尺只看凭据形状的标签；把其中一枚换成 revoked 就只剩一命中，
    那一格就不再证明"整表都是键"这条判据了。
    """

    rel = _table(tmp_root, [("token_unknown", VALUE), ("revoked_token", "shared.refusedRevoked"),
                            ("expired_token", "shared.refusedExpired")])
    hits = CL.find_literals([rel], tmp_root)
    assert len(hits) == 3, hits
    for h in hits:
        assert h["pattern"] == "labeled_assignment", h
        assert h["in_product_path"] is True, h
        assert h["vocabulary_exemption"] == "translation_lookup_table:3 entries, dictionary:4 keys", h
    report = CL.scan(tmp_root)
    assert report["hits_in_product_path"] == 0, report["live"]
    assert report["verdict"] == CL.CODE_OK, report["verdict"]
    assert report["hits_vocabulary_exempted"] == 3, report["vocabulary_exemptions"]
    assert {e["position_fp"] for e in report["vocabulary_exemptions"]} == \
        {h["position_fp"] for h in hits}, report["vocabulary_exemptions"]


def test_H01b_the_shipped_tree_clears_with_one_named_exemption() -> None:
    """真树上：C07 那句断言成立，且赦免的原因可指名——不是占位词、不是申报通道。"""

    report = CL.scan(REPO)
    assert report["hits_in_product_path"] == 0, report["live"]
    assert report["verdict"] == CL.CODE_OK, report["verdict"]
    sites = [(e["path"], e["line"], e["reason"]) for e in report["vocabulary_exemptions"]]
    assert (SITE, 45, sites[0][2]) in sites or any(p == SITE for p, _l, _r in sites), sites
    assert all("translation_lookup_table" in r for _p, _l, r in sites), sites


# ---------------------------------------------------------------- H02 正控：真凭据形状仍红
def test_H02_a_real_credential_shape_on_the_same_label_stays_live(tmp_root: Path) -> None:
    rel = _write(tmp_root, "frontend/src/features/shared/positive.ts",
                 'const cfg = { token_unknown: "%s" };\n' % _synthetic_key("ord0479-positive-control"))
    hits = CL.find_literals([rel], tmp_root)
    assert len(hits) == 2, hits  # 同一行被 provider_key_shape 与 labeled_assignment 各抓一次
    for h in hits:
        assert h["vocabulary_exemption"] is None, h
    report = CL.scan(tmp_root)
    assert report["hits_in_product_path"] == len(hits) == report["live_total"], report["live"]
    assert report["verdict"] == CL.CODE_IN_PRODUCT_PATH, report["verdict"]


# ---------------------------------------------------------------- H03 反例：形状像、词典里没有
def test_H03_a_dotted_camel_value_that_no_locale_translates_stays_live(tmp_root: Path) -> None:
    rel = _table(tmp_root, [("token_unknown", "shared.refusedMadeUpKey"),
                            ("revoked_token", "shared.refusedRevoked"),
                            ("expired_token", "shared.refusedExpired")])
    report = CL.scan(tmp_root)
    assert report["hits_in_product_path"] >= 1, report["live"]
    assert report["verdict"] == CL.CODE_IN_PRODUCT_PATH, report["verdict"]


# ---------------------------------------------------------------- H04 反例：只有一本词典认得它
def test_H04_a_key_present_in_one_locale_only_does_not_exempt(tmp_root: Path) -> None:
    _write(tmp_root, CL.I18N_SOURCE_REL,
           'const en: Dict = {\n  "shared.refusedOneSided": "only english",\n};\n\n'
           'const zhCN: Dict = {\n  "shared.refusedRevoked": "中文",\n'
           '  "shared.refusedExpired": "中文",\n};\n')
    rel = _write(tmp_root, "frontend/src/features/shared/one_sided.ts",
                 'const T: Record<string, string> = {\n  revoked_token: "shared.refusedOneSided",\n'
                 '  expired_token: "shared.refusedOneSided",\n};\n')
    hits = CL.find_literals([rel], tmp_root)
    assert len(hits) == 2, hits
    for h in hits:
        assert h["vocabulary_exemption"] is None, h
    assert CL.scan(tmp_root)["verdict"] == CL.CODE_IN_PRODUCT_PATH


# ---------------------------------------------------------------- H05 反例：表里混进非键值
def test_H05_a_table_mixed_with_a_non_key_value_does_not_exempt(tmp_root: Path) -> None:
    rel = _table(tmp_root, [("token_unknown", VALUE),
                            ("revoked_token", _synthetic_key("ord0479-mixed-table"))])
    hits = CL.find_literals([rel], tmp_root)
    assert hits, "nothing was probed -- the fixture does not exercise the rule"
    for h in hits:
        assert h["vocabulary_exemption"] is None, h
    assert CL.scan(tmp_root)["verdict"] == CL.CODE_IN_PRODUCT_PATH


# ---------------------------------------------------------------- H06 反例：provider 形状借词典也进不来
def test_H06_a_provider_shaped_value_cannot_hide_inside_a_translated_table(tmp_root: Path) -> None:
    """把真凭据形状写进两本词典、再放进查表里——赦免仍然一次都不给。

    结构判据要求整表的值都是字典键形状，而 DICT_KEY_SHAPE 不认 provider 形状（见 H09），
    所以这一格同时钉两条：混进一枚就整表不赦免，且 provider 图案永远不被赦免。
    """

    key = _synthetic_key("ord0479-smuggled")
    _dict(tmp_root, [VALUE, "shared.refusedRevoked", key], [VALUE, "shared.refusedRevoked", key])
    rel = _write(tmp_root, "frontend/src/features/shared/smuggled.ts",
                 'const T: Record<string, string> = {\n  token_unknown: "%s",\n'
                 '  revoked_token: "%s",\n};\n' % (VALUE, key))
    hits = CL.find_literals([rel], tmp_root)
    assert len(hits) == 3, hits  # 两行 labeled_assignment + provider 形状那一行再被抓一次
    assert [h for h in hits if h["pattern"] in CL.NEVER_EXEMPT_PATTERNS], [h["pattern"] for h in hits]
    for h in hits:
        assert h["vocabulary_exemption"] is None, h
    assert CL.scan(tmp_root)["verdict"] == CL.CODE_IN_PRODUCT_PATH


# ---------------------------------------------------------------- H07 两条禁路没被走
def test_H07_the_two_forbidden_shortcuts_were_not_taken() -> None:
    """词表与申报表都必须与基座尖上逐字节相同；in_product_path 的算法也一样。

    这格是反"洗绿"的：如果谁把那一处假阳性塞进 PLACEHOLDER_MARKERS，或者用 DECLARED_SAMPLES 给它
    登记一个指纹，这里立刻红。
    """
    rel = "backend/app/security/credential_literals.py"

    def tuple_from(text: str, name: str) -> str:
        m = re.search(r"^%s: tuple\[[^\]]*\] = \((.*?)\)\n" % name, text, re.M | re.S)
        assert m, "the %s tuple is no longer shaped like the one this cell pins" % name
        return m.group(1)

    base = _git_show(BASE_TIP, rel)
    cur = _git_show("HEAD", rel)
    assert tuple_from(cur, "PLACEHOLDER_MARKERS") == tuple_from(base, "PLACEHOLDER_MARKERS"), \
        "PLACEHOLDER_MARKERS moved: the placeholder list must not carry this order's exemption"
    assert tuple_from(cur, "DECLARED_SAMPLES") == tuple_from(base, "DECLARED_SAMPLES"), \
        "DECLARED_SAMPLES moved: the declaration channel must not be used for this"
    assert 'rp.startswith(PRODUCT_ROOTS)' in cur, "the product-path rule was rewritten"


# ---------------------------------------------------------------- H08 词典读不到时朝闭
def test_H08_an_unreadable_dictionary_exempts_nothing(tmp_path: Path) -> None:
    """没有词典（或它解析不出两块）⇒ 赦免必须为 0，那一处回到 live。"""

    rel = _table(tmp_path, [("token_unknown", VALUE), ("revoked_token", "shared.refusedRevoked"),
                            ("expired_token", "shared.refusedExpired")])
    assert CL.i18n_dictionary_keys(tmp_path) == frozenset()
    hits = CL.find_literals([rel], tmp_path)
    assert hits and all(h["vocabulary_exemption"] is None for h in hits), hits
    report = CL.scan(tmp_path)
    assert report["hits_in_product_path"] == len(hits), report["live"]
    assert report["hits_vocabulary_exempted"] == 0, report["vocabulary_exemptions"]


# ---------------------------------------------------------------- H09 结构判据够不到 provider 形状
def test_H09_no_provider_shape_is_shaped_like_a_dictionary_key() -> None:
    """五把 provider 图案各自的样本，全都不满足 DICT_KEY_SHAPE —— 赦免通道对它们结构性关闭。"""

    samples = {"provider_key_shape": "sk-" + "a" * 24,
               "aws_access_key": "AKIA" + "A" * 16,
               "github_token": "ghp_" + "a" * 40,
               "google_api_key": "AIza" + "a" * 35,
               "bearer_or_basic_literal": "Bearer " + "a" * 30}
    for name, sample in samples.items():
        assert name in CL.NEVER_EXEMPT_PATTERNS, name
        assert not CL.DICT_KEY_SHAPE.match(sample), name
