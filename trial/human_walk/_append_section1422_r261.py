"""Append section 14.22: every neighbour swap on the stay-materialised plan answers 503."""

import io
import sys

REPORT = r"D:\moodle\_cmdr_rescue_v3_1022\trial\results\20261026_GO_FROM_BLANK_REPORT.md"

BLOCK = """
14.22 补（10-29 午）：住下带出的那一版方案，拖动任何相邻两格都拿到 503，句子里还带着 KeyError

接着 §14.21 待点的那一格走：探针 trial/human_walk/_cmdr_accept_walk_r260.py:151 把当前方案的全部相邻
换序逐条递给产品自己的接受路由（trial/human_walk/_cmdr_accept_walk_r260.py:154 一道自检断言
「换序只能重排、不许增删」，防止仪表自己造出坏输入）。

- 读数：玖 条活动、捌 种相邻换序，捌 次全部 http_status=503（回执
  trial/results/20261026_gozero/bw260-accept-walk-against-the-gate.txt:19 与
  trial/results/20261026_gozero/bw260-accept-walk-against-the-gate.txt:33），
  句子同一形状 —— 「preview mobility evidence unavailable: mobility fact unavailable for
  某点|另一点: KeyError」。
- 链条（现读坐标）：接受路由要为新顺序补算移动事实（backend/app/main.py:18474，且
  backend/app/main.py:18480 明写 require_explicit_facts=True）；提供方臂取不到这条边时
  backend/app/integrations/mobility/snapshot_capture.py:166 兜住异常、
  backend/app/integrations/mobility/snapshot_capture.py:169 抛出快照捕获错误，而
  backend/app/integrations/mobility/snapshot_capture.py:171 把**内部异常类名**拼进句子；
  backend/app/main.py:18482 再把这一整类错误统一包成 503。
- 为什么会全断：这一版的移动证据是住下材料化时按**原顺序**造的，矩阵里没有拖动产生的新边；
  该方案所用的 玖 处地点行也全是 backend/app/operations/v9.py:340 那把 provider
  （回执 trial/results/20261026_gozero/bw260-accept-walk-against-the-gate.txt:7）。
  所以「一拖就 503」在这支路由上是必然，不是偶发。
- 这格还没答的问题（不许顺嘴判）：共享权威门在这捌 次换序里被问 0 次
  （回执 trial/results/20261026_gozero/bw260-accept-walk-against-the-gate.txt:3 记 壹 次，
  即探针自己拿真数据直接问门的那一次 trial/human_walk/_cmdr_accept_walk_r260.py:213，
  同回执 :5 见 seen_by_trace=True）——
  因为这支行进不到 backend/app/main.py:19038 就断了。所以 §14.21 待点的「接受这一版绕不绕开门」
  仍然是未判，需要一个矩阵充分的库（带完整 OD 事实）才能走到那一行。
- 边界（不外推）：这一支是「住下方案 → 直接出发 → 拖动换序」，不是主人真机走的那条
  Revolution 链（那条有自己的屏证 walk-88）。本班 0 改产品字节。
- 待裁三件（建议并进「别把内部码与 id 端给旅客」那张单）：一，状态码语义 ——
  「缺这条路线的证据」报 503（服务不可用）而不是 409/422，旅客会以为服务挂了；
  二，内部异常类名 KeyError 出现在给旅客的句子里；
  三，拖动之前该不该先补算或明示「这一拖需要新的路线证据」，而不是按下去才 503。
"""


def main():
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    text = io.open(REPORT, encoding="utf-8", newline="").read()
    if "14.22 补" in text:
        print("ABORT the section is already appended")
        return 4
    block = BLOCK.strip("\n").replace("\n", "\r\n") + "\r\n\r\n"
    io.open(REPORT, "w", encoding="utf-8", newline="").write(text + block)
    read_back = io.open(REPORT, encoding="utf-8", newline="").read()
    if not read_back.startswith(text):
        print("ABORT bytes before the insertion point changed")
        return 5
    print("APPENDED bytes_added=%d hits=%d"
          % (len(block.encode("utf-8")), read_back.count("14.22 补")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
