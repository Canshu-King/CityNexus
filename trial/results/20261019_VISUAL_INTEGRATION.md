# 实景照片、可读方案与地图联动

**现在可以在本机 `/revolution` 试用新版画面。** 当前连城任务能查看冠豸山、石门湖、培田照片，挑选纵向方案卡，从照片打开对应日程，也能继续向同一个 Agent 提要求。

- 试玩入口：http://127.0.0.1:14332/revolution
- 产品提交：`24f83ea44fbe8f4bd3270f3a3b35e220e43c3e6f`（主体 `338db540d2`，最后补正地图地点计数，不把临时查看地点称为已排日程）。
- 集成来源：[PR #41](https://github.com/Canshu-King/CityNexus/pull/41)，`f94f6917d0c73f6615c39634050336c2d7819346`；共同起点 `e1b672bd79`，安全快进，保留原提交。
- 对应指示：[6263149016](https://github.com/Canshu-King/CityNexus/pull/23#issuecomment-6263149016)、[6263900534](https://github.com/Canshu-King/CityNexus/pull/23#issuecomment-6263900534)。

## 用户现在能做什么

1. 看目的地实景封面和横向景点相册。三个地点的图片均在实际 Chrome 中加载成功，图片原页、作者、许可可点击。石门湖原来缺少的作者和许可已补齐；重复的参考图声明已收起为一处简短的历史照片/裁切标识。
2. 看完整纵向旅行卡，标题 **16px**、正文 **13px**。390/430/1366/1566 视口都没有三列挤字；滚动到操作位置时三份方案的选用按钮均可操作，聊天框位于底栏上方。
3. 点击照片，打开同一 `place_id` 的安排；尚未排入日程的地点显示「在地图中查看」。相邻图钉展开地点列表，避免互相遮挡。GCJ02 高德地点仍走高德入口，WGS84 才进入 OSM 地图和坐标预览。
4. 默认先看旅行结果。完整对话、来源、工作记录可展开；底部保留一个持续输入框，正常闲置时不重复显示状态说明。

## 真实对话与刷新恢复

在现有签名连城任务中，通过 **Chrome-use 原生 fill/click** 发送一次：

> 第二天下午只保留连城县博物馆和客家博物馆，去掉下午的石门湖备选。其他日期和时段保持原样，不新增地点或路线查询，只修改已有草案。

服务端实际完成 `replace_draft_slots`，草案 **6 → 7**，11 项变为 10 项。任务 ID 不变；第二天下午以外的全部安排逐字一致，三份备选保留。四档截图前分别刷新，之后再次签名读取，第 7 版内容仍完全一致。地图 ProviderCall 行数 **73 → 73**。

实测使用现有 owner 的本机 operator 签名会话。截图是安装版 Chrome 的模拟视口，非手机硬件；真人试用项仍为 **USER_VERIFIED=PENDING**。截图未替换内容或加工像素，截图切换图层使用 DOM 点击；照片入口及上述发送通过 Chrome-use 原生操作。

[真实对话收据](20261019_VISUAL_LIVE_FOLLOWUP.json)

## 直接看画面

| Chrome 视口 | 旅行首页 | 照片与地图 | 可读方案 |
| --- | --- | --- | --- |
| 390 × 844 | [首页](assets/20261019-visual-390-overview.png) | [相册](assets/20261019-visual-390-photos.png) | [方案](assets/20261019-visual-390-plans.png) |
| 430 × 932 | [首页](assets/20261019-visual-430-overview.png) | [相册](assets/20261019-visual-430-photos.png) | [方案](assets/20261019-visual-430-plans.png) |
| 1366 × 1000 | [首页](assets/20261019-visual-1366-overview.png) | [相册](assets/20261019-visual-1366-photos.png) | [方案](assets/20261019-visual-1366-plans.png) |
| 1566 × 1000 | [首页](assets/20261019-visual-1566-overview.png) | [相册](assets/20261019-visual-1566-photos.png) | [方案](assets/20261019-visual-1566-plans.png) |

每档 `20261019_VISUAL_BROWSER_<width>.json` 记录加载图片、来源、许可、字体、宽度、唯一输入框及滚动居中后的按钮位置。

## 验证

- `npm.cmd run typecheck:all`：通过。
- `npm.cmd run build`：通过；保留已有 bundle 体积提示。
- `npx.cmd playwright test --config _visual_test.config.ts`：**42/42**，配置在此次本机验收中复用 14332 前端，所有业务 API 被各用例隔离拦截；没有用夹具调用真实模型或来源。
- 新视觉用例进入 `playwright.mobile-trial.config.ts`，覆盖四档视口、照片失败回退、同名但来源不匹配不配图、图片到日程、重叠图钉、加载底图前零瓦片请求。旧工作记录测试按展开操作适配，保留原权限/恢复断言。
- 初次整组的 7 项失败分别来自旧折叠入口定位与新增图片被旧离线计数捕获，已具名修复；最终整组通过。[最终本地原始输出](20261019_VISUAL_UI_TESTS.txt)
- 产品 CI：[39254702734](https://github.com/Canshu-King/CityNexus/actions/runs/39254702734) **PASS**：TypeScript、Vite、42 项 Chromium 界面回归均通过。
- 地图计数补正后，四档视觉定向用例 **4/4**；四档截图/浏览器测量已更新绑定 `24f83ea44f`。真实对话发生于主体 `338db540d2`，对应后端文件与最后产品提交一致。

## 图片来源与下一棒

- [冠豸山原图](https://commons.wikimedia.org/wiki/File:%E8%BF%9C%E6%9C%9B%E5%86%A0%E8%B1%B8%E5%B1%B1_-_Guanzhai_Mountain_-_2010.07_-_panoramio.jpg)：rheins，CC BY 3.0。
- [石门湖原图](https://commons.wikimedia.org/wiki/File:%E7%9F%B3%E9%97%A8%E6%B9%96_-_Shimeng_Lake_-_2010.07_-_panoramio_-_rheins.jpg)：rheins，CC BY 3.0。
- [培田原图](https://commons.wikimedia.org/wiki/File:2012_%E7%A6%8F%E5%BB%BA_%E9%BE%99%E5%B2%A9_%E8%BF%9E%E5%9F%8E%E5%8E%BF_%E5%9F%B9%E7%94%B0%E5%8F%A4%E6%9D%91_-_panoramio_(3).jpg)：张元柏，CC BY-SA 3.0。

本次三张为人工核对、按来源 ID 与照片地点元数据绑定的图片，不改写来源记录的 UNKNOWN 地区/营业/费用状态。通用 Agent 自动取图及服务端 PlaceMedia 接口尚未接入本分支，后续接这条能力；其余地点继续使用已有地图/地点信息。

`PRODUCT_SHA=24f83ea44f | LIVE_PHOTO=3_LOADED | CHAT=ONE_INPUT_LIVE_FOLLOWUP | THREE_PLANS=READABLE_4_WIDTHS | MAP=SOURCE_COORDINATES_AND_FOCUS | USER_VERIFIED=PENDING`
