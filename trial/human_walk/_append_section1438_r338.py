"""Append section 14.38: three faults in my own rulers, what the corrected readings are, and what they void.

Every figure is read out of the receipts while this runs - the old numbers come out of the
`.before_catch_body_fix` copies and the new ones out of the live receipts - so this section cannot quote a
reading its own artifacts do not carry. It also names the two ledger blocks whose published counts are now
wrong, by counting their headings in the ledger rather than asserting it from memory.
"""

import io
import os
import re
import sys

ROOT = r"D:/moodle/_cmdr_rescue_v3_1022"
REPORT = os.path.join(ROOT, "trial", "results", "20261026_GO_FROM_BLANK_REPORT.md")
LEDGER = os.path.join(ROOT, "..", "CITYNEXUS_AGENT_CONTROL.md")
GOZERO = os.path.join(ROOT, "trial", "results", "20261026_gozero")

BW325 = "bw325-what-the-screen-says.txt"
BW326 = "bw326-what-the-panels-do-with-a-refusal.txt"
BW327 = "bw327-what-the-panels-say-instead.txt"
BW328 = "bw328-is-that-sentence-on-screen.txt"
BW337 = "bw337-which-chinese-sentence-sits-on-which-refusal.txt"
KEPT = ".before_catch_body_fix"

VOID_HEADINGS = ["交「屏上改写成什么话」的逐枚靶面：十九处自造句子的 catch",
                 "交「面板自造的话句句被标记读到」的逐枚闭链：十九处 catch 各自的 state 与渲染行"]

CITES = {
    "revision": (BW325, "CATCH_BODY_REVISION"),
    "tally_325": (BW325, "TALLY shows_server_text="),
    "tally_326": (BW326, "TALLY panels="),
    "tally_327": (BW327, "TALLY catch="),
    "tally_328": (BW328, "TALLY rows="),
    "tally_337": (BW337, "TALLY refusals="),
    "reverse_337": (BW337, "REVERSE_CHECK"),
    "ruler_325": ("trial/human_walk/_cmdr_screen_text_r325.py", "def catch_body"),
    "control_327": (BW327, "LITERAL_SCANNER_CONTROL"),
    "ruler_327": ("trial/human_walk/_cmdr_sentence_shape_r327.py", "def strip_comments"),
    "ruler_328": ("trial/human_walk/_cmdr_render_check_r328.py", "left these unread"),
    "ruler_337": ("trial/human_walk/_cmdr_pair_refusal_to_sentence_r337.py", "def scan_catches"),
    "prev_section": ("trial/results/20261026_GO_FROM_BLANK_REPORT.md", "14.37 补（10-29 夜）"),
}


def read(rel):
    base = GOZERO if rel.startswith("bw") else ROOT
    path = os.path.join(base, rel.replace("/", os.sep))
    if not os.path.exists(path):
        raise SystemExit("ABORT cited artifact missing: %s" % path)
    return io.open(path, encoding="utf-8", errors="replace").read()


def line_of(rel, needle):
    hits = [index + 1 for index, cell in enumerate(read(rel).split("\n")) if needle in cell]
    if len(hits) != 1:
        raise SystemExit("ABORT anchor %r found %d times in %s" % (needle[:40], len(hits), rel))
    return hits[0]


def row_at(rel, line):
    return read(rel).split("\n")[line - 1]


def numbers(rel, needle, keys):
    """Pull a fixed set of `key=value` readings out of the one line that carries them."""
    line = next((cell for cell in read(rel).split("\n") if cell.startswith(needle)), "")
    if not line:
        raise SystemExit("ABORT no %r line in %s" % (needle, rel))
    out = {}
    for key in keys:
        match = re.search(r"%s=(\d+)" % key, line)
        if not match:
            raise SystemExit("ABORT %s has no %s= in %s" % (needle, key, rel))
        out[key] = int(match.group(1))
    return out


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    at = {name: line_of(rel, needle) for name, (rel, needle) in CITES.items()}
    print("LIVE ANCHORS %s" % at)

    shape = row_at(BW325, at["revision"])
    body = dict((key, int(value)) for key, value in
                re.findall(r"(files|bodies|shortest|median|longest)=(\d+)", shape))
    for key in ("files", "bodies", "shortest", "median", "longest"):
        if key not in body:
            raise SystemExit("ABORT the body-shape reading is missing %s" % key)

    control_line = row_at(BW327, at["control_327"])
    scanner = re.search(r"says_zh=(\d+) instead of (\d+)", control_line)
    fake_site = re.search(r"is/are (\S+?:\d+)", control_line)
    fake_text = re.search(r"handler is (.+) - prose", control_line)
    if not (scanner and fake_site and fake_text):
        raise SystemExit("ABORT the literal-scanner control in bw327 does not carry its three readings")
    old_scanner_zh, now_scanner_zh = int(scanner.group(1)), int(scanner.group(2))
    if old_scanner_zh <= now_scanner_zh:
        raise SystemExit("ABORT the comment fix did not actually change the count it claims to change")
    print("SCANNER CONTROL old=%d now=%d site=%s fake=%r"
          % (old_scanner_zh, now_scanner_zh, fake_site.group(1), fake_text.group(1)))

    old_326 = numbers(BW326 + KEPT, "TALLY panels=", ("catch", "reads_the_refusal", "hides_the_refusal"))
    new_326 = numbers(BW326, "TALLY panels=", ("catch", "reads_the_refusal", "hides_the_refusal"))
    old_327 = numbers(BW327 + KEPT, "TALLY catch=", ("says_zh", "into_state", "nowhere", "retry_shaped"))
    new_327 = numbers(BW327, "TALLY catch=", ("says_zh", "into_state", "nowhere", "retry_shaped"))
    old_328 = numbers(BW328 + KEPT, "TALLY rows=", ("rows", "rendered"))
    new_328 = numbers(BW328, "TALLY rows=", ("rows", "rendered"))
    new_337 = numbers(BW337, "TALLY refusals=", ("refusals", "unpaired"))
    line_337 = next(cell for cell in read(BW337).split("\n") if cell.startswith("TALLY refusals="))
    for pattern, key in ((r"paired to a listed self-written sentence=(\d+)", "listed"),
                         (r"paired only to an unlisted catch sentence=(\d+)", "unlisted")):
        match = re.search(pattern, line_337)
        if not match:
            raise SystemExit("ABORT bw337's TALLY does not state its %s count in words" % key)
        new_337[key] = int(match.group(1))
    if new_337["listed"] + new_337["unlisted"] + new_337["unpaired"] != new_337["refusals"]:
        raise SystemExit("ABORT bw337's three refusal buckets do not add up to its own refusals count")
    reached, never = [int(v) for v in re.search(r"reached by this join: (\d+).*refusals: (\d+)",
                                                 row_at(BW337, at["reverse_337"])).groups()]
    print("LIVE NUMBERS body=%s old326=%s new326=%s old327=%s new327=%s old328=%s new328=%s "
          "337=%s reached=%d never=%d" % (body, old_326, new_326, old_327, new_327, old_328, new_328,
                                          new_337, reached, never))
    if not (old_327["says_zh"] == old_328["rows"] == 19):
        raise SystemExit("ABORT the kept copies do not agree on the number this section is correcting")
    if new_327["says_zh"] != new_328["rows"]:
        raise SystemExit("ABORT bw327 publishes %d and bw328 %d, so the corrected set is not one set"
                         % (new_327["says_zh"], new_328["rows"]))
    if new_326["reads_the_refusal"] <= old_326["reads_the_refusal"]:
        raise SystemExit("ABORT the corrected read count did not move, so the body fix did not take")
    if reached + never != new_327["says_zh"]:
        raise SystemExit("ABORT bw337's reverse check does not cover the corrected catch set")

    ledger = io.open(LEDGER, encoding="utf-8", errors="replace").read()
    voided = [(heading, ledger.count(heading)) for heading in VOID_HEADINGS]
    for heading, hits in voided:
        if hits != 1:
            raise SystemExit("ABORT the block I am voiding reads %d times in the ledger, not once: %s"
                             % (hits, heading[:24]))

    text = read("trial/results/20261026_GO_FROM_BLANK_REPORT.md")
    if "14.38 补" in text:
        return 4
    section = "\n".join([
        "",
        "### 14.38 补（10-29 深夜）：三把我自己的尺都量错过，先把错认下来，再给改口后的数",
        "",
        "- 错一（catch 的体被切短）：尺 trial/human_walk/_cmdr_screen_text_r325.py:%d 原先按整行数花括号。"
        "本仓的写法是 `} catch {`——行首那个 `}` 是收 try 的、行末 `{` 才是开的，整行净值就成了 0，于是 body "
        "只收到下一条语句就返回。改成「从 catch 的花括号之后起算，深度回一且该行以 `}` 开头即收」；同一把尺现读 "
        "%d 个文件、%d 枚 catch body，体长最短 %d 行、中位 %d 行、最长 %d 行（回执 "
        "trial/results/20261026_gozero/%s:%d）。"
        % (at["ruler_325"], body["files"], body["bodies"], body["shortest"], body["median"],
           body["longest"], BW325, at["revision"]),
        "- 错二（把注释读成句子）：字符串扫描器原先的字符类吃换行，文档块里一左一右两个引号就被当成一枚字面量。"
        "现读对照就在回执 trial/results/20261026_gozero/%s:%d——旧口径 says_zh=%d、修后 %d，多出的那枚是 %s，"
        "旧扫描器从该 handler 头顶注释里提出来的句子原文是 %s（连同它自带的书名号）。修法：先剥块注释，再剥「该行第一个引号之前」的"
        "行注释（URL 里的 // 因引号在前而不会被剥），尺见 trial/human_walk/_cmdr_sentence_shape_r327.py:%d。"
        % (BW327, at["control_327"], old_scanner_zh, now_scanner_zh, fake_site.group(1),
           fake_text.group(1), at["ruler_327"]),
        "- 错三（丢行不报）：尺 trial/human_walk/_cmdr_render_check_r328.py:%d 原先把解析不动的行直接跳过——"
        "上面那枚注释假串不是任何 setter 的实参，于是旧口径列 %d 枚句子时它只收 %d 枚，TALLY 还照报 no_setter=0。"
        "现在它要求解析出的行数等于 bw327 公布的 says_zh，并把读不动的行原文打出来才继续。"
        % (at["ruler_328"], old_scanner_zh, now_scanner_zh),
        "- 改口后的数（新回执现读，旧数取自同目录 .before_catch_body_fix 留底）：面板读拒绝句从 %d 处变 %d 处、"
        "藏起来从 %d 处变 %d 处（trial/results/20261026_gozero/%s:%d）；面板自造中文句从 %d 处变 %d 处、交给 "
        "state 从 %d 处变 %d 处、两头都不是从 %d 处变 %d 处、带重试句形从 %d 处变 %d 处"
        "（trial/results/20261026_gozero/%s:%d）；被标记读到从 %d 处变 %d 处、存了没人读仍 %d 处"
        "（trial/results/20261026_gozero/%s:%d）。"
        % (old_326["reads_the_refusal"], new_326["reads_the_refusal"], old_326["hides_the_refusal"],
           new_326["hides_the_refusal"], BW326, at["tally_326"], old_327["says_zh"], new_327["says_zh"],
           old_327["into_state"], new_327["into_state"], old_327["nowhere"], new_327["nowhere"],
           old_327["retry_shaped"], new_327["retry_shaped"], BW327, at["tally_327"],
           old_328["rows"], new_328["rows"], new_328["rendered"], BW328, at["tally_328"]),
        "- 作废两句已入账的数：账本里那两格标题各命中 %d 次（现读 %s），标题与正文里的「十九处」都按上条改口——"
        "「%s」那一格（#370）与「%s」那一格（#372）。旧帖不改，勘误另交一块（#373）。§14.36、§14.37 正文里的"
        "%d 同此。" % (voided[0][1], "CITYNEXUS_AGENT_CONTROL.md", voided[0][0], voided[1][0],
                        old_327["says_zh"]),
        "- 顺带把链上缺的那一格补了：新尺 trial/human_walk/_cmdr_pair_refusal_to_sentence_r337.py:%d 从每条"
        "旅客面英文拒绝的前端调用处走到它背后的 catch，再认那句 catch 自造的话。现读：%d 条拒绝里 %d 条配得上"
        "列表内的自造句、%d 条只配到列表外某枚 catch 的句子、%d 条配不上（回执 trial/results/20261026_gozero/%s:%d）；"
        "反过来，%d 枚自造句 catch 里被这 %d 条拒绝走到的是 %d 枚、没走到的 %d 枚（回执 :%d）。所以甲刀与乙刀"
        "覆盖的面几乎不重叠——改了后端那 %d 句英文，屏上那 %d 句中文基本不动。"
        % (at["ruler_337"], new_337["refusals"], new_337["listed"], new_337["unlisted"],
           new_337["unpaired"], BW337, at["tally_337"],
           new_327["says_zh"], new_337["refusals"], reached, never, at["reverse_337"],
           new_337["refusals"], new_327["says_zh"]),
        "- 还欠一把尺（不装已补）：判「读没读拒绝」的正则只认 detail/message/response/data/statusText 这几个"
        "属性名，而现读到的真实写法是 `cause.body as { detail?... }`、`refusalReasonCode(cause)`、"
        "`cause.facts`。读了字段不等于把那句显在屏上——DestinationPreparationPanel 与 RealCityDiscoveryPanel "
        "就是把 detail 当码比。这条我另开一尺分三档（读字段／把字段交出去显／只拿来比），不在本节里含糊过去。",
        "- 这三处都是量具的错，不是产品的错：本节自始至终 0 改产品字节；被改的是我自己的尺与读数。留底份"
        "（.before_catch_body_fix）与新份同目录并存，谁都能自己比。",
        "- 上一节正文在 trial/results/20261026_GO_FROM_BLANK_REPORT.md:%d。" % at["prev_section"],
        "",
    ])
    # Append at the byte level. This report is CRLF-dominant with a minority of bare-LF lines, and reading
    # it through a text-mode handle would rewrite every one of those endings.
    io.open(REPORT, "rb").read()  # keep the path warm and prove it is readable
    with io.open(REPORT, "rb") as handle:
        blob = handle.read()
    crlf = blob.count(b"\r\n")
    bare = blob.count(b"\n") - crlf
    if blob[-2:] != b"\r\n":
        blob = blob + (b"\r\n" if blob.endswith(b"\r") or blob.endswith(b"\n") else b"\r\n\r\n")
    lines = section.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    payload = (b"\r\n".join(cell.encode("utf-8") for cell in lines) + b"\r\n")
    io.open(REPORT, "wb").write(blob + payload)
    back = io.open(REPORT, "rb").read()
    hits = back.count("14.38 补".encode("utf-8"))
    crlf_after = back.count(b"\r\n")
    bare_after = back.count(b"\n") - crlf_after
    print("APPENDED bytes_added=%d section_lines=%d heading_hits=%d crlf_before=%d crlf_now=%d "
          "bare_lf_before=%d bare_lf_now=%d" % (len(payload), len(lines), hits, crlf, crlf_after,
                                                bare, bare_after))
    if hits != 1:
        raise SystemExit("ABORT the heading is not unique")
    if crlf_after != crlf + len(lines) or bare_after != bare:
        raise SystemExit("ABORT the line endings moved: this append must add CRLF only, and it added "
                         "%d CRLF and %d bare LF" % (crlf_after - crlf, bare_after - bare))
    return 0


if __name__ == "__main__":
    sys.exit(main())
