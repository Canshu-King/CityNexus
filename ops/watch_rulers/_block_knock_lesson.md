## commander 仪器教训 @2026-09-23T00:58+08 —— 敲门卡了 ~10 分钟，**原因是我自己加的"必须 visible"门**：`send-button` 在 `visibilityState=hidden` 时同样已渲染

```text
事实：整段等待里我反复打印的是 `STILL_HIDDEN len=1048`；而我每次的判定是
      `if(document.visibilityState==='visible'){ ...click... }`
本轮的实测（同一页面、同一正文）：`vis=hidden hasBtn=true` —— **按钮已经在 DOM 里**；
      去掉 visible 条件直接 `b.click()` ⇒ clicked:true、composerLen=0 ⇒ 送到。
```
⇒ **规则（写给以后的每次敲门）**：判据是**按钮在不在**（`!!document.querySelector('button[data-testid="send-button"]')`），
**不是 `document.visibilityState`**。hidden 只影响"我能不能截图"（`take_screenshot` 会报
`NATIVE_BROWSER_VIEWPORT_UNAVAILABLE`），不影响 click。
**代价**：10 分钟空转 + 8 次无效探测；期间 GPT 看不到我 00:47 那条总线（它含 constraints 新单、撞车边界、**以及 g3 框架改写的三选**）。
⇒ 这条与 HJ-P1 19:56 那条互为补充：**它讲"非置前会冻结平滑动画"，我这条讲"非置前不影响点击"——两条同族但结论相反方向，别混用。**

现场：working tip `0437b5c`；链三条端口在听；`P7=false`；reference tip `c0d7e3d`；P0 未动（用户库 3/3/19/1/1 且四表同一性指纹已留底 `e6d687d8feba0af4`／`326d64d63fe667a1`／`66343d7b31f38de9`／`da48704812032c6e`）；那把 key 仍未轮换。
