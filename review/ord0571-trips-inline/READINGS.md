# ORD-0571 - the inline stop actions vs the fixed bottom bar, measured on a private stack

Order text (relayed by the watch lane): reproduce 1ba48dbf's ORD-0561 item 4 on /v8/trips -
the per-stop 详情 / 打卡 rows whose centre hit-tests into the fixed bar (their numbers: y=817,
band 768..844) - and hand back a fix branch.

What this run measured (own headless Chromium, 390x844, product build of the head; the shared
Playwright tab kept being navigated away mid-read, so the instrument owns its browser):

- nav band: [768, 844] - identical to the reported band, so the shell is the same shape.
- .v8-product-shell padding-bottom: 80px (token --cn-nav-clearance, design-tokens.css --cn-nav-h 80px).
- document scrollHeight 1630, viewport 844, maxScroll 786.
- 8 inline actions over 4 stops; at scroll 0 none sits inside the band; scrolled to
  the bottom their centres sit at 74, 74, 231, 231 px - every one clears 768 px.
- allClearable = True. worst centre at full scroll = 545 px.

So on this generation and this data item 4 does not reproduce as 'permanently covered': the rows
below the fold need scrolling, and scrolling is enough. The reported row was 查看详情: Old Town
Gate - that journey in my private copy carries 0 legs, hence 0 inline actions, which is why the
exact y cannot be regenerated here. What is NOT claimed: that the defect is absent on the stack
1ba48dbf walked (different data, taller/shorter page). See the block for the two things needed.

Stack ownership (private, this lane only): {"api_pid": 25468, "api_port_lines": ["TCP    127.0.0.1:14902        0.0.0.0:0              LISTENING       25468"], "front_port_lines": ["TCP    127.0.0.1:14901        0.0.0.0:0              LISTENING       53988"], "db_path": "D:\\moodle\\_qoder_seed_ord0489\\run\\_ord0571.db", "db_bytes": 4349952, "dist_index": 1200}
