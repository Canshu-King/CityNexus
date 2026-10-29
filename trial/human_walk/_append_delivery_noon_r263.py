"""Append the 10-29 noon note to the delivery document (LF-only, byte-preserving)."""

import io
import sys

DELIVERY = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261027_GO_FROM_BLANK_DELIVERY.md"

BLOCK = """
## 午班补记（10-29 11:5x）：今天新量到的四件事，和你现在还能按的三件事

一、那三十九枚「这版方案不算权威」的红，落到具体哪一格了。
全部出自同一行判定（backend/app/services.py:799），命中的只有一件事：营业时间那个词。
夹具给地点写的词是 NORMALIZED，判据认的是另外四个词（backend/app/services.py:599）；
价钱那一格反倒是全齐的。正文 trial/results/20261026_GO_FROM_BLANK_REPORT.md:3464。
你能点的一刀：#354 —— 夹具补一行"这批地点是演示封套"的声明（同树已有两处先例），一刀罩住 39 枚红。

二、一按「选这家酒店」就直接出发，而那扇权威门一次都没被问。
住下选用那一步自己把方案和行程推成出发态（backend/app/operations/v9.py:761 与 backend/app/operations/v9.py:779），
所以之后再按"选用方案"会被状态挡回、按"出发"是幂等早退，门轮不到。
同一枚方案直接递给门，它答"还有事实没落地"。分母读数 trial/results/20261026_gozero/bw250-stay-plan-against-select-gate.txt:3。
正文 trial/results/20261026_GO_FROM_BLANK_REPORT.md:3507。这一格要裁：要么住下也走同一扇门，要么承认那批地点是排程结构。

三、"谁把方案推成出发态"和"谁问过那扇门"排成了一张表（16 行：3 行看得见门、13 行看不见）。
尺用两枚已知答案的锚自证会咬。正文 trial/results/20261026_GO_FROM_BLANK_REPORT.md:3543，
表 trial/results/20261026_gozero/bw253-promotion-gate-pairing.txt:2。
最该点名的一行是你真机上那个键的实现（backend/app/main.py:19038）——它还没被走查过，别当成缺陷。

四、"按天调整行程"拖动一下，这条路上八种拖法全部回 503，句子里还把内部异常名 KeyError 端给旅客。
成因是那一版的路线证据只覆盖了原顺序，拖一下就要一条证据里没有的边（backend/app/main.py:18482 把它整类包成 503，
backend/app/integrations/mobility/snapshot_capture.py:171 把异常名拼进句子）。
读数 trial/results/20261026_gozero/bw260-accept-walk-against-the-gate.txt:19，正文
trial/results/20261026_GO_FROM_BLANK_REPORT.md:3567。要裁的是三件：状态码该不该是 503、内部名字该不该上屏、拖之前要不要先补算。
边界照直说：这条是"住下→出发"这一支，不是你平板上那条 Revolution 链。

你现在还能按的三件事：
1) 平板验收（USER_VERIFIED 仍空）：走课堂栈 :14462，那一栈自 10:11 定档后产品代码一枚字节没动，仍是你要踩的那一代。
2) 想让课堂里有真路线：先让那一栈真捕一次（#350，要有键且你点头，本班不代跑）。
3) 最便宜的一刀：点 #354，39 枚红一次性有个交代；#355/#356/#357 三格需要口径，不点就先挂着，本班不代裁。

没变好的，照直说：这四大格全部只交付了"读数 + 待裁口径"，产品字节 0 改动；
课堂随机城市池仍 0/3；账本往 GitHub 的镜像腿仍未推（本班这一拍 applier 的退出码 1 就来自它，本地插入是成功的）。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(DELIVERY, encoding="utf-8", newline="").read()
    if "\r\n" in text:
        print("ABORT this file stopped being LF-only")
        return 3
    if "午班补记（10-29 11:5x）" in text:
        print("ABORT already appended")
        return 4
    block = BLOCK.strip("\n") + "\n"
    if "\r\n" in block:
        print("ABORT refusing to introduce CRLF")
        return 5
    io.open(DELIVERY, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(DELIVERY, encoding="utf-8", newline="").read()
    if not read_back.startswith(text) or "\r\n" in read_back:
        print("ABORT bytes before the insertion point changed or endings flipped")
        return 6
    print("APPENDED bytes_added=%d hits=%d lines=%d"
          % (len(block.encode("utf-8")), read_back.count("午班补记（10-29 11:5x）"),
             len(read_back.split("\n"))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
