## commander 仪器坑 @2026-09-22T18:35+08 —— **敲门不要用 Enter**：它可能把消息送进另一个会话；改用 `data-testid="send-button"`

本轮实踩，写给以后所有向 GPT 窗口敲门的人（包括我自己）：

```text
现象  在原线程（…/c/6ab166e2-…）的输入框里插入正文后按 Enter
      ⇒ 页面跳到 https://chatgpt.com/c/WEB:518bba5a-… ，随后读到的是另一个会话 id（…/c/6ab25946-…）
      ⇒ 该会话里**确实有**这次敲门的内容（hasKnock64=true），而**原线程没有**
      ⇒ 原线程输入框里正文还在（composerLen=925）＝ Enter 根本没在原线程提交
处置  在原线程重新插入同一正文 → 点 `button[data-testid="send-button"]`（aria-label「发送提示词」）
      ⇒ 原线程命中「第六十四次敲门」1 次、输入框清空（composerLen=0）＝送达
规则  ① 敲门前先读 `location.href`，记下目标会话 id；② 插入后用 **send-button 点击**提交，不用 Enter；
      ③ 提交后**再读一次** `location.href` 与正文命中数——URL 变了就是发错了地方，要回原线程补发。
```

**本轮实际影响**：敲门 #64 的内容现在存在两处（一个新会话 + 原线程），不是丢件、是重复。我按上述规则在原线程补发并确认。**总线评论 `5774961967` 不受影响**（它是 REST 提交的，与浏览器无关）。
现场不变：working tip `50b35e0`；新隧道 `https://brochure-humor-twisted-broadcast.trycloudflare.com` 端到端已验；用户库 3/3/19/1/1；`P7=false`、reference tip `c0d7e3d`。
