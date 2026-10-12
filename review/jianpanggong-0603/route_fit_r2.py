# ORD-0603 audit, AST version.
#
# Why this version exists: the first pass measured a route's body as "from its decorator to
# the next decorator", which swallowed every undecorated helper defined in between --
# route-evidence's "body" came out 2555 lines long and read as carrying all three field
# families. That was a broken ruler, not a finding. This pass parses backend/app/main.py
# with ast, takes each decorated function's own source segment, and follows the same-file
# private helpers it calls one level deep as a second arm.
import ast
import io
import json
import os
import re
import subprocess
import sys

REPO = r"D:/moodle/CityNexus"
LINE = "refs/heads/mirror/integration-frontend-apple-pass1"
OUT = r"D:/moodle/_jp_0603_audit"
PROVENANCE = ["provenance", "route_provenance", "fact_quality"]
PROVIDER = ["provider", "provider_key"]
DURATION = ["duration_min", "minutes"]
CAPTURE = ["explicit_fact", "provider_failed", "provider_degraded"]
REQUEST = ["origin_key", "target_key", "requested_mode", "provider_policy_version",
           "route_truth_policy_version", "origin_evidence"]


def sh(args):
    p = subprocess.Popen(["git", "-c", "core.quotepath=false"] + args, cwd=REPO,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    o, e = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(e.decode("utf-8", "replace")[:160])
    return o.decode("utf-8", "replace")


def words_in(text, words):
    out = {}
    for w in words:
        n = len(re.findall(r'\b%s\b' % re.escape(w), text))
        if n:
            out[w] = n
    return out


def missing(x):
    fam = {"出处": x["tr_prov"], "供应商": x["tr_provider"], "分钟": x["tr_dur"]}
    return [k for k, v in fam.items() if not v]


def main():
    tip = sh(["ls-remote", "origin", LINE]).split()[0]
    src = sh(["show", tip + ":backend/app/main.py"])
    tree = ast.parse(src)
    lines = src.split("\n")

    helpers = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            helpers[node.name] = ast.get_source_segment(src, node) or ""

    routes = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call) or not isinstance(dec.func, ast.Attribute):
                continue
            if getattr(dec.func.value, "id", None) != "app":
                continue
            if dec.func.attr not in ("get", "post", "put", "patch", "delete"):
                continue
            path = str(dec.args[0].value) if dec.args and isinstance(dec.args[0], ast.Constant) else ""
            own = ast.get_source_segment(src, node) or ""
            called = sorted({n.id for n in ast.walk(node)
                             if isinstance(n, ast.Name) and n.id in helpers and n.id.startswith("_")})
            routes.append(dict(line=node.lineno, method=dec.func.attr, path=path, name=node.name,
                               own=own, called=called, end=getattr(node, "end_lineno", node.lineno)))
    gets = [r for r in routes if r["method"] == "get"]

    def build(pool):
        out = []
        for r in pool:
            span = "\n".join([r["own"]] + [helpers.get(h, "") for h in r["called"]])
            x = dict(line=r["line"], end=r["end"], path=r["path"], name=r["name"], method=r["method"],
                     called=r["called"],
                     own_prov=words_in(r["own"], PROVENANCE), own_provider=words_in(r["own"], PROVIDER),
                     own_dur=words_in(r["own"], DURATION),
                     tr_prov=words_in(span, PROVENANCE), tr_provider=words_in(span, PROVIDER),
                     tr_dur=words_in(span, DURATION),
                     cap=words_in(span, CAPTURE), req=words_in(span, REQUEST))
            x["own_all"] = bool(x["own_prov"] and x["own_provider"] and x["own_dur"])
            x["tr_all"] = bool(x["tr_prov"] and x["tr_provider"] and x["tr_dur"])
            out.append(x)
        return out

    posts = build([r for r in routes if r["method"] != "get"])
    post_all = [x for x in posts if x["tr_all"]]

    rows = []
    for r in gets:
        span = "\n".join([r["own"]] + [helpers.get(h, "") for h in r["called"]])
        x = dict(line=r["line"], end=r["end"], path=r["path"], name=r["name"], called=r["called"],
                 own_prov=words_in(r["own"], PROVENANCE), own_provider=words_in(r["own"], PROVIDER),
                 own_dur=words_in(r["own"], DURATION),
                 tr_prov=words_in(span, PROVENANCE), tr_provider=words_in(span, PROVIDER),
                 tr_dur=words_in(span, DURATION),
                 cap=words_in(span, CAPTURE), req=words_in(span, REQUEST))
        x["own_all"] = bool(x["own_prov"] and x["own_provider"] and x["own_dur"])
        x["tr_all"] = bool(x["tr_prov"] and x["tr_provider"] and x["tr_dur"])
        rows.append(x)

    own_all = [x for x in rows if x["own_all"]]
    tr_all = [x for x in rows if x["tr_all"]]
    counts = {}
    for x in rows:
        n = len(missing(x))
        counts[n] = counts.get(n, 0) + 1
    near = [x for x in rows if len(missing(x)) <= 2]
    none3 = [x for x in rows if len(missing(x)) == 3]
    cap_rows = [x for x in rows if x["cap"]]
    req_rows = [x for x in rows if x["req"]]

    os.makedirs(OUT, exist_ok=True)
    L = []
    A = L.append
    A("# ORD-0603 现尖读路由能否承接 route_session_contract（AST 重测）。尖 %s，backend/app/main.py 共 %d 行、路由 %d 枚、其中 GET %d 枚。"
      % (tip, len(lines), len(routes), len(gets)))
    A("# 尺的形状：ast.get_source_segment 只取被 @app.get 装饰的那枚函数自己的源码段（体内那一列）；连同它调用的本文件私有 helper 一层（span 那一列）。")
    A("# 第一版按「装饰器到下一个装饰器」取段，把中间未装饰的 helper 全吞了进来：route-evidence 因此被量成 2555 行的体，报出假「三样齐」，那是尺坏不是线有。")
    A("# 判据词族：出处 %s；供应商 %s；分钟 %s。这三样是 fact_is_eligible_for_live_readiness 真正读的名字（现读 backend/app/execution/route_session_contract.py:93 至 :100）。"
      % (PROVENANCE, PROVIDER, DURATION))
    A("# 总结论：体内三样齐 %d 枚；含一层 helper 三样齐 %d 枚；缺样分布 缺1=%d 缺2=%d 缺3=%d（合计 %d 枚 GET）。"
      % (len(own_all), len(tr_all), counts.get(1, 0), counts.get(2, 0), counts.get(3, 0), len(rows)))
    A("")
    A("# 一、最接近的 %d 枚（连一层 helper 也算上，缺样最少优先）" % len(near))
    for x in sorted(near, key=lambda y: (len(missing(y)), y["line"])):
        A("main.py:%d-%d GET %s 函数 %s ｜ 缺：%s ｜ 体内 出处=%s 供应商=%s 分钟=%s ｜ 含 helper 出处=%s 供应商=%s 分钟=%s ｜ helper=%s"
          % (x["line"], x["end"], x["path"], x["name"], "、".join(missing(x)),
             json.dumps(x["own_prov"], ensure_ascii=False), json.dumps(x["own_provider"], ensure_ascii=False),
             json.dumps(x["own_dur"], ensure_ascii=False), json.dumps(x["tr_prov"], ensure_ascii=False),
             json.dumps(x["tr_provider"], ensure_ascii=False), json.dumps(x["tr_dur"], ensure_ascii=False),
             ",".join(x["called"]) or "无"))
    A("")
    A("# 二、classify_capture 那一面（要 explicit_fact / provider_failed / provider_degraded）")
    A("# 76 枚 GET 里，连一层 helper 也算上，出现这三个名字的共 %d 枚。" % len(cap_rows))
    for x in cap_rows[:8]:
        A("main.py:%d GET %s 命中 %s" % (x["line"], x["path"], json.dumps(x["cap"], ensure_ascii=False)))
    A("")
    A("# 三、RouteRequest 那一面（要 origin_key / target_key / requested_mode / 两枚策略版本 / origin_evidence）")
    A("# 同样口径下命中 %d 枚。" % len(req_rows))
    for x in req_rows[:8]:
        A("main.py:%d GET %s 命中 %s" % (x["line"], x["path"], json.dumps(x["req"], ensure_ascii=False)))
    A("")
    A("# 四、三样全缺的 %d 枚 GET，逐枚行号与路径（这是「无处可接」那半边的一张一张点名）" % len(none3))
    for x in sorted(none3, key=lambda y: y["line"]):
        A("main.py:%d GET %s 函数 %s" % (x["line"], x["path"], x["name"]))
    A("")
    A("# 五、对照臂：非 GET 的路由（写路由）里有 %d 枚连一层 helper 三样齐，它们是这枚契约将来真正的落点候选"
      % len(post_all))
    for x in sorted(post_all, key=lambda y: y["line"])[:12]:
        A("main.py:%d-%d %s %s 函数 %s ｜ 出处=%s 供应商=%s 分钟=%s ｜ helper=%s"
          % (x["line"], x["end"], x["method"].upper(), x["path"], x["name"],
             json.dumps(x["tr_prov"], ensure_ascii=False), json.dumps(x["tr_provider"], ensure_ascii=False),
             json.dumps(x["tr_dur"], ensure_ascii=False), ",".join(x["called"]) or "无"))
    text = "\n".join(L) + "\n"
    with io.open(os.path.join(OUT, "routes_ast_r1.txt"), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    json.dump(dict(tip=tip, lines=len(lines), routes=len(routes), gets=len(gets),
                   own_all=[x["line"] for x in own_all], tr_all=[x["line"] for x in tr_all],
                   missing_counts=counts, near=[x["line"] for x in near],
                   capture=[x["line"] for x in cap_rows], request=[x["line"] for x in req_rows],
                   rows=rows),
              io.open(os.path.join(OUT, "routes_ast_r1.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    sys.stdout.write(text[:1200] + "\n...\nGET=%d 体内齐=%d 含helper齐=%d 接近(缺<=1)=%d 三样全缺=%d cap命中=%d req命中=%d\n"
                     % (len(gets), len(own_all), len(tr_all),
                        len([x for x in near if len(missing(x)) <= 1]), len(none3), len(cap_rows), len(req_rows)))


main()
