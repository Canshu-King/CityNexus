# -*- coding: utf-8 -*-
"""wake_names.py — 「一块账本正文点到哪些车道」的名字表与匹配器（wake_from_commits 用它）。

为什么要单独拿出来：旧版只认 8 位会话 id，而号令者 16:52 那块写的是「给 n3 与 ORD-0383 车道」——
一个人类名字都没有 id，于是 `点到=（无人）`，我的叫醒判据整个失灵。这里两层都认：
  ① 8 位会话 id（老规矩）
  ② 每辆车的花名（`lane N2`、`给 n3`、`ORD-0383 车道`、`道0370` 这类写法）
匹配一律大小写不敏感，并且把「作者自己」剔掉（块头里的人不算被点名）。
"""
import re

# id8 -> 花名（这一班现读的 13 条会话；改名/新增就动这张表）
ID8 = {
    "494abfd7": "号令者",
    "1d64acf5": "S4",
    "9759f1ac": "N2",
    "49fe0d7b": "N3",
    "3b65af59": "map",
    "a68b0631": "rel",
    "904a042d": "Q",
    "bac10f40": "AI",
    "e4f3490f": "道0370",
    "8e5245f0": "道0369",
    "be19052c": "dt",
    "2d2d7428": "0441",
    "4033270f": "0383",
    "1ba48dbf": "newlane",
    "6a150e1e": "newlane2",
    # 08:16 补：这两条今夜一直在交块（`R_0712.md.inserted_071629`、`Q-ord0432…`/`ORD-0443`），
    # 但表里没有，于是「车道任务表」把 14 条里漏成 12 条、转达扫描也把它们的枝当陌生人。
    "8ac89982": "R0417",
    "a6b95d59": "DSH",
    # 08:23 又抓到一条同表漏覆盖：`9cc37e57` 今夜交了 ORD-0437 r2 与 ORD-0426 勘误两块，
    # 表里没有 ⇒ 车道表少一行、转达与撞号尺都看不见它。
    "9cc37e57": "0421",
}

# 花名 -> 匹配式。只写「在正文里能唯一指向这辆车」的形状，避免 map/rel 这类常用词误伤：
#   要么带「车道/lane/给/·」这类指向词，要么用不会出现在散文里的名字。
NAME_PATTERNS = {
    "号令者": [r"号令者"],
    "S4": [r"(?:lane|车道|给)\s*S4", r"S4-ast-taint", r"S4（量具"],
    "N2": [r"(?:lane|车道|给)\s*N2", r"车道 N2"],
    "N3": [r"(?:lane|车道|给)\s*N3", r"·\s*N3\s*·", r"给 n3 与"],
    "map": [r"(?:车道|给|·)\s*map\b", r"车道 map", r"map_0\d{2}\.md"],
    "rel": [r"(?:车道|给|·)\s*rel\b", r"车道 rel", r"rel_0\d{2}\.md"],
    # `Q` 这一条 08:16 修过一次：`\b` 在 `-` 前就成立，所以 `lane Q-dsh`（DSH 车道的块头写法）
    # 会被判成点了 904a042d，两条车道都在表里同名「Q」。加上「后面不能是连字符」才收口。
    "Q": [r"车道 Q\b(?!-)", r"lane Q\b(?!-)", r"（lane Q）", r"（会话 904a042d"],
    "AI": [r"车道\s*`?AI`?", r"给.*AI 车道"],
    "道0370": [r"道0370", r"车道 0370", r"qoder-0370"],
    "道0369": [r"道0369", r"车道 0369", r"qoder-0369"],
    "dt": [r"车道 dt", r"道tokens", r"dt_0\d{2}\.md"],
    "0441": [r"qoder-0441", r"车道 2d2d7428", r"ORD-0441 车道", r"车道 qoder-0388", r"qoder-0388r\d_"],
    "0383": [r"ORD-0383 车道", r"车道 0383", r"给 n3 与 ORD-0383", r"0383_<HHMM>|_qoder_lane_ord0383"],
    "newlane": [r"一条新车道", r"newlane_0\d{2}\.md", r"ORD-0444 车道"],
    "newlane2": [r"第二条新车道", r"newlane2_0\d{2}\.md", r"ORD-0445 车道"],
    "R0417": [r"车道 `?8ac89982", r"R-ord0417", r"车道 R0417", r"R_0\d{2}\.md"],
    "DSH": [r"车道 DSH", r"lane Q-dsh", r"Q-dsh（", r"a6b95d59"],
    "0421": [r"车道 `?9cc37e57", r"qoder-0437", r"qoder-0426", r"ORD-0421 车道"],
}


def named_in(text, exclude_owner=None):
    """返回被点名的车道花名列表（大小写不敏感），exclude_owner 里的名字不算（作者点自己不算被叫）。"""
    out = []
    for nm, pats in NAME_PATTERNS.items():
        if exclude_owner and nm == exclude_owner:
            continue
        for p in pats:
            if re.search(p, text, re.I):
                out.append(nm)
                break
    return out


def ids_named(text, owner_id=None):
    """老规矩：正文里出现的 8 位 id（排除作者那枚）。"""
    return [k for k in ID8 if k in text and k != owner_id]


def hits_for(name, text):
    """这辆车是否被这段文字点名（用它自己的匹配式，要求带指向词）。"""
    for p in NAME_PATTERNS.get(name, []):
        if re.search(p, text, re.I):
            return True
    return False


def selftest():
    cases = []
    t = ("### CMDR 2026-09-28 16:52 · 号令者 · 给 n3 与 ORD-0383 车道的 rebase 事实\n"
         "ORD-0384（n3）· blob 4c802d5a 的实测；ORD-0383（新车道）· blob c57bd95b")
    got = sorted(named_in(t, exclude_owner="号令者"))
    cases.append(("正控 号令者 16:52 那块要点到 N3 与 0383", got, ["0383", "N3"]))
    t2 = "### ORD-0359 同代复验（lane N2）— 替代 n2_1824.md"
    cases.append(("正控 lane N2 认得到", sorted(named_in(t2)), ["N2"]))
    t3 = "这一句里出现 mapping 与 relation 两个词，还有 relay"
    cases.append(("反控 常用词不误伤（map/rel 要带指向词）", sorted(named_in(t3)), []))
    t4 = "### CMDR 16:52 · 号令者 · 我自己的块，正文也提了号令者"
    cases.append(("反控 作者点自己不算被叫", sorted(named_in(t4, exclude_owner="号令者")), []))
    t5 = "### Q 道tokens（会话 be19052c）05:57 — 丙的判定 + 已落尖表面的门"
    cases.append(("反控 历史名 道tokens 现在归 dt，且作者点自己不算被叫",
                  sorted(named_in(t5, exclude_owner="dt")), []))
    t6 = "### 车道 dt（会话 be19052c）ORD-0435 r2：以现尖 35326e62 为基座重放"
    cases.append(("正控 今日块头「车道 dt」认得到 dt", sorted(named_in(t6)), ["dt"]))
    t7 = "### qoder-0441 2026-09-29 05:34 · 车道 2d2d7428 · ORD-0441 重交（请用 r2）"
    cases.append(("正控 0441 的块头认得到 0441，不再误叫成 0388",
                  sorted(named_in(t7)), ["0441"]))
    t8 = "你是 CityNexus 项目的第二条新车道（并行开发会话），工单 ORD-0445；另一条新车道领 ORD-0444"
    cases.append(("正控 两条新车道按各自写法分开", sorted(named_in(t8)), ["newlane", "newlane2"]))
    t9 = "上一句里的 mapping、relation、relay、given 都只是散文，不该点任何车道"
    cases.append(("反控 散文里的常用词不误伤（含 dt/tokens 类子串）", sorted(named_in(t9)), []))
    t10 = "### ORD-0417 · 车道 8ac89982 · 现尖产物级几何尺已跑 · 2026-09-29 07:12+08"
    cases.append(("正控 R0417 的块头认得到（08:16 前这张表里没有它）", sorted(named_in(t10)), ["R0417"]))
    t11 = "### ORD-0443 · lane Q-dsh（Qoder，会话 a6b95d59）· at_local 2026-09-29 06:52"
    cases.append(("正控 DSH 的块头认得到（且不再误叫 Q）", sorted(named_in(t11)), ["DSH"]))
    t12 = "### ORD-0431 · 车道 Q（会话 904a042d-51c9-4291-89ca-5d420afe419e）· 顶栏折行基线已量"
    cases.append(("正控 真·车道 Q 仍认得到（改连字符负向前瞻不能把它改没了）", sorted(named_in(t12)), ["Q"]))
    t13 = "R ORD-0437 r2 · 文本/链接导入 · 车道 9cc37e57 · 重基到现尖交付 2026-09-29"
    cases.append(("正控 0421(9cc37e57) 的块头认得到（第二次补同一张表）", sorted(named_in(t13)), ["0421"]))
    cases.append(("反控 hits_for：段落里只有 controller/previous 不算点 rel 的名",
                  [hits_for("rel", "the controller re-read previous bytes"), hits_for("rel", "车道 rel 的那一段")],
                  [False, True]))
    bad = 0
    for name, got, want in cases:
        ok = got == want
        bad += 0 if ok else 1
        print("  %-46s got=%s want=%s %s" % (name, got, want, "OK" if ok else "FAIL"))
    print("selftest %s (%d/%d)" % ("PASS" if bad == 0 else "FAIL", len(cases) - bad, len(cases)))
    return 1 if bad else 0


if __name__ == "__main__":
    import sys
    sys.exit(selftest())
