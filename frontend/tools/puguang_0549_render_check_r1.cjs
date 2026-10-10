/* ORD-0549 · puguang-0408's rendered-copy check for the simulation panel's retry label.
 *
 * The acceptance line this cell has to answer is "the words on screen do not change".  That is only honest if
 * something compares bytes, so this tool reads the dictionary's two arms for the key the product line now asks
 * for, compares each against the literal that was deleted from that line, and refuses when they differ.  It
 * also reads the product line itself: if the line still says `zh ?` or asks for a different key, the claim is
 * no longer what this cell delivered, and that is a MISMATCH too.
 *
 * A checker that can only print PROVEN is worth nothing, so `--positive-control` runs the same comparison
 * against a string the dictionary does not hold and requires it to come back MISMATCH - the arm has to be able
 * to fail before its green means anything.
 *
 *   node frontend/tools/puguang_0549_render_check_r1.cjs [--tree <frontend root>] [--positive-control]
 */
'use strict';
const fs = require('fs');
const path = require('path');

const ROOT = (() => {
  for (let i = 0; i < process.argv.length; i++) {
    if (process.argv[i] === '--tree') return process.argv[i + 1];
  }
  return path.resolve(__dirname, '..');
})();
const DICT = path.join(ROOT, 'src', 'i18n', 'LocaleContext.tsx');
const PANEL = path.join(ROOT, 'src', 'features', 'simulation', 'SimulationPanel.tsx');
const KEY = 'shared.refresh';
/* The two strings this cell deleted from the product line, byte for byte. */
const REMOVED_ZH = '再读一次';
const REMOVED_EN = 'Read it again';

function dictArms(text, key) {
  const out = [];
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(new RegExp('^\\s*"' + key + '":\\s*"((?:[^"\\\\]|\\\\.)*)"\\s*,?\\s*$'));
    if (m) out.push({ line: i + 1, value: JSON.parse('"' + m[1] + '"') });
  }
  return out;
}

function productLine(text) {
  const lines = text.split(/\r?\n/);
  const hits = [];
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].includes(REMOVED_ZH) || lines[i].includes('"' + KEY + '"')) {
      hits.push({ line: i + 1, text: lines[i].trim() });
    }
  }
  return hits;
}

function main() {
  const dict = fs.readFileSync(DICT, 'utf8');
  const panel = fs.readFileSync(PANEL, 'utf8');
  const arms = dictArms(dict, KEY);
  const want = { zh: REMOVED_ZH, en: REMOVED_EN };
  if (process.argv.includes('--positive-control')) {
    /* Feed it a string the dictionary does not carry.  The tool must refuse; if it prints PROVEN here, the
       comparison is decoration and this cell has no evidence at all. */
    want.zh = '不可行';
  }
  const problems = [];
  if (arms.length !== 2) {
    problems.push('KEY_NOT_ON_BOTH_SIDES: found ' + arms.length + ' arms for ' + KEY);
  }
  const zhArm = arms.find(a => a.value === REMOVED_ZH) || arms[0];
  const enArm = arms.find(a => a.value === REMOVED_EN) || arms[1];
  if (arms.length === 2) {
    if (zhArm.value !== want.zh) problems.push('ZH_ARM_DIFFERS: dictionary says ' + JSON.stringify(zhArm.value) + ', this cell removed ' + JSON.stringify(want.zh));
    if (enArm.value !== want.en) problems.push('EN_ARM_DIFFERS: dictionary says ' + JSON.stringify(enArm.value) + ', this cell removed ' + JSON.stringify(want.en));
  }
  const stillInline = panel.split(/\r?\n/).filter(l => l.includes(REMOVED_ZH) && l.includes('zh ?'));
  if (stillInline.length) problems.push('PRODUCT_LINE_STILL_INLINE: ' + stillInline.map(l => l.trim()).join(' | ').slice(0, 120));
  const routed = productLine(panel).filter(h => h.text.includes('t("' + KEY + '")'));
  if (!routed.length) problems.push('PRODUCT_LINE_DO_NOT_ASK_THE_NAMED_KEY: no t("' + KEY + '") in SimulationPanel.tsx');
  const report = {
    key: KEY, dictionary_arms: arms, product_line_now_keyed: routed,
    checked_against: want, zh_arm_line: zhArm && zhArm.line, en_arm_line: enArm && enArm.line,
    problems,
    claim_kind: 'pattern_determined',
    claimed_result: problems.length ? 'MISMATCH - do not ship' : 'PROVEN rendered text cannot change',
  };
  process.stdout.write(JSON.stringify(report, null, 1) + '\n');
  if (process.argv.includes('--positive-control')) {
    /* the control passes only when the checker refused */
    return problems.length ? 0 : 7;
  }
  return problems.length ? 1 : 0;
}
process.exit(main());
