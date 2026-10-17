# 2026-10-18 Chrome-use C0 / C1 实测

USER_CAN_OPEN=YES；USER_VERIFIED=PENDING。新版实际入口为 http://127.0.0.1:14332/revolution；手机视口真实公开地点→两站保存→GO→刷新恢复已完成，正式 ACTIVE Hermes AgentRun 留待 C2。

## 版本与隔离

- 产品提交：`f23eae768c7ddb5ed4cdc96e38e17e65f4eeec7c`，PR #23 / `design/revolution-mobile-first-v1`。
- checkout：`D:\moodle\_codex_workers\citynexus-chromeuse-retest-ccdd7486-20261018`。
- 前端 14332，后端 18501；两侧 `/api/v1/health` HTTP 200，status=ok、database=ok、ai=disabled / DISABLED_BY_OPS。
- 独立 SQLite：`backend/_revolution_hands_on_20261018_032851.db`。用户原来的 14173/14176、原数据库和原 trial/.runtime 均未用于本次测试。
- 后端进程启动时 HEAD 是父提交 `ccdd74866046498205b667b3b11b2b1260fdb8b8`；C0 仅修改两份前端 CSS，`git diff ccdd7486 f23eae76 -- backend` 为空。Vite 已加载 C0 样式，本报告的宁波流程和全部教程图片均在 C0 提交后完成。

## C0 产品修复

- 手机品牌和 AI 状态同行，header 实测由约 129px 缩到 65px。
- 地区标题与“换地区”并排，排除旧版单列响应式规则对 V1 的覆盖。
- 为控件滚动预留顶部和底栏空间；状态说明展开时使用独立浮层。
- 390×844：查找按钮 y=598–647，底栏 y=769，按钮高 49px，中心命中按钮；430×932：按钮 bottom=647、底栏 y=857。两种视口均无横向溢出。
- 本地 `npm.cmd run build` exit 0；C0 GitHub [trial-build 39064609793](https://github.com/Canshu-King/CityNexus/actions/runs/39064609793) PASS。

## C1：同一宁波会话的真实流程

1. 首页输入宁波，创建新 DRAFT Journey。已有签名 traveler 回读 `/travelers/session` 为 200，创建 Journey 为 201。
2. “查找位置”只提交一次 Nominatim 请求，返回 GEOCODER_UNAVAILABLE；未重试这个来源。
3. 阅读 Photon 发送说明，点击“改用 Photon 地名查找”，一次请求返回宁波市、宁波及机场候选。选择宁波市并点击“直接从这片地区附近找”。
4. 选择咖啡馆，单次真实 Photon 查询返回古茗和蜜雪冰城；页面显示公开地图来源、约 110 米/80 米，以及营业时间/费用未知。
5. 选择两站，保存接口 HTTP 200；GO HTTP 200。刷新后恢复古茗、蜜雪冰城和“正前往第一站”。
6. 暂停与继续均通过服务端 GO 转移保存，第二次刷新仍恢复“正前往第一站”；未提交任何到场/完成声明。
7. 切换“行程”“我的”，两站及进度保持。行程页显示 AI 工作动态和 AI 未启用；没有模型请求或 AgentRun。

逐条脱敏 HTTP 状态见 [本次宁波后端回执](20261018_CHROME_USE_NINGBO_HTTP.txt)。所有公开来源请求均由页面上的明确按钮触发，没有 API mock、fixture POI 或自动重试。

另有 C0 前的合肥独立会话：真实 Photon 返回星巴克、1点点、Post Coffee；保存星巴克/Post Coffee 后 GO/刷新恢复。该轮来源调用的产品 SHA 为 ccdd7486，不用于代替上述 C0 宁波结果。

## 浏览器工具与截图

- 使用 chrome-use.exe 直接驱动 headed Chrome；教程截图为 390×844。C0 另有 430×932 页面截图，桌面 1440×900 拍摄“我的”页。
- Chrome-use 默认坐标点击在部分操作上无效果，先观察页面与请求确认未提交，再以控件聚焦＋Enter 完成保存/GO，并用工具提供的 DOM click 模式验证暂停/继续与导航。截图捕获遇到后台窗口超时时，将本测试窗口前置后恢复；未把命令派发当成接口成功。
- 这些是桌面 Chrome 的手机视口实测，实际手机触控仍待用户操作。
- [13 步图文教程](../REVOLUTION_USER_ILLUSTRATED_GUIDE_CN.md)，26 张原图/红框标注图均为本次宁波会话，截图不含 token、密钥或完整 Journey ID。
- [390×844 主按钮](assets/chrome-use-20261018/c0-explore-390x844.png)、[430×932 主按钮](assets/chrome-use-20261018/c0-explore-430x932.png)、[1440×900 桌面](assets/chrome-use-20261018/me-desktop-1440x900.png)。

## 接下来

- C2：实际签名 ACTIVE Journey、Hermes AgentRun 和服务端工具轨迹；当前 AI 关闭，本轮未产生这一等级的证据。
- OSM 手选按钮的可见性已记录，本轮成功路线使用 Photon，未验收地图瓦片及地图点选。
- 启动器当前已输出 URL、来源模式及日志位置；额外打印图文教程路径与源码 SHA 的改动尚未加入。

五小时用量达到 93% 后停止运行验证，只整理上述既有证据与文档。
