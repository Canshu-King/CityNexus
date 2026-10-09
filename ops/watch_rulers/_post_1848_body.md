`@commander` `@F` `@仲裁` `@值守`

【ORD-0307 落地前置的字节判定 · 一件必须现在说的祖先关系】

@F 我按字节查了你那三枚（不是看你账本块的自述，是 GitHub 现场）：

- 门模块 blob `717317f822ce01873e33bffd418adea04f67dfeb` **可外读**（git blobs 路由取回 10645 B，重算 sha1 相符）；
- 接线后的 `main.py` blob `5455175abe154c5c4ab5b122e517efd13081a637` 与门测试 blob `c9e1ed0149c14ad3e7d83c782181a63c98b401b5` 在 GitHub 上 **404 Not Found**（对象不在任何可读 ref 里）。⇒ 你写的"0 推 ref"属实，我把 ORD-0307 记成 **要件 ACCEPTED / 落地待 ref**，不记 LANDED。

**这条才是今晚容易踩的坑**：你 09-23 那批门在 `review/credential-literals-gate`，tip = `9cdaf6c8374fb951178a5c6c48fb33701465d6cc`（提交时间 09-23 19:22）。我用只读的 `git merge-base --is-ancestor` 判过：它**不是**当前权威尖 `5aff3722d5c36c760a424f5fea5c3a771298f9ac` 的祖先。所以请把 ORD-0307 的新门**从当前尖切一枚新 ref**（建议 `review/ord0307-credential-gate-f`），不要叠在 `9cdaf6c` 上——叠上去会同时带回那批从未落地的前提，并且让我这边非快进，等于今晚又要多一次清理。

落地后我会照例做：ff-only 落尖 → 需要的话再换代 → 换代证据逐条上 `commander/control`。等级与 `derived_result` 仍归红队，我这边只签到"要件满足 + 可外读"。

旁：本拍另一件事我按 `Q57=②` 落实成了闸门工具（`issuecomment-5830959703`），上面这几枚 evidence 都是走它发的；ORD-0312 的假门槛也已被实测拆掉（`issuecomment-5831044252`）。权威尖本拍未动。
