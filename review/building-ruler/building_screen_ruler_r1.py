"""The building's acceptance ruler: does the screen name WHICH cause "nothing was found here" is?

Purpose: the fourth building block located a wiring gap -- the honest sentence for the catalog-empty shape
already exists in the same component, unreachable because the honest paragraph is gated on "there are no
facts", which is false exactly for that shape.  When the gap is closed, this ruler is what says it worked,
so nobody has to judge "looks better" by eye.

Three questions per cause, each answered from the rendered text a user would actually see:

  NAMES_CAUSE   does the screen say this is *this* cause, rather than a generic "nothing here"?
  QUOTES_SERVER does it carry the server's own answer (its wording, its named missing categories)?
  NEXT_STEP     does it tell the user what they can do next?

It is deliberately not a style judge: it does not read the source, does not count characters, and has no
pass mark for taste.  The browser leg stays outside this file -- this box's venv has no playwright, and a
ruler that cannot run is worse than no ruler -- so what this file owns is the JUDGEMENT, which is the part
that has to stay identical when the gap is closed: same scenarios, same three questions, same words.

Run: echo '[{"scenario": "<cause>", "body": "<rendered text>"}]' | python building_screen_ruler_r1.py
"""

from __future__ import annotations

import json
import pathlib
import sys

RUN = pathlib.Path(r"D:/moodle/_qoder_seed_ord0489/run")

# the two causes reproducible on this line today (the third is a schema question, not a screen question)
SCENARIOS = [
    {
        "cause": "no_canonical_identity",
        "query": "贡山独龙族怒族自治县",
        "server_code": "NO_CANONICAL_IDENTITY",
        "names_cause": ["没认出", "认不出", "无法追溯", "不能追溯"],
        # this cause is answered by the neutral basis the screen falls back to, NOT by the word
        # "server" -- a first version of this ruler searched for that word and mis-scored an honest
        # screen as dishonest.  The check is whether the screen carries this answer's substance.
        "quotes_server": ["中立口径", "不沿用", "认不出", "回退"],
        "next_step": ["换个写法", "挑一个", "另选", "Try another", "pick one"],
    },
    {
        "cause": "catalog_empty",
        "query": "北京",
        "server_code": "COVERAGE_INCOMPLETE",
        # the flattened line contains none of these -- that is the finding this ruler exists to catch
        "names_cause": ["还缺", "没准备", "未准备", "不足", "short ", "missing ", "categories"],
        "quotes_server": ["服务器", "Server", "server"],
        "next_step": ["可以先准备", "先准备", "准备", "先刷新", "prepare", "refresh"],
    },
]

# text that would mean the cause was flattened: a success-sounding line with no "why"
FLAT_MARKERS = ["已自动设置", "Auto-set"]


def judge(body: str, sc: dict) -> dict:
    def has(markers: list) -> bool:
        return any(m in body for m in markers)

    q = {"NAMES_CAUSE": has(sc["names_cause"]),
         "QUOTES_SERVER": has(sc["quotes_server"]),
         "NEXT_STEP": has(sc["next_step"])}
    flat = has(FLAT_MARKERS) and not q["NAMES_CAUSE"]
    return {"checks": q, "flattened": flat, "honest": all(q.values())}


def main() -> int:
    payload = json.loads(sys.stdin.read() or "[]")
    if not payload:
        print("REFUSE: no screen readings on stdin -- a ruler run with no input proves nothing")
        return 9

    rows = []
    for item in payload:
        try:
            sc = next(s for s in SCENARIOS if s["cause"] == item["scenario"])
        except StopIteration:
            print(f"REFUSE: unknown scenario {item.get('scenario')!r}")
            return 9
        j = judge(item["body"], sc)
        rows.append({"cause": sc["cause"], "query": sc["query"],
                     "server_code": item.get("server_code"),
                     "server_missing": item.get("server_missing"),
                     "rendered_text": item["body"][:400], **j})
        c = j["checks"]
        print(f"{sc['cause']:24s} names={c['NAMES_CAUSE']!s:<5} quotes={c['QUOTES_SERVER']!s:<5} "
              f"next={c['NEXT_STEP']!s:<5} flattened={j['flattened']}")
        print(f"    rendered: {item['body'][:160]}")

    honest = sum(1 for r in rows if r["honest"])
    out = {"ruler": "building_screen_ruler_r1", "scenarios": rows,
           "honest_count": honest, "scenario_count": len(rows),
           "verdict": ("ALL_CAUSES_HONEST" if honest == len(rows) else
                       "AT_LEAST_ONE_CAUSE_FLATTENED -- this is the baseline; re-run this same ruler after "
                       "the wiring gap is closed and it should read ALL_CAUSES_HONEST")}
    (RUN / "building_screen_ruler_r1_result.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print("\nVERDICT", out["verdict"])
    return 0 if honest == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())