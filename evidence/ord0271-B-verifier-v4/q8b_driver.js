// ORD-0271-B per-pass driver.
//
// The Q8(b) readout body stays verbatim in `q8b_readout.js` - one body for the control pass and for every
// mutant pass, which is that file's own promise. This driver only pins, per pass, which build the page must be
// executing, by writing the expected asset name and sha256 into `q8b_expected.json` before the call, and it
// reports the sha256 of the body bytes it actually read so the receipt names one instrument rather than a copy
// I retyped per pass. Nothing here re-types a reading. (The Playwright sandbox is ESM, hence dynamic imports.)
async (page) => {
  const fs = await import('node:fs/promises');
  const crypto = await import('node:crypto');
  const base = 'C:/Users/仓鼠王/cnx0271b/';
  const buf = await fs.readFile(base + 'q8b_readout.js');
  const body_sha256 = crypto.createHash('sha256').update(buf).digest('hex');
  const exp = JSON.parse(await fs.readFile(base + 'q8b_expected.json', 'utf8'));
  const src = buf.toString('utf8').split('__ASSET__').join(exp.asset).split('__SHA256__').join(exp.sha256);
  const raw = await page.evaluate(`(${src})`);
  return JSON.stringify({ expected: exp, readout_body_sha256: body_sha256,
                          readout: JSON.parse(raw) }, null, 1);
}
