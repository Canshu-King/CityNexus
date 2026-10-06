## 补记 @2026-09-25 08:1x+08 —— Q38 尺出 **r2**（r1 对车道真发的形状失明）；D 的 ORD-0292 我用尺过了：**硬 0 / 软 6**，不因此挂他

```text
evidence/q38-cell-derivation-gate/receipt_cell_derivation_check_r2.py  18,867 B  91ae8b1ec55f5c19122af11bf775df14580955e4
evidence/q38-cell-derivation-gate/selftest_20260925_0812.txt            1,354 B  f0b35ab4f450c8b11509ae3c705d5bbfa795f833  （10 臂全过）
evidence/q38-cell-derivation-gate/gate_on_ord0292_arms.json             5,244 B  104ba0abd2a83833c77e3ff187d19f023cc6815e
```
**r1 的洞是真工件撞出来的**：r1 只认 `cells` 容器 / 兄弟格 / 判决映射三种形状，而 D 把 7 格放在一个叫 `arms` 的**列表**里 ⇒ r1 读成 `NOT_ASSESSABLE`。这不是 D 的问题，**是我的尺失明**。r2 收集任意键名的"每格列表"，并加了自检臂 S10 把这一形状钉住（谁再改坏，自测先红）。
**r1 不回写**：它的 blob `35caa42c0697faf0a8eeb0929a3e11cb53c9709a` 已经进了 08:0x 块和 5824326806 那张贴文 ⇒ 路径冻结，只另发 r2。

**对 D 的收据实测**（副本 sha1 `cb9270671adc323ff2816d406739e04518b9d05f` 与线上相等）：**7 格 / 硬 0（七句 why 各不相同）/ 软 6（句子里没有任何可机器核对的 token）**。
⇒ 我不挂这一单：按 B-1 车道写的本来就是 `claimed_result`，本代击杀的 `derived_result` 归红队（她手上还有 ORD-0295）。**但从此对所有车道生效的新要求**：下一版每格 `why` 自带具名值（锚点数 / sha 前缀 / nodeid 任一），软档才能清零；我落地时会同时看硬档与软档。
**0278 / 0253 继续拦停**（等 derived），谁的 ref 都不动。

**队列**：等 ORD-0294（HJ-P1）→ 落 0274（父链已在尖上，ff-only 可行）→ 换代到手机；ORD-0287 已 KILLED 待换代之后由 F re-parent；ORD-0280 的候选 `48827a9d`（父 = 尖）排在换代后验（要"服务端字段＋屏幕渲染文字"两侧同判，需 e2e 一轮，来不及就明说 PARTIAL）。
**权威线未动** `45b0a5e2…`；用户库 0 读写；`demo/reset` 0；凭据 0 打印。
