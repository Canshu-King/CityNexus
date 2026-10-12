# -*- coding: utf-8 -*-
"""ORD-0590 execution 域接尖可行性探针（入库版，可移植）。

对任意一枚"权威尖"与"代表枝"现读三件事：
  1. 代表枝上 backend/app/execution/ 对权威尖的独有模块有哪几枚；
  2. 每枚的传递依赖闭包里，哪些符号在权威尖已有、哪些缺签名、哪些整块没有；
  3. 由此给出 ①能直接接 / ②改某一行签名 / ③权威尖根本没有对应形状 的三态表。

用法：
  python execution_feasibility_probe_r2.py                 # 用 ORD-0590 那两个 ref 现取
  CNX_REPO=D:/moodle/CityNexus python execution_feasibility_probe_r2.py
  CNX_TIP_REF=refs/heads/... CNX_REP_REF=refs/heads/... python execution_feasibility_probe_r2.py

退出码：0 = 算完并出了表；3 = 现取不到尖或代表枝（不猜、不退化成旧 sha）。
"""
import ast
import os
import subprocess
import sys

REPO = os.environ.get("CNX_REPO", "D:/moodle/CityNexus")
TIP_REF = os.environ.get("CNX_TIP_REF", "refs/heads/mirror/integration-frontend-apple-pass1")
REP_REF = os.environ.get("CNX_REP_REF",
                         "refs/heads/gpt/revolution-r33-open-world-journey-adaptation")
EXEC_DIR = "backend/app/execution"


def git(*a, **kw):
    r = subprocess.run(["git", "-C", REPO] + list(a), capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=kw.get("timeout", 300))
    if r.returncode != 0:
        return None
    return r.stdout


def tip_sha():
    out = git("ls-remote", "origin", TIP_REF, timeout=120)
    return out.split()[0] if out and out.split() else None


def rep_sha():
    out = git("ls-remote", "origin", REP_REF, timeout=120)
    if out and out.split():
        return out.split()[0]
    # 代表枝可能没在 origin 上单独发布过；退而取本地已有对象，但必须是现读而非记忆
    return git("rev-parse", REP_REF)


_cache = {}


def blob(rev, path):
    k = (rev, path)
    if k not in _cache:
        _cache[k] = git("show", rev + ":" + path)
    return _cache[k]


def dotted_to_path(d):
    return "backend/" + d.replace(".", "/") + ".py"


def module_of_file(rel):
    return "app.execution." + rel.split("/")[-1][:-3]


def top_level(src):
    """symbol -> (kind, line, header text)"""
    out = {}
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out[node.name] = (type(node).__name__, node.lineno)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    out.setdefault(t.id, ("Assign", node.lineno))
    return out


def class_fields(src, name):
    """Column-ish field names of a class, plus whether it is a declarative table."""
    for node in ast.parse(src).body:
        if isinstance(node, ast.ClassDef) and node.name == name:
            cols, init = set(), None
            for sub in node.body:
                if isinstance(sub, ast.AnnAssign) and isinstance(sub.target, ast.Name):
                    cols.add(sub.target.id)
                elif isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Name):
                            cols.add(t.id)
                elif isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef)) and sub.name == "__init__":
                    a = sub.args
                    init = [p.arg for p in (a.posonlyargs + a.args + a.kwonlyargs)]
                    init.append("__star__" if a.kwarg else "")
            return node.lineno, cols, init
    return None, None, None


def func_signature(src, name):
    """Top-level functions only, so every parameter listed here is a real one (no self to drop)."""
    for node in ast.parse(src).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            a = node.args
            names = [p.arg for p in (a.posonlyargs + a.args)] + [p.arg for p in a.kwonlyargs]
            return node.lineno, names, (a.kwarg is not None or a.vararg is not None)
    return None, None, None


def imports_of(src):
    d = {}
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("app."):
            for a in node.names:
                if a.name != "annotations":
                    d.setdefault(node.module, []).append((a.name, node.lineno, a.asname or a.name))
        elif isinstance(node, ast.Import):
            for a in node.names:
                if a.name.startswith("app."):
                    d.setdefault(a.name, []).append(("*", node.lineno, a.asname or a.name))
    return d


def main():
    TIP, REP = tip_sha(), rep_sha()
    if not TIP or not REP:
        sys.stderr.write("CANNOT_PROCEED: tip=%r rep=%r 现取不到，不猜 sha\n" % (TIP, REP))
        return 3
    print("TIP  %s  <- %s" % (TIP, TIP_REF))
    print("REP  %s  <- %s" % (REP, REP_REF))
    print("MERGE-BASE %s" % (git("merge-base", TIP, REP) or "").strip())

    tip_files = sorted((git("ls-tree", "-r", "--name-only", TIP, "--", EXEC_DIR) or "").split())
    rep_files = sorted((git("ls-tree", "-r", "--name-only", REP, "--", EXEC_DIR) or "").split())
    only = [f for f in rep_files if f not in tip_files]
    shared = [f for f in rep_files if f in tip_files]
    print("execution files: tip=%d rep=%d unique_to_rep=%d shared=%d"
          % (len(tip_files), len(rep_files), len(only), len(shared)))
    for f in shared:
        same = blob(TIP, f) == blob(REP, f)
        print("  shared %-46s byte_identical=%s  tip=%d lines rep=%d lines"
              % (f.split("/")[-1], same, len(blob(TIP, f).splitlines()),
                 len(blob(REP, f).splitlines())))

    BATCH = set(module_of_file(f) for f in only)
    verdicts = {}
    for rel in only:
        mod = module_of_file(rel)
        src = blob(REP, rel)
        n = len(src.splitlines())
        direct = imports_of(src)
        seen, sig_gaps, no_shape, tip_ok_mods = set(), set(), set(), set()
        queue = [(mm, s, ln, alias) for mm, ss in direct.items() for s, ln, alias in ss]
        while queue:
            dm, sym, ln, alias = queue.pop()
            if (dm, sym) in seen:
                continue
            seen.add((dm, sym))
            if dm in BATCH:
                if dm != mod:
                    sub = imports_of(blob(REP, dotted_to_path(dm)))
                    for m2, syms2 in sub.items():
                        for s2, l2, al2 in syms2:
                            queue.append((m2, s2, l2, al2))
                continue
            tip_src = blob(TIP, dotted_to_path(dm))
            if tip_src is None:
                no_shape.add("整枚模块 %s 在权威尖没有" % dotted_to_path(dm))
                continue
            tip_ok_mods.add(dm)
            if sym == "*":
                continue
            if sym not in top_level(tip_src):
                if dm == "app.db.models" and class_fields(tip_src, sym)[0] is None:
                    no_shape.add("表 %s 在权威尖整张没有" % sym)
                else:
                    # the module itself is on the tip, so the gap has an addressable line -> ②
                    sig_gaps.add("符号 %s 在权威尖 %s 的顶层没有（模块在，改动点可指名）"
                                 % (sym, dotted_to_path(dm)))
                continue
            # attribute / constructor level: does the tip shape carry the fields the code uses?
            tree = ast.parse(src)
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                        and node.value.id == alias and node.attr not in ("query", "metadata"):
                    line, cols, init = class_fields(tip_src, sym)
                    if line and cols and init is None and node.attr not in cols \
                            and not node.attr.startswith("_"):
                        sig_gaps.add("列 %s.%s 权威尖 %s:%d 该类没声明（用于 %s:%d）"
                                     % (sym, node.attr, dotted_to_path(dm), line, rel, node.lineno))
                if isinstance(node, ast.Call) and node.keywords:
                    target = None
                    if isinstance(node.func, ast.Name) and node.func.id == alias:
                        target = sym
                    elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name) \
                            and node.func.value.id == alias:
                        target = sym + "." + node.func.attr
                    if target is None:
                        continue
                    base = target.split(".")[0]
                    cline, cols, init = class_fields(tip_src, base)
                    fline, fnames, variadic = func_signature(tip_src, target)
                    kws = [k.arg for k in node.keywords if k.arg]
                    if fline:
                        allowed, star = set(fnames), variadic
                    elif cline and init is not None:
                        allowed, star = set(init) - {"__star__"}, "__star__" in init
                    elif cline:
                        allowed, star = set(cols), False
                    else:
                        continue
                    if star:
                        continue
                    for bad in [k for k in kws if k not in allowed]:
                        sig_gaps.add("%s 调用不接受 %s（权威尖 %s:%s）"
                                     % (target, bad, dotted_to_path(dm), fline or cline))
        if sig_gaps and no_shape:
            v = "②③"
        elif no_shape:
            v = "③"
        elif sig_gaps:
            v = "②"
        else:
            v = "①"
        verdicts[mod] = {"lines": n, "verdict": v, "sig": sorted(sig_gaps),
                         "none": sorted(no_shape)}

    print("\n=== 三态判定 ===")
    for mod in sorted(verdicts, key=lambda m: (verdicts[m]["verdict"], m)):
        d = verdicts[mod]
        print("%-46s %5d lines  %s" % (mod, d["lines"], d["verdict"]))
        for s in d["sig"]:
            print("      [②签名] %s" % s)
        for s in d["none"]:
            print("      [③无形状] %s" % s)

    counts = {}
    for d in verdicts.values():
        counts[d["verdict"]] = counts.get(d["verdict"], 0) + 1
    lines = {}
    for d in verdicts.values():
        lines[d["verdict"]] = lines.get(d["verdict"], 0) + d["lines"]
    print("\n=== 汇总 ===")
    for k in ("①", "②", "②③", "③"):
        print("  %s : %d 枚 / %d 行" % (k, counts.get(k, 0), lines.get(k, 0)))
    assert sum(counts.values()) == len(only), "verdict count must equal module count"
    tables = sorted({s.split()[1] for d in verdicts.values() for s in d["none"] if s.startswith("表 ")})
    mods = sorted({s.split()[1].split("/")[-1] for d in verdicts.values() for s in d["none"] if s.startswith("整枚模块 ")})
    print("  去重后：缺失表 %d 张，缺失兄弟模块 %d 枚" % (len(tables), len(mods)))
    print("  缺失模块：%s" % ", ".join(mods))

    # ---- API wiring: which routes the execution family needs, and which request models exist
    def collect_routes(rev):
        src = blob(rev, "backend/app/main.py")
        if src is None:
            return []
        res = []
        for node in ast.parse(src).body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for dec in node.decorator_list:
                if not (isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute)
                        and isinstance(dec.func.value, ast.Name)
                        and dec.func.value.id in ("app", "router")
                        and dec.func.attr in ("get", "post", "patch", "put", "delete")):
                    continue
                path = dec.args[0].value if dec.args and isinstance(dec.args[0], ast.Constant) else "?"
                emods = set()
                ann = []
                for sub in ast.walk(node):
                    if isinstance(sub, ast.ImportFrom) and sub.module and sub.module.startswith("app.execution"):
                        emods.add(sub.module)
                for a in node.args.args + node.args.kwonlyargs:
                    if a.annotation is not None:
                        txt = ast.unparse(a.annotation)
                        if txt and txt[0].isupper():
                            ann.append(txt.strip("[]|, ").split("[")[0].strip())
                res.append({"m": dec.func.attr, "p": path, "line": dec.lineno,
                            "exec": sorted(emods), "ann": ann})
        return res

    tr, rr = collect_routes(TIP), collect_routes(REP)
    tkeys = {(r["m"], r["p"]) for r in tr}
    er = [r for r in rr if r["exec"]]
    coll = [r for r in er if (r["m"], r["p"]) in tkeys]
    new = [r for r in er if (r["m"], r["p"]) not in tkeys]
    tip_models = top_level(blob(TIP, "backend/app/schemas.py"))
    NOISE = {"Request", "UUID", "Session", "Response"}
    used = sorted({a for r in er for a in r["ann"] if a and a[0].isupper()})
    missing_models = [a for a in used if a not in tip_models and a not in NOISE]
    reusable = [a for a in used if a in tip_models]
    print("\n=== API 接线面（现读两尖 main.py）===")
    print("  路由总数 tip=%d rep=%d；体内引用 app.execution 的路由=%d" % (len(tr), len(rr), len(er)))
    print("  其中 method+path 与权威尖相同（真撞面）=%d 枚：" % len(coll))
    for r in coll:
        print("      %-6s %s  代表枝 backend/app/main.py:%d" % (r["m"], r["p"], r["line"]))
    print("  其中权威尖完全没有的新路由=%d 枚" % len(new))
    print("  这些路由引用的请求/响应模型名=%d 个，权威尖 schemas 里缺=%d 个，可直接复用=%d 个（%s）"
          % (len(used), len(missing_models), len(reusable), ", ".join(reusable)))
    print("\nprobe done (every claim above is re-measured from the two SHAs printed first)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
