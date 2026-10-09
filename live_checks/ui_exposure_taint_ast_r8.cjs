/* ui_exposure_taint_ast_r3.cjs - ORD-0331 follow-up: ruler r6. Same decision as r5 (blob
 * ff98091cf3accb0d836ae25ba49820170b92d932) plus an honest statement of what each mode can see, because the
 * two modes were being read as one number.
 *
 * WHAT A MODE CAN SEE (measured on generation 821a0eb54cca1b305a4aa75c1ca8d46a95d51bba, 76 modules):
 *   --tree        24 cells   the module graph: a helper's own body decides, and poison may cross a boundary
 *   --file/--ref  22 cells   each file alone: an imported helper is opaque
 *   1 cell existed ONLY per-file  - app/V8Experience.tsx:1348 - a call into a helper that turns out to return
 *       only device wording; per file the ruler must assume "anything handed to an unknown function can come
 *       back", so it over-reports. This is the exoneration r5 removed.
 *   3 cells existed ONLY in --tree - app/V8Experience.tsx:1380, app/V8Experience.tsx:2609,
 *       features/simulation/SimulationPanel.tsx:934 - poison that arrives across an `import`. Per file there
 *       is nothing to trace, so the screen reads clean.
 *   So a per-file count is NOT an upper bound on --tree, and not a lower bound either: 22 < 24 here while
 *   per file also holds a cell --tree does not. The modes answer different questions; a receipt that quotes
 *   one has to say which. Arms F and G of --selftest keep both directions honest, and every per-file
 *   document carries `scope` / `scope_note`.
 *
 * Original r5 header follows.
 */
/* ui_exposure_taint_ast_r2.cjs - ORD-0331: the same Q64 ruler r4 (file ui_exposure_taint_ast_r1.cjs, blob
 * eb262f59e54d5142ad0e8041704e751eac473ace) with the module graph added, so a helper that hands back the
 * answer's words is no longer invisible one file away from the screen that prints them.
 *
 * r1 stays byte-for-byte as published; this is a new coordinate. What changed:
 *   - relative `import` / `export` (including `export ... from`, `export * from`, `import * as ns`,
 *     default imports and index files) are resolved across the scanned tree, and an import binding's taint
 *     is answered by the exporting module's own data flow;
 *   - `--tree <dir>` scans a whole module graph; `--file` still behaves exactly as r1 did per file;
 *   - an unresolved specifier (a package like react, or a file outside the tree) is recorded and counted in
 *     `unresolved_import_specs`, so a clean verdict says how much of the graph it actually saw.
 * Everything else - poison sources, spread, sinks, property paths, the fixpoint - is r1's, unchanged.
 *
 * Original r1 header follows.
 */
/* ui_exposure_taint_ast_r1.cjs - ORD-0322: the UI_EVIDENCE_EXPOSURE_GATE_V1 ruler (Q64) decided by real
 * data flow over the TypeScript AST, replacing the regular-expression ruler r3.
 *
 * Supersedes ui_exposure_field_check_r3.py = 44e062e6ce9c7b5d97d78e09e432072da102292c. r1, r2 and r3 are
 * left byte-for-byte untouched; a published coordinate is never rewritten.
 *
 * Why r3 had to go: every round of lane E's reverse attack (ORD-0319 rounds 2 and 3) bought a new indirect
 * shape that r3's grammar could not spell - optional chaining, a `.value` tail name, a bare local hop, the
 * alias `(x.y || {}).text`, the bracket key `body["detail"]`, and the forwarding helper
 * `function wrap(b){ return serverReasonSentence(b); }`, where the poison travels along a return edge.
 * Enumerating spellings does not converge. Reachability over the call graph is a finite rule, and the AST
 * gives it: `body?.detail`, `body.detail` and `body["detail"]` are one node shape, and a binding is a node.
 *
 * The decision is r3's semantics, not a new one (standing rule Q64=1, arbiter):
 *   allowed on screen  http_status content_type body_bytes response_received elapsed_ms request_id
 *   forbidden          the answer's own words reaching the DOM, by any route.
 *
 * poison source   a read of a forbidden field: `detail` `body_head` `stack` `trace` `raw` `componentStack`
 *                 by name, and `message` `body` `error` `payload` `content` `output` `exception` when the
 *                 base carries the answer (a response envelope, or a value already poisoned). All three
 *                 spellings are the same check. Plus `.message`/`.stack` off Error / `cause` / React error
 *                 `info`, a caught value reaching the screen, and a whole response body reaching it.
 * poison spread   assignment and compound assignment, object-literal property VALUES (a property NAME is a
 *                 binding point, never data), destructuring with and without rename, template holes, call
 *                 arguments resolved into the callee's parameters by position, `return` values (so a
 *                 forwarding helper inherits what it forwards), `||` `??` `+`, ternary branches, array and
 *                 object literals, callbacks handed to `map`/`then`/`catch`, and React `useState` setters
 *                 writing through to the state variable they were destructured with.
 * sinks           a JSX text child, `dangerouslySetInnerHTML`, `textContent=`/`innerText=`/`innerHTML=`.
 *                 NOT sinks: an attribute interpolation (`data-reason-origin={x.from}` stays clean) and the
 *                 tested side of a guard (`{cond && (` renders no prose, so it is not reported).
 * precision       property-path sensitive, so a poisoned `out.failureReason` does not condemn `out.status`;
 *                 context-insensitive per file, settled by fixpoint over the call graph, so cycles converge.
 *
 * A hit names a shape to justify; it is not a defect verdict.
 * Read-only by construction: it parses text. `--ref` reads a blob with `git show`, which touches no working
 * tree. It writes only the file named by `--out`.
 *
 * usage: node ui_exposure_taint_ast_r1.cjs --file a.tsx,b.tsx | --ref <sha> --path <in-tree path>
 *                                            [--out <json>] | --selftest [--out <json>]
 */
'use strict';

const fs = require('fs');
const cp = require('child_process');
const crypto = require('crypto');

const TS_CANDIDATES = [
  process.env.CNX_TS_MODULE,
  // D:/moodle/CityNexus/frontend/node_modules is a junction whose source was emptied, so requiring
  // typescript from it threw and the ruler fell back to NOT_MEASURED -- the Q64 no-grow arm was idle.
  // The live line's own tree carries the real deps (394 packages), the same source that unblocked
  // vite_build (2026-10-08 00:0x).  Keep it first so the arm measures again.
  'D:/moodle/_qoder_integration_20260919/frontend/node_modules/typescript',
  'D:/moodle/CityNexus/frontend/node_modules/typescript',
];
const REPO = process.env.CNX_REPO || 'D:/moodle/CityNexus';

function loadTs() {
  for (const c of TS_CANDIDATES) { try { return require(c); } catch (e) { /* next */ } }
  return null;
}

const ALLOWED_FIELDS = ['http_status', 'content_type', 'body_bytes', 'response_received', 'elapsed_ms', 'request_id'];

// Upstream prose by field name alone: Q64 names these, and this codebase never spells a device-composed
// label the same way.
const FORBIDDEN_ALWAYS = new Set(['detail', 'body_head', 'stack', 'trace', 'raw', 'componentStack', 'component_stack']);
// Ambiguous names: poison only when the base carries the answer.
const FORBIDDEN_WITH_PROVENANCE = new Set(['message', 'body', 'error', 'errors', 'payload', 'content', 'output', 'exception']);
// The attribute slot is guarded by name as well as by provenance; see the sink comment.
const ATTRIBUTE_NAMED_PROSE = new Set(['message', 'stack']);
// Names that only ever hold an answer or an exception.
const ENVELOPE_NAMES = new Set(['body', 'payload', 'resp', 'res', 'response', 'json', 'result_body', 'server_body',
  'answer', 'error', 'err', 'e', 'exception', 'cause', 'info', 'unreadable', 'refused', 'reason']);
// Reads whose result is itself an envelope.
const ENVELOPE_READS = new Set(['error', 'errors', 'data', 'payload', 'cause', 'detail']);
// Globals that only turn a value into text. Crossing them is not crossing a helper, so it must not
// relabel a direct read as `via helper` - that is a naming claim, and r3 named `String(error?.message)`
// at ProductErrorBoundary.tsx:104 a direct read.
const BUILTIN_FUNCS = new Set(['String', 'Number', 'Boolean', 'Array', 'Object', 'JSON', 'Math', 'Date', 'RegExp',
  'Intl', 'encodeURIComponent', 'decodeURIComponent', 'encodeURI', 'decodeURI', 'escape', 'unescape', 'parseFloat',
  'parseInt', 'isNaN', 'isFinite', 'fetch', 'structuredClone', 'require']);
/* members that answer with a number or a boolean whatever they are read off: `body.length` is a byte
 * count, which is one of the six fields Q64 allows on screen, so inheriting prose through it would turn
 * the gate against itself. */
const NUMERIC_MEMBERS = new Set(['length', 'size', 'byteLength', 'byteOffset', 'index', 'lastIndex',
  'lineNumber', 'columnNumber', 'start_index', 'end_index']);
const EXCEPTION_FIELDS = new Set(['message', 'stack', 'trace', 'componentStack', 'component_stack']);
// Methods that hand back data derived from their receiver (boolean answers deliberately absent).
const PASS_THROUGH = new Set(['then', 'catch', 'finally', 'map', 'filter', 'flatMap', 'forEach', 'reduce', 'join',
  'split', 'trim', 'trimStart', 'trimEnd', 'toUpperCase', 'toLowerCase', 'slice', 'substring', 'substr',
  'replace', 'replaceAll', 'concat', 'padStart', 'padEnd', 'toString', 'charAt', 'at', 'reverse', 'sort',
  'find', 'repeat', 'normalize']);

const SCOPE_PER_FILE = "per-file: no module graph is built here (--file / --ref --path)";
const SCOPE_GRAPH = "module-graph: relative imports, index files, re-exports and namespace imports resolved (--tree)";
const SCOPE_NOTE_PER_FILE = "a per-file count is neither an upper nor a lower bound on --tree: a call into an "
  + "imported helper is opaque, so a value the helper actually returns as device wording is still reported here "
  + "(over-report); and poison that arrives through an import has no edge to follow, so the screen reads clean "
  + "here (under-report). Both directions are pinned by selftest arms F and G, and the split measured on "
  + "generation 821a0eb54cca1b305a4aa75c1ca8d46a95d51bba is 1 cell only per-file, 3 cells only in --tree.";
const MAXD = Number(process.env.CNX_R4_MAXD || 150);
// one budget for the whole run, shared by every module, so a cycle between two files cannot outlive a query
const MAX_CROSSINGS = Number(process.env.CNX_R4_MAX_HOPS || 24);
let crossings = 0;
let crossingCuts = 0;   // module scope: the CLI reports the cap it ran with


/* ------------------------------------------------------------------ Q64 structured exemptions
 * ORD-0408.  Before this, waiving the no-growth arm was a hand at the gate: `--exposure-arm off`, a re-pinned
 * ruler blob, or a candidate landed around the door by hand.  An exemption is now DATA the RULER reads and
 * applies, so a cell is either covered by a named ledger entry (whose id travels in the measurement document)
 * or it is not, and the same run can be re-audited without asking anybody what was waived.
 *
 * Fail-closed, three ways, because an exemption mechanism is exactly the thing a tired shift can use to switch
 * the gate off:
 *   ABSENT     no ledger file -> zero exemptions applied, the census reads exactly like r7b;
 *   REJECTED   malformed JSON, an unknown face, an active entry without a ruling named, or a grant wide enough
 *              to silence the arm (wildcard path AND wildcard rule) -> the ruler refuses to certify the run at
 *              all: measurement NOT_PERFORMED, hits emptied BY CONSTRUCTION, so the door cannot read zero cells
 *              as a clean tree;
 *   OK_ACTIVE/OK_HELD  the normal shapes; a `held` entry never exempts anything, it only reports how many cells
 *              it WOULD have covered so the commander can size a waiver before signing it.
 */
const EXEMPTION_LEDGER_DEFAULT = __dirname + '/q64_exposure_exemptions.json';
const WILDCARD_GLOBS = ['', '*', '**', '/**', './**', '**/*'];

function globToRegExp(glob) {
  let head = '', rest = String(glob);
  if (rest.indexOf('**/') === 0) { head = '(?:.*/)?'; rest = rest.slice(3); }
  let out = '';
  for (let i = 0; i < rest.length; i++) {
    const ch = rest.charAt(i);
    if (ch === '*') { out += (rest.charAt(i + 1) === '*') ? (i++, '.*') : '[^/]*'; }
    else if (ch === '.') { out += '\\.'; }
    else if ('+/'.indexOf(ch) >= 0) { out += ch === '/' ? '/' : '\\+'; }
    else if (/^[A-Za-z0-9_$\-]$/.test(ch)) { out += ch; }
    else { out += '\\' + ch; }
  }
  return new RegExp('^' + head + out + '$');
}

function isWildcardGlob(g) {
  return WILDCARD_GLOBS.indexOf(String(g || '').trim()) >= 0;
}

function loadExemptionLedger(args) {
  const p = args.exemptions || process.env.CNX_Q64_EXEMPTIONS || EXEMPTION_LEDGER_DEFAULT;
  let raw;
  try { raw = fs.readFileSync(p); }
  catch (e) {
    return { path: p, status: 'ABSENT', reason: 'no ledger file at ' + p, entries: [],
             bytes: 0, sha1: null };
  }
  const res = { path: p, bytes: raw.length, sha1: gitBlobId(raw), entries: [], status: null, reason: null };
  let doc;
  try { doc = JSON.parse(raw.toString('utf8')); }
  catch (e) {
    res.status = 'REJECTED_MALFORMED_JSON';
    res.reason = 'the ledger is not valid JSON, so no exemption can be trusted: ' + String(e).slice(0, 120);
    return res;
  }
  if (doc.schema !== 'CNX_Q64_EXPOSURE_EXEMPTIONS_V1' || !Array.isArray(doc.entries)) {
    res.status = 'REJECTED_UNKNOWN_SCHEMA';
    res.reason = 'schema is ' + JSON.stringify(doc.schema) + ' / entries is ' + typeof doc.entries;
    return res;
  }
  const faces = (doc.policy && Array.isArray(doc.policy.faces_vocabulary)) ? doc.policy.faces_vocabulary : [];
  res.entries = doc.entries;
  for (const en of res.entries) {
    const st = String(en.status || ''), match = en.match || {};
    if (['active', 'held'].indexOf(st) < 0) {
      res.status = 'REJECTED_ENTRY_STATUS'; res.reason = 'entry ' + en.id + ' status ' + JSON.stringify(en.status);
      return res;
    }
    if (faces.indexOf(String(en.face)) < 0) {
      res.status = 'REJECTED_ENTRY_FACE'; res.reason = 'entry ' + en.id + ' face ' + JSON.stringify(en.face)
        + ' is not in faces_vocabulary';
      return res;
    }
    if (st === 'active' && !String(en.decided_by || '').trim()) {
      res.status = 'REJECTED_ACTIVE_WITHOUT_RULING';
      res.reason = 'entry ' + en.id + ' is active but names no decided_by';
      return res;
    }
    if (isWildcardGlob(match.path_glob) && String(match.rule || '') === '*') {
      res.status = 'REJECTED_BLANKET_GRANT';
      res.reason = 'entry ' + en.id + ' matches any path and any rule: that is not an exemption, it is the arm '
        + 'switched off';
      return res;
    }
    en.__path_re = globToRegExp(match.path_glob || '');
    en.__rule = String(match.rule || '');
  }
  res.status = res.entries.some(function (e) { return e.status === 'active'; }) ? 'OK_ACTIVE' : 'OK_HELD';
  return res;
}

function gitBlobId(buf) {
  return crypto.createHash('sha1')
    .update('blob ' + buf.length + String.fromCharCode(0)).update(buf).digest('hex');
}

/* The one place that decides.  A hit carries `exempt` and the id of the entry that covered it, so the cell is
 * still in the document -- an exemption changes what the arm counts, never what the ruler saw. */
function applyExemptions(hits, ledger) {
  const sum = {
    schema: 'CNX_Q64_EXEMPTIONS_APPLIED_V1', path: ledger.path, bytes: ledger.bytes, sha1: ledger.sha1,
    status: ledger.status, reason: ledger.reason,
    entries_total: ledger.entries.length, entries_active: 0, entries_held: 0,
    applied_by_entry: {}, held_would_match: {},
    cells_total: hits.length, cells_exempt: 0, cells_product: hits.length,
    exempted_cells: [],
  };
  for (const en of ledger.entries) {
    if (en.status === 'active') { sum.entries_active++; sum.applied_by_entry[en.id] = 0; }
    else { sum.entries_held++; sum.held_would_match[en.id] = 0; }
  }
  for (const h of hits) {
    let covered = null, would = null;
    for (const en of ledger.entries) {
      const ruleOk = en.__rule === '*' || en.__rule === String(h.rule);
      if (!ruleOk || !en.__path_re.test(String(h.file))) continue;
      if (en.status === 'active') { covered = en; break; }
      if (!would) would = en;
      sum.held_would_match[en.id] = (sum.held_would_match[en.id] || 0) + 1;
    }
    if (covered) {
      h.exempt = true; h.exemption_id = covered.id; h.exemption_face = covered.face;
      sum.applied_by_entry[covered.id]++; sum.cells_exempt++;
      sum.exempted_cells.push({ file: h.file, line: h.line, rule: h.rule, exemption_id: covered.id });
    } else {
      h.exempt = false;
      if (would) { h.exemption_would_be = would.id; }
    }
  }
  sum.cells_product = hits.length - sum.cells_exempt;
  return sum;
}

const RULER = {
  name: 'ui_exposure_taint_ast_r8.cjs',
  supersedes: 'ui_exposure_taint_ast_r7b.cjs (blob e2ea5ce64ca67bb476006766db27b0612789dd36), which superseded r7 = ui_exposure_taint_ast_r7.cjs (blob 3272a4336f60ddd183875000c11e5b5ead6be2be), which superseded '
    + 'r6 = ui_exposure_taint_ast_r3.cjs (blob 6a251d3a6bea70329e06581384a81d5ef54c96a6)',
  supersedes_blob: 'e2ea5ce64ca67bb476006766db27b0612789dd36',
  also_supersedes_r4: { file: 'ui_exposure_taint_ast_r1.cjs', blob: 'eb262f59e54d5142ad0e8041704e751eac473ace' },
  rule_lineage: 'r1 regex -> r2 regex -> r3 regex -> r4 AST per-file -> r5 module graph -> r6 scope+prose/structure '
    + '-> r7 attribute slot (Q71) + attributed-fold exoneration (Q67=1 / Q75) '
    + '-> r7b a cell identity that does not move when the file\'s lines move',
  order: 'ORD-0354 (attribute slot + line-independent cell identity) + ORD-0348 (fold exoneration) + ORD-0408 (structured exemption ledger read by the ruler)',
  also_supersedes: { r3: 'ui_exposure_field_check_r3.py', r3_blob: '44e062e6ce9c7b5d97d78e09e432072da102292c' },
  generation: 'r8 / r7b + a data-shaped Q64 exemption ledger (nothing is waived by a hand at the gate)',
  /* The local filename now says what generation it is. r4/r5/r6 were published from files named r1/r2/r3,
     which is how a lane can quote a blob and still have nobody know which bytes ran; the mismatch stops here. */
  naming: 'local file name == published generation name from r7 onward',
};

/* ------------------------------------------------------------------ analyzer */

function makeAnalyzer(ts, fileName, text, hooks) {
  const sf = ts.createSourceFile(fileName, text, ts.ScriptTarget.ESNext, true,
    /\.tsx$/.test(fileName) ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  const diagnostics = (sf.parseDiagnostics || []).length;
  const lines = text.split(/\r?\n/);

  const nodes = [];
  const bindings = [];
  const idBinding = new Map();
  const fnOf = new Map();
  const callSites = [];
  const assignments = [];
  const statePairs = [];
  const classes = [];                       // {node, props: Map<name, binding>, state}
  const exportedNames = new Map();          // export name -> {local} | {fnRecord}
  const reexportFrom = new Map();           // export name -> {from, exported}
  const starFrom = [];                      // `export * from './m'` forwards whatever ./m exports
  const importBindings = [];                // bindings created by an import clause
  function isExportedNode(node) {
    const mods = (ts.getModifiers ? ts.getModifiers(node) : node.modifiers) || undefined;
    if (!mods) return false;
    for (const m of mods) if (m.kind === ts.SyntaxKind.ExportKeyword) return true;
    return false;
  }
  function defaultKeyword(node) {
    const mods = (ts.getModifiers ? ts.getModifiers(node) : node.modifiers) || undefined;
    if (!mods) return false;
    for (const m of mods) if (m.kind === ts.SyntaxKind.DefaultKeyword) return true;
    return false;
  }
  const rootScope = { map: new Map(), parent: null };
  const scopeStack = [rootScope];

  function lineOf(n) { return sf.getLineAndCharacterOfPosition(n.getStart(sf)).line + 1; }
  function srcOf(n) { return text.slice(n.getStart(sf), n.getEnd()); }
  function brief(n) {
    const s = srcOf(n).replace(/\s+/g, ' ').trim();
    return s.length > 78 ? s.slice(0, 78) + '...' : s;
  }
  // this TS release spells the node ThisKeyword, not ThisExpression, and offers no isThisExpression()
  function isThisNode(n) { return !!n && n.kind === ts.SyntaxKind.ThisKeyword; }
  function unwrap(n) {
    let c = n;
    while (c && (ts.isParenthesizedExpression(c) || ts.isAsExpression(c) || ts.isTypeAssertionExpression(c)
      || ts.isNonNullExpression(c) || ts.isSatisfiesExpression(c) || ts.isPartiallyEmittedExpression(c)
      || ts.isAwaitExpression(c) || ts.isOmittedExpression(c))) c = c.expression;
    return c;
  }
  function propKey(node) {
    if (ts.isPropertyAccessExpression(node)) return node.name.text;
    if (ts.isElementAccessExpression(node)) {
      const a = node.argumentExpression;
      if (a && (ts.isStringLiteral(a) || ts.isNoSubstitutionTemplateLiteral(a))) return a.text;
      return null;                                    // a computed key: what is behind it is unknown
    }
    return null;
  }
  function propName(p) {
    if (!p.name) return null;
    if (ts.isIdentifier(p.name)) return p.name.text;
    if (ts.isStringLiteral(p.name) || ts.isNumericLiteral(p.name)) return p.name.text;
    return null;
  }
  function rootOf(node) {
    let c = unwrap(node);
    while (c) {
      if (ts.isPropertyAccessExpression(c) || ts.isElementAccessExpression(c)) { c = unwrap(c.expression); continue; }
      if (ts.isCallExpression(c) || ts.isNewExpression(c)) {
        const callee = unwrap(c.expression);
        if (ts.isPropertyAccessExpression(callee)) { c = unwrap(callee.expression); continue; }
        return null;
      }
      return c;
    }
    return null;
  }
  function scopeFor(node) {
    for (let cur = node; cur; cur = cur.parent) { const f = fnOf.get(cur); if (f) return f.scope; }
    return rootScope;
  }
  function lookup(name, scope) { for (let s = scope; s; s = s.parent) { const b = s.map.get(name); if (b) return b; } return null; }
  function fnFor(node) { for (let cur = node.parent; cur; cur = cur.parent) { const f = fnOf.get(cur); if (f) return f; } return null; }

  function declare(nameIdent, kind, declNode, fn, initNode) {
    if (!nameIdent) return null;
    const b = { name: nameIdent.text, kind, declNode, fn, initNode: initNode || null, writers: [],
      envelope: false, byParam: null };
    const scope = fn ? fn.scope : scopeStack[0];
    if (!scope.map.has(b.name)) scope.map.set(b.name, b);
    bindings.push(b);
    idBinding.set(nameIdent, b);
    if (kind === 'param' || kind === 'catch') b.envelope = kind === 'catch' || ENVELOPE_NAMES.has(b.name);
    if (kind === 'import') b.envelope = ENVELOPE_NAMES.has(b.name);
    return b;
  }
  function patternNames(pattern, cb) {
    if (!pattern) return;
    if (ts.isIdentifier(pattern)) { cb(pattern, null); return; }
    if (ts.isObjectBindingPattern(pattern)) {
      for (const el of pattern.elements) {
        if (ts.isOmittedExpression(el)) continue;
        let key = null;
        if (el.propertyName) key = ts.isIdentifier(el.propertyName) ? el.propertyName.text
          : (ts.isStringLiteral(el.propertyName) ? el.propertyName.text : null);
        else if (ts.isIdentifier(el.name)) key = el.name.text;   // `{ error }` reads the slot `error`
        if (key !== null && ts.isIdentifier(el.name)) cb(el.name, key);
        else patternNames(el.name, cb);
      }
      return;
    }
    if (ts.isArrayBindingPattern(pattern)) {
      let i = 0;
      for (const el of pattern.elements) { if (!ts.isOmittedExpression(el)) cb(el.name, 'index:' + i); i++; }
    }
  }

  function walk(node, fn) {
    nodes.push(node);
    if (ts.isFunctionLike(node)) {
      const rec = { node, name: node.name ? node.name.text : null, params: [], returns: [],
        scope: { map: new Map(), parent: scopeStack[scopeStack.length - 1] } };
      fnOf.set(node, rec);
      if (node.name) {
        const hb = declare(node.name, 'fn', node, null, node);
        hb.isFunctionRecord = true;
        rec.binding = hb;
        if (isExportedNode(node)) exportedNames.set(defaultKeyword(node) ? 'default' : node.name.text,
          { local: node.name.text });
      } else if (isExportedNode(node)) {
        exportedNames.set('default', { fnNode: node });
      }
      scopeStack.push(rec.scope);
      node.parameters.forEach((p, idx) => {
        patternNames(p.name, (ident, key) => {
          const b = declare(ident, 'param', p, rec, p);
          if (!b) return;
          b.paramIndex = idx;
          b.paramKey = key;
          if (key && ENVELOPE_NAMES.has(String(key))) b.envelope = true;
          rec.params.push(b);
        });
      });
      if (node.body) walk(node.body, rec);
      scopeStack.pop();
      return;
    }
    if (ts.isVariableDeclaration(node)) {
      patternNames(node.name, (ident, key) => {
        const b = declare(ident, 'var', node, fn, node.initializer);
        if (!b) return;
        b.destructureKey = key;
        if (node.initializer) addWriter(b, node.initializer, fn, [], lineOf(node), '`' + b.name + '` = ' + brief(node.initializer));
      });
      if (node.initializer) walk(node.initializer, fn);
      return;
    }
    if (ts.isCatchClause(node)) {
      if (node.variableDeclaration) patternNames(node.variableDeclaration.name, (ident) => {
        const b = declare(ident, 'catch', node.variableDeclaration, fn, null);
        if (b) b.envelope = true;
      });
      walk(node.block, fn);
      return;
    }
    if (ts.isImportDeclaration(node)) {
      if (node.importClause) {
        const from = node.moduleSpecifier.text;
        const clause = node.importClause;
        const mark = (ident, asName) => {
          const b = declare(ident, 'import', clause, fn, null);
          if (!b) return;
          b.importFrom = from;
          b.importedAs = asName;
          importBindings.push(b);
        };
        if (clause.name) mark(clause.name, 'default');
        if (clause.namedBindings && ts.isNamespaceImport(clause.namedBindings)) {
          mark(clause.namedBindings.name, '*');
        } else if (clause.namedBindings) {
          for (const el of clause.namedBindings.elements) {
            mark(el.name, el.propertyName ? el.propertyName.getText(sf) : el.name.text);
          }
        }
      }
      return;
    }
    if (ts.isExportDeclaration(node)) {
      const specs = (node.exportClause && ts.isNamedExports(node.exportClause)) ? node.exportClause.elements : [];
      if (node.moduleSpecifier) {
        const from = node.moduleSpecifier.text;
        for (const el of specs) {
          reexportFrom.set(el.name.getText(sf), { from, exported: el.propertyName ? el.propertyName.getText(sf) : el.name.text });
        }
      } else {
        for (const el of specs) {
          exportedNames.set(el.name.getText(sf), { local: el.propertyName ? el.propertyName.getText(sf) : el.name.text });
        }
      }
      if (!node.exportClause && node.moduleSpecifier) starFrom.push(node.moduleSpecifier.text);
      if (node.exportClause && ts.isNamespaceExport && ts.isNamespaceExport(node.exportClause)) {
        exportedNames.set(node.exportClause.name.getText(sf), { local: 'default' });
      }
      return;
    }
    if (isExportedNode(node) && (ts.isVariableStatement(node) || ts.isClassDeclaration(node))) {
      if (ts.isVariableStatement(node)) {
        for (const dcl of node.declarationList.declarations) {
          patternNames(dcl.name, (ident) => { exportedNames.set(ident.text, { local: ident.text }); });
        }
      } else if (node.name) {
        const cb = declare(node.name, 'class', node, fn, null);
        if (cb) cb.isClassRecord = true;
        exportedNames.set(node.name.text, { local: node.name.text });
      }
    }
    if (ts.isClassDeclaration(node)) {
      const cls = { node, props: new Map(), state: null };
      for (const m of node.members) {
        if (!ts.isPropertyDeclaration(m) || !m.name) continue;
        const nm = m.name.getText(sf).replace(/^["']|["']$/g, '');
        const b = { name: 'this.' + nm, kind: 'class-prop', declNode: m, fn: null, initNode: m.initializer || null,
          writers: [], envelope: false };
        cls.props.set(nm, b);
        bindings.push(b);
        if (nm === 'state') cls.state = b;
      }
      classes.push(cls);
    }
    if (ts.isCallExpression(node)) callSites.push(node);
    if (ts.isBinaryExpression(node) && (node.operatorToken.kind === ts.SyntaxKind.EqualsToken
      || node.operatorToken.kind === ts.SyntaxKind.PlusEqualsToken)) assignments.push(node);
    if (ts.isReturnStatement(node) && fn && node.expression) fn.returns.push(node);
    ts.forEachChild(node, (c) => walk(c, fn));
  }
  walk(sf, null);
  // node.getStart() is shared by a node and its leftmost descendant (`a.b()` and `a.b().c()` both start at
  // `a`), so it cannot identify a node either; every node gets its own index here and the memo keys on that.
  for (let i = 0; i < nodes.length; i++) nodes[i].__cnxId = i;
  for (const n of nodes) {
    if (!ts.isIdentifier(n) || idBinding.has(n)) continue;
    const b = lookup(n.text, scopeFor(n));
    if (b) idBinding.set(n, b);
  }
  // React state: `const [v, setV] = useState(...)` and the bare-hook form `const v = useState(...)[0]`
  for (const b of bindings) {
    if (b.kind !== 'var' || !b.initNode || !ts.isCallExpression(b.initNode)) continue;
    const callee = b.initNode.expression;
    if (!(ts.isIdentifier(callee) && /^[Uu]se[A-Z]/.test(callee.text))) continue;
    b.hookCall = b.initNode;
    const decl = b.declNode;
    if (decl && decl.parent && ts.isArrayBindingPattern(decl.name) && decl.name.elements.length === 2) {
      const getter = idBinding.get(decl.name.elements[0].name);
      const setter = idBinding.get(decl.name.elements[1].name);
      if (getter && setter && /^set[A-Z]/.test(setter.name)) statePairs.push({ get: getter, set: setter });
    }
  }

  /* -------- taint values */

  function origin(kind, line, note, level) {
    return { kind, line, note, hops: [{ line, text: note }], boundaries: 0, level: level || 'value' };
  }
  function through(o, line, note, boundary) {
    if (!o) return null;
    if (o.hops[o.hops.length - 1].text === note) return o;
    const hops = o.hops.concat([{ line, text: note }]);
    return { kind: o.kind, line: o.line, note: o.note, level: o.level, boundaries: (o.boundaries || 0) + (boundary ? 1 : 0),
      hops: hops.length > 30 ? hops.slice(hops.length - 30) : hops };
  }

  function addWriter(b, exprNode, exprFn, path, line, note, extra) {
    b.writers.push({ expr: exprNode, fn: exprFn, path: path || [], extra: extra || [], line, note });
  }
  function isPrefix(short, long) {
    if (short.length > long.length) return false;
    for (let i = 0; i < short.length; i++) if (short[i] !== long[i]) return false;
    return true;
  }

  let truncated = 0;
  const memo = new Map();
  const active = new Set();
  // node.pos counts leading trivia and is shared with the enclosing node, so it cannot key a memo:
  // two shapes of one expression would answer for each other. Start offset plus kind is the node itself.
  function keyOf(node, fn, tail) { return (node.__cnxId === undefined ? 'u' + node.kind + '@' + node.getStart(sf) : node.__cnxId)
    + '|' + (fn ? fn.name || 'fn' + fn.node.getStart(sf) : 'root') + '|' + tail.join('.'); }

  function valueOf(node, fn, tail, d) {
    if (!node) return null; if (d > MAXD) { truncated++; return null; }
    const key = keyOf(node, fn, tail || []);
    if (memo.has(key)) return memo.get(key);
    if (active.has(key)) return null;
    active.add(key);
    let out = null;
    try { out = compute(node, fn, tail || [], d); }
    catch (e) { out = null; }
    active.delete(key);
    memo.set(key, out);
    return out;
  }
  function compute(node, fn, tail, d) {
    const n = unwrap(node);
    if (!n) return null;
    if (ts.isPropertyAccessExpression(n) || ts.isElementAccessExpression(n)) return memberOrigin(n, fn, tail, d);
    if (ts.isIdentifier(n)) return identifierOrigin(n, tail, d, fn);
    if (ts.isCallExpression(n)) {
      const o = callOrigin(n, fn, tail, d);
      if (!o && isStringifyCall(n)) {
        for (const a of (n.arguments || [])) {
          const av = valueOf(a, fn, tail, d + 1);
          if (av) return through(av, lineOf(n), 'turned back into text by ' + brief(n), false);
        }
      }
      return o;
    }
    if (ts.isNewExpression(n)) {
      const cls = ts.isIdentifier(n.expression) ? n.expression.text : '';
      const a = anyArg(n, fn, tail, d);
      if (/Error|Exception|DOMException/.test(cls)) {
        if (a) return through(a, lineOf(n), 'the words were put into a new ' + cls + '(...)', false);
        return null;
      }
      return a;
    }
    if (isThisNode(n)) {
      let cls = null;
      for (let cur = n; cur; cur = cur.parent) { const hit = classes.find((c) => c.node === cur); if (hit) { cls = hit; break; } }
      if (!cls || !tail.length) return null;
      const prop = cls.props.get(tail[0]);
      if (!prop) return null;
      return writersOrigin(prop, tail.slice(1), d);
    }
    if (ts.isObjectLiteralExpression(n)) return objectOrigin(n, fn, tail, d);
    if (ts.isArrayLiteralExpression(n)) {
      if (tail.length) return null;
      let o = null;
      for (const el of n.elements) { o = o || valueOf(el, fn, [], d + 1); if (o) break; }
      return o;
    }
    if (ts.isTemplateExpression(n)) {
      let o = null;
      for (const span of n.templateSpans) {
        const t = ts.isPropertyAccessExpression(span.expression) || ts.isElementAccessExpression(span.expression)
          ? memberOrigin(span.expression, fn, [], d + 1) : valueOf(span.expression, fn, [], d + 1);
        if (t) { o = through(t, lineOf(n), 'interpolated into ' + brief(n), false); break; }
        const env = valueOf(span.expression, fn, [], d + 1);
        if (env && env.level === 'envelope') {
          o = through({ kind: 'raw-body', line: env.line, note: env.note, level: 'prose',
            hops: [{ line: env.line, text: env.note }], boundaries: env.boundaries || 0 },
            lineOf(n), 'a response value was interpolated into text here, which is where its words become visible', false);
          break;
        }
      }
      return o;
    }
    if (ts.isBinaryExpression(n)) {
      const k = n.operatorToken.kind;
      if (k === ts.SyntaxKind.AmpersandAmpersandToken) return valueOf(n.right, fn, tail, d + 1);
      if (k === ts.SyntaxKind.BarBarToken || k === ts.SyntaxKind.QuestionQuestionToken || k === ts.SyntaxKind.PlusToken) {
        return valueOf(n.left, fn, tail, d + 1) || valueOf(n.right, fn, tail, d + 1);
      }
      return null;
    }
    if (ts.isConditionalExpression(n)) return valueOf(n.whenTrue, fn, tail, d + 1) || valueOf(n.whenFalse, fn, tail, d + 1);
    if (ts.isTypeOfExpression(n) || ts.isPrefixUnaryExpression(n)) return null;
    if (ts.isJsxElement(n) || ts.isJsxFragment(n) || ts.isJsxSelfClosingElement(n)) {
      let o = null;
      for (const c of jsxTextChildren(n)) { o = o || valueOf(c.expr, fn, [], d + 1); if (o) break; }
      return o;
    }
    if (ts.isFunctionLike(n)) {
      const inner = fnOf.get(n);
      return inner ? fnReturn(inner, tail, d + 1) : null;
    }
    if (ts.isStringLiteral(n) || ts.isNumericLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n)
      || ts.isKeyword(n) || n.kind === ts.SyntaxKind.NullKeyword || n.kind === ts.SyntaxKind.TrueKeyword
      || n.kind === ts.SyntaxKind.FalseKeyword || ts.isRegularExpressionLiteral(n) || isThisNode(n)) return null;
    if (ts.isAssertionExpression && ts.isAssertionExpression(n)) return valueOf(n.expression, fn, tail, d + 1);
    return null;
  }
  function anyArg(node, fn, tail, d) {
    let o = null;
    for (const a of (node.arguments || [])) { o = o || valueOf(a, fn, tail, d + 1); if (o) break; }
    return o;
  }
  function objectOrigin(lit, fn, tail, d) {
    if (!tail.length) {
      // The object itself is not the sentence: rendering a whole object reaches the screen as
      // `[object Object]`. Only the field that was handed the answer carries it, so a poisoned
      // `out.failureReason` must not condemn `out.status` - that narrowing is what keeps the
      // attribute-only controls clean while the same chain stays red.
      return null;
    }
    for (const p of lit.properties) {
      if (ts.isSpreadAssignment(p)) {
        const t = valueOf(p.expression, fn, tail, d + 1);
        if (t) return t;
        continue;
      }
      if (!ts.isPropertyAssignment(p) && !ts.isShorthandPropertyAssignment(p)) continue;
      if (propName(p) !== tail[0]) continue;
      const init = ts.isPropertyAssignment(p) ? p.initializer : p.name;
      return valueOf(init, fn, tail.slice(1), d + 1);
    }
    return null;                        // a field this object never carries is not carrying the answer
  }
  function memberOrigin(node, fn, tail, d) {
    const chain = [];
    let cur = node;
    while (ts.isPropertyAccessExpression(cur) || ts.isElementAccessExpression(cur)) {
      chain.unshift({ node: cur, name: propKey(cur) });
      cur = unwrap(cur.expression);
    }
    // leftmost first: the deepest read is decided by what its own base carries
    for (let i = 0; i < chain.length; i++) {
      const link = chain[i];
      const name = link.name;
      const baseNode = i === 0 ? cur : chain[i - 1].node;
      const rest = chain.slice(i + 1).map((l) => l.name).concat(tail);
      if (name === null) {                                 // `error[key]`
        const o = valueOf(baseNode, fn, [], d + 1);
        if (o) return through(o, lineOf(link.node), 'read off ' + brief(baseNode) + ' through a computed key', false);
        continue;
      }
      if (ALLOWED_FIELDS.includes(name)) {                 // an allowed machine field is never the answer
        if (!rest.length) return null;
        continue;
      }
      if (FORBIDDEN_ALWAYS.has(name) && isStaticExpr(baseNode, 0)) {
        continue;                                  // device wording that never had a network in it
      }
      if (FORBIDDEN_ALWAYS.has(name)) {
        return origin(exceptionish(name) ? 'exception' : (name === 'body_head' || name === 'raw' ? 'raw-body' : 'prose'),
          lineOf(link.node), 'upstream read ' + brief(link.node), 'prose');
      }
      if (NUMERIC_MEMBERS.has(name)) return null;      // a length is a number, never the answer's sentence
      const basePoison = valueOf(baseNode, fn, [], d + 1);
      // Only a value that IS the sentence passes its poison down a property read. An envelope (`body`,
      // a caught value) is an object holding fields: `cause.method` is a device fact, not the answer's
      // words, and treating every read off an envelope as prose is how a gate cries wolf.
      if (basePoison && basePoison.level === 'prose') return through(basePoison, lineOf(link.node), 'read further as ' + name + ' of it', false);
      if (basePoison && basePoison.level === 'envelope' && (FORBIDDEN_WITH_PROVENANCE.has(name) || EXCEPTION_FIELDS.has(name))) {
        return origin(exceptionish(name) ? 'exception' : 'raw-body', lineOf(link.node),
          'upstream read ' + brief(link.node) + ' off ' + brief(baseNode), 'prose');
      }
      if (FORBIDDEN_WITH_PROVENANCE.has(name) && envelopeOf(baseNode, fn, d)) {
        return origin(exceptionish(name) ? 'exception' : 'raw-body', lineOf(link.node),
          'upstream read ' + brief(link.node) + ' off ' + brief(baseNode), 'prose');
      }
    }
    const last = chain[chain.length - 1];
    const full = chain.map((l) => l.name);
    if (full.some((x) => x === null)) return valueOf(cur, fn, tail, d + 1);
    return valueOf(cur, fn, full.concat(tail), d + 1);
  }
  function exceptionish(name) { return EXCEPTION_FIELDS.has(name); }
  // `detail` is a forbidden field name, and it is also the name of an i18n label ("详情"/"Details") in a
  // copy table that never sees the network. The name alone cannot tell those apart; the *content* can.
  // So a forbidden read is excused only when everything the base can hold is a literal this device wrote.
  // A response envelope, an unknown function, or a table with one non-literal in it is not excused.
  // `detail` is a forbidden field name, and it is also the name of an i18n label ("详情" / "Details") in a
  // copy table that never sees the network. A field name cannot tell those apart; the content can. So a
  // forbidden read is excused only when EVERY value the base can hold is a literal this device wrote -
  // one non-literal anywhere, an unresolved function, or a parameter and the excuse is refused.
  function isStaticExpr(node, d) {
    if (d > 12) return false;
    const n = unwrap(node);
    if (!n) return false;
    if (ts.isStringLiteral(n) || ts.isNoSubstitutionTemplateLiteral(n) || ts.isNumericLiteral(n)) return true;
    if (n.kind === ts.SyntaxKind.NullKeyword || n.kind === ts.SyntaxKind.TrueKeyword || n.kind === ts.SyntaxKind.FalseKeyword) return true;
    if (ts.isTemplateExpression(n)) { for (const h of n.templateSpans) if (!isStaticExpr(h.expression, d + 1)) return false; return true; }
    if (ts.isConditionalExpression(n)) return isStaticExpr(n.whenTrue, d + 1) && isStaticExpr(n.whenFalse, d + 1);
    if (ts.isBinaryExpression(n) && (n.operatorToken.kind === ts.SyntaxKind.BarBarToken
      || n.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken || n.operatorToken.kind === ts.SyntaxKind.PlusToken)) {
      return isStaticExpr(n.left, d + 1) && isStaticExpr(n.right, d + 1);
    }
    if (ts.isObjectLiteralExpression(n)) {
      for (const p of n.properties) {
        if (ts.isPropertyAssignment(p)) { if (!isStaticExpr(p.initializer, d + 1)) return false; }
        else return false;                                 // shorthand or spread: content not proven here
      }
      return true;
    }
    if (ts.isArrayLiteralExpression(n)) { for (const el of n.elements) if (!isStaticExpr(el, d + 1)) return false; return true; }
    if (ts.isCallExpression(n)) {
      const f = resolveCallee(n);
      if (!f || !f.f || !f.f.returns.length) return false;
      for (const r of f.f.returns) if (!isStaticExpr(r.expression, d + 1)) return false;
      return true;
    }
    if (ts.isPropertyAccessExpression(n) || ts.isElementAccessExpression(n)) {
      // a field of a table that is static all the way down is static whatever the field is called
      return isStaticExpr(rootOf(n), d + 1);
    }
    if (ts.isIdentifier(n)) {
      const b = idBinding.get(n) || lookup(n.text, scopeFor(n));
      if (!b || b.kind === 'param' || b.kind === 'catch') return false;
      if (!b.writers.length) return false;
      for (const w of b.writers) {
        if (w.path.length || w.extra.length) return false;
        if (!isStaticExpr(w.expr, d + 1)) return false;
      }
      return true;
    }
    return false;
  }
  function identifierOrigin(ident, tail, d, fn) {
    const b = idBinding.get(ident) || lookup(ident.text, scopeFor(ident));
    if (b && b.kind === 'import') {
      if (tail.length && b.importedAs === '*' && hooks && hooks.importOrigin) {
        const o = hooks.importOrigin(b, tail, d);
        return o ? through(o, lineOf(ident), brief(ident) + '.' + tail.join('.') + ' came in from ' + b.importFrom, false) : null;
      }
      if (!tail.length && hooks && hooks.importOrigin) {
        const o = hooks.importOrigin(b, [], d);
        if (o) return through(o, lineOf(ident), 'the imported value ' + b.name + ' (from ' + b.importFrom + ')', false);
        if (b.envelope) return origin('raw-body', lineOf(ident), 'the imported response value `' + b.name + '` itself reached the DOM', 'envelope');
        return null;
      }
      if (tail.length && hooks && hooks.importOrigin) {
        const o = hooks.importOrigin(b, tail, d);
        if (o) return through(o, lineOf(ident), 'the imported value ' + b.name + ' (from ' + b.importFrom + ')', false);
      }
      if (b.envelope && EXCEPTION_FIELDS.has(tail[0])) {
        return origin('exception', lineOf(ident), 'the imported exception field `' + b.name + '.' + tail[0] + '`');
      }
      return null;
    }
    if (!b) {
      if (!ENVELOPE_NAMES.has(ident.text)) return null;
      if (tail.length) return null;
      return origin('raw-body', lineOf(ident), 'the response value `' + ident.text + '` itself reached the DOM', 'envelope');
    }
    if (tail.length) {
      const o = writersOrigin(b, tail, d);
      if (o) return o;
      if (b.envelope && EXCEPTION_FIELDS.has(tail[0])) {
        return origin('exception', lineOf(b.declNode), 'the exception `' + b.name + '.' + tail[0] + '`');
      }
      if (b.envelope && tail.length === 1 && FORBIDDEN_ALWAYS.has(tail[0])) {
        return origin('prose', lineOf(b.declNode), 'the response field `' + b.name + '.' + tail[0] + '`');
      }
      return null;
    }
    if (b.kind === 'catch') return origin('exception', lineOf(b.declNode), 'the caught value `' + b.name + '` reached the DOM', 'envelope');
    const o = writersOrigin(b, [], d);
    if (o) return o;
    if (b.proseBody) return origin('raw-body', lineOf(b.declNode),
      'the answer\'s own body held in `' + b.name + '` reached the DOM as text', 'prose');
    if (b.envelope) return origin('raw-body', lineOf(b.declNode), 'the response value `' + b.name + '` itself reached the DOM', 'envelope');
    return null;
  }
  function writersOrigin(b, tail, d) {
    let o = null;
    for (const w of b.writers) {
      if (!isPrefix(w.path, tail)) continue;
      const suffix = w.extra.concat(tail.slice(w.path.length));
      const t = valueOf(w.expr, w.fn, suffix, d + 1);
      if (t) {
        o = through(t, w.line, w.note, false);
        if (o.hops.length >= 3 && tail.length) break;
      }
    }
    if (!o && b.kind === 'param' && b.fn) o = paramFromCallSites(b, tail, d);
    if (!o && b.kind === 'fn' && b.initNode) {                 // the name of a function, used as a value
      const inner = fnOf.get(unwrap(b.initNode));
      if (inner) o = fnReturn(inner, tail, d);
    }
    return o;
  }
  function paramFromCallSites(b, tail, d) {
    const f = b.fn;
    let o = null;
    if (hooks && hooks.inboundArgs && f.name) {
      for (const inc of hooks.inboundArgs(f.name)) {
        const arg = (inc.call.arguments || [])[b.paramIndex];
        if (!arg) continue;
        if (crossings >= MAX_CROSSINGS) { crossingCuts++; continue; }
        crossings++;
        let t = null;
        try { t = inc.answer(arg, tail, d); } finally { crossings--; }
        if (t) {
          const marked = through(t, inc.line, 'what ' + inc.from + ':' + inc.line + ' passed in as `' + b.name + '`', true);
          if (!o || marked.hops.length < o.hops.length) o = marked;
        }
      }
    }
    for (const cs of callSites) {
      const target = resolveCallee(cs);
      if (!target || target.f !== f) continue;
      const arg = (cs.arguments || [])[b.paramIndex];
      if (!arg) continue;
      const t = valueOf(arg, fnFor(cs), tail, d + 1);
      if (t) { o = through(t, lineOf(cs), brief(arg) + ' was handed to ' + (f.name || 'the helper') + '() as `' + b.name + '`', true); if (o.hops.length >= 4) break; }
    }
    return o;
  }
  function resolveCallee(call) {
    const callee = unwrap(call.expression);
    if (ts.isIdentifier(callee)) {
      const b = idBinding.get(callee) || lookup(callee.text, scopeFor(callee));
      if (b && b.kind === 'import' && b.importedAs !== '*' && hooks && hooks.calleeOrigin) {
        const target = hooks.calleeOrigin(b);
        if (target) return { crossName: b.importedAs, cross: target, via: b.name + ' imported from ' + b.importFrom };
      }
      if (b && b.initNode) { const direct = fnOf.get(unwrap(b.initNode)); if (direct) return { f: direct, viaParamOf: b }; }
      for (const f of fnOf.values()) if (f.name === callee.text) return { f };
      if (b && b.kind === 'param') return { fnParam: b };
      return null;
    }
    if (ts.isPropertyAccessExpression(callee)) {
      const obj = unwrap(callee.expression);
      if (ts.isIdentifier(obj) && hooks && hooks.calleeNamedIn) {
        const b = idBinding.get(obj) || lookup(obj.text, scopeFor(obj));
        if (b && b.kind === 'import' && b.importedAs === '*') {
          const target = hooks.calleeNamedIn(b, callee.name.text);
          if (target) return { cross: target, via: obj.text + '.' + callee.name.text + ' imported from ' + b.importFrom };
        }
      }
      for (const f of fnOf.values()) if (f.name === callee.name.text) return { f, method: callee.name.text };
    }
    return null;
  }
  function fnReturn(f, tail, d) {
    let o = null;
    let best = 99;
    for (const r of f.returns) {
      const t = valueOf(r.expression, f, tail, d + 1);
      if (t && t.hops.length < best) { best = t.hops.length; o = through(t, lineOf(r), (f.name || 'the helper') + '() returns ' + brief(r.expression), true); }
    }
    return o;
  }
  function callOrigin(call, fn, tail, d) {
    const target = resolveCallee(call);
    const recvCallee = unwrap(call.expression);
    if (target && target.f) {
      const o = fnReturn(target.f, tail, d);
      if (o) return o;
      return null;
    }
    if (target && target.cross) {
      // the callee lives in another file: its return is that file's answer, not an opaque value
      if (crossings >= MAX_CROSSINGS) { crossingCuts++; return null; }
      crossings++;
      let o = null;
      try { o = target.cross(tail, d); } finally { crossings--; }
      return o ? through(o, lineOf(call), 'came back from ' + target.via, true) : null;
    }
    if (target && target.fnParam) {                       // `props.render(x)` - a callback handed in
      const o = callbackReturnForParam(target.fnParam, tail, d);
      if (o) return o;
    }
    if (ts.isPropertyAccessExpression(recvCallee) && PASS_THROUGH.has(recvCallee.name.text)) {
      const recv = valueOf(recvCallee.expression, fn, tail, d + 1);
      if (recv) return through(recv, lineOf(call), '.' + recvCallee.name.text + '(...) passes it on', false);
      for (const a of (call.arguments || [])) {
        const inner = ts.isArrowFunction(a) || ts.isFunctionExpression(a) ? fnOf.get(a) : null;
        if (inner) { const o = fnReturn(inner, tail, d); if (o) return through(o, lineOf(call), (recvCallee.name.text) + '(...) hands back what its callback returned', true); }
      }
      return null;
    }
    if (ts.isPropertyAccessExpression(recvCallee) && /^(json|text|blob|arrayBuffer|data|body|formData)$/.test(recvCallee.name.text)) {
      return null;                                        // the envelope itself, not its words yet
    }
    // JSON.parse and res.json() consume text and hand back a structure: the answer's words stop being words
    // there and become fields, which are then judged one by one by name. Letting prose sail straight through
    // them is what made every screen that renders any server field look like a leak.
    if (isStructureProducing(call)) {
      for (const a of (call.arguments || [])) {
        const t = valueOf(a, fn, [], d + 1);
        if (t) return through({ kind: t.kind, line: t.line, note: t.note, level: 'envelope',
          hops: [{ line: t.line, text: t.note }], boundaries: (t.boundaries || 0) },
          lineOf(call), 'parsed into fields by ' + brief(call) + ', so what is left to read is fields', false);
      }
      return null;
    }
    // an unresolvable function: what went in can come out
    let o = null;
    const calleeName = ts.isIdentifier(recvCallee) ? recvCallee.text
      : (ts.isPropertyAccessExpression(recvCallee) ? recvCallee.name.text : null);
    const builtin = calleeName && BUILTIN_FUNCS.has(calleeName);
    for (const a of (call.arguments || [])) {
      const t = valueOf(a, fn, tail, d + 1);
      if (!t) continue;
      // JSON.stringify(answer) or String(answer) is where a parsed structure becomes the answer's text again:
      // that is the words on screen, not the object.
      if (isStringifyCall(call) && t.level === 'envelope') {
        return through({ kind: 'raw-body', line: t.line, note: t.note, level: 'prose',
          hops: [{ line: t.line, text: t.note }], boundaries: t.boundaries || 0 },
          lineOf(call), 'turned back into text by ' + brief(call), false);
      }
      o = through(t, lineOf(call), 'passed through ' + brief(call.expression) + '()', builtin ? false : true);
      break;
    }
    return o;
  }
  function callbackReturnForParam(b, tail, d) {
    const f = b.fn;
    let o = null;
    for (const cs of callSites) {
      const target = resolveCallee(cs);
      if (!target || target.f !== f) continue;
      const arg = (cs.arguments || [])[b.paramIndex];
      const inner = arg && (ts.isArrowFunction(arg) || ts.isFunctionExpression(arg)) ? fnOf.get(arg) : null;
      if (inner) { const t = fnReturn(inner, tail, d); if (t) { o = t; break; } }
    }
    return o;
  }

  /* -------- envelope (provenance that something carries the answer, without its words being read yet) */

  const STRINGIFY_CALLEES = new Set(['String', 'JSON']);
  function isStructureProducing(node) {
    const n = unwrap(node);
    if (!ts.isCallExpression(n)) return false;
    const c = unwrap(n.expression);
    if (ts.isPropertyAccessExpression(c) && /^(parse|json)$/i.test(c.name.text)) return true;   // JSON.parse, res.json()
    return false;
  }
  function isStringifyCall(node) {
    const n = unwrap(node);
    if (!ts.isCallExpression(n)) return false;
    const c = unwrap(n.expression);
    if (ts.isIdentifier(c) && STRINGIFY_CALLEES.has(c.text)) return true;                 // String(x)
    if (ts.isPropertyAccessExpression(c) && c.name.text === 'stringify') return true;      // JSON.stringify(x)
    if (ts.isPropertyAccessExpression(c) && /^(toString|toLocaleString|join)$/.test(c.name.text)) return true;
    return false;
  }
  // a value that IS the answer's words, not merely an answer
  function proseSourceOf(node, fn, d) {
    const n = unwrap(node);
    if (!n || d > 8) return false;
    if (ts.isAwaitExpression(n)) return proseSourceOf(n.expression, fn, d + 1);
    if (ts.isCallExpression(n)) {
      const c = unwrap(n.expression);
      if (ts.isPropertyAccessExpression(c) && /^(text|body)$/i.test(c.name.text)) return true;   // res.text()
      if (isStringifyCall(n)) {
        for (const a of (n.arguments || [])) if (proseSourceOf(a, fn, d + 1) || (envelopeOf(a, fn, d + 1) && true)) return true;
        return false;
      }
      return false;
    }
    if (ts.isPropertyAccessExpression(n)) {
      // `body_head` and `raw` name the body by themselves; `body` and `text` only do so when what they are
      // read off is itself an answer. A screen's own `banner.text`, written from a local literal, is that
      // screen's wording, and calling it the server's sentence is exactly the false red that makes a gate
      // ignored.
      if (/^(body_head|raw|raw_body)$/i.test(n.name.text)) return true;
      if (/^(body|text)$/i.test(n.name.text)) {
        const base = unwrap(n.expression);
        const bb = ts.isIdentifier(base) ? (idBinding.get(base) || lookup(base.text, scopeFor(base))) : null;
        return proseSourceOf(n.expression, fn, d + 1) || !!(bb && (bb.proseBody || bb.envelope)) || !!envelopeOf(base, fn, d + 1);
      }
      return proseSourceOf(n.expression, fn, d + 1);
    }
    if (ts.isConditionalExpression(n)) return proseSourceOf(n.whenTrue, fn, d + 1) || proseSourceOf(n.whenFalse, fn, d + 1);
    if (ts.isBinaryExpression(n) && (n.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken
      || n.operatorToken.kind === ts.SyntaxKind.BarBarToken)) return proseSourceOf(n.left, fn, d + 1);
    if (ts.isTemplateExpression(n)) { for (const h of n.templateSpans) if (proseSourceOf(h.expression, fn, d + 1)) return true; return false; }
    if (ts.isIdentifier(n)) {
      const b = idBinding.get(n) || lookup(n.text, scopeFor(n));
      if (!b) return ENVELOPE_NAMES.has(n.text) ? false : false;
      if (b.proseBody) return true;
      if (b.kind === 'var' && b.initNode) return proseSourceOf(b.initNode, b.fn, d + 1);
      if (b.kind === 'param') return false;                       // a parameter's shape is decided at the call
      return false;
    }
    return false;
  }
  function envelopeOf(node, fn, d) {
    const n = unwrap(node);
    if (!n) return null;
    if (ts.isIdentifier(n)) {
      const b = idBinding.get(n) || lookup(n.text, scopeFor(n));
      if (!b) return ENVELOPE_NAMES.has(n.text) ? 'named ' + n.text : null;
      if (b.envelope) return 'named ' + b.name;
      if (b.kind === 'var' && b.initNode) return envelopeOf(b.initNode, b.fn, d + 1);
      return null;
    }
    if (ts.isCallExpression(n)) {
      const callee = unwrap(n.expression);
      if (ts.isPropertyAccessExpression(callee) && /^(json|text|blob|arrayBuffer|data|body)$/.test(callee.name.text)) return 'the answer read by ' + brief(n);
      if (ts.isIdentifier(callee) && /^(fetch|request)$/.test(callee.text)) return 'an HTTP answer';
      if (ts.isPropertyAccessExpression(callee) && /^(catch|then|finally)$/.test(callee.name.text)) return envelopeOf(callee.expression, fn, d + 1);
      return null;
    }
    if (ts.isNewExpression(n)) {
      const cls = ts.isIdentifier(n.expression) ? n.expression.text : '';
      return /Error|Exception|DOMException/.test(cls) ? 'an exception object' : null;
    }
    if (ts.isPropertyAccessExpression(n) || ts.isElementAccessExpression(n)) {
      const name = propKey(n);
      const up = envelopeOf(n.expression, fn, d + 1);
      if (up && (name === null || ENVELOPE_READS.has(name) || ENVELOPE_NAMES.has(name))) return up;
      if (name && ENVELOPE_READS.has(name)) return 'the ' + name + ' of ' + brief(n.expression);
      return up;
    }
    if (ts.isConditionalExpression(n)) return envelopeOf(n.whenTrue, fn, d + 1) || envelopeOf(n.whenFalse, fn, d + 1);
    if (ts.isBinaryExpression(n) && (n.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken || n.operatorToken.kind === ts.SyntaxKind.BarBarToken)) return envelopeOf(n.left, fn, d + 1);
    return null;
  }

  /* -------- fixpoint */

  function settle() {
    for (let iter = 0; iter < 1; iter++) {   // writers are a function of the text; query-time resolution + the cycle guard settle the rest
      memo.clear(); active.clear();
      for (const b of bindings) b.writers.length = 0;
      for (const b of bindings) {
        if (b.kind === 'var' && b.initNode) {
          const init = unwrap(b.initNode);
          // `const text = await response.text()` carries the body AS WORDS, and printing it is what Q64
          // forbids. A parsed answer (`res.json()`, `JSON.parse`) is a structure instead: its fields are judged
          // by their own names, and the object is not the answer's words until something turns it back to text.
          // a parsed answer (`res.json()`, JSON.parse) is NOT marked as carrying the body: marking it did
          // catch `{JSON.stringify(body)}` but also let one shared `String(field)` helper poison every
          // screen that used it (14 cells on the live tree from one union of arguments). A structure is
          // judged field by field, by name; the body-as-words case above is the one that is judged whole.
          if (!b.proseBody && proseSourceOf(init, b.fn, 0)) {
            b.proseBody = true;
            b.envelope = true;
          }
          if (b.destructureKey) {
            // `const { error } = this.state` - the binding IS that slot, so the slot is resolved as part of
            // the value, not as a sibling of it.
            addWriter(b, init, b.fn, [], lineOf(b.declNode), '`' + b.name + '` destructured from ' + brief(init), [String(b.destructureKey)]);
          } else addWriter(b, init, b.fn, [], lineOf(b.declNode), '`' + b.name + '` = ' + brief(init));
        }
      }
      for (const a of assignments) {
        const lhs = a.left;
        if (ts.isPropertyAccessExpression(lhs) || ts.isElementAccessExpression(lhs)) {
          const base = unwrap(lhs.expression);
          const b = ts.isIdentifier(base) ? (idBinding.get(base) || lookup(base.text, scopeFor(base))) : null;
          if (!b) continue;
          const name = propKey(lhs);
          if (name === null) continue;
          addWriter(b, a.right, fnFor(a) || b.fn, [name], lineOf(a), '`' + b.name + '.' + name + '` = ' + brief(a.right));
        } else if (ts.isIdentifier(lhs)) {
          const b = idBinding.get(lhs) || lookup(lhs.text, scopeFor(lhs));
          if (b) addWriter(b, a.right, fnFor(a), [], lineOf(a), '`' + b.name + '` reassigned to ' + brief(a.right));
        }
      }
      for (const cls of classes) {
        if (!cls.state) continue;
        for (const cs of callSites) {
          const callee = unwrap(cs.expression);
          if (!ts.isPropertyAccessExpression(callee) || callee.name.text !== 'setState') continue;
          if (!isThisNode(callee.expression)) continue;
          let owns = false;
          for (let cur = cs.parent; cur; cur = cur.parent) if (cur === cls.node) { owns = true; break; }
          if (!owns) continue;
          const arg = unwrap(cs.arguments && cs.arguments[0]);
          if (!arg) continue;
          addWriter(cls.state, arg, fnFor(cs), [], lineOf(cs), 'class state written by this.setState(...)');
        }
        for (const m of cls.node.members) {
          if (!ts.isMethodDeclaration(m) || !m.name) continue;
          const nm = m.name.getText(sf);
          const f = fnOf.get(m);
          if (!f) continue;
          if (nm === 'getDerivedStateFromError') {
            f.params.forEach((p) => { p.envelope = true; });          // React hands the thrown value in
            for (const r of f.returns) addWriter(cls.state, r.expression, f, [], lineOf(r), 'getDerivedStateFromError() returned');
          }
          if (nm === 'componentDidCatch') f.params.forEach((p) => { p.envelope = true; });   // error + ErrorInfo
        }
      }
      for (const pair of statePairs) {
        for (const cs of callSites) {
          if (!ts.isIdentifier(cs.expression) || cs.expression.text !== pair.set.name) continue;
          const arg = unwrap(cs.arguments && cs.arguments[0]);
          if (!arg) continue;
          let expr = arg, efn = fnFor(cs);
          if (ts.isArrowFunction(arg) || ts.isFunctionExpression(arg)) {
            const inner = fnOf.get(arg);
            if (!inner || !inner.returns.length) continue;
            expr = inner.returns[0].expression;
            efn = inner;
          }
          addWriter(pair.get, expr, efn, [], lineOf(cs), 'state `' + pair.get.name + '` written by ' + brief(cs.expression) + '(...)');
        }
      }
    }
  }

  /* -------- sinks */

  const ATTR_SLOT = /^(data|aria)-/i;
  /* The six fields Q64=1 whitelists as this device's own observables. An attribution label inside a
     fold is recognised only through `data-cnx-field` naming one of them -- the contract name the
     anchor convention already carries (Q70) -- never through a class name, a test id or a comment. */
  const ANCHOR_FIELDS = ['http_status', 'content_type', 'body_bytes', 'response_received', 'elapsed_ms', 'request_id'];

  function jsxAttrsOf(element) {
    return element.openingElement.attributes.properties.filter((p) => ts.isJsxAttribute(p));
  }
  /* The last member a read takes, through an optional chain or a bracket: `a?.b`, `a["b"]`, `(a || b).c`. */
  function memberNameOf(node) {
    const u = unwrap(node);
    if (!u) return null;
    if (ts.isPropertyAccessExpression(u)) return u.name.text;
    if (ts.isElementAccessExpression(u) && u.argumentExpression
        && (ts.isStringLiteral(u.argumentExpression) || ts.isNoSubstitutionTemplateLiteral(u.argumentExpression))) {
      return u.argumentExpression.text;
    }
    if (ts.isBinaryExpression(u)
        && (u.operatorToken.kind === ts.SyntaxKind.BarBarToken || u.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken)) {
      return memberNameOf(u.right) || memberNameOf(u.left);
    }
    if (ts.isParenthesizedExpression(u)) return memberNameOf(u.expression);
    return null;
  }
  function anchorInside(node) {
    const found = [];
    const walk = (n) => {
      if (ts.isJsxAttribute(n) && n.name && n.name.getText(sf) === 'data-cnx-field' && n.initializer) {
        let value = n.initializer;
        if (ts.isJsxExpression(value)) value = value.expression;
        if ((ts.isStringLiteral(value) || ts.isNoSubstitutionTemplateLiteral(value))
            && ANCHOR_FIELDS.indexOf(value.text) >= 0) {
          found.push({ field: value.text, line: lineOf(n) });
        }
      }
      ts.forEachChild(n, walk);
    };
    walk(node);
    return found[0] || null;
  }
  /* ORD-0348 (Q67=1 as ruled by Q75): a server sentence that is *attributed* and *folded* is compliant
     attribution, and the ruler has to be able to tell that apart from the same sentence on the face of
     the screen. The decision is read off the rendered structure: the nearest enclosing fold element --
     a `<details>` or anything carrying `data-cnx-fold` -- decides, and it exonerates only when that
     same container holds an anchor naming which measured field spoke. No fold, or a fold whose label
     was removed, is a hit. The nearest fold decides on purpose: letting an outer container vouch for an
     inner one would be a loophole with a shape a lane could grow. */
  function foldContext(node) {
    for (let cur = node.parent; cur; cur = cur.parent) {
      if (!ts.isJsxElement(cur)) continue;
      const tag = cur.openingElement.tagName.getText(sf);
      const isFold = tag === 'details'
        || jsxAttrsOf(cur).some((a) => a.name && a.name.getText(sf) === 'data-cnx-fold');
      if (!isFold) continue;
      const anchor = anchorInside(cur);
      return anchor ? { container: tag, container_line: lineOf(cur.openingElement),
                        anchor_field: anchor.field, anchor_line: anchor.line }
                    : { blocked: 'fold_without_attribution_anchor', container: tag,
                        container_line: lineOf(cur.openingElement) };
    }
    return null;
  }

  function jsxTextChildren(node) {
    const out = [];
    const kids = ts.isJsxElement(node) ? node.children : (ts.isJsxFragment(node) ? node.children : []);
    for (const c of kids) {
      if (ts.isJsxExpression(c) && c.expression) out.push({ node: c, expr: c.expression });
      else if (ts.isJsxElement(c) || ts.isJsxFragment(c)) for (const g of jsxTextChildren(c)) out.push(g);
    }
    return out;
  }
  function sinkList() {
    const out = [];
    for (const n of nodes) {
      if (ts.isJsxExpression(n) && n.expression && n.parent && (ts.isJsxElement(n.parent) || ts.isJsxFragment(n.parent))) {
        out.push({ kind: 'jsx-text', node: n, expr: n.expression });
      }
      if (ts.isJsxAttribute(n) && n.name && n.name.getText(sf) === 'dangerouslySetInnerHTML') {
        out.push({ kind: 'inner-html', node: n, expr: n.initializer });
      }
      /* ORD-0354 (Q71): `data-*` and `aria-*` are DOM. A sentence that never reaches the eye still
         reaches the accessibility tree, a gate's getAttribute, and anyone reading the element --
         the commander replanted the exact violation ORD-0339 removed
         (`data-error-message={sealedDemoDetail?.message ?? ""}`, probe commit
         7c0d21b7cbe968378d964e2dde856274fca7da86) and r6 reported nothing, so this slot had no
         whole-tree ruler standing over it. A literal string in the attribute is this file's own
         wording and is not asked about. */
      if (ts.isJsxAttribute(n) && n.name && ATTR_SLOT.test(n.name.getText(sf)) && n.initializer
          && !ts.isStringLiteral(n.initializer) && !ts.isNoSubstitutionTemplateLiteral(n.initializer)) {
        out.push({ kind: 'dom-attribute', node: n, expr: n.initializer });
      }
      if (ts.isBinaryExpression(n) && n.operatorToken.kind === ts.SyntaxKind.EqualsToken && ts.isPropertyAccessExpression(n.left)) {
        const name = n.left.name.text;
        if (name === 'textContent' || name === 'innerText') out.push({ kind: 'dom-text', node: n, expr: n.right });
        if (name === 'innerHTML') out.push({ kind: 'inner-html', node: n, expr: n.right });
      }
    }
    return out;
  }

  function ruleFor(o, sinkKind) {
    if (sinkKind === 'dom-text') return 'RAW_TEXT_INTERPOLATION';
    if ((o.boundaries || 0) > 0) return 'UPSTREAM_TEXT_VIA_HELPER_TO_DOM';
    if (o.kind === 'exception') return 'UPSTREAM_EXCEPTION_TO_DOM';
    if (o.kind === 'raw-body') return 'RAW_BODY_TO_DOM';
    return 'UPSTREAM_READ_DIRECT';
  }
  function run() {
    settle();
    settledOnce = true;
    memo.clear(); active.clear();
    const hits = [];
    for (const s of sinkList()) {
      let expr = s.expr ? unwrap(s.expr) : null;
      if (!expr) continue;
      const fn = fnFor(s.node);
      if (s.kind === 'inner-html') {
        let inner = expr;
        if (ts.isJsxExpression(inner)) inner = unwrap(inner.expression);
        if (ts.isObjectLiteralExpression(inner)) {
          for (const p of inner.properties) if (ts.isPropertyAssignment(p) && propName(p) === '__html') inner = unwrap(p.initializer);
        }
        const o = valueOf(inner, fn, [], 0);
        if (o) { hits.push(mkHit('DANGEROUS_HTML', s, o)); continue; }
        // Writing markup is only an exposure question when something other than this file's own words
        // goes in: `container.innerHTML = ""` is a teardown, not a leak, and a gate that flags it teaches
        // people to ignore the gate.
        if (!isStaticExpr(inner, 0)) {
          hits.push(mkHit('DANGEROUS_HTML', s, origin('raw-html', lineOf(s.node),
            'a value this file cannot prove is its own wording was handed to innerHTML / dangerouslySetInnerHTML')));
        }
        continue;
      }
      // ORD-0354: the attribute slot. Narrower than the text rule on purpose -- a number, an enum or a
      // contract id in `data-*` is what Q70 *asks* for (`data-cnx-field="http_status"` with the raw
      // reading beside it), so only a value this file cannot tell apart from the answer's own wording
      // fires here. `??` is peeled because the planted violation is written with it.
      if (s.kind === 'dom-attribute') {
        let inner = s.expr;
        if (ts.isJsxExpression(inner)) inner = unwrap(inner.expression);
        const queue = inner ? [inner] : [];
        const slots = [];
        for (let step = 0; step < queue.length && step < 32; step++) {
          const u = unwrap(queue[step]);
          if (!u) continue;
          if (ts.isBinaryExpression(u) && u.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken) {
            queue.push(u.left, u.right); continue;
          }
          if (ts.isParenthesizedExpression(u)) { queue.push(u.expression); continue; }
          if (ts.isConditionalExpression(u)) { queue.push(u.whenTrue, u.whenFalse); continue; }
          if (ts.isStringLiteral(u) || ts.isNoSubstitutionTemplateLiteral(u)) continue;
          slots.push(u);
        }
        for (const e of slots) {
          const o = valueOf(e, fn, [], 0);
          if (o && o.level !== 'envelope') { hits.push(mkHit('UPSTREAM_PROSE_TO_ATTRIBUTE_SLOT', s, o)); continue; }
          /* The second way in, and the one the planted probe needs. A value can reach an attribute with no
             provenance this file can follow at all -- `sealedDemoDetail?.message` is written in
             V8Experience.tsx and printed in JourneyTrialSetup.tsx, across a component-prop boundary the
             module graph does not model. So the slot is also guarded by the field's own name: Q64 lists six
             observables a screen may carry, and this codebase spells a device-composed label none of
             `message` / `stack` / `detail` / `trace` / `raw` / `body_head` -- a member with one of those
             names, dropped into `data-*` or `aria-*`, is the answer's or the exception's own sentence by
             naming, whether or not this file can see where it came from. */
          const name = memberNameOf(e);
          if (name && (FORBIDDEN_ALWAYS.has(name) || ATTRIBUTE_NAMED_PROSE.has(name))) {
            hits.push(mkHit('UPSTREAM_PROSE_TO_ATTRIBUTE_SLOT', s, origin('named-prose-member', lineOf(e),
              'attribute received the member `' + name + '`, a name this project only ever spells for the'
              + ' answer\'s or the exception\'s own words', 'prose')));
          }
        }
        continue;
      }
      // A guard renders either markup or nothing: `{copy && (...)}` and `{a ? <X/> : <Y/>}` put no prose of
      // their own on screen, and the text inside them is already a sink of its own. Peel the guard and drop
      // the markup/wording leaves, so only a value that is itself handed to the DOM is asked about.
      const rendered = [];
      const queue = [expr];
      for (let step = 0; step < queue.length && step < 64; step++) {
        const u = unwrap(queue[step]);
        if (!u) continue;
        if (ts.isBinaryExpression(u) && u.operatorToken.kind === ts.SyntaxKind.AmpersandAmpersandToken) { queue.push(u.right); continue; }
        if (ts.isConditionalExpression(u)) { queue.push(u.whenTrue, u.whenFalse); continue; }
        if (ts.isParenthesizedExpression(u)) { queue.push(u.expression); continue; }
        if (ts.isJsxElement(u) || ts.isJsxFragment(u) || ts.isJsxSelfClosingElement(u) || ts.isJsxText(u)
          || ts.isStringLiteral(u) || ts.isNoSubstitutionTemplateLiteral(u)) continue;
        rendered.push(u);
      }
      for (const e of rendered) {
        let o = valueOf(e, fn, [], 0);
        // an object rendered as a child is `[object Object]`: structure, not the answer's words. It becomes
        // words only through String() / JSON.stringify / a template, and those promote it above.
        if (o && o.level === 'envelope' && o.kind !== 'exception') continue;
        if (!o) continue;
        hits.push(mkHit(ruleFor(o, s.kind), s, o));
      }
    }
    const m = new Map();
    /* Deduplication used to be `line|rule`, which quietly made two different renders on one source line
     * one cell - and a cell that disappears because of where it sits is the same defect the identity
     * string below exists to remove. The key now carries the sink's shape as well. */
    for (const h of hits) {
      const k = h.line + '|' + h.rule + '|' + ((h.structural || {}).sink_shape || h.sink);
      if (!m.has(k)) m.set(k, h);
    }
    /* The exception, applied and recorded. A hit that is exonerated does not disappear quietly: it moves
       to `attributed_in_fold` with the container and the anchor that vouched for it, so a reader can
       check the ruling against the file instead of trusting the ruler. */
    const kept = [], folded = [], foldless = [];
    for (const h of m.values()) {
      const context = h.sink === 'jsx-text' ? foldContext(h._node) : null;
      if (context && context.anchor_field) {
        folded.push({ file_line: h.line, rule: h.rule, sink: h.sink, snippet: h.snippet,
          taint_chain: h.taint_chain, fold_container: context.container,
          fold_container_line: context.container_line, attribution_anchor_field: context.anchor_field,
          attribution_anchor_line: context.anchor_line });
        continue;
      }
      if (context && context.blocked) {
        foldless.push({ file_line: h.line, rule: h.rule, why: context.blocked,
          fold_container: context.container, fold_container_line: context.container_line });
      }
      kept.push(h);
    }
    for (const h of kept) delete h._node;
    return { hits: kept.sort((a, b) => a.line - b.line), attributed_in_fold: folded,
      fold_without_anchor: foldless,
      diagnostics, truncated,
      crossingCuts: crossingCuts,
      graph: { bindings: bindings.length, functions: fnOf.size, call_sites: callSites.length,
        state_pairs: statePairs.map((p) => p.get.name + '/' + p.set.name), sinks: sinkList().length } };
  }
  /* What the sink *is*, said without a line number: the attribute name, or the element the text is
     rendered inside. Two cells that differ only in where they sit are still two different shapes. */
  /* The innermost enclosing element that carries a `data-testid`: two renders of the same poisoned value
     in one file are two cells, and the test id is the line-independent way to tell them apart. */
  function testidSuffix(node) {
    for (let cur = node; cur; cur = cur.parent) {
      if (!ts.isJsxElement(cur)) continue;
      const hit = jsxAttrsOf(cur).filter((a) => a.name && a.name.getText(sf) === 'data-testid' && a.initializer)[0];
      if (!hit) continue;
      let value = hit.initializer;
      if (ts.isJsxExpression(value)) value = value.expression;
      const text = value && value.text !== undefined ? String(value.text) : '{computed}';
      return ' testid=' + cur.openingElement.tagName.getText(sf) + ':' + text;
    }
    return '';
  }
  function sinkShape(s) {
    const n = s.node;
    if (s.kind === 'dom-attribute' && n.name) {
      const owner = n.parent && n.parent.parent ? n.parent.parent : null;
      return 'attribute:' + n.name.getText(sf) + (owner && ts.isJsxElement(owner) ? testidSuffix(owner) : '');
    }
    if (s.kind === 'inner-html') return 'markup:innerHTML';
    if (s.kind === 'dom-text') return 'dom:text-or-innerText-write';
    for (let cur = n.parent; cur; cur = cur.parent) {
      if (ts.isJsxElement(cur)) return 'text-in:' + cur.openingElement.tagName.getText(sf) + testidSuffix(cur);
      if (ts.isJsxFragment(cur)) return 'text-in:fragment';
    }
    return 'text';
  }
  function helperNames(o) {
    const seen = [];
    for (const hop of o.hops) {
      for (const raw of String(hop.text).matchAll(/([A-Za-z_$][\w$]*)\s*\(/g)) {
        const name = raw[1];
        // `read (` comes from this file's own hop wording ("upstream read (…)"), not from the code.
        if (name !== 'read' && !BUILTIN_FUNCS.has(name) && seen.indexOf(name) < 0) seen.push(name);
      }
    }
    return seen;
  }
  function mkHit(rule, s, o) {
    const line = lineOf(s.node);
    const structural = { sink_shape: sinkShape(s), origin_kind: o.kind,
      member: memberNameOf(s.expr ? unwrap(s.expr) : null),
      helpers: helperNames(o),
      hops: o.hops.map((h) => String(h.text).replace(/\s+/g, ' ').trim()) };
    return { rule, line, sink: s.kind, _node: s.node, origin_kind: o.kind, structural,
      function_boundaries: o.boundaries || 0,
      snippet: (lines[line - 1] || '').trim().slice(0, 120),
      taint_trace: o.hops.concat([{ line, text: 'rendered here' }]).map((h) => ':' + h.line + ' ' + h.text),
      taint_chain: o.hops.map((h) => ':' + h.line + ' ' + h.text).concat([':' + line + ' rendered here']).join(' -> ') };
  }
  let settledOnce = false;
  function ensureSettled() { if (!settledOnce) { settle(); settledOnce = true; } }
  function bindingOfLocal(name) { return lookup(name, rootScope); }
  function exportRecord(name) {
    if (exportedNames.has(name)) return exportedNames.get(name);
    if (reexportFrom.has(name)) return { reexport: reexportFrom.get(name) };
    if (exportedNames.has('default') && (name === 'default')) return exportedNames.get('default');
    return null;
  }
  function calleeThunk(exportedName) {
    return function (tail, d) { return originOfExportCross(exportedName, tail, d); };
  }
  function originOfExportCross(name, tail, d) {
    const rec = exportRecord(name);
    if (!rec) {
      // a barrel forwards names it never lists: `export * from './inner'`
      for (const spec of starFrom) {
        if (!hooks || !hooks.followStar) continue;
        const o = hooks.followStar(spec, name, tail, d);
        if (o) return o;
      }
      return null;
    }
    if (rec.reexport) return hooks && hooks.followReexport ? hooks.followReexport(rec.reexport, tail, d, null) : null;
    if (rec.fnNode) return fnReturn(fnOf.get(rec.fnNode), tail, d);
    const b = rec.local ? bindingOfLocal(rec.local) : null;
    if (!b) return null;
    if (b.kind === 'fn' && b.initNode) {
      const inner = fnOf.get(unwrap(b.initNode));
      if (inner) return fnReturn(inner, tail, d);
    }
    return originOfBindingForQuery(b, tail, d);
  }
  function importCalls() {
    const out = [];
    for (const cs of callSites) {
      if (!ts.isIdentifier(cs.expression)) continue;
      const b = idBinding.get(cs.expression) || lookup(cs.expression.text, scopeFor(cs.expression));
      if (b && b.kind === 'import' && b.importedAs !== '*') out.push({ call: cs, binding: b });
    }
    return out;
  }
  function answerFrom(node, tail, d) { return valueOf(node, fnFor(node), tail, d); }
  function originOfExport(name, tail, d, seen) {
    const rec = exportRecord(name);
    if (!rec) return null;
    if (rec.reexport) return hooks && hooks.followReexport ? hooks.followReexport(rec.reexport, tail, d, seen) : null;
    if (rec.fnNode) return fnReturn(fnOf.get(rec.fnNode), tail, d);
    const b = rec.local ? bindingOfLocal(rec.local) : null;
    if (!b) return null;
    return originOfBindingForQuery(b, tail, d);
  }
  function originOfBindingForQuery(b, tail, d) {
    if (tail.length) {
      const o = writersOrigin(b, tail, d);
      if (o) return o;
      if (b.envelope && (EXCEPTION_FIELDS.has(tail[0]) || FORBIDDEN_ALWAYS.has(tail[0]))) {
        return origin(tail[0] === 'stack' || tail[0] === 'message' ? 'exception' : 'raw-body',
          lineOf(b.declNode), 'the response field `' + b.name + '.' + tail.join('.') + '`');
      }
      return null;
    }
    const o = writersOrigin(b, [], d);
    if (o) return o;
    if (b.kind !== 'param' && b.envelope) {
      return origin('raw-body', lineOf(b.declNode), 'the imported response value `' + b.name + '` itself reached the DOM', 'envelope');
    }
    return null;
  }
  return { run, sf, diagnostics, lineOf, srcOf, ensureSettled, exportRecord, originOfExport, bindingOfLocal,
    importBindings, exportedNames, reexportFrom, starFrom,
    calleeThunk, originOfExportCross, importCalls, answerFrom, stats2: () => ({ imports: importBindings.length,
      exports: exportedNames.size + reexportFrom.size }) };
}

/* ------------------------------------------------------------------ module graph (ORD-0331) */

function dirOf(k) { const p = k.split("/"); p.pop(); return p.join("/"); }
function joinKey(base, rel) {
  const parts = (base ? base.split("/") : []).concat(rel.split("/"));
  const out = [];
  for (const p of parts) {
    if (p === "" || p === ".") continue;
    if (p === "..") { if (out.length && out[out.length - 1] !== "..") out.pop(); else out.push(".."); continue; }
    out.push(p);
  }
  return out.join("/");
}
const TS_EXTS = [".ts", ".tsx"];

/* The graph is what r4 could not see: a helper in `lib/` that hands back the answer's own words, and a
 * component two directories away that prints it. Resolution is TypeScript-ish for what this tree actually
 * uses - relative specifiers, .ts/.tsx, and index files; a package specifier (react, i18next) is recorded
 * as unresolved rather than guessed at, because a clean verdict must be able to say how much it saw. */
function createProgram(ts, opts) {
  const modules = new Map();
  const unresolved = [];
  const seenEdges = new Set();

  function exists(key) { return !!opts.exists(key); }
  function resolveKey(fromKey, spec) {
    if (typeof spec !== "string" || spec.charAt(0) !== ".") return null;
    const target = joinKey(dirOf(fromKey), spec);
    for (const e of TS_EXTS) if (exists(target + e)) return target + e;
    for (const e of TS_EXTS) if (exists(target + "/index" + e)) return target + "/index" + e;
    return null;
  }
  function noteUnresolved(fromMod, spec) {
    const k = fromMod.key + ">" + spec;
    if (!seenEdges.has(k)) { seenEdges.add(k); unresolved.push({ from: fromMod.key, spec: spec }); }
  }
  function getModule(key) {
    if (modules.has(key)) return modules.get(key);
    const text = opts.read(key);
    if (text === null || text === undefined) return null;
    const mod = { key: key, analyzer: null };
    const hooks = {
      importOrigin: function (binding, tail, d) { return importOrigin(mod, binding, tail, d); },
      followReexport: function (re, tail, d, seen) { return followSpec(mod, re.from, re.exported, tail, d, seen); },
      calleeOrigin: function (binding) { return calleeNamedIn(mod.key, binding, binding.importedAs); },
      calleeNamedIn: function (binding, exportedName) { return calleeNamedIn(mod.key, binding, exportedName); },
      followStar: function (spec, name, tail, d) { return followSpec(mod, spec, name, tail, d, null); },
      inboundArgs: function (fnName) { return inboundEdgesFor(mod.key, fnName); },
    };
    mod.analyzer = makeAnalyzer(ts, key, text, hooks);
    modules.set(key, mod);
    return mod;
  }
  function followSpec(fromMod, spec, exportedName, tail, d, seen) {
    const guardKey = fromMod.key + ">" + spec + ">" + exportedName + ">" + tail.join(".");
    const s2 = seen ? new Set(seen) : new Set();
    if (s2.has(guardKey)) return null;                 // a cycle answers unknown; it never answers clean
    s2.add(guardKey);
    const key = resolveKey(fromMod.key, spec);
    if (!key) { noteUnresolved(fromMod, spec); return null; }
    const target = getModule(key);
    if (!target) { noteUnresolved(fromMod, spec); return null; }
    target.analyzer.ensureSettled();
    return originOfExportIn(target, exportedName, tail, d, s2);
  }
  function originOfExportIn(mod, name, tail, d, seen) {
    const rec = mod.analyzer.exportRecord(name);
    if (rec) {
      if (rec.reexport) return followSpec(mod, rec.reexport.from, rec.reexport.exported, tail, d, seen);
      return mod.analyzer.originOfExport(name, tail, d);
    }
    for (const spec of mod.analyzer.starFrom) {        // `export * from` - the barrel never names it
      const o = followSpec(mod, spec, name, tail, d, seen);
      if (o) return o;
    }
    return null;
  }
  function calleeNamedIn(ownerKey, binding, exportedName) {
    const key = resolveKey(ownerKey, binding.importFrom);
    if (!key) { noteUnresolvedByKey(ownerKey, binding.importFrom); return null; }
    const target = getModule(key);
    if (!target) { noteUnresolvedByKey(ownerKey, binding.importFrom); return null; }
    target.analyzer.ensureSettled();
    return target.analyzer.calleeThunk(exportedName);
  }
  function noteUnresolvedByKey(fromKey, spec) {
    if (!fromKey) return;
    const k = fromKey + ">" + spec;
    if (!seenEdges.has(k)) { seenEdges.add(k); unresolved.push({ from: fromKey, spec: spec }); }
  }
  function importOrigin(mod, binding, tail, d) {
    const spec = binding.importFrom;
    if (typeof spec !== "string" || spec.charAt(0) !== ".") return null;
    if (binding.importedAs === "*") {
      if (!tail.length) return null;
      return followSpec(mod, spec, tail[0], tail.slice(1), d, null);
    }
    return followSpec(mod, spec, binding.importedAs, tail, d, null);
  }
  /* Which calls in this graph hand an argument to `fnName` as it is exported by `targetKey`? Answered by
   * scanning the loaded modules, because an import edge is only visible from the consuming side. */
  function inboundEdgesFor(targetKey, fnName) {
    const out = [];
    for (const m of modules.values()) {
      if (m.key === targetKey) continue;
      let calls;
      try { calls = m.analyzer.importCalls(); } catch (e) { continue; }
      for (const ic of calls) {
        if (ic.binding.importedAs !== fnName) continue;
        if (resolveKey(m.key, ic.binding.importFrom) !== targetKey) continue;
        out.push({ call: ic.call, from: m.key, line: m.analyzer.lineOf(ic.call),
          answer: function (node, tail, d) { return m.analyzer.answerFrom(node, tail, d); } });
      }
    }
    return out;
  }

  function analyzeAll(keys) {
    for (const k of keys) getModule(k);
    for (const m of modules.values()) m.analyzer.ensureSettled();
    const hits = [];
    const perFile = [];
    const folded = [], foldless = [];
    let diag = 0, truncated = 0, hopCuts = 0;
    for (const k of modules.keys()) {
      const m = modules.get(k);
      let r;
      try { r = m.analyzer.run(); }
      catch (e) {
        hits.push({ rule: "RULER_ERROR", file: k, line: 0,
          error: String((e && e.stack) || e).split(String.fromCharCode(10)).slice(0, 3).join(" | ") });
        continue;
      }
      diag += r.diagnostics; truncated += r.truncated || 0; hopCuts += r.crossingCuts || 0;
      for (const h of r.hits) { h.file = k; cellIdentity(k, h); }
      for (const f of r.attributed_in_fold) { f.file = k; folded.push(f); }
      for (const f of r.fold_without_anchor) { f.file = k; foldless.push(f); }
      hits.push.apply(hits, r.hits);
      perFile.push({ file: k, hits: r.hits.length, parse_diagnostics: r.diagnostics,
        attributed_in_fold: r.attributed_in_fold.length,
        depth_cut_lookups: r.truncated || 0, imports: m.analyzer.importBindings.length,
        exports: m.analyzer.exportedNames.size + m.analyzer.reexportFrom.size + m.analyzer.starFrom.length,
        graph: r.graph });
    }
    hits.sort(function (a, b) { return a.file < b.file ? -1 : a.file > b.file ? 1 : a.line - b.line; });
    return { hits: hits, attributed_in_fold: folded, fold_without_anchor: foldless,
      perFile: perFile, modules: modules.size, diagnostics: diag, truncated: truncated,
      crossing_cuts: hopCuts, unresolved: unresolved };
  }
  return { getModule: getModule, analyzeAll: analyzeAll, resolveKey: resolveKey, modules: modules,
    unresolved: unresolved };
}

function diskTree(dir) {
  const root = String(dir).split(String.fromCharCode(92)).join("/").replace(/\/+$/, "");
  const keys = [];
  (function walkAbs(p, rel) {
    for (const ent of fs.readdirSync(p, { withFileTypes: true })) {
      if (ent.name === "node_modules" || ent.name === "dist") continue;
      const abs = p + "/" + ent.name;
      const r = rel ? rel + "/" + ent.name : ent.name;
      if (ent.isDirectory()) walkAbs(abs, r);
      else if (/\.(ts|tsx)$/.test(ent.name)) keys.push(r);
    }
  })(root, "");
  return {
    keys: keys,
    exists: function (k) { return fs.existsSync(root + "/" + k); },
    read: function (k) { return fs.existsSync(root + "/" + k) ? fs.readFileSync(root + "/" + k, "utf8") : null; },
  };
}

function virtualTree(files) {
  const map = {};
  for (const name of Object.keys(files)) map[name.split(String.fromCharCode(92)).join("/")] = files[name];
  const keys = Object.keys(map);
  return {
    keys: keys,
    exists: function (k) { return Object.prototype.hasOwnProperty.call(map, k); },
    read: function (k) { return map[k] === undefined ? null : map[k]; },
  };
}

function scanTree(ts, tree) {
  const prog = createProgram(ts, tree);
  return prog.analyzeAll(tree.keys);
}

function scanText(ts, label, text) {
  const a = makeAnalyzer(ts, /\.tsx?$/.test(label) ? label : label + '.tsx', text);
  const r = a.run();
  for (const h of r.hits) { h.file = label; cellIdentity(label, h); }
  return r;
}

/* ------------------------------------------------------------------ fixtures */

const FIXTURES_R3 = {
  "clean_whitelist_only.tsx": '<pre>{`http_status=${r.http_status}\\n`}{`bytes=${r.body_bytes}`}' + '<code>{result.note.text}</code></pre>',
  "clean_literal_helper.tsx": 'function localWording(code: string): string {\n  return code ? "这台设备自己的读数" : "";\n}\n' + 'export function X() { const note = {failureReason: localWording(code)};' + 'return <code>{note.failureReason.text}</code>; }',
  "bad_direct_optional_chain.tsx": 'export function X({body}) { return <code>{body?.detail}</code>; }',
  "bad_helper_taint.tsx": 'function serverReasonSentence(body: unknown): string | null {\n' + '  const detail = (body as { detail?: unknown } | null)?.detail;\n' + '  if (typeof detail === "string") return detail;\n  return null;\n}\n' + 'export function X() { const r = {failureReason: note(serverReasonSentence(body))};\n' + '  return <code data-testid="plan-ai-reason">{r.failureReason.text}</code>; }',
  "bad_dangerous_html.tsx": '<div dangerouslySetInnerHTML={{__html: serverText}} />',
  "clean_tainted_but_attribute_only.tsx": 'function serverReasonSentence(body: unknown): string | null {\n' + '  const detail = (body as { detail?: unknown } | null)?.detail;\n' + '  if (typeof detail === "string") return detail;\n  return null;\n}\n' + 'export function X() { const out = {failureReason: failureNote(\n' + '  serverReasonSentence(body), "x")};\n' + '  return <code data-reason-origin={out.failureReason.from}>' + '{out.status}</code>; }',
  "bad_raw_body.tsx": "<pre>{`body=${r.body_head}`}</pre>",
  "bad_rename_last_part.tsx": 'function serverReasonSentence(body: unknown): string | null {\n  const d = (body as { detail?: unknown } | null)?.detail;\n  if (typeof d === "string") return d;\n  return null;\n}\nexport function X() {\n  const out = {failureReason: failureNote(\n  serverReasonSentence(body), "fb")};\n  return <code>{out.failureReason.value}</code>; }',
  "bad_bare_local_hop.tsx": 'function serverReasonSentence(body: unknown): string | null {\n  const d = (body as { detail?: unknown } | null)?.detail;\n  if (typeof d === "string") return d;\n  return null;\n}\nexport function X() {\n  const sentence = serverReasonSentence(body);\n  return <code>{sentence}</code>; }',
  "bad_paren_alias.tsx": 'function serverReasonSentence(body: unknown): string | null {\n  const d = (body as { detail?: unknown } | null)?.detail;\n  if (typeof d === "string") return d;\n  return null;\n}\nexport function X() {\n  const out = {failureReason: failureNote(\n  serverReasonSentence(body), "fb")};\n  return <code>{(out.failureReason || {}).text}</code>; }',
  "clean_bare_local_from_literal.tsx": 'function localWording(code: string): string {\n  return code ? "device own wording" : "";\n}\nexport function X() { const sentence = localWording(code);\n  return <code>{sentence}</code>; }',
  "clean_untainted_value_name.tsx": 'export function X() { const out = {failureReason: {from: "device"}};\n  return <code>{out.failureReason.value}</code>; }',
  "bad_helper_taint_multiline.tsx": 'function serverReasonSentence(body: unknown): string | null {\n' + '  const detail = (body as { detail?: unknown } | null)?.detail;\n' + '  if (typeof detail === "string") return detail;\n  return null;\n}\n' + 'export function X() { const out = {failureReason: failureNote(\n' + '  serverReasonSentence(body),\n  "fallback"\n)};\n' + '  return <code data-testid="plan-ai-reason">{out.failureReason.text}</code>; }',
};
const EXPECT_R3 = { "clean_whitelist_only.tsx": 0, "clean_literal_helper.tsx": 0, "clean_tainted_but_attribute_only.tsx": 0,
  "bad_direct_optional_chain.tsx": 1, "bad_helper_taint.tsx": 1, "bad_helper_taint_multiline.tsx": 1,
  "bad_rename_last_part.tsx": 1, "bad_bare_local_hop.tsx": 1, "bad_paren_alias.tsx": 1,
  "clean_bare_local_from_literal.tsx": 0, "clean_untainted_value_name.tsx": 0, "bad_dangerous_html.tsx": 1, "bad_raw_body.tsx": 1 };

/* Lane E d2305848's counterexamples, taken off origin/cmdcontrol and inlined byte-for-byte; the blob each was
 * read from is named beside it so a later reader can prove which bytes are under test. */
const FIXTURES_E = {
  "e0319r2_A_rename_last_part.tsx": { blob: "4c1bdae7f371ae96f580a7e590331c95ba04715e",
    src: 'function serverReasonSentence(body: unknown): string | null {\n  const detail = (body as { detail?: unknown } | null)?.detail;\n  if (typeof detail === "string") return detail;\n  return null;\n}\nexport function X() { const out = {failureReason: failureNote(\n  serverReasonSentence(body), "fb")};\n  return <code>{out.failureReason.value}</code>; }\n' },
  "e0319r2_B_destructure_hop.tsx": { blob: "ace904808257b02b002c63e424e8bdc6855623f6",
    src: 'function serverReasonSentence(body: unknown): string | null {\n  const detail = (body as { detail?: unknown } | null)?.detail;\n  if (typeof detail === "string") return detail;\n  return null;\n}\nexport function X() { const sentence = serverReasonSentence(body);\n  return <code>{sentence}</code>; }\n' },
  "e0319r2_C_paren_alias.tsx": { blob: "c6ef79c50cea55e3024b8dfe79ff8273bf24c16e",
    src: 'function serverReasonSentence(body: unknown): string | null {\n  const detail = (body as { detail?: unknown } | null)?.detail;\n  if (typeof detail === "string") return detail;\n  return null;\n}\nexport function X() { const out = {failureReason: failureNote(\n  serverReasonSentence(body), "fb")};\n  return <code>{(out.failureReason || {}).text}</code>; }\n' },
  "e0319r2_D_control_clean.tsx": { blob: "aac913740eb191e453144ea0d2e253a8611e5883",
    src: 'export function X() { const note = {failureReason: {from: "device", text: "这台设备自己的读数"}};\n  return <code data-testid="plan-ai-reason">{note.failureReason.text}</code>; }\n' },
  "e0319r3_E1_bracket_read.tsx": { blob: "95547a73642cd9959c62548b0195bc6a54967398",
    src: 'function serverReasonSentence(body: unknown): string | null {\n  const d = body["detail"];\n  if (typeof d === "string" && d) return d;\n  return null;\n}\nexport function X() { const r = {failureReason: note(serverReasonSentence(body))};\n  return <code>{r.failureReason.text}</code>; }\n' },
  "e0319r3_E2_forwarding_helper.tsx": { blob: "b2f507455e610dd639e882f72651be8e120953c8",
    src: 'function serverReasonSentence(body: unknown): string | null {\n  const detail = (body as { detail?: unknown } | null)?.detail;\n  if (typeof detail === "string") return detail;\n  return null;\n}\nfunction wrap(b: unknown): string | null { return serverReasonSentence(b); }\nexport function X() { const s = wrap(body);\n  return <code>{s}</code>; }\n' },
  "e0319r3_E3_control_attribute_only.tsx": { blob: "b5fda05334fd0b5088571cb7cd6394ea088be8c5",
    src: 'function serverReasonSentence(body: unknown): string | null {\n  const detail = (body as { detail?: unknown } | null)?.detail;\n  if (typeof detail === "string") return detail;\n  return null;\n}\nexport function X() { const out = {failureReason: failureNote(\n  serverReasonSentence(body), "fb")};\n  return <code data-reason-origin={out.failureReason.from}>{out.status}</code>; }\n' },
};
const EXPECT_E = { "e0319r2_A_rename_last_part.tsx": 1, "e0319r2_B_destructure_hop.tsx": 1, "e0319r2_C_paren_alias.tsx": 1,
  "e0319r2_D_control_clean.tsx": 0, "e0319r3_E1_bracket_read.tsx": 1, "e0319r3_E2_forwarding_helper.tsx": 1,
  "e0319r3_E3_control_attribute_only.tsx": 0 };

/* ORD-0354 + ORD-0348 arms. Each one is a whole file, and each claim is stated in both directions: the
 * same server sentence on the face of the screen, in a fold that carries an attribution anchor, and in a
 * fold whose anchor has been deleted; an exception's own words in a data-* slot, and that slot removed;
 * structural attributes that must stay legal; and the two ways the exception must NOT open (a class
 * name, or an anchor naming something outside the six allowed fields). */
const R7_SERVER = 'function serverReasonSentence(body: unknown): string | null {\n'
  + '  const detail = (body as { detail?: unknown } | null)?.detail;\n'
  + '  if (typeof detail === "string") return detail;\n  return null;\n}\n';
const R7_EXC = 'export function X() { let detail: { message?: string } | null = null;\n'
  + '  try { doIt(); } catch (e) { detail = { message: e instanceof Error ? e.message : "" }; }\n';
const R7_ARMS = [
  { name: "R7_1_server_sentence_on_the_face_still_fires", file: "r7_1.tsx", expect_hits: 1, expect_folded: 0,
    src: R7_SERVER + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <p data-testid="outcome">{sentence}</p>; }\n' },
  { name: "R7_2_same_sentence_in_a_fold_with_an_anchor", file: "r7_2.tsx", expect_hits: 0, expect_folded: 1,
    src: R7_SERVER + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <details><summary>x</summary>'
      + '<span data-cnx-field="http_status">{String(status)}</span>'
      + '<span>{sentence}</span></details>; }\n' },
  { name: "R7_3_anchor_deleted_so_the_cell_returns", file: "r7_3.tsx", expect_hits: 1, expect_folded: 0,
    src: R7_SERVER + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <details><summary>x</summary>'
      + '<span>{sentence}</span></details>; }\n' },
  { name: "R7_4_exception_words_in_a_data_attribute_fires", file: "r7_4.tsx", expect_hits: 1, expect_folded: 0,
    expect_rule: "UPSTREAM_PROSE_TO_ATTRIBUTE_SLOT",
    src: R7_EXC + '  return <p data-error-message={detail?.message ?? ""}>device own wording</p>;\n}\n' },
  { name: "R7_5_attribute_removed_so_the_denominator_returns", file: "r7_5.tsx", expect_hits: 0, expect_folded: 0,
    src: R7_EXC + '  return <p>device own wording</p>;\n}\n' },
  { name: "R7_6_structural_attributes_stay_legal", file: "r7_6.tsx", expect_hits: 0, expect_folded: 0,
    src: 'export function X({ row }: { row: { canonical_destination_id: string | null; capability: string;'
      + ' place_count: number; name: string } }) {\n'
      + '  return <li data-canonical-destination-id={row.canonical_destination_id}'
      + ' data-capability={row.capability} data-cnx-value={String(row.place_count)}>{row.name}</li>;\n}\n' },
  { name: "R7_7_the_fold_never_exonerates_an_attribute", file: "r7_7.tsx", expect_hits: 1, expect_folded: 0,
    expect_rule: "UPSTREAM_PROSE_TO_ATTRIBUTE_SLOT",
    src: R7_EXC + '  return <details><summary>x</summary>'
      + '<span data-cnx-field="http_status">{String(status)}</span>'
      + '<p data-error-message={detail?.message ?? ""}>device own wording</p></details>;\n}\n' },
  { name: "R7_8_data_cnx_fold_counts_as_a_fold_surface", file: "r7_8.tsx", expect_hits: 0, expect_folded: 1,
    src: R7_SERVER + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <div data-cnx-fold="true"><span data-cnx-field="request_id">{String(id)}</span>'
      + '<span>{sentence}</span></div>;\n}\n' },
  { name: "R7_9_a_class_name_opens_nothing", file: "r7_9.tsx", expect_hits: 1, expect_folded: 0,
    src: R7_SERVER + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <details className="today-technical-detail"><summary>x</summary>'
      + '<span>{sentence}</span></details>;\n}\n' },
  { name: "R7_10_an_anchor_outside_the_six_fields_opens_nothing", file: "r7_10.tsx", expect_hits: 1, expect_folded: 0,
    src: R7_SERVER + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <details><summary>x</summary>'
      + '<span data-cnx-field="server_message">{sentence}</span></details>;\n}\n' },
  /* The planted probe's shape, in one file: the value arrives as a prop, so no provenance is followable and
     only the field's own name can guard the slot. */
  { name: "R7_11_prop_carried_message_in_an_attribute_fires", file: "r7_11.tsx", expect_hits: 1, expect_folded: 0,
    expect_rule: "UPSTREAM_PROSE_TO_ATTRIBUTE_SLOT",
    src: 'export function X({ detail }: { detail?: { message?: string; name?: string } }) {\n'
      + '  return <p data-error-message={detail?.message ?? ""}>device own wording</p>;\n}\n' },
  { name: "R7_12_the_same_member_in_text_is_left_to_the_old_rule", file: "r7_12.tsx", expect_hits: 0, expect_folded: 0,
    src: 'export function X({ detail }: { detail?: { message?: string; name?: string } }) {\n'
      + '  return <p>{detail?.message ?? ""}</p>;\n}\n' },
];

/* Two of lane E's controls expected 0 under r6 for one reason only: r6 never looked at an attribute slot,
 * so "the tainted value went into data-* instead of the text" was clean by construction. ORD-0354 removes
 * that blindness, so those two expectations move. The fixture *sources* are kept byte-for-byte as lane E
 * wrote them (their blob is printed in the output); only the expected count changes, and it changes here,
 * in the open, rather than by editing somebody else's counterexample. */
const R7_EXPECTATION_CHANGES = {
  "clean_tainted_but_attribute_only.tsx": { was: 0, now: 1, why: 'ORD-0354: the same member in a text position already '
    + 'fired (probe: `out.failureReason.from` as a child gives UPSTREAM_TEXT_VIA_HELPER_TO_DOM); the attribute '
    + 'slot is now read the same way, so the control is no longer clean by invisibility' },
  "e0319r3_E3_control_attribute_only.tsx": { was: 0, now: 1, why: 'same shape, lane E blob b5fda05334fd0b5088571cb7cd6394ea088be8c5' },
};

/* ORD-0354's second half: a cell identity that does not move when the file's lines move.
 * It is the rule, the file's position in the tree, the sink's shape, the members and helpers the value
 * crossed, and every link of the taint chain - and no line number anywhere. The readable string is kept
 * beside its digest so a reader can see what the digest stands for instead of trusting it. */
function stableFileLabel(file) {
  const f = String(file || '').replace(/\\/g, '/');
  // A tracked copy under `review/<checkpoint>/` is its own file: collapsing those onto the live path made
  // 20 separate cells share one identity, which is the opposite of what a cell id is for.
  if (f.startsWith('review/')) return f;
  for (const marker of ['/frontend/', 'frontend/']) {
    const i = f.indexOf(marker);
    if (i >= 0) return f.slice(i + marker.length - 'frontend/'.length);
  }
  const parts = f.split('/');
  return parts[parts.length - 1];
}
function cellIdentity(file, h) {
  const st = h.structural || {};
  const parts = [h.rule, stableFileLabel(file), st.sink_shape || h.sink, st.origin_kind || '',
    (st.member || '-') , (st.helpers || []).join('>'), (st.hops || []).join(' | ')];
  h.cell_identity = parts.join(' :: ').replace(/\s+/g, ' ').trim();
  h.cell_id = crypto.createHash('sha1').update(h.cell_identity).digest('hex').slice(0, 16);
  return h;
}

function blobSha1(text) {
  const buf = Buffer.from(text, 'utf8');
  return crypto.createHash('sha1').update('blob ' + buf.length + ' ').update(buf).digest('hex');
}


/* The arms ORD-0331 asks for, as whole virtual trees - no disk, no product file.
 * A is the control: a lib that composes its own wording and a consumer that prints it, and it must stay
 * clean. B is the counterexample: the same helper handing back the answer's `detail`; its cell must land in
 * the CONSUMER file, because a lib-only report would still miss the screen. C is B's reverse mutation - the
 * helper kept, its body replaced by allowed fields - and B's cell must vanish. D is the shape a shared
 * channel actually takes here: a barrel re-export resolved through index.ts and `export * from`.
 * E is the namespace-import form (`import * as say`, `say.quoted(b)`). */
const CROSS_ARMS = [
  { name: "A_control_clean_lib_and_clean_consumer", consumer: "panels/Panel.tsx",
    expected_consumer_cells: 0,
    files: {
      "lib/wording.ts": "export function reasonLabel(code: string): string {\n"
        + "  return code ? \u8fd9\u53f0\u8bbe\u5907\u81ea\u5df1\u7684\u8bfb\u6570 : \"\";\n}\n",
      "panels/Panel.tsx": "import { reasonLabel } from \"../lib/wording\";\n"
        + "export function P({ code }: { code: string }) {\n"
        + "  const note = reasonLabel(code);\n"
        + "  return <p data-testid=\"reason\">{note}</p>;\n}\n",
    } },
  { name: "B_helper_returns_detail_cell_lands_in_consumer", consumer: "panels/Panel.tsx",
    expected_consumer_cells: 1,
    files: {
      "lib/wording.ts": "export function reasonLabel(body: unknown): string {\n"
        + "  const d = (body as { detail?: unknown } | null)?.detail;\n"
        + "  return typeof d === \"string\" ? d : \"\";\n}\n",
      "panels/Panel.tsx": "import { reasonLabel } from \"../lib/wording\";\n"
        + "export function P() {\n"
        + "  const response = await fetch(\"/api/x\");\n"
        + "  const body = await response.json();\n"
        + "  const note = reasonLabel(body);\n"
        + "  return <p data-testid=\"reason\">{note}</p>;\n}\n",
    } },
  { name: "C_mutated_helper_returns_allowed_fields_only", consumer: "panels/Panel.tsx",
    expected_consumer_cells: 0,
    files: {
      "lib/wording.ts": "export function reasonLabel(reading: { http_status: number; content_type: string }): string {\n"
        + "  return `HTTP ${reading.http_status} ${reading.content_type}`;\n}\n",
      "panels/Panel.tsx": "import { reasonLabel } from \"../lib/wording\";\n"
        + "export function P({ response }: { response: { status: number; headers: { get(k: string): string | null } } }) {\n"
        + "  const reading = { http_status: response.status, content_type: response.headers.get(\"content-type\") ?? \"\" };\n"
        + "  const note = reasonLabel(reading);\n"
        + "  return <p data-testid=\"reason\">{note}</p>;\n}\n",
    } },
  { name: "D_barrel_reexport_through_index_and_star", consumer: "panels/Panel.tsx",
    expected_consumer_cells: 1,
    files: {
      "lib/inner.ts": "export function serverSentence(body: unknown): string | null {\n"
        + "  const error = (body as { error?: { message?: string } } | null)?.error;\n"
        + "  if (error && typeof error.message === \"string\") return error.message;\n"
        + "  return null;\n}\n",
      "lib/index.ts": "export * from \"./inner\";\n",
      "panels/Panel.tsx": "import { serverSentence } from \"../lib\";\n"
        + "export function P() {\n"
        + "  const res = await fetch(\"/api/y\");\n"
        + "  const payload = await res.json();\n"
        + "  const line = serverSentence(payload);\n"
        + "  return <span>{line}</span>;\n}\n",
    } },
  { name: "E_namespace_import_member_call", consumer: "panels/Name.tsx",
    expected_consumer_cells: 1,
    files: {
      "lib/say.ts": "export function quoted(body: unknown): string {\n"
        + "  return String((body as { detail?: string } | null)?.detail ?? \"\");\n}\n",
      "panels/Name.tsx": "import * as say from \"../lib/say\";\n"
        + "export function Q() {\n"
        + "  const r = await fetch(\"/api/z\");\n"
        + "  const b = await r.json();\n"
        + "  return <b>{say.quoted(b)}</b>;\n}\n",
    } },
];

/* F and G are the two directions of the mode split, and they are deliberately run through BOTH modes in
 * the same selftest, because the claim being tested is about a comparison, not about a single number. */
const SL = "/";
const N = String.fromCharCode(10);
const Q = String.fromCharCode(34);
const MODE_ARMS = [
  /* F: per file a call into an imported helper is opaque, so a poisoned argument alone makes the result
   * read poisoned and the screen is reported. In the graph the same helper turns out to return only this
   * device own wording, and that cell is cleared. So the per-file count EXCEEDS the graph count. */
  { name: "F_per_file_over_reports_where_the_helper_exonerates",
    consumer: ["panels", "Panel.tsx"].join(SL), expect: "per_file_more_than_graph", files: {} },
  /* G: the other direction. The poison is an imported VALUE, not a call, so per file there is no edge to
   * follow and the screen reads clean while the graph condemns it. Graph count EXCEEDS per-file. */
  { name: "G_per_file_under_reports_poison_arriving_as_an_imported_value",
    consumer: ["panels", "Show.tsx"].join(SL), expect: "graph_more_than_per_file", files: {} },
];
MODE_ARMS[0].files[["lib", "note.ts"].join(SL)] = [
  "export function deviceNote(e: unknown, zh: boolean): string {",
  "  return zh ? " + Q + "\u8fd9\u53f0\u8bbe\u5907\u81ea\u5df1\u7684\u8bfb\u6570" + Q + " : " + Q + "this device own reading" + Q + ";",
  "}",
].join(N) + N;
MODE_ARMS[0].files[["panels", "Panel.tsx"].join(SL)] = [
  "import { deviceNote } from " + Q + ".." + SL + "lib" + SL + "note" + Q + ";",
  "export function P() {",
  "  const body = await response.json();",
  "  const note = deviceNote(body?.detail, zh);",
  "  return <p>{note}</p>;",
  "}",
].join(N) + N;
MODE_ARMS[1].files[["lib", "cache.ts"].join(SL)] =
  "export const cachedSentence: string = (body as { detail?: string } | null)?.detail ?? " + Q + Q + ";" + N;
MODE_ARMS[1].files[["panels", "Show.tsx"].join(SL)] = [
  "import { cachedSentence } from " + Q + ".." + SL + "lib" + SL + "cache" + Q + ";",
  "export function S() {",
  "  return <p>{cachedSentence}</p>;",
  "}",
].join(N) + N;

function modePairReport(ts, arm) {
  const tree = scanTree(ts, virtualTree(arm.files));
  const consumerCells = function (hits) {
    return hits.filter(function (h) { return h.file === arm.consumer; }).map(function (h) { return h.file + ":" + h.line + " " + h.rule; });
  };
  const graph = { cells: consumerCells(tree.hits), scope: SCOPE_GRAPH };
  const perFile = { cells: [], scope: SCOPE_PER_FILE };
  for (const name of Object.keys(arm.files)) {
    const r = scanText(ts, name, arm.files[name]);
    perFile.cells.push.apply(perFile.cells, r.hits.map(function (h) { return h.file + ":" + h.line + " " + h.rule; }));
  }
  const differ = JSON.stringify(graph.cells.slice().sort()) !== JSON.stringify(perFile.cells.slice().sort());
  let met;
  if (arm.expect === 'per_file_more_than_graph') met = perFile.cells.length > graph.cells.length && graph.cells.length === 0;
  else if (arm.expect === 'graph_more_than_per_file') met = graph.cells.length >= 1 && perFile.cells.length === 0;
  else met = false;
  return { assertion_met: Boolean(met && differ && graph.scope && perFile.scope),
    modes_differ: differ, scope_in_per_file_report: perFile.scope, scope_in_graph_report: graph.scope,
    per_file_cells: perFile.cells.sort(), graph_cells: graph.cells.sort() };
}

const CROSS_ARMS_EXTRA = [
  /* H is not a hypothetical: it is frontend/src/lib/rawFacts.ts:29-40 as written at generation
   * 821a0eb54cca1b305a4aa75c1ca8d46a95d51bba, consumed by four files. The helper returns the answer's body as
   * a string, the consumer destructures it and prints it. Before this build the ruler said nothing, because
   * only a parameter whose NAME was in the envelope set was treated as carrying the answer. */
  { name: "H_raw_response_text_through_a_shared_channel", consumer: "panels/Show.tsx",
    expected_consumer_cells: 1,
    files: {
      "lib/rawFacts.ts": "export type RawFacts = { http_status: number; bytes: number };" + "\n"
        + "export async function readResponseFacts(" + "\n"
        + "  response: { text(): Promise<string>; status: number }," + "\n"
        + "): Promise<{ text: string; facts: RawFacts }> {" + "\n"
        + "  const text = await response.text();" + "\n"
        + "  return { text, facts: { http_status: response.status, bytes: text.length } };" + "\n"
        + "}" + "\n",
      "panels/Show.tsx": "import { readResponseFacts } from \"../lib/rawFacts\";" + "\n"
        + "export function S() {" + "\n"
        + "  const r = await fetch(\"/api/x\");" + "\n"
        + "  const { text } = await readResponseFacts(r);" + "\n"
        + "  return <p data-testid=\"raw\">{text}</p>;" + "\n"
        + "}" + "\n",
    } },
  /* H2 is the same channel used the way Q64 allows: only measured facts cross the boundary, and the screen
   * composes its own sentence. Without this the fix would just be a wider net. */
  { name: "H2_same_channel_allowing_only_measured_facts", consumer: "panels/Show2.tsx",
    expected_consumer_cells: 0,
    files: {
      "lib/rawFacts.ts": "export type RawFacts = { http_status: number; bytes: number };" + "\n"
        + "export async function readResponseFacts(" + "\n"
        + "  response: { text(): Promise<string>; status: number }," + "\n"
        + "): Promise<{ facts: RawFacts }> {" + "\n"
        + "  const text = await response.text();" + "\n"
        + "  return { facts: { http_status: response.status, bytes: text.length } };" + "\n"
        + "}" + "\n",
      "panels/Show2.tsx": "import { readResponseFacts } from \"../lib/rawFacts\";" + "\n"
        + "export function S2() {" + "\n"
        + "  const r = await fetch(\"/api/x\");" + "\n"
        + "  const { facts } = await readResponseFacts(r);" + "\n"
        + "  return <p data-testid=\"facts\">{`http_status=${facts.http_status} bytes=${facts.bytes}`}</p>;" + "\n"
        + "}" + "\n",
    } },
];

function crossArmReport(ts, arm) {
  const tree = virtualTree(arm.files);
  const r = scanTree(ts, tree);
  const cells = r.hits.map(function (h) { return h.file + ":" + h.line + " " + h.rule; });
  const consumerCells = r.hits.filter(function (h) { return h.file === arm.consumer; });
  const want = arm.expected_consumer_cells;
  const met = want === 0 ? consumerCells.length === 0 : consumerCells.length >= want;
  return { assertion_met: Boolean(met), consumer: arm.consumer, expected_consumer_cells: want,
    observed_consumer_cells: consumerCells.length, observed_other_cells: r.hits.length - consumerCells.length,
    cells: cells, chains: r.hits.map(function (h) { return h.taint_chain; }),
    modules: r.modules, unresolved_import_specs: r.unresolved, parse_diagnostics: r.diagnostics,
    depth_cut_lookups: r.truncated };
}

function selftest(ts) {
  const per = {};
  const all = [];
  for (const [name, src] of Object.entries(FIXTURES_R3)) all.push([name, src, EXPECT_R3[name], 'r3 selftest fixture, source taken from blob 44e062e6ce9c7b5d97d78e09e432072da102292c']);
  for (const [name, rec] of Object.entries(FIXTURES_E)) all.push([name, rec.src, EXPECT_E[name], 'lane E d2305848 counterexample, blob ' + rec.blob]);
  let ok = true;
  for (const [name, src, want, note] of all) {
    const moved = R7_EXPECTATION_CHANGES[name] || null;
    const expected = moved ? moved.now : want;
    let res = null, err = null;
    try { res = scanText(ts, name, src); } catch (e) { err = String((e && e.stack) || e).split('\n').slice(0, 3).join(' | '); }
    if (err) { per[name] = { expected, observed: null, hits: [], verdict: 'RULER_ERROR', error: err.slice(0, 300), assertion_met: false, note }; ok = false; continue; }
    const good = expected === 0 ? res.hits.length === 0 : res.hits.length >= 1;
    ok = ok && good;
    per[name] = { expected, expected_under_r6: want,
      expectation_moved_by_this_revision: moved,
      observed: res.hits.length, hits: res.hits.map((h) => h.rule),
      verdict: res.hits.length ? 'HIT' : 'CLEAN', assertion_met: good, note,
      fixture_bytes: Buffer.byteLength(src, 'utf8'), fixture_blob_sha1: blobSha1(src),
      lines: res.hits.map((h) => h.line), chains: res.hits.map((h) => h.taint_chain),
      parse_diagnostics: res.diagnostics, graph: res.graph };
  }
  const modes = {};
  for (const arm of MODE_ARMS) {
    let res = null, err = null;
    try { res = modePairReport(ts, arm); }
    catch (e) { err = String((e && e.stack) || e).split(String.fromCharCode(10)).slice(0, 3).join(' | '); }
    modes[arm.name] = res || { assertion_met: false, error: err };
    ok = ok && Boolean(res && res.assertion_met);
  }
  const cross = {};
  for (const arm of CROSS_ARMS.concat(CROSS_ARMS_EXTRA)) {
    let res = null, err = null;
    try { res = crossArmReport(ts, arm); }
    catch (e) { err = String((e && e.stack) || e).split(String.fromCharCode(10)).slice(0, 3).join(' | '); }
    cross[arm.name] = res || { assertion_met: false, error: err, expected_consumer_cells: arm.expected_consumer_cells };
    ok = ok && Boolean(res && res.assertion_met);
  }
  /* ORD-0348/0354: the exception and the new slot, each arm asserting both directions at once - how many
     cells survived, and how many moved into `attributed_in_fold`. An arm that only counted hits could be
     satisfied by a rule that stopped firing. */
  const slots = {};
  for (const arm of R7_ARMS) {
    let res = null, err = null;
    try { res = scanText(ts, arm.file, arm.src); }
    catch (e) { err = String((e && e.stack) || e).split(String.fromCharCode(10)).slice(0, 3).join(' | '); }
    const rules = res ? res.hits.map((h) => h.rule) : [];
    const good = Boolean(res) && res.hits.length === arm.expect_hits
      && res.attributed_in_fold.length === arm.expect_folded
      && (!arm.expect_rule || (rules.length > 0 && rules.every((x) => x === arm.expect_rule)));
    ok = ok && good;
    slots[arm.name] = { expected_hits: arm.expect_hits, observed_hits: res ? res.hits.length : null,
      expected_attributed_in_fold: arm.expect_folded,
      observed_attributed_in_fold: res ? res.attributed_in_fold.length : null,
      observed_rules: rules,
      observed_slots: res ? res.hits.map((h) => h.sink) : [],
      exonerated_by: res ? res.attributed_in_fold.map((f) => f.fold_container + ':' + f.fold_container_line
        + ' via ' + f.attribution_anchor_field + ':' + f.attribution_anchor_line) : [],
      assertion_met: good, error: err, fixture_bytes: Buffer.byteLength(arm.src, 'utf8'),
      fixture_blob_sha1: blobSha1(arm.src) };
  }
  /* ORD-0354's cell identity: the claim is that a cell is named by what it is, not by where it sits.
   * Four directions are checked, because an identity that only ever matches itself proves nothing. */
  let identity = {};
  try {
    const base = R7_SERVER + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <p data-testid="o">{sentence}</p>;\n}\n';
    const shifted = '\n\n\n' + base;
    const a = scanText(ts, 'frontend/src/identity/Base.tsx', base);
    const b = scanText(ts, 'frontend/src/identity/Base.tsx', shifted);
    const attr = scanText(ts, 'frontend/src/identity/Base.tsx', R7_SERVER
      + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <p data-error-sentence={sentence}>own wording</p>;\n}\n');
    const wrapped = scanText(ts, 'frontend/src/identity/Base.tsx', R7_SERVER
      + 'function wrapIt(b: unknown): string | null { return serverReasonSentence(b); }\n'
      + 'export function X() { const sentence = wrapIt(body);\n'
      + '  return <p data-testid="o">{sentence}</p>;\n}\n');
    const otherFile = scanText(ts, 'frontend/src/identity/Other.tsx', base);
    const relabeled = scanText(ts, 'D:/elsewhere/checkout/frontend/src/identity/Base.tsx', base);
    const twice = scanText(ts, 'frontend/src/identity/Twice.tsx', R7_SERVER
      + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <><p data-testid="first">{sentence}</p><p data-testid="second">{sentence}</p></>;\n}\n');
    const one = (r) => (r.hits[0] || {});
    const idsOf = (r) => r.hits.map((h) => h.cell_id);
    identity = {
      base_cell_id: one(a).cell_id, base_line: one(a).line, shifted_line: one(b).line,
      twice_ids: idsOf(twice),
      identity_text: one(a).cell_identity,
      identity_survives_a_line_shift: Boolean(one(a).cell_id) && one(a).cell_id === one(b).cell_id
        && one(a).line !== one(b).line,
      line_number_is_not_in_the_identity: !/(^|[^A-Za-z$]):\d/.test(one(a).cell_identity || ''),
      identity_names_the_helper_and_every_link: ['serverReasonSentence', 'detail']
        .every((token) => (one(a).cell_identity || '').indexOf(token) >= 0)
        && (one(a).cell_identity || '').indexOf('(body as { detail?: unknown } | null)?.detail') >= 0,
      attribute_slot_is_a_different_cell: Boolean(one(attr).cell_id) && one(attr).cell_id !== one(a).cell_id
        && one(attr).rule !== one(a).rule,
      a_different_chain_is_a_different_cell: Boolean(one(wrapped).cell_id) && one(wrapped).cell_id !== one(a).cell_id
        && (one(wrapped).cell_identity || '').indexOf('wrapIt') >= 0,
      a_different_file_is_a_different_cell: one(otherFile).cell_id !== one(a).cell_id,
      the_same_file_under_a_different_root_is_the_same_cell: one(relabeled).cell_id === one(a).cell_id,
      /* The other direction: the same value printed twice in one file is two cells, and an identity that
         cannot say which is which cannot be used to track them. */
      two_renders_are_two_cells: idsOf(twice).length === 2 && new Set(idsOf(twice)).size === 2,
    };
    identity.assertion_met = identity.identity_survives_a_line_shift
      && identity.line_number_is_not_in_the_identity
      && identity.identity_names_the_helper_and_every_link
      && identity.attribute_slot_is_a_different_cell
      && identity.a_different_chain_is_a_different_cell
      && identity.a_different_file_is_a_different_cell
      && identity.the_same_file_under_a_different_root_is_the_same_cell
      && identity.two_renders_are_two_cells;
  } catch (e) {
    identity = { assertion_met: false, error: String((e && e.stack) || e).split(String.fromCharCode(10)).slice(0, 3).join(' | ') };
  }
  ok = ok && Boolean(identity.assertion_met);
  return { ok, out: { schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R7_SELFTEST', ruler: RULER, typescript: ts.version,
    verdict: ok ? 'SELFTEST_PASS' : 'SELFTEST_FAIL', n_fixtures: all.length,
    n_clean_expected: all.filter((r) => r[2] === 0).length, n_bad_expected: all.filter((r) => r[2] !== 0).length,
    n_single_file_assertions_met: all.filter((r) => per[r[0]].assertion_met).length,
    n_cross_file_arms: CROSS_ARMS.length + CROSS_ARMS_EXTRA.length,
    n_mode_arms: MODE_ARMS.length,
    n_mode_arms_met: MODE_ARMS.filter((a) => modes[a.name].assertion_met).length,
    mode_arms: modes,
    n_cross_file_arms_met: CROSS_ARMS.concat(CROSS_ARMS_EXTRA).filter((a) => cross[a.name].assertion_met).length,
    n_slot_arms: R7_ARMS.length,
    n_expectations_moved: all.filter((r) => R7_EXPECTATION_CHANGES[r[0]]).length,
    expectations_moved: Object.keys(R7_EXPECTATION_CHANGES).map((k) => ({ fixture: k, was: R7_EXPECTATION_CHANGES[k].was,
      now: R7_EXPECTATION_CHANGES[k].now, why: R7_EXPECTATION_CHANGES[k].why,
      fixture_blob_sha1: blobSha1(FIXTURES_R3[k] || (FIXTURES_E[k] && FIXTURES_E[k].src)) })),
    n_slot_arms_met: R7_ARMS.filter((a) => slots[a.name].assertion_met).length,
    slot_arms: slots,
    cell_identity_arms: identity,
    cross_file_arms: cross, fixtures: per } };
}

/* ------------------------------------------------------------------ cli */

function main() {
  const argv = process.argv.slice(2);
  const args = {};
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === '--selftest') args.selftest = true;
    else if (argv[i].indexOf('--') === 0) { args[argv[i].slice(2)] = argv[i + 1]; i++; }
  }
  const ts = loadTs();
  if (!ts) {
    // ORD-0579 fallback: without the TypeScript compiler API this ruler cannot do AST data flow.
    // It used to exit 9 with no output, which the landing door read as "instrument failed" and turned
    // into a blanket REFUSED - the arm silently blocked every frontend candidate while claiming it had
    // measured nothing.  Emit an explicit NOT_MEASURED document instead (hits empty BY CONSTRUCTION,
    // not by inspection) so the door can mark the arm skipped without pretending it ran.
    // emit() is not defined yet at this point, so the out file is written directly.
    var exempt = { schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R4',
      verdict: 'NOT_MEASURED_NO_TS_COMPILER', tried: TS_CANDIDATES, hits: [],
      measurement: 'NOT_PERFORMED',
      note: 'AST analysis not performed: the compiler API is unavailable. hits is empty because the '
          + 'scan never ran, NOT because the tree was found clean. Do not read this as a pass.' };
    if (args.out) { try { fs.writeFileSync(args.out, JSON.stringify(exempt, null, 1), 'utf8'); }
                    catch (e) { /* stdout still carries the verdict */ } }
    process.stdout.write(JSON.stringify(exempt, null, 1) + '\n');
    return 0;
  }
  const emit = (obj) => {
    const txt = JSON.stringify(obj, null, 1);
    if (args.out) fs.writeFileSync(args.out, txt, 'utf8');
    process.stdout.write(txt + '\n');
  };
  if (args.selftest) { const r = selftest(ts); emit(r.out); return r.ok ? 0 : 7; }
  if (args.tree) {
    let r;
    const tree = diskTree(args.tree);
    try { r = scanTree(ts, tree); }
    catch (e) {
      const errDoc = JSON.stringify({ schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R5',
        verdict: 'RULER_ERROR', tree: args.tree,
        error: String((e && e.stack) || e).split(String.fromCharCode(10)).slice(0, 4).join(' | ') }, null, 1);
      // r7b wrote this document to stdout only, so a door that runs the ruler with --out saw 'ruler wrote no
      // output (rc 0)' and refused three candidates on 2026-10-08 14:1x for an instrument reason.  The error
      // document now lands wherever the caller asked for the result.
      if (args.out) { try { fs.writeFileSync(args.out, errDoc, 'utf8'); } catch (e2) { /* stdout still carries it */ } }
      process.stdout.write(errDoc + String.fromCharCode(10));
      return 8;
    }
    const perRule = {};
    for (const h of r.hits) perRule[h.rule] = (perRule[h.rule] || 0) + 1;
    /* ORD-0354 asks for the two denominators kept apart: a cell in front of the eye and a cell in an
       attribute are different defects with different fixes, and one blended number lets a lane trade
       one for the other without anyone seeing. */
    const bySlot = { text_position: 0, attribute_position: 0, markup: 0, dom_write: 0 };
    for (const h of r.hits) {
      if (h.sink === 'jsx-text') bySlot.text_position += 1;
      else if (h.sink === 'dom-attribute') bySlot.attribute_position += 1;
      else if (h.sink === 'inner-html') bySlot.markup += 1;
      else bySlot.dom_write += 1;
    }
    const ledger = loadExemptionLedger(args);
    const ex = applyExemptions(r.hits, ledger);
    if (String(ledger.status).indexOf('REJECTED') === 0) {
      // A ledger the ruler cannot trust must not produce a census.  Emitting hits=[] with NOT_PERFORMED is
      // the same honesty rule as the missing-compiler path: an empty list here is empty BY CONSTRUCTION.
      const refused = { schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R8', ruler: RULER,
        verdict: 'EXEMPTION_LEDGER_' + ledger.status, measurement: 'NOT_PERFORMED',
        exemption_ledger: ex, hits: [], tree: args.tree,
        note: 'the exemption ledger was rejected, so the run measured nothing; hits is empty because the '
            + 'census was withheld, NOT because the tree was found clean' };
      if (args.out) fs.writeFileSync(args.out, JSON.stringify(refused, null, 1), 'utf8');
      process.stdout.write(JSON.stringify(refused, null, 1) + String.fromCharCode(10));
      return 0;
    }
    const out = {
      schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R8', ruler: RULER, typescript: ts.version,
      scope: SCOPE_GRAPH,
      scope_note: 'this mode is the one the pre-landing gate must run: it can both clear a value a helper '
        + 'rebuilds from device wording and condemn a value that arrives through an import',
      method: 'whole-graph module resolution: relative specifiers, .ts/.tsx and index files, `export ... from`, '
        + '`export * from`, default and namespace imports. An import binding is answered by the exporting file\'s '
        + 'own data flow, so a helper that returns the answer\'s words reaches the cell in the file that prints '
        + 'it. Package specifiers are recorded unresolved, never guessed at.',
      standing_rule: 'Q64=1 (arbiter): data reaching UI / screenshot / evidence artifacts must pass source classification -> allowed fields -> render. mask is a helper, never the first gate.',
      allowed_fields: ALLOWED_FIELDS,
      forbidden: ['raw body', 'raw detail', 'raw exception', 'the answer\'s own words reaching the DOM by any route, including across a file boundary'],
      tree: args.tree, modules_in_graph: r.modules, files_found: tree.keys.length,
      rules_fired: Object.keys(perRule).sort(), per_rule: perRule,
      unresolved_import_specs: r.unresolved, unresolved_import_count: r.unresolved.length,
      parse_diagnostics_total: r.diagnostics, resolution_depth_cap: MAXD, crossing_budget: MAX_CROSSINGS, crossing_cuts: r.crossing_cuts,
      resolution_truncated_total: r.truncated,
      truncated_meaning: 'how many lookups ran out of depth and had to answer unknown - a clean verdict with a nonzero value is not a proven clean verdict',
      per_file: r.perFile, hits: r.hits,
      exemption_ledger: ex,
      cells_by_slot: bySlot,
      cells_total: r.hits.length,
      cells_product: ex.cells_product, cells_exempt: ex.cells_exempt,
      exempted_cells: ex.exempted_cells,
      attributed_in_fold: r.attributed_in_fold,
      attributed_in_fold_count: r.attributed_in_fold.length,
      fold_without_anchor: r.fold_without_anchor,
      fold_without_anchor_count: r.fold_without_anchor.length,
      exception_definition: 'a text-position cell is exonerated only when the nearest enclosing fold '
        + 'element (a <details>, or any element carrying data-cnx-fold) also holds a data-cnx-field anchor '
        + 'naming one of the six allowed fields. Attribute-position cells are never exonerated, and no class '
        + 'name, test id or comment can open the exception.',
      verdict: r.hits.length ? 'EXPOSURE_SHAPE_FOUND' : 'NO_EXPOSURE_SHAPE_FOUND',
      verdict_product: ex.cells_product ? 'EXPOSURE_SHAPE_FOUND' : 'NO_EXPOSURE_SHAPE_FOUND',
      verdict_product_note: 'verdict counts every cell the ruler saw; verdict_product counts only the ones '
        + 'the exemption ledger left in force. The pre-landing arm compares verdict_product cells.',
      interpretation_limit: 'a hit names a shape to justify, not a defect verdict; unresolved_import_specs lists what this run could not see through',
      claim_kind: 'pattern_determined', claimed_result: null, derived_result: null,
    };
    out.claimed_result = out.verdict + ' over ' + out.modules_in_graph + ' modules: ' + r.hits.length + ' hit(s) '
      + JSON.stringify(Array.from(new Set(r.hits.map(function (h) { return h.rule + '@' + h.file + ':' + h.line; })))).slice(0, 400);
    emit(out);
    return 0;
  }
  const targets = [];
  if (args.file) for (const one of args.file.split(',').filter(Boolean)) targets.push([one, fs.readFileSync(one, 'utf8')]);
  if (args.ref && args.path) {
    let buf;
    try { buf = cp.execFileSync('git', ['-C', REPO, 'show', args.ref + ':' + args.path], { maxBuffer: 64 * 1024 * 1024 }); }
    catch (e) {
      process.stdout.write(JSON.stringify({ schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R4', verdict: 'REFUSED',
        reason: args.ref + ':' + args.path + ' did not resolve', git_stderr: String((e && e.stderr) || '').slice(0, 200) }, null, 1) + '\n');
      return 4;
    }
    targets.push([args.ref.slice(0, 12) + ':' + args.path, buf.toString('utf8')]);
  }
  if (!targets.length) {
    process.stdout.write('usage: node ui_exposure_taint_ast_r2.cjs --tree <dir> | --file a,b,c | --ref <sha> --path <in-tree path> | --selftest  [--out <json>]\n');
    return 2;
  }
  const hits = [];
  const perFile = [];
  let failed = 0, diag = 0, truncated = 0;
  const folded = [], foldless = [];
  for (const [label, text] of targets) {
    let res;
    try { res = scanText(ts, label, text); }
    catch (e) { failed++; hits.push({ rule: 'RULER_ERROR', file: label, line: 0, error: String((e && e.stack) || e).split('\n').slice(0, 3).join(' | ') }); continue; }
    diag += res.diagnostics;
    truncated += res.truncated || 0;
    for (const f of res.attributed_in_fold) { f.file = label; folded.push(f); }
    for (const f of res.fold_without_anchor) { f.file = label; foldless.push(f); }
    perFile.push({ file: label, hits: res.hits.length, parse_diagnostics: res.diagnostics,
      attributed_in_fold: res.attributed_in_fold.length,
      depth_cut_lookups: res.truncated || 0, graph: res.graph });
    hits.push(...res.hits);
  }
  const perRule = {};
  for (const h of hits) perRule[h.rule] = (perRule[h.rule] || 0) + 1;
  const bySlot = { text_position: 0, attribute_position: 0, markup: 0, dom_write: 0 };
  for (const h of hits) {
    if (h.sink === 'jsx-text') bySlot.text_position += 1;
    else if (h.sink === 'dom-attribute') bySlot.attribute_position += 1;
    else if (h.sink === 'inner-html') bySlot.markup += 1;
    else bySlot.dom_write += 1;
  }
  const out = {
    schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R7', ruler: RULER, typescript: ts.version,
    scope: SCOPE_PER_FILE, scope_note: SCOPE_NOTE_PER_FILE,
    upper_bound_claim: 'REFUTED on the live generation: 1 cell here does not exist under --tree and 3 cells '
      + 'under --tree do not exist here; see selftest arms F and G',
    method: 'per-file AST taint through the TypeScript compiler API: poison source, spread along assignment / object-property value / destructure / template hole / call argument by position / return / useState setter, property-path sensitive, fixpoint over the call graph. No regular expression decides anything.',
    standing_rule: 'Q64=1 (arbiter): data reaching UI / screenshot / evidence artifacts must pass source classification -> allowed fields -> render. mask is a helper, never the first gate.',
    allowed_fields: ALLOWED_FIELDS,
    forbidden: ['raw body', 'raw detail', 'raw exception', 'the answer\'s own words reaching the DOM by any route, including a forwarding helper'],
    rules_fired: Object.keys(perRule).sort(), per_rule: perRule,
    files_scanned: targets.length, files_failed: failed, parse_diagnostics_total: diag,
    per_file: perFile,
    cells_by_slot: bySlot,
    cells_total: hits.length,
    attributed_in_fold: folded, attributed_in_fold_count: folded.length,
    fold_without_anchor: foldless, fold_without_anchor_count: foldless.length,
    /* r6's published bytes print 40 here while the analyzer runs with MAXD; that self-report fault is
       declared in the r6 receipt and is fixed in this revision rather than back-ported. */
    resolution_depth_cap: MAXD,
    resolution_truncated_total: truncated,
    truncated_meaning: 'how many times a lookup ran out of depth and had to answer "unknown" - a clean verdict with a nonzero value here is NOT a proven clean verdict',
    targets_scanned: targets.map((t) => t[0]), hits,
    verdict: hits.length ? 'EXPOSURE_SHAPE_FOUND' : 'NO_EXPOSURE_SHAPE_FOUND',
    interpretation_limit: 'a hit names a shape to justify, not a defect verdict',
    claim_kind: 'pattern_determined',
    claimed_result: null, derived_result: null,
  };
  out.claimed_result = out.verdict + ' across ' + targets.length + ' scanned file(s): ' + hits.length + ' hit(s) '
    + JSON.stringify(Array.from(new Set(hits.map((h) => h.rule + '@' + String(h.file).split(/[/:]/).pop() + ':' + h.line)))).slice(0, 400);
  emit(out);
  return 0;
}

if (require.main === module) process.exit(main());
module.exports = { scanText, selftest, loadTs, FIXTURES_R3, FIXTURES_E, blobSha1, cellIdentity };
