# 课堂演示运行手册（3–5 分钟）

**一句话**：平板上点「课堂演示：进入示例行程」→ 打开「行程守护」→ 按「接受这份调整」→ 行程当场变短。

## 开演前（电脑上，约 1 分钟）

1. 双击 `D:\moodle\_cmdr_v3_port_1022\start_classroom_demo.bat`（版本库副本：`trial/play_launcher/classroom_demo/start_classroom_demo.bat`，两份同源；脚本默认每次生成随机会话密钥，不写死）。
   它会：把演示库重置成有「北京 · 2日行程」的初始场景 → 起后端 `127.0.0.1:60391` → 起前端 `0.0.0.0:14492` → 预生成一张待接受的调整卡。窗口不要关。
2. 平板连与电脑**同一 WiFi**（电脑当前 WLAN：`10.15.5.23`）。
3. 平板浏览器打开 `http://10.15.5.23:14492/revolution`。

> 打不开时先看电脑浏览器同一地址；仍打不开就重跑第 1 步（会重置场景）。

## 台上（实测 18 秒，可慢慢讲）

4. 点底部「我的旅程」。
5. 点「课堂演示：进入示例行程」——进入「北京 · 2日行程」。
6. 指一下屏：第一站故宫博物院、之后天坛公园，路线「约 78 分钟」来自真实地图。
7. 点「行程守护」，卡片会自己滚到眼前：「找到一份可行的调整 / 移除故宫博物院；路上少 66 分钟。」
8. 点「接受这份调整」。页面自动刷新一次，第一站变成「天坛公园 · 12月3日 09:00」。
9. （可选 40 秒）往下滚到「课堂时空模拟」条，点「+1 小时」：模拟时间从 09:00 变 10:00；水印一直写着「不是实际定位或真实灾情」。再点上方「地图」→「加载地图」，真实 OSM 底图中央出现蓝色圆点（模拟旅客，状态行标明 WGS84 与「不是物理 GPS」）。
10. 收一句：**变化是服务器检测到的，方案是服务器生成的，只有你按下「接受」才改行程。**

## 如果当场出问题

- 卡片没出现：重开「行程守护」或等 3 秒；仍无 → 重跑第 1 步。
- 平板连不上：用电脑浏览器打开同一地址演示（步骤相同）。
- 完全没网：展示这三张截图——
  - `trial/results/20261022_v3_human_chrome/guardian-proposal-390-r8.png`（提案卡）
  - `trial/results/20261022_v3_human_chrome/guardian-accepted-390-r8.png`（按完后）
  - `trial/results/20261022_v3_human_chrome/rehearsal2-5-after.png`（平板视口彩排）

## 已知边界（照实说，不必展开）

- 「课堂演示」入口只在演示模式存在（`CITYNEXUS_DEMO_MODE=true`），生产不出现。
- 手机屏上同时有旧恢复面板的两张「方案 A/B」卡（带内部 id）；正式入口是流程第 7 步那张。
- 平板上点按的实测仍待主人亲自走一遍（`TABLET_OPEN` 仅本机浏览器验证）。
- 时空模拟（虚拟时钟、地图蓝点）在面板浮球里，是另一段，不占这 5 分钟。

## 短回执（来自 `prepare_classroom_scene_r1.py` 的现读）

```text
DEMO_READY=1
WINDOWS_START=start_classroom_demo.bat
TABLET_OPEN=http://10.15.5.23:14492/revolution   (tablet: UNVERIFIED)
AGENT_QA=direct-replan-only (agent path verified separately)
REAL_POI=1
SAVED_PLAN=1
RESTART_SESSION=1
FALLBACK_SCREENSHOT=trial/results/20261022_v3_human_chrome/guardian-proposal-390-r8.png
```
