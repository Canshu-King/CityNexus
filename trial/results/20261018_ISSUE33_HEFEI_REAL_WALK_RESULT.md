# Issue #33：合肥真实两站散步验收

**路线验收等级：C1 实际探索闭环完成。正式 ACTIVE 行程、AI 工具运行和真人手机操作未完成。**

## 这次实际走通的流程

- 产品代码 SHA：`1dbaa828872543112c9db2457f2c3ab6b54a6058`，对应 PR #23 当前代码提交。
- 入口：`http://127.0.0.1:14332/revolution`；隔离前端 health 200，隔离后端 health 200。
- 浏览器：headed Chrome-use，会话 `citynexus-issue33-final`；390×844 CSS 视口、DPR 3。截图未使用 Qoder 页面或测试夹具。
- 地名：`Hefei City, Anhui Province, China` 的首个公开地名查询返回不可用；页面随后显示 Photon 名称和发送内容，经用户点击后只请求一次 Photon，返回合肥候选。
- 地点：确认合肥地区并选择“公园和绿地”后，用户点击搜索，Photon 返回 3 处公开地点：市府小花园、人民广场、李鸿章故居陈列馆。地点来源链接指向 OpenStreetMap；营业时间与费用在本次结果中为未知。
- 路线：选择“市府小花园”和“人民广场”，保存为当前签名成员的私人 Pocket Walk；点击 GO 后显示“正前往第一站”。整页刷新后，同两站及 `HEADING_TO_FIRST` 进度恢复。
- 验收等级分别记录：`LIVE_PROVIDER=YES`（Photon 地点请求）；`POCKET_WALK_TWO_STOPS=YES`；`GO=YES`；`PERSISTED_AFTER_RELOAD=YES`；`USER_CAN_OPEN=YES`；`USER_VERIFIED=PENDING`。

## 证据

- 同一隔离 SQLite 的只读核对，按地点名称匹配保存路线，读到第一站“市府小花园”、第二站“人民广场”、状态 `HEADING_TO_FIRST`。
- Photon `bootstrap_city_discovery` 服务端记录：`SUCCESS`，3 个结果；本次请求由页面确认发起。Nominatim 失败记录是 `DEGRADED`、0 个结果，没有重试。
- 当前库中正式 ACTIVE Journey 数为 0，`agent_runs` 数为 0。页面“行程”显示 AI 暂未开启、正式行程尚未启动；没有创建 ACTIVE 行程或伪造工具轨迹。
- 原图 9 张在 `assets/illustrated-revolution-first-trip/raw/`，每张为 390×844；标注图在 `annotated/`，包含实际 CSS 元素框、编号和控件原文。浏览器坐标与原图对应关系见 `annotations.json`。
- GitHub Actions `trial-build`：产品 SHA `1dbaa828` 对应 run [39078495728](https://github.com/Canshu-King/CityNexus/actions/runs/39078495728)，通过 TypeScript、Vite 构建和移动 Chromium fixture smoke。自动浏览器项是 fixture，不代替本次真实 Chrome/provider 路线。

## 现在怎么打开

在 Windows 上双击 [`../OPEN_REVOLUTION.cmd`](../OPEN_REVOLUTION.cmd)。启动窗口会打印当前分支、源码 SHA、教程路径和实际本机 URL；窗口需保持打开。已有同工作目录的健康实例会被复用，否则启动器选择空闲端口，并新建隔离试玩数据库。浏览器页面只在该电脑服务运行时可用。

## 继续项

- 真人 Android/iPhone 触控：待用户在自己的手机上验收。
- 正式 ACTIVE Journey 与真实 Hermes `AgentRun`：AI 当前关闭且本次路线为 DRAFT，尚无服务端运行记录。
- `USER_VERIFIED` 由用户本人打开并操作后再更新。
