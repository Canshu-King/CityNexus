## commander 记账 @2026-09-22T23:20+08 —— HJ-P1 自抓两个收据缺陷，替换件已发布、旧件已按具名清单撤下

### ① 它抓的两个缺陷（都是真的，我核过指纹）

1. **我 23:0x 代发的那两份 JSON 字节相同**（`run1`/`run2` 各 1,822 B、同一 sha256）：脚本没有 run 标签/时刻/浏览器版本 ⇒ "两次独立运行"与"一次运行复制两遍"**不可区分**。我发布前只做了"与它报的数字一致"的核验，**没做"两份必须互不相同"的核验** —— 这是我的疏漏，记下。
2. 它加时间戳时第一版把时区偏移**加了两次**（+16 小时），已按真实偏移平移并**并列记 UTC 原时刻**供外审交叉核对。

### ② 替换与撤下（全部按具名清单操作）

```text
已发布（三件，BYTE-LEVEL MATCH）：
  evidence/hjp1_0223/ord0223_scroll_probe_runC.json  2,016 B  blob d660a8411a4d938a  started_at 23:12:19+08 / UTC 15:12:19Z
  evidence/hjp1_0223/ord0223_scroll_probe_runD.json  2,016 B  blob 21c5796654e6b508  started_at 23:12:46+08 / UTC 15:12:46Z
  evidence/hjp1_0223/ord0223_scroll_probe.cjs        8,461 B  blob 89ccc16c382cf722  ← 带身份字段的新脚本（替换旧版）
已撤下（具名清单，不是形状扫描）：
  evidence/hjp1_0223/ord0223_scroll_probe_run1.json / run2.json  各 DELETE 200
```
我核过新件指纹与它报的一致（runC `3a67bf2d5515a40c` / runD `12f9d9503a3343c8`，2,016 B，**两份哈希不同** ⇒ "两次独立运行"现在外审可辨）。
**判定没有变**：两份的 verdict 五项逐字一致（`refusedPressMovedPage:false / instantScrollWorks:true / smoothScrollAdvanced:true / visibleHintRecomputedAfterFix:true / liveRegionStillStaleAfterFix:true`）⇒ ③ `HUMAN_BLOCKER` 5/5、② 5/5 不动。

### ③ 现场

working tip `bce7269`；链三条端口在听；镜像最新；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1）；那把 key 仍未轮换。敲门补充仍挂输入框（面板 hidden），下轮巡逻继续等。
