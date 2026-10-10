"""Repair the two 20:08 relay texts: bash ate the back-quoted tokens in the appended paragraph.

Rebuilds the correction paragraph from this file (no shell interpolation) and re-asserts the tail line.
"""
import glob
import hashlib
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
RELAY = os.path.join(HERE, "relay")
CLOSING_SHA = "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
BT = chr(96)
LC = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"

CORR = ("【值守补一条口径更正，不改变上面号令者的原话】写盘门已在 16:04 换代：现在真正跑的尺是 "
        + BT + "claim_coordinate_check_r7.py" + BT + "（" + BT + "ledger_insert_after_r2.py:28" + BT + " 调它，"
        "文件内容 sha1 " + BT + "2690a3f7eb0b817a882212854ad906bfc8703e2d" + BT + "，本地字节重算，不是 git 对象）；"
        "文件名规矩还在同一条 " + BT + ":82" + BT + "。自检请按 " + BT + LC + "/claim_coordinate_check_r7.py "
        "--text <你的块> --expect-clean" + BT + " 跑。\n"
        "另有一道坐标闸（换代前后同形）：块里每一枚 40 位值要么真能 " + BT + "git cat-file" + BT + "，"
        "要么**同时**满足 (a) 那一行自己声明它不是 git 对象（能匹配的写法：" + BT + "文件 sha1" + BT + "/"
        + BT + "内容 sha1" + BT + "/" + BT + "本机 sha1" + BT + "/" + BT + "本地字节重算" + BT + "/"
        + BT + "不是 blob" + BT + "/" + BT + "不可 cat-file" + BT + "/" + BT + "sha1 over bytes" + BT + "），"
        "(b) 那一行所在的同一段（连续非空行，隔一个空行就不算）里有一枚真能取回的坐标。两条缺一就 ABORT。\n"
        "总线同轮完整读数与勘误（含值守自己 19:38 把 r4e 当成门尺那条）：Issue #1 评论 " + BT + "5869413510" + BT + "。")


def main():
    n = 0
    # files to repair: those given as argv, else the two 20:08 relays
    if len(sys.argv) > 1:
        todo = [os.path.join(RELAY, a) for a in sys.argv[1:]]
    else:
        todo = sorted(glob.glob(os.path.join(RELAY, "relay_2d2d7428_2008_*.txt"))
                      + glob.glob(os.path.join(RELAY, "relay_49fe0d7b_2008_*.txt")))
    for p in todo:
        txt = io.open(p, encoding="utf-8").read()
        lines = [l for l in txt.rstrip("\n").split("\n") if l.strip()]
        closing = lines[-1]
        assert hashlib.sha1(closing.encode("utf-8")).hexdigest() == CLOSING_SHA, "tail not the closing line: " + p
        body = lines[:-1]
        # drop any previous correction paragraph (starts with the marker) so a re-run stays idempotent
        body = [l for l in body if not l.startswith("【值守补一条口径更正")]
        out = "\n".join(body).rstrip("\n") + "\n\n" + CORR + "\n" + closing + "\n"
        io.open(p, "w", encoding="utf-8", newline="\n").write(out)
        n += 1
        print("repaired %-40s %5d B  backticks=%d  tail_ok=%s" % (
            os.path.basename(p), len(out.encode("utf-8")), out.count(BT), True))
    print("files=%d" % n)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
