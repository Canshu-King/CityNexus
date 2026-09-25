"""换代后要做的后手（包工头 08:1x 块 ③）：把同一枚载体测试 re-parent 到新尖，另开新 ref，旧 ref 保持冻结。

这一支现在只 dry-run：尖没动 ⇒ 不许铸提交、不许推 ref、不许动权威线。
它回答的是「等尖一动，我这一分钟能不能真跑起来」：
  * 守卫那一段在新尖上还是不是唯一一处（不唯一 ⇒ 载体要重新推导，不是 re-parent 就完事）；
  * 载体 import 的产品符号在新尖上还全不全（缺一个 ⇒ 按第 0 条口径具名停手，不改断言换绿）；
  * 新 ref 名字、预期提交形状（只 1 件、test-only）先算出来。
"""
from __future__ import annotations

import base64
import hashlib
import json
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

RUN = Path("D:/moodle/_qoder_f_run")
RCP = RUN / "o225_receipts"
LANE = r"D:/moodle/_qoder_f_ord253_20260923"
CITY = r"D:/moodle/CityNexus"
TOK = Path("D:/moodle/_qoder_recovery_20260919/.api_tok_20260920").read_text(encoding="utf-8").strip()
HDRS = {"Authorization": f"Bearer {TOK}", "Accept": "application/vnd.github+json",
        "User-Agent": "citynexus-lane-f"}
GR = "Canshu-King/CityNexus"
AUTH_REF = "mirror/integration-frontend-apple-pass1"
FROZEN_PARENT = "45b0a5e281cae9c37715173afd3ac5778f309ca7"
FROZEN_TIP = "c31ba195d94ae6ab0cd0a50e17470bebc7587f44"
CARRIER_PATH = "backend/tests/test_qoder_ord0287_k8_carrier.py"
CARRIER_BLOB = "894c6d54e345dabdc4050a38f413fdaaa1a92748"
MAIN = "backend/app/main.py"
MAIN_BLOB_LANDED = "416ea4f210e967130710a900cdecd20e7a1b5eca"
GUARD_EXPR = "IdempotencyKey.response_json.is_(None)"
GO = "--go" in sys.argv


def api(path, tries=4):
    for a in range(tries):
        try:
            r = urllib.request.Request("https://api.github.com" + path)
            for k, v in HDRS.items():
                r.add_header(k, v)
            with urllib.request.urlopen(r, timeout=90) as resp:
                return json.loads(resp.read().decode())
        except Exception as exc:  # noqa: BLE001
            print("   GET retry", a + 1, type(exc).__name__, str(exc)[:60])
            time.sleep(2 + 2 * a)
    return None


def git(*a: str) -> str:
    p = subprocess.run(["git", "-C", LANE, *a], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.stdout.strip() if p.returncode == 0 else "GIT_ERR " + p.stderr.strip()[:140]


out = {"ran_at": datetime.now().astimezone().isoformat(timespec="seconds"), "mode": "GO" if GO else "DRY-RUN"}

tip = api("/repos/" + GR + "/git/ref/heads/" + AUTH_REF)["object"]["sha"]
out["authoritative_tip_read"] = tip
out["tip_moved"] = tip != FROZEN_PARENT
out["generation_note"] = ("尖还没动 ⇒ [2][3] 读的就是我这一代的父那一棵：它只证明工具与判据可用，"
                           "不能当成对未来的预测；真正那一次要等 0274 落地后重跑（Q24/Q25 不跨代折算）。")
print(f"[1] 权威尖（GitHub https 读法）= {tip} | 相对我这一代的父 {FROZEN_PARENT[:12]} ⇒ moved={out['tip_moved']}")
if not out["tip_moved"]:
    print("    ⇒ REFUSE_TIP_UNCHANGED：新一代还没落地，re-parent 无从谈起；旧 ref 继续按 Q37 冻结，我什么都不铸。")

tree = api("/repos/" + GR + "/git/commits/" + tip)["tree"]["sha"]
rec = api("/repos/" + GR + "/git/trees/" + tree + "?recursive=1")
byname = {e["path"]: e for e in rec["tree"]}
main_entry = byname.get(MAIN)
out["main_py_entry_at_new_tip"] = {"path": MAIN, "blob": main_entry["sha"], "bytes": main_entry.get("size")}
out["main_py_unchanged_vs_my_generation"] = main_entry["sha"] == MAIN_BLOB_LANDED
print(f"[2] 新尖的 {MAIN} = {main_entry['sha']} ({main_entry['size']:,} B) "
      f"| 与我这一代逐位相同：{out['main_py_unchanged_vs_my_generation']}")

raw = base64.b64decode(api("/repos/" + GR + "/git/blobs/" + main_entry["sha"])["content"]).decode("utf-8")
hits = [i + 1 for i, ln in enumerate(raw.splitlines()) if GUARD_EXPR in ln]
out["guard_expression_hit_lines"] = hits
out["guard_unique"] = len(hits) == 1

# 载体真正 import 了什么，从它自己的 import 语句里读——不是我猜的名字表。
carrier_src = git("show", FROZEN_TIP + ":" + CARRIER_PATH)
out["carrier_source_bytes"] = len(carrier_src.encode("utf-8"))
blocks: list[str] = [carrier_src]
imported: list[tuple[str, str]] = []
lines = carrier_src.splitlines()
i = 0
while i < len(lines):
    ln = lines[i]
    m = __import__("re").match(r"^from\s+([\w\.]+)\s+import\s+(.*)$", ln)
    if m:
        mod, rest = m.group(1), m.group(2)
        while rest.count("(") > rest.count(")"):
            i += 1
            rest += " " + lines[i].strip()
        for nm in [x.strip().rstrip(",") for x in rest.replace("(", "").replace(")", "").split(",")]:
            nm = nm.split(" as ")[0].strip()
            if nm:
                imported.append((mod, nm))
    i += 1
out["carrier_imports_read_from_its_own_file"] = [f"{m}:{n}" for m, n in imported]

src_lines = raw.splitlines()

module_cache: dict[str, tuple[str, list[str]] | None] = {}


def module_file(mod: str) -> str:
    return "backend/" + mod.replace(".", "/") + ".py"


def resolve_in_module(mod: str, name: str) -> dict:
    """在一个模块自己的源里找定义形制；找不到就说找不到（不猜、不拿别的模块顶）。"""
    f = module_file(mod)
    if f not in module_cache:
        entry = byname.get(f)
        if not entry:
            module_cache[f] = None
        else:
            b = base64.b64decode(api("/repos/" + GR + "/git/blobs/" + entry["sha"])["content"]).decode("utf-8")
            module_cache[f] = (entry["sha"], b.splitlines())
    cached = module_cache[f]
    if cached is None:
        return {"file": f, "status": "MODULE_NOT_IN_TREE"}
    pats = [("def", rf"^(?:async )?def {name}\b"), ("class", rf"^class {name}\b"),
            ("binding", rf"^{name}\s*="), ("reexport", rf"^from\s+\S+\s+import\s+.*\b{name}\b"),
            ("import", rf"^import\s+\S*\.?{name}\b"), ("any", rf"\b{name}\b\s*=")]
    for kind, pat in pats:
        for i, ln in enumerate(cached[1], 1):
            if __import__("re").match(pat, ln):
                return {"file": f, "module_blob": cached[0], "status": f"{kind}_at_line_{i}",
                        "line": i, "text": ln.strip()[:90]}
    return {"file": f, "module_blob": cached[0], "status": "NOT_FOUND_IN_THAT_MODULE"}


resolved = {}
for m, n in imported:
    if m == "app" or m.startswith("app."):
        resolved[f"{m}:{n}"] = resolve_in_module(m, n)
out["carrier_imports_resolved_in_their_own_module"] = resolved
out["imports_all_present"] = all(v["status"].startswith(("def", "class", "binding", "reexport", "import"))
                                 for v in resolved.values())
out["unresolved"] = sorted(k for k, v in resolved.items() if not out["carrier_imports_resolved_in_their_own_module"][k]["status"].startswith(("def", "class", "binding", "reexport", "import")))
out["first_probe_self_correction"] = (
    "两枚我自己造出来的假缺失，都记在这里：① 第一版手写符号表只匹配 `def NAME`/`NAME(`，把 ORM 模型 "
    "`class Mission(Base)` 判成缺失；② 第二版把所有 `app.*` 的名字都拿到 main.py 里找，于是 `app.models` 的 "
    "`Journey`/`Place` 与 `app.schemas` 的 `GeneratePlansRequest` 又被判缺失。现在按「名字在它自己那个模块的源里"
    "解析」，并给出命中行与原句。这类错误正是我今晚在别人收据里点名的东西，我自己犯得更早。")
print(f"[3] 守卫表达式 {GUARD_EXPR} 在新尖命中行 {hits} ⇒ 唯一：{out['guard_unique']}")
print(f"    载体 import 的 app.* 名字 {len(resolved)} 个：")
for k, v in resolved.items():
    print(f"      {k:56s} {v['file']:34s} {v['status']}"
          + (f"  | {v.get('text','')[:48]}" if v.get("text") else ""))
print(f"    全部解析到：{out['imports_all_present']} | 未解析：{out['unresolved'] or '无'}")

carrier_at_frozen = git("rev-parse", FROZEN_TIP + ":" + CARRIER_PATH)
out["carrier_blob_at_frozen_tip"] = carrier_at_frozen
out["carrier_blob_matches_r1"] = carrier_at_frozen == CARRIER_BLOB
print(f"[4] 载体文件在冻结尖上的 blob {carrier_at_frozen} | 与 07:14 交付那枚相同：{out['carrier_blob_matches_r1']}")

new_ref = f"review/ord0287-k8-carrier-on-{tip[:9]}"
st_ref, got_ref = None, None
try:
    import urllib.error
    _r = urllib.request.Request("https://api.github.com/repos/" + GR + "/git/ref/heads/" + new_ref)
    for _k, _v in HDRS.items():
        _r.add_header(_k, _v)
    with urllib.request.urlopen(_r, timeout=45) as _x:
        got_ref = json.loads(_x.read().decode())
except urllib.error.HTTPError as _e:
    st_ref = _e.code
out["planned_new_ref"] = new_ref
out["planned_new_ref_already_exists"] = bool(got_ref and "object" in got_ref)
out["planned_new_ref_probe_http_status"] = st_ref
out["planned_commit_shape"] = {
    "parent": tip, "files": [CARRIER_PATH], "mode": "plumbing-only（read-tree/update-index/write-tree/commit-tree）",
    "dates_pinned": True, "pinned_via": "GIT_AUTHOR_DATE / GIT_COMMITTER_DATE 固定 ⇒ 重跑铸出同一枚 sha，不再产生兄弟提交",
    "expected_test_only_diff": True}
print(f"[5] 计划用的新 ref：{new_ref}（已存在：{out['planned_new_ref_already_exists']}）；"
      "旧 ref review/ord0287-k8-carrier-f 不动")

out["ready"] = bool(out["guard_unique"] and out["imports_all_present"] and out["carrier_blob_matches_r1"])
out["if_not_ready"] = ("具名停手并交事实（缺哪个符号 / 守卫命中几处），不改断言、不改产品码、不 skip"
                       if not out["ready"] else "—")
print(f"\nREADY={out['ready']} ⇒ {out['if_not_ready']}")
(RCP / "ord0287_reparent_readiness_r1.json").write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
if GO and out["tip_moved"]:
    print("--go 与尖已动同时成立才会真正铸提交；本脚本的 --go 分支未在本拍执行（尖还没动）。")
elif GO:
    print("ABORT：--go 但尖没动 ⇒ 不铸、不推。")
    sys.exit(1)
