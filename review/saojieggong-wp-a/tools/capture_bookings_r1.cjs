// 票夹/收件箱取景器（扫街工 WP-A′）：判据函数逐字抄号令者的 capture_r1.cjs（简报 §4 点名的共享量具），
// 只把取景改成 /v8/bookings，并加了三枚不参与判据的记录字段：content（这屏真渲染了什么）、
// bg/fg（是谁画的这块底）。为什么必须带 content：没有它，"0 格不达标"可能只是"什么都没渲染"。
const fs = require("fs");
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright/index.js");

const FRONT = process.env.SAOJIE_FRONT || "4720";
const BASE = "http://127.0.0.1:" + FRONT;
const JOURNEY = process.env.SAOJIE_JOURNEY || "22222222-2222-4222-8222-222222222222";
const ARM = process.argv[2] || "armA";
const OUT = "D:/moodle/_cmdr_saojieggong_1016/probe_" + ARM;
fs.mkdirSync(OUT, { recursive: true });

// ↓↓↓ 这段判据函数与 _cmdr_fe_rev_1016/capture_r1.cjs:12-37 逐字相同，只多记 bg/fg 两枚字段 ↓↓↓
const CONTRAST_PROBE = `
(() => {
  function lum(r,g,b){const f=c=>{c=c/255;return c<=0.03928?c/12.92:Math.pow((c+0.055)/1.055,2.4)};return 0.2126*f(r)+0.7152*f(g)+0.0722*f(b)}
  function prgb(s){const m=String(s).match(/rgba?\\(([^)]+)\\)/);if(!m)return null;const p=m[1].split(',').map(x=>parseFloat(x.trim()));return {r:p[0],g:p[1],b:p[2],a:p.length>3?p[3]:1}}
  function effBg(el){let n=el;while(n&&n!==document.documentElement){const c=prgb(getComputedStyle(n).backgroundColor);if(c&&c.a>0.85)return c;n=n.parentElement}const w=prgb(getComputedStyle(document.body).backgroundColor);return w||{r:255,g:255,b:255,a:1}}
  function ratio(f,b){const L1=lum(f.r,f.g,f.b),L2=lum(b.r,b.g,b.b);const hi=Math.max(L1,L2),lo=Math.min(L1,L2);return (hi+0.05)/(lo+0.05)}
  const out=[];
  document.querySelectorAll("h1,h2,h3,p,button,a,span,small,b,li,label,td,th").forEach(el=>{
    const cs=getComputedStyle(el);
    const t=(el.innerText||"").trim();
    if(!t||t.length>90)return;
    const r=el.getBoundingClientRect();
    if(r.width<2||r.height<2)return;
    const fsz=parseFloat(cs.fontSize), fw=parseInt(cs.fontWeight)||400;
    const large=(fsz>=24)||(fsz>=18.66&&fw>=700);
    const fg=prgb(cs.color); if(!fg||fg.a<0.5)return;
    const bg=effBg(el);
    const rr=ratio(fg,bg);
    out.push({tag:el.tagName.toLowerCase(),cls:(typeof el.className==="string")?el.className.slice(0,52):"",
      text:t.slice(0,52),px:Math.round(fsz),weight:fw,ratio:Math.round(rr*100)/100,
      need:large?3:4.5, pass:rr>=(large?3:4.5), role:el.getAttribute("data-contrast-role")||"",
      bg:"rgb("+Math.round(bg.r)+","+Math.round(bg.g)+","+Math.round(bg.b)+")",
      fg:"rgb("+Math.round(fg.r)+","+Math.round(fg.g)+","+Math.round(fg.b)+")",
      lh:cs.lineHeight, ls:cs.letterSpacing, fam:cs.fontFamily.split(',')[0].replace(/"/g,'')});
  });
  return out;
})()
`;

(async () => {
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const report = { arm: ARM, started: new Date().toISOString(), scenes: [], errors: [] };
  for (const vp of [{ name: "phone", width: 390, height: 844 }, { name: "desk", width: 1440, height: 900 }]) {
    for (const theme of ["light", "dark"]) {
      const ctx = await browser.newContext({
        viewport: { width: vp.width, height: vp.height },
        deviceScaleFactor: 2, hasTouch: vp.name === "phone", isMobile: vp.name === "phone",
        locale: "zh-CN",
      });
      const page = await ctx.newPage();
      const tag = vp.name + "_" + theme;
      page.on("pageerror", (e) => report.errors.push({ where: tag, kind: "pageerror", text: String(e).slice(0, 180) }));
      await page.addInitScript((a) => {
        try { localStorage.setItem("citynexus.v8.journey_id", a.j); } catch (e) {}
        try { localStorage.setItem("citynexus.theme", a.t); } catch (e) {}
      }, { j: JOURNEY, t: theme });
      await page.goto(BASE + "/v8/bookings", { waitUntil: "networkidle", timeout: 45000 })
        .catch((e) => report.errors.push({ where: tag + " goto", text: String(e).slice(0, 150) }));
      await page.waitForTimeout(2000);
      await page.screenshot({ path: OUT + "/" + tag + "_bookings.png" });
      const content = await page.evaluate(() => ({
        theme_attr: document.documentElement.getAttribute("data-theme"),
        url: location.pathname,
        booking_cards: document.querySelectorAll(".v8-booking-card").length,
        booking_cards_selected: document.querySelectorAll(".v8-booking-card.selected").length,
        booking_states: document.querySelectorAll(".v8-booking-state").length,
        booking_states_safe: document.querySelectorAll(".v8-booking-state.safe").length,
        booking_icons: document.querySelectorAll(".v8-booking-icon").length,
        selected_labels: document.querySelectorAll(".v8-selected-label").length,
        no_payment: document.querySelectorAll(".v8-no-payment").length,
        inbox_aside: document.querySelectorAll("aside.v9-inbox").length,
        inbox_label: document.querySelectorAll("aside.v9-inbox label").length,
        inbox_textarea: document.querySelectorAll("aside.v9-inbox textarea").length,
        body_head: (document.body.innerText || "").slice(0, 260).replace(/\s+/g, " "),
      }));
      const contrast = await page.evaluate(CONTRAST_PROBE);
      const fails = contrast.filter((c) => !c.pass);
      report.scenes.push({
        vp: vp.name, theme: theme, content: content,
        text_nodes_measured: contrast.length,
        fails: fails.length,
        fail_rows: fails.map((c) => ({ sel: c.tag + "." + c.cls.split(/\s+/)[0], text: c.text, ratio: c.ratio, need: c.need, fg: c.fg, bg: c.bg })),
        on_booking: contrast.filter((c) => /v8-booking|v9-inbox|v8-no-payment|v8-selected-label/.test(c.cls))
          .map((c) => ({ sel: c.tag + "." + c.cls.split(/\s+/)[0], text: c.text, ratio: c.ratio, need: c.need, pass: c.pass, fg: c.fg, bg: c.bg })),
      });
      await ctx.close();
    }
  }
  const tot = report.scenes.reduce((a, s) => a + s.fails, 0);
  const nodes = report.scenes.reduce((a, s) => a + s.text_nodes_measured, 0);
  const cards = report.scenes.reduce((a, s) => a + s.content.booking_cards, 0);
  const inbox = report.scenes.reduce((a, s) => a + s.content.inbox_aside, 0);
  report.totals = { fails: tot, nodes: nodes, booking_cards: cards, inbox_aside: inbox };
  fs.writeFileSync(OUT + "/report.json", JSON.stringify(report, null, 1), "utf8");
  console.log("arm=" + ARM + " scenes=" + report.scenes.length + " fails=" + tot + " nodes=" + nodes +
    " booking_cards=" + cards + " inbox_aside=" + inbox + " errors=" + report.errors.length);
  for (const s of report.scenes) {
    console.log("  " + s.vp + "/" + s.theme + " fails=" + s.fails + "/" + s.text_nodes_measured +
      " cards=" + s.content.booking_cards + " inbox=" + s.content.inbox_aside +
      " safe=" + s.content.booking_states_safe + " no_payment=" + s.content.no_payment);
  }
  if (cards === 0 || inbox === 0) {
    console.log("NEGATIVE-CONTROL FAILED: 票夹没渲染出卡片或收件栏，这屏的 0 格不算读数");
    await browser.close();
    process.exit(7);
  }
  await browser.close();
})();
