"""ORD-0320: bucket the 16 `upstream_prose` cells of the Q64 sweep - read-only, one new delivery.

Three predicates decide everything, and all three are computed against the bytes of the current tip
rather than against anyone's summary:

  upstream_read   - does the string come out of an HTTP response body field (or a throw that embeds
                    one, found in the same file or in a request helper the file imports)?
  reaches_dom     - is it rendered as JSX text / text content (not merely held in a variable)?
  attributed      - at that render site (a window around it) is there an origin marker: an
                    `*-origin` attribute or a visible label that names who wrote the sentence?

The order's own definitions then map them. Two cases are deliberately NOT forced into the first two
buckets, because my predicates cannot decide them and pretending otherwise is how a triage becomes a
rubber stamp; they go to NEEDS_RULING with the missing definition named.

Every cited line is re-read from `git show <tip>:<path>` and asserted byte-equal to the text the
sweep quoted, so the file's blob equality is not the only thing checked - the line numbers are too.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path("D:/moodle/_qoder_d_lane_20260923")
SC = ROOT / "_scratch_0320"
SWEEP = json.loads((SC / "sweep_r1.json").read_text(encoding="utf-8"))
VERIFY = json.loads((SC / "verify_r1.json").read_text(encoding="utf-8"))
TIP = SWEEP["generation"]
RULER_R2 = SWEEP["ruler"]
OUT = SC / "ord0320_triage_r2.json"
URL = "https://github.com/Canshu-King/CityNexus.git"
ORDER = "CMDR-0926-0308 / ORD-0320"

# an origin marker: an attribute that names where the sentence came from, or a label that says so
ATTRIBUTION = re.compile(r"(data-[a-z-]*origin\s*=|origin=\{|\bfrom\s*===\s*\"server\"|"
                         r"服务器给出的原因|这台设备自己的读数|Reason the server gave|server sent no sentence)")
# reading a field that came off a response body. An i18n label like `t.detail` / `detail: "技术详情"`
# is NOT one - the first version of this regex matched those and manufactured an upstream read.
UPSTREAM_FIELD = re.compile(r"\b(body|payload|data|json|resp|response)\s*\??\.\s*(error|detail|message|text)"
                            r"|\brejectionReason\s*\("
                            r"|\bresponse\s*\??\.\s*message\b")
I18N_LABEL = re.compile(r"(\{\s*t\.[a-zA-Z_.]+\s*\}|\bt\.[a-z]+[A-Z]\w*|^\s*detail\s*:|\bstrings?\b\s*=)")
# a render site: JSX expression children and text-ish attributes
RENDER = re.compile(r"(<(p|code|pre|span|div|summary)\b|^\s*[\{\[]|=\{)")
# success-path content channels: a server-authored message shown as content, not as a failure reason
CONTENT_CHANNEL = re.compile(r"(role:\s*\"assistant\"|agentRun\.(outcome|failure_reason))")
# a file that renders a caught Error object it did not itself produce (the root boundary shape)
BOUNDARY_LIKE = re.compile(r"(componentDidCatch|static\s+getDerivedStateFromError)")


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          encoding="utf-8", errors="replace").stdout


def blob(data: bytes) -> str:
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


FILES: dict[str, list[str]] = {}
# strongest link wins; a missing key here would raise, so the table lives in exactly one place
RANK = {"DIRECT_FROM_RESPONSE_FIELD": 0, "VIA_LOCAL_VARIABLE": 1,
        "FROM_ERROR_OBJECT_MESSAGE": 2, "VIA_VARIABLE_CHAIN": 3}


def upstream_throwers() -> list[str]:
    """Every `throw new Error(...)` across frontend/src that embeds a response field.

    This is the population a root error boundary could in principle surface, so the boundary cell is
    argued from a countable set instead of from my reading of one file.
    """
    out = git("grep", "-n", "-e", "throw new Error", TIP, "--", "frontend/src")
    hits = []
    for line in out.splitlines():
        if not line.startswith(TIP + ":"):
            continue
        path, _, rest = line[len(TIP) + 1:].partition(":")
        _, _, text = rest.partition(":")
        if re.search(r"(body|payload)\??\.(error|detail)|rejectionReason\(", text):
            hits.append(f"{path.replace('frontend/src/', '')}:{text.strip()[:70]}")
    return sorted(hits)


UPSTREAM_THROWERS = upstream_throwers()


def lines_of(path: str) -> list[str]:
    if path not in FILES:
        out = git("show", f"{TIP}:{path}")
        if not out:
            raise SystemExit(f"ABORT: git show returned nothing for {path}@{TIP}")
        FILES[path] = out.splitlines()
    return FILES[path]


def cite(path: str, line: int) -> str:
    src = lines_of(path)
    if not 1 <= line <= len(src):
        raise SystemExit(f"ABORT: {path}:{line} is outside the file ({len(src)} lines at the tip)")
    return src[line - 1]


def quoted_matches(path: str, line: int, expected: str) -> bool:
    return cite(path, line).strip() == expected.strip()


def referrers(path: str) -> list[str]:
    base = path.split("/")[-1].rsplit(".", 1)[0]
    out = git("grep", "-n", base, TIP, "--", "frontend/src")
    hits = {}
    for line in out.splitlines():
        if not line.startswith(TIP + ":"):
            continue
        rest = line[len(TIP) + 1:]
        where, _, text = rest.partition(":")
        if where == path or not where.endswith((".ts", ".tsx")):
            continue
        if re.search(r"import[^;]*from\s+[^;]*" + base + r"|import\s*\(\s*[^;]*" + base, text):
            hits[where] = text.strip()[:80]
    return sorted(hits)


def mounted_at_root(path: str, depth: int = 0, seen=None) -> list[str]:
    """The import chain from this file up to main.tsx, or [] when no chain exists at this depth."""
    seen = seen or set()
    if path in seen or depth > 4:
        return []
    seen = seen | {path}
    for parent in referrers(path):
        if parent.endswith("main.tsx"):
            return [path, parent]
        chain = mounted_at_root(parent, depth + 1, seen)
        if chain:
            return [path] + chain
    return []


def window(path: str, centre: int, span: int = 10) -> tuple[int, list[str]]:
    src = lines_of(path)
    lo, hi = max(1, centre - span), min(len(src), centre + span)
    return lo, [cite(path, n) for n in range(lo, hi + 1)]


def rendered_names(verified: list[dict]) -> list[str]:
    """Identifiers actually rendered at the sink, inside any expression form."""
    out = []
    for v in verified:
        for expr in re.findall(r"\{([^{}]*)\}", v["text"]):
            out += [t for t in re.findall(r"\b([a-z][\w$]*)\b", expr)
                    if t not in ("string", "null", "true", "false", "zh", "error", "typeof",
                                 "length", "toString")
            or t == "error"]
    return sorted(set(out))


def value_carries_upstream(path: str, name: str, depth: int = 0,
                           hops: list | None = None) -> list | None:
    """Follow a local variable back to an upstream field or an Error message, at most 3 hops.

    `setRawDetail(failure)` is not a chain until `failure` itself is traced to
    `error.message`; stopping at one hop would leave a real cell looking unproven.
    """
    hops = hops or []
    if depth > 3 or name in [h[0] for h in hops]:
        return None
    src = lines_of(path)
    pattern = re.compile(rf"\b(?:const|let|var)?\s*{re.escape(name)}\s*=\s*(.+)", re.M)
    for n, line in enumerate(src, 1):
        m = pattern.search(line)
        if not m:
            continue
        rhs = m.group(1)
        hops_here = hops + [(name, n, rhs.strip()[:90])]
        if UPSTREAM_FIELD.search(rhs):
            return hops_here
        if re.search(r"\b(error|err|e|reason)\s*\??\.\s*message|String\(\s*(error|err|e)\b", rhs):
            return hops_here
        for inner in re.findall(r"\b([a-z][\w$]*)\b", rhs):
            if inner in ("null", "true", "false", "zh", "t", "String", "error", "err"):
                continue
            deeper = value_carries_upstream(path, inner, depth + 1, hops_here)
            if deeper:
                return deeper
    return None


def setter_link(path: str, rendered: str, anchor: int) -> dict:
    """Prove the rendered state variable is written from an upstream-derived expression.

    Every call site has to be looked at: the first `setMessage(null)` is a clearing call, and an
    instrument that stops there reports "no chain" for a cell that does have one.
    """
    src = lines_of(path)
    joined = "\n".join(src)
    setter_candidates = [f"set{rendered[0].upper()}{rendered[1:]}", f"set{rendered}"]
    setter = next((s for s in setter_candidates if re.search(rf"\b{s}\(", joined)), None)
    if setter is None:
        return {"rendered": rendered, "link": "NO_SETTER_FOUND"}
    carried = set(re.findall(r"\bconst\s+(\w+)\s*=[^;\n]*(?:body|payload|raw)\b", joined))
    sites = []
    best = None
    for n, line in enumerate(src, 1):
        if not re.search(rf"\b{setter}\(", line):
            continue
        depth, region = 0, []
        for k in range(n - 1, min(len(src), n + 14)):
            text = src[k]
            region.append(text)
            depth += text.count("(") - text.count(")")
            if depth <= 0 and "(" in text:
                break
        body = "\n".join(region)
        if re.search(r"\bset\w*\(\s*null\s*\)", line):
            sites.append({"setter_line": n, "verdict": "CLEARING_CALL"})
            continue
        link = None
        if UPSTREAM_FIELD.search(body):
            link = "DIRECT_FROM_RESPONSE_FIELD"
        elif carried & set(re.findall(r"\b(\w+)\b", body)):
            link = "VIA_LOCAL_VARIABLE"
        elif re.search(r"\b(error|err|e|reason)\s*\??\.\s*message|String\(\s*(error|err|e)\b", body):
            link = "FROM_ERROR_OBJECT_MESSAGE"
        else:
            for arg in re.findall(r"\b([a-z][\w$]*)\b", body):
                chain_hops = value_carries_upstream(path, arg)
                if chain_hops:
                    link = "VIA_VARIABLE_CHAIN"
                    sites.append({"setter_line": n, "verdict": link, "hops": chain_hops,
                                  "setter_text": line.strip()[:90]})
                    if best is None or (RANK[link], abs(n - anchor)) < (
                            RANK[best["link"]], abs(best["setter_line"] - anchor)):
                        best = {"rendered": rendered, "link": link, "setter_line": n,
                                "setter_text": line.strip()[:90],
                                "hops": [[h[0], h[1], h[2]] for h in chain_hops]}
                    break
        if link and best is not None and (RANK[link], abs(n - anchor)) < (
                RANK[best["link"]], abs(best["setter_line"] - anchor)):
            best = {"rendered": rendered, "link": link, "setter_line": n,
                    "setter_text": line.strip()[:90], "region": sites[-1]["region"]} \
                if link != "VIA_VARIABLE_CHAIN" else best
        sites.append({"setter_line": n, "verdict": link or "ARGUMENT_NOT_UPSTREAM",
                      "setter_text": line.strip()[:90],
                      "region": [f"{n + i}:{t.strip()[:80]}" for i, t in enumerate(region)][:6]})
        if link and (best is None or RANK[link] < RANK[best["link"]]):
            best = {"rendered": rendered, "link": link, "setter_line": n,
                    "setter_text": line.strip()[:90],
                    "region": sites[-1]["region"]}
    return best or {"rendered": rendered, "link": "ALL_SETTER_SITES_CLEAN_OR_UNUPSTREAM",
                    "sites_examined": len(sites), "per_site": sites[:8]}


rows = []
for hit in SWEEP["hits"]:
    if hit["classification"] != "upstream_prose":
        continue
    path, anchor = hit["file"], hit["line"]
    blob_at_tip = git("rev-parse", f"{TIP}:{path}").strip()
    basis = hit.get("basis") or []
    verified = []
    for b in basis:
        bpath, bline, btext = b["file"], b["line"], b["text"]
        ok = quoted_matches(bpath, bline, btext)
        verified.append({"cite": f"{bpath}:{bline}", "text": cite(bpath, bline),
                         "equals_what_the_sweep_quoted": ok})
    unmatched = [v for v in verified if not v["equals_what_the_sweep_quoted"]]
    producers = [v for v in verified if UPSTREAM_FIELD.search(v["text"])
                 and not I18N_LABEL.search(v["text"])]
    sinks = [v for v in verified if RENDER.search(v["text"]) and ("<" in v["text"] or v["text"].strip().startswith("{"))]
    lo, win = window(path, anchor)
    attribution_hits = [(lo + i, t.strip()) for i, t in enumerate(win) if ATTRIBUTION.search(t)]
    file_throws_upstream = bool(re.search(r"throw new Error\([^\n]*(body|payload)", "\n".join(lines_of(path))))
    boundary_like = bool(BOUNDARY_LIKE.search("\n".join(lines_of(path))))
    content_channel = bool(CONTENT_CHANNEL.search(hit.get("why", "") + " " + " ".join(
        v["text"] for v in verified)))
    own_read = bool(producers) or file_throws_upstream
    # a boundary renders an Error object thrown somewhere below it; whether an upstream-carrying
    # throw can reach it depends on the phase it throws in, which this sweep cannot see
    inherited_read = boundary_like and bool(UPSTREAM_THROWERS) and not producers
    upstream_read = own_read or inherited_read
    reaches_dom = bool(sinks)
    attributed = bool(attribution_hits)
    chain = mounted_at_root(path)
    # the last link of the chain: is the identifier actually rendered by the file really the one the
    # upstream value was written into?
    sink_names = rendered_names(sinks)
    links = [setter_link(path, name, anchor) for name in sink_names]
    rank = {"DIRECT_FROM_RESPONSE_FIELD": 0, "VIA_LOCAL_VARIABLE": 1,
            "FROM_ERROR_OBJECT_MESSAGE": 2, "VIA_VARIABLE_CHAIN": 3}
    established = [l for l in links if l["link"] in RANK]
    established.sort(key=lambda l: RANK[l["link"]])
    identity = established[0] if established else (links[0] if links else {"link": "NO_RENDERED_NAME"})
    state_proven = bool(established) or bool(inherited_read or own_read and not sink_names)

    if attributed and reaches_dom:
        # the order's own compliance condition is checked first: it is what distinguishes the
        # shipped cell from the free-text ones
        bucket, missing = "COMPLIANT_WITH_ATTRIBUTION", None
    elif not upstream_read:
        bucket, missing = "NEEDS_RULING", ("本文件的引用行里没有一条真的读响应字段（i18n 标签不算），"
                                          "也没有内嵌上游正文的 thrower ⇒ 它是不是 upstream_prose 本身要重判")
    elif content_channel:
        bucket = "NEEDS_RULING"
        missing = ("Q64 未定义『服务器 authored 的内容通道』（助手回话 / agent outcome）算不算「上游正文」："
                   "这类句子不是失败原因，但确实是服务器写的字上屏")
    elif inherited_read:
        bucket = "NEEDS_RULING"
        missing = (f"根错误边界渲染的是别处抛出的 Error.message + React 组件栈；全树有 "
                   f"{len(UPSTREAM_THROWERS)} 枚 thrower 把响应字段塞进 Error.message（清单见 "
                   f"population_upstream_throwers），上游句子能否到达这里"
                   "取决于抛出阶段（render/effect 会被边界接住，事件处理器里的 throw 不会），"
                   "Q64/边界口径都没定义这一层 ⇒ 不自己拍。另记一句：组件栈进 `<pre>` 是"
                   "另一条规则的事，不在本单射程")
    elif reaches_dom and not state_proven:
        bucket = "NEEDS_RULING"
        missing = (f"渲染点上的名字 `{identity.get('rendered', '?')}` 与本文件里的上游生产者找不到写入链"
                   f"（setter 分析结果 `{identity['link']}`）⇒ 这条上游句子到底有没有走到这里，未证")
    elif reaches_dom:
        bucket = "FIX_IN_PRODUCT"
        missing = None
    else:
        bucket, missing = "NEEDS_RULING", "该格的值在本文件内没有可确认的渲染点（sink 行未落在本文件）"
    # two known shape questions the predicates cannot settle, applied as explicit annotations
    if bucket == "FIX_IN_PRODUCT" and re.search(r"^\s*<details|<summary>", "\n".join(win)):
        missing_fold = ("该渲染点在默认折叠的 <details> 里：字节进 DOM，但『不展开就算不算上屏』"
                        "Q64 未定义 ⇒ 仍按上屏记 FIX，同时把这一句挂给仲裁")
    else:
        missing_fold = None

    rows.append({
        "id": f"T{len(rows) + 1:02d}",
        "file": path,
        "blob_at_tip": blob_at_tip,
        "blob_quoted_by_the_sweep": hit.get("blob"),
        "blob_equality": blob_at_tip == hit.get("blob"),
        "ruler_rule": hit["rule"],
        "ruler_anchor_line": anchor,
        "basis_lines_re_read": verified,
        "basis_lines_that_do_not_match_the_tip": [v["cite"] for v in unmatched],
        "predicates": {
            "upstream_read": upstream_read,
            "upstream_producer_lines": [v["cite"] for v in producers],
            "in_file_thrower_embeds_response_body": file_throws_upstream,
            "reaches_dom": reaches_dom,
            "render_lines": [v["cite"] for v in sinks],
            "attributed_at_the_render_site": attributed,
            "attribution_evidence": [{"line": n, "text": t} for n, t in attribution_hits],
            "window_checked": {"from": lo, "to": lo + len(win) - 1},
            "rendered_names_at_the_sink": sink_names,
            "state_write_chain": identity,
            "state_link_established": state_proven,
        },
        "bucket": bucket,
        "missing_definition": missing,
        "details_fold_open_question": missing_fold,
        "mount_chain_to_root": [c.replace("frontend/src/", "") for c in chain] or "NOT_MOUNTED_WITHIN_4_HOPS",
        "phone_side": (
            {"verdict": "REACHABLE_IF_THE_STATE_OCCURS" if chain else "UNKNOWN",
             "why": (f"组件挂在 {' -> '.join(c.replace('frontend/src/', '') for c in chain) if chain else '未在 4 跳内挂到根'}；"
                     "句子只在该失败状态出现时上屏"),
             "unknown_step": ("手机侧 served bundle 的 asset 归属未查（边界：不碰手机链、不跑 vite build）；"
                              "本行只主张源码可达 + 触发条件")})
        ,
        "s1_why_verbatim": hit.get("why"),
    })

buckets = {}
for r in rows:
    buckets[r["bucket"]] = buckets.get(r["bucket"], 0) + 1
counts_by_file = {}
for r in rows:
    counts_by_file[r["file"]] = counts_by_file.get(r["file"], 0) + 1

tip_now = git("ls-remote", URL, "refs/heads/mirror/integration-frontend-apple-pass1").split("\t")[0].strip()


def line_at(rev: str, path: str, n: int) -> str:
    src = git("show", f"{rev}:{path}").splitlines()
    return src[n - 1].strip() if 1 <= n <= len(src) else "ABSENT_AT_THIS_REV"


# The tip can move while this order is being measured, so every cited line is re-read at the new tip
# too: a cell whose file bytes are unchanged transfers, and a cell whose line moved must say so.
transfer = {}
for r in rows:
    path = r["file"]
    blob_new = git("rev-parse", "--verify", "-q", f"{tip_now}:{path}").strip()
    lines_cited = sorted({int(v["cite"].rsplit(":", 1)[1]) for v in r["basis_lines_re_read"]}
                         | {int(c.rsplit(":", 1)[1]) for c in r["predicates"]["upstream_producer_lines"]}
                         | {int(r["ruler_anchor_line"])})
    moved = [n for n in lines_cited
             if line_at(TIP, path, n) != line_at(tip_now, path, n)]
    transfer[r["id"]] = {"blob_at_sweep_tip": r["blob_at_tip"], "blob_at_current_tip": blob_new,
                         "bytes_identical": blob_new == r["blob_at_tip"],
                         "cited_lines": lines_cited, "lines_that_differ": moved,
                         "verdict": ("CITES_HOLD_ON_BOTH_TIPS" if blob_new == r["blob_at_tip"] and not moved
                                     else "RE-MEASURE_ON_THE_CURRENT_TIP")}
    if blob_new != r["blob_at_tip"] or moved:
        # re-find the same render site by its own text at the new tip; a shifted line is not a
        # different cell, and silently keeping the old number would be a stale cite
        new_src = git("show", f"{tip_now}:{path}").splitlines()
        sink_text = next((v["text"].strip() for v in r["basis_lines_re_read"]
                          if v["cite"].rsplit(":", 1)[1] in {str(n) for n in
                                                             [int(x.rsplit(":", 1)[1])
                                                              for x in r["predicates"]["render_lines"]]}), None)
        at_new = [n for n, line in enumerate(new_src, 1) if sink_text and line.strip() == sink_text]
        nearby_attr = []
        if at_new:
            lo2 = max(1, at_new[0] - 10)
            for k in range(lo2, min(len(new_src), at_new[0] + 10) + 1):
                if ATTRIBUTION.search(new_src[k - 1]):
                    nearby_attr.append([k, new_src[k - 1].strip()[:70]])
        transfer[r["id"]]["remeasured_at_current_tip"] = {
            "looked_for_this_sink_text": sink_text,
            "found_at_lines": at_new,
            "attribution_within_the_same_window": nearby_attr,
            "bucket_carries_over": bool(at_new) and bool(nearby_attr) == bool(
                r["predicates"]["attributed_at_the_render_site"]),
            "bucket_at_current_tip": r["bucket"] if at_new and (bool(nearby_attr) == bool(
                r["predicates"]["attributed_at_the_render_site"])) else "CANNOT_SAY",
        }
ranks = {v["verdict"] for v in transfer.values()}
payload = {
    "schema": "CNX_ORD0320_TRIAGE_V1",
    "order": ORDER, "lane": "D e345b9d6",
    "at_local": datetime.now().astimezone().strftime("%Y-%m-%dT%H:%M:%S%z"),
    "kind": "READ_ONLY_TRIAGE",
    "generation": {
        "tip_read_by_this_run": tip_now,
        "tip_the_sweep_measured": TIP,
        "same": tip_now == TIP,
        "frontend_subtree": git("rev-parse", f"{TIP}:frontend").strip(),
        "ruler_r2_blob": RULER_R2,
        "sweep_artifact": {"path": "commander/control:evidence/q64-sweep-S1/sweep_r1.json",
                           "blob": blob((SC / "sweep_r1.json").read_bytes())},
        "commander_verify_artifact": {"path": "commander/control:evidence/cmdr-s1-verify-0306/verify_r1.json",
                                      "blob": blob((SC / "verify_r1.json").read_bytes())},
    },
    "method": "三个谓词（upstream_read / reaches_dom / attributed）全部在本脚本对 `git show <tip>:<path>` 的字节上算，"
              "引用的每一行都重新读回并与清扫件引文逐字比对；桶计数由 rows 派生，不写字面量",
    "input_cells": {"selected_upstream_prose": len(rows),
                    "sweep_classification_tally": SWEEP["classification_tally"],
                    "sweep_hits_total": SWEEP["hits_total"],
                    "consistency_check": SWEEP["classification_tally"]["upstream_prose"] == len(rows),
                    "files_touched_by_these_cells": len(counts_by_file)},
    "generation_transfer": {"current_tip_read_after_the_rows": tip_now,
                            "sweep_tip": TIP, "same": tip_now == TIP,
                            "per_cell": transfer,
                            "verdicts": sorted({v["verdict"] for v in transfer.values()})},
    "population_upstream_throwers": UPSTREAM_THROWERS,
    # where my measurement does not support the sweep's label, named as rows rather than argued in prose
    "disagreement_with_the_sweep": [
        {"id": r["id"], "cite": f"{r['file']}:{r['ruler_anchor_line']}", "bucket": r["bucket"],
         "why_this_lane_cannot_confirm_upstream_prose": r["missing_definition"]}
        for r in rows if r["bucket"] == "NEEDS_RULING"],
    "buckets": buckets,
    "per_file_cell_count": counts_by_file,
    "rules_of_mapping": {
        "checked_in_this_order": ["attributed -> COMPLIANT_WITH_ATTRIBUTION",
                                  "no upstream read -> NEEDS_RULING",
                                  "content channel -> NEEDS_RULING",
                                  "inherited read at a root boundary -> NEEDS_RULING",
                                  "no setter chain to the rendered name -> NEEDS_RULING",
                                  "reaches DOM with a proven chain -> FIX_IN_PRODUCT"],
        "NEEDS_RULING": "谓词不足以判定（内容通道未定义 / 本文件内找不到渲染点 / 找不到上游读取行），"
                        "并写出缺哪个定义，不偷转为前两桶",
    },
    "rows": rows,
    "discipline": {"product_bytes_written": 0, "refs_pushed": 0, "vite_build_run": 0,
                   "node_modules_touched": 0, "phone_chain_touched": 0, "credentials_printed": 0,
                   "how": "全部只读：git show / git grep / git ls-remote / git rev-parse；"
                          "清扫件与复核件是从 commander/control 用 contents API 取回后逐字节重算 blob 的"},
    "claimed_result": None, "derived_result": None,
    "self_reference_note": "this file cannot carry its own blob; the published name is read back by a "
                           "separate single GET whose number goes in the ledger block",
}
(OUT).write_bytes((json.dumps(payload, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))
print(json.dumps({"cells": len(rows), "buckets": buckets,
                  "files": len(counts_by_file),
                  "basis_mismatches": sum(len(r["basis_lines_that_do_not_match_the_tip"]) for r in rows),
                  "blob_mismatches": [r["file"] for r in rows if not r["blob_equality"]],
                  "tip_same": payload["generation"]["same"]}, ensure_ascii=False, indent=1))
for r in rows:
    print(f"  {r['id']} {r['file'].replace('frontend/src/', '')}:{r['ruler_anchor_line']:5d} "
          f"{r['bucket']:30s} attr={r['predicates']['attributed_at_the_render_site']} "
          f"sink={len(r['predicates']['render_lines'])} prod={len(r['predicates']['upstream_producer_lines'])} "
          f"mount={'y' if r['mount_chain_to_root'] != 'NOT_MOUNTED_WITHIN_4_HOPS' else 'n'}")
print(f"wrote {OUT} {OUT.stat().st_size:,} B blob={blob(OUT.read_bytes())}")
