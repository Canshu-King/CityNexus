# 手机工作台改版：单页切换与紧凑输入栏

手机浏览器已可试用这一版；Android/iOS 真机键盘和触摸手感仍需实际设备确认。

产品提交：`d0e61d6f5916681e688b60a3bfec6c2d0d4fde5c`。继承 `2431a1e8030e5d883b52200ef8bf4e58635a3b64`，保留原服务端草案和照片来源。

## 这次实际改了什么

- 手机不再横向排列地图与日程，也不在它们下面堆完整 Agent 面板；地图、日程、对话按页切换，组件保持挂载，草案编辑不会因为切页丢失。
- 移除重复的地区标题；目的地封面从205px缩为112px，换地区操作保留。桌面仍保留多栏。
- 常驻输入栏收为一行布局，实测约77px，文字16px。来源、额度、偏好通过齿轮打开上方设置面板，勾选与发送语义不变。
- 修复输入框失焦导致底栏移动、设置按钮按下后点击落空的问题；不再通过焦点变化搬动底栏。
- 照片打开对应日程、未排入日程的地点在地图中查看；底部地图/AI入口同步选择对应手机页。ACTIVE默认打开执行助手。

## 已执行检查

- `npx.cmd --prefix frontend playwright test --config frontend/_phone_test.config.ts --max-failures 1`：最终42/42通过，58.6秒，exit0。安装版Chrome、单worker，API使用TEST_FIXTURE；测试配置已移回本次备份目录。
- `npm.cmd --prefix frontend run typecheck:all`：exit0。
- `npm.cmd --prefix frontend run build`：exit0，原有大包体积提示仍在。
- `git diff --check`：exit0。
- 390×844、430×932：安装版Chrome中读取原隔离后端与已有签名旅行草案；每次一个主面板，文档宽度等于视口宽度，3张960px来源图片加载成功。截图切换日程采用DOM click，仅作构图；交互测试采用Chrome原生点击。
- 此轮浏览复核未提交模型/地点请求或业务写入。沿用此前的服务端数据，未把浏览器尺寸模拟说成手机硬件验收。

## 原始截图

- [390 地图](assets/20261019-phone-390-map.png)
- [390 日程](assets/20261019-phone-390-timeline.png)
- [430 地图](assets/20261019-phone-430-map.png)
- [430 日程](assets/20261019-phone-430-timeline.png)
- [尺寸与请求收据](20261019_PHONE_LAYOUT_RECEIPT.json)

试用入口：`http://127.0.0.1:14332/revolution`。现有隔离服务保持运行。
