/* CMDR ORD-0419 candidate instrument r1 - do the three `#v8-nav-drawer > button` rules ever match?
 * Claim under test (lane 2d2d7428, ORD-0416 wrap-up): each drawer row <button> is wrapped in a <div>
 * (V8Experience.tsx:1976), so the child-combinator rules in styles.css:331/:337/:338 match nothing and
 * the 14 rows fall back to the UA default button paint.  Reported per row, from the RENDERED tree:
 *   - the button's parent tag (is it really a div, i.e. is `> button` structurally dead?)
 *   - computed background-color / color / padding / border-radius / font-size / offsetHeight
 *   - the sample pixel at the row's own centre (what a user actually sees)
 * Plus one control arm: the same computed values for a row we DID style via a descendant rule
 * (`#v8-nav-drawer button svg`), to show descendant matching works on this markup.
 * Usage: node cmdr_drawer_button_scope_r1.js <base> <out-dir>
 */
const { chromium } = require("D:/moodle/CityNexus/frontend/node_modules/playwright");
const fs = require("fs");
const path = require("path");

const BASE = process.argv[2] || "http://127.0.0.1:4805/";
const OUT = process.argv[3] || "D:/moodle/_qoder_cmdr_ref_20260921/live_checks/_drawer_scope_r1/";

function cssNumber(v) {
  const m = /-?[\d.]+/.exec(v || "");
  return m ? Number(m[0]) : null;
}

async function main() {
  fs.mkdirSync(OUT, { recursive: true });
  const browser = await chromium.launch({ channel: "chrome", headless: true });
  const ctx = await browser.newContext({ viewport: { width: 390, height: 844 }, hasTouch: true });
  const page = await ctx.newPage();
  const pageErrors = [];
  page.on("pageerror", (e) => pageErrors.push(String(e).slice(0, 200)));
  await page.goto(BASE, { waitUntil: "networkidle", timeout: 90000 });

  const seal = page.getByText("使用封存的演示行程", { exact: false }).first();
  if (await seal.count()) {
    await seal.click();
    await page.waitForTimeout(4000);
  }
  const hamburger = page.locator('[aria-controls="v8-nav-drawer"]');
  const hamburgerFound = await hamburger.count();
  if (hamburgerFound) {
    await hamburger.first().click();
    await page.waitForTimeout(1200);
  }

  const rows = await page.evaluate(() => {
    const drawer = document.querySelector("#v8-nav-drawer");
    if (!drawer) return null;
    const buttons = Array.from(drawer.querySelectorAll("button"));
    return buttons.map((b) => {
      const cs = getComputedStyle(b);
      const r = b.getBoundingClientRect();
      const label = (b.textContent || "").trim();
      const svg = b.querySelector("svg");
      const svgBox = svg ? svg.getBoundingClientRect() : null;
      return {
        label,
        parentTag: b.parentElement ? b.parentElement.tagName.toLowerCase() : null,
        parentIsDrawer: b.parentElement === drawer,
        directChildOfDrawer: b.parentElement === drawer,
        bgColor: cs.backgroundColor,
        color: cs.color,
        padding: cs.padding,
        borderRadius: cs.borderTopLeftRadius,
        fontSize: cs.fontSize,
        borderWidth: cs.borderTopWidth + "/" + cs.borderStyle,
        rectTop: Math.round(r.top),
        rectHeight: Math.round(r.height),
        rectWidth: Math.round(r.width),
        offsetHeight: b.offsetHeight,
        svgWidthPx: svgBox ? Math.round(svgBox.width) : null,
      };
    });
  });

  if (!rows) {
    console.log(JSON.stringify({ base: BASE, verdict: "DRAWER_NOT_FOUND", hamburgerFound }, null, 2));
    await browser.close();
    return;
  }

  // Screenshot the drawer, then sample each row's own centre pixel from the same PNG.
  const drawerShot = path.join(OUT, "drawer_390x844.png");
  const nav = page.locator("#v8-nav-drawer");
  await nav.screenshot({ path: drawerShot });
  const png = fs.readFileSync(drawerShot);
  const shotBox = await nav.boundingBox();

  const sampleRowCentres = (buf) => {
    // walk the PNG chunks to find IHDR width/height, then use a tiny scanline decode via zlib
    const w = buf.readUInt32BE(16);
    const h = buf.readUInt32BE(20);
    const bitDepth = buf[24];
    const colorType = buf[25];
    const idat = [];
    let off = 8;
    while (off < buf.length) {
      const len = buf.readUInt32BE(off);
      const type = buf.toString("ascii", off + 4, off + 8);
      if (type === "IDAT") idat.push(buf.slice(off + 8, off + 8 + len));
      off += 12 + len;
    }
    const raw = require("zlib").inflateSync(Buffer.concat(idat));
    const channels = colorType === 6 ? 4 : colorType === 2 ? 3 : 1;
    const stride = w * channels;
    const out = Buffer.alloc(h * stride);
    let pos = 0;
    const paeth = (a, b, c) => {
      const p = a + b - c;
      const pa = Math.abs(p - a), pb = Math.abs(p - b), pc = Math.abs(p - c);
      return pa <= pb && pa <= pc ? a : pb <= pc ? b : c;
    };
    for (let y = 0; y < h; y++) {
      const filter = raw[pos++];
      const line = raw.slice(pos, pos + stride);
      pos += stride;
      for (let x = 0; x < stride; x++) {
        const a = x >= channels ? out[y * stride + x - channels] : 0;
        const b = y > 0 ? out[(y - 1) * stride + x] : 0;
        const c = x >= channels && y > 0 ? out[(y - 1) * stride + x - channels] : 0;
        let v = line[x];
        if (filter === 1) v = (v + a) & 255;
        else if (filter === 2) v = (v + b) & 255;
        else if (filter === 3) v = (v + ((a + b) >> 1)) & 255;
        else if (filter === 4) v = (v + paeth(a, b, c)) & 255;
        out[y * stride + x] = v;
      }
    }
    return { out, w, h, channels };
  };

  const img = sampleRowCentres(png);
  const sampled = rows.map((row) => {
    if (!shotBox || shotBox.height <= 0) return { ...row, pixel: null };
    const y = Math.round(((row.rectTop + row.rectHeight / 2) - shotBox.y) * (img.h / shotBox.height));
    const x = Math.round(((shotBox.width / 2) + 4) * (img.w / shotBox.width));
    if (y < 0 || y >= img.h || x < 0 || x >= img.w) return { ...row, pixel: null };
    const i = y * img.w * img.channels + x * img.channels;
    return {
      ...row,
      pixel: {
        rgb: [img.out[i], img.out[i + 1], img.out[i + 2]],
        hex: "#" + img.out.slice(i, i + 3).toString("hex"),
      },
    };
  });

  // Structurally dead?  A rule with `> button` can only match a button whose parent IS the drawer.
  const directChildren = sampled.filter((r) => r.directChildOfDrawer).length;
  const uaDefault = sampled.filter((r) => /rgb\(229|rgb\(212|rgb\(225|ButtonFace/i.test(r.bgColor)).length;

  const report = {
    instrument: "cmdr_drawer_button_scope_r1",
    base: BASE,
    entryAsset: null,
    viewport: "390x844",
    locale: "zh",
    drawerButtonsTotal: sampled.length,
    buttonsDirectlyUnderDrawer: directChildren,
    buttonsWrappedInOtherTag: sampled.length - directChildren,
    parentTagsSeen: Array.from(new Set(sampled.map((r) => r.parentTag))),
    rowsWithUaDefaultBackground: uaDefault,
    bgColorsDistinct: Array.from(new Set(sampled.map((r) => r.bgColor))),
    radiusDistinct: Array.from(new Set(sampled.map((r) => r.borderRadius))),
    fontSizeDistinct: Array.from(new Set(sampled.map((r) => r.fontSize))),
    heightDistinct: Array.from(new Set(sampled.map((r) => r.rectHeight))),
    svgWidthPxSeen: Array.from(new Set(sampled.map((r) => r.svgWidthPx))),
    rowHeightSum: sampled.reduce((a, r) => a + r.rectHeight, 0),
    rows: sampled,
    pageErrors,
  };
  const entry = await page.evaluate(() => {
    const s = Array.from(document.querySelectorAll('script[src*="assets/index-"]'));
    return s.map((x) => x.getAttribute("src"));
  });
  report.entryAsset = entry;

  const outFile = path.join(OUT, "drawer_button_scope_r1.json");
  fs.writeFileSync(outFile, JSON.stringify(report, null, 2));
  console.log(JSON.stringify({
    base: BASE,
    entryAsset: entry,
    drawerButtonsTotal: sampled.length,
    buttonsDirectlyUnderDrawer: directChildren,
    parentTagsSeen: report.parentTagsSeen,
    rowsWithUaDefaultBackground: uaDefault,
    bgColorsDistinct: report.bgColorsDistinct,
    radiusDistinct: report.radiusDistinct,
    fontSizeDistinct: report.fontSizeDistinct,
    svgWidthPxSeen: report.svgWidthPxSeen,
    shot: drawerShot,
    outFile,
  }, null, 2));
  await browser.close();
}

main().catch((e) => { console.error("FATAL", e); process.exit(1); });
