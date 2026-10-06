r"""追加 07:43 的补读数（对第 27 拍那条"选择性停住"的**减损**：root 里有一大半是作者自己重切的）。"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "PATROL_LOG.md")

ENTRY = """
### 07:43 补（对第 27 拍"对 D 选择性停住"那条形状的减损）

- 现数 `_qoder_ledger_inbox` root：`.superseded_by_*` / `.my_superseded*` 共 **D 6 枚**，
  别人 b-c01d72a3 1、cmdr 1、f-8ccd71d8 3、S1 1、S4 1；仍待发的 **d-e345b9d6 3 枚 + S2-hermes-port 1 枚**。
- 07:38 那枚 `d-e345b9d6_0738.md` 在两分钟内被 D 自己改名成 `…superseded_by_0748`（07:38:19），**没经过号令者**。
- ⇒ 所以"root 只剩 D"至少有一部分是**作者自己按代次重切块**（尖每进一代她就重投一次，她 07:07 的块里就写明
  「上一枚块写完后尖又进了一代」），而不是单写者不动。**这不推翻第 27 拍的读数**（那三枚确实压着 98/70/38 分钟），
  但它推翻了我那句里可能被人读成"号令者卡住 D"的含义。
- 处置：**不再为这件事发帖**（我 07:40 的勘误帖已经说"不再追第二遍"；而且这条新读数指向的是 D 自己的成本，不是谁的错）。
  只记在这里，下一班若看到 root 又涨，先分清"待发"与"作者自取代"两类，别把后者算进任何人的 SLA。
"""


def main():
    cur = io.open(LOG, encoding="utf-8", newline="").read()
    assert cur.endswith("\n")
    before = len(cur.encode("utf-8"))
    io.open(LOG, "a", encoding="utf-8", newline="").write(ENTRY.lstrip("\n"))
    print("APPENDED +%d B (=%d -> %d)" % (os.stat(LOG).st_size - before, before, os.stat(LOG).st_size))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
