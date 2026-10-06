"""Append the ruler-correction paragraph to relay texts (template with @BT@ tokens, then replace).

Avoids the two traps hit at 20:24: (1) bash eating backticks inside a `python -c` string, and (2) implicit
string concatenation + `+` producing a SyntaxError in the generated source. The template is one literal with
@BT@ markers replaced by chr(96) afterwards, and the result is asserted before it is written.
"""
import glob
import hashlib
import io
import os
import sys

BT = chr(96)
HERE = r"D:\moodle\_qoder_cmdr_ref_20260921\live_checks\patrol"
RELAY = os.path.join(HERE, "relay")
CLOSING_SHA = "de4b708bbc11aab7f4f1e5661188e8e9b65ff153"
LC = "D:/moodle/_qoder_cmdr_ref_20260921/live_checks"
MARK = "【值守补一条口径更正"

TEMPLATE = (MARK + "，不改变上面块的原话】写盘门已在 16:04 换代：现在真正跑的尺是 @BT@claim_coordinate_check_r7.py@BT@"
            "（@BT@ledger_insert_after_r2.py:28@BT@ 调它，文件内容 sha1 "
            "@BT@2690a3f7eb0b817a882212854ad906bfc8703e2d@BT@，本地字节重算，不是 git 对象）；"
            "文件名规矩还在同一条 @BT@:82@BT@。自检请按 @BT@@LC@/claim_coordinate_check_r7.py "
            "--text <你的块> --expect-clean@BT@ 跑。@NL@"
            "另有一道坐标闸（换代前后同形）：块里每一枚 40 位值要么真能 @BT@git cat-file@BT@，"
            "要么**同时**满足 (a) 那一行自己声明它不是 git 对象（能匹配的写法：@BT@文件 sha1@BT@/"
            "@BT@内容 sha1@BT@/@BT@本机 sha1@BT@/@BT@本地字节重算@BT@/@BT@不是 blob@BT@/@BT@不可 cat-file@BT@/"
            "@BT@sha1 over bytes@BT@），(b) 那一行所在的同一段（连续非空行，隔一个空行就不算）里有一枚真能取回的"
            "坐标。两条缺一就 ABORT。@NL@"
            "总线同轮完整读数与勘误：Issue #1 评论 @BT@5869413510@BT@。")


def corr():
    out = TEMPLATE.replace("@NL@", chr(10)).replace("@LC@", LC).replace("@BT@", BT)
    assert "%s" not in out and "@BT@" not in out and "@LC@" not in out, "template left a placeholder"
    assert out.count(BT) == TEMPLATE.count("@BT@"), "backtick count mismatch"
    return out


def main():
    args = sys.argv[1:]
    paths = [os.path.join(RELAY, a) for a in args] if args else sorted(
        glob.glob(os.path.join(RELAY, "relay_*_0206_*.txt")))
    c = corr()
    for p in paths:
        if not os.path.exists(p):
            print("MISSING", p)
            continue
        lines = [l for l in io.open(p, encoding="utf-8").read().rstrip("\n").split("\n") if l.strip()]
        closing = lines[-1]
        assert hashlib.sha1(closing.encode("utf-8")).hexdigest() == CLOSING_SHA, "tail not closing: " + p
        body = [l for l in lines[:-1] if "值守补一条口径更正" not in l[:24]]
        out = chr(10).join(body).rstrip(chr(10)) + chr(10) + chr(10) + c + chr(10) + closing + chr(10)
        io.open(p, "w", encoding="utf-8", newline=chr(10)).write(out)
        print("wrote %-44s %5d B backticks=%3d closing_at_tail=%s" % (
            os.path.basename(p), len(out.encode("utf-8")), out.count(BT),
            out.rstrip().split(chr(10))[-1] == closing))
    print("files=%d  corr=%d B" % (len(paths), len(c.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
