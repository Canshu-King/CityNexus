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

const RULER = {
  name: 'ui_exposure_taint_ast_r3.cjs',
  supersedes: 'ui_exposure_taint_ast_r2.cjs (r5, same decision, scope reporting added)',
  supersedes_blob: 'ff98091cf3accb0d836ae25ba49820170b92d932',
  also_supersedes_r4: { file: 'ui_exposure_taint_ast_r1.cjs', blob: 'eb262f59e54d5142ad0e8041704e751eac473ace' },
  rule_lineage: 'r1 regex -> r2 regex -> r3 regex -> r4 AST per-file -> r5 AST with the module graph',
  order: 'ORD-0331',
  also_supersedes: { r3: 'ui_exposure_field_check_r3.py', r3_blob: '44e062e6ce9c7b5d97d78e09e432072da102292c' },
  generation: 'r5 / AST taint + module graph',
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
    for (const h of hits) { const k = h.line + '|' + h.rule; if (!m.has(k)) m.set(k, h); }
    return { hits: Array.from(m.values()).sort((a, b) => a.line - b.line), diagnostics, truncated,
      crossingCuts: crossingCuts,
      graph: { bindings: bindings.length, functions: fnOf.size, call_sites: callSites.length,
        state_pairs: statePairs.map((p) => p.get.name + '/' + p.set.name), sinks: sinkList().length } };
  }
  function mkHit(rule, s, o) {
    const line = lineOf(s.node);
    return { rule, line, sink: s.kind, origin_kind: o.kind, function_boundaries: o.boundaries || 0,
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
      for (const h of r.hits) h.file = k;
      hits.push.apply(hits, r.hits);
      perFile.push({ file: k, hits: r.hits.length, parse_diagnostics: r.diagnostics,
        depth_cut_lookups: r.truncated || 0, imports: m.analyzer.importBindings.length,
        exports: m.analyzer.exportedNames.size + m.analyzer.reexportFrom.size + m.analyzer.starFrom.length,
        graph: r.graph });
    }
    hits.sort(function (a, b) { return a.file < b.file ? -1 : a.file > b.file ? 1 : a.line - b.line; });
    return { hits: hits, perFile: perFile, modules: modules.size, diagnostics: diag, truncated: truncated,
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
  for (const h of r.hits) h.file = label;
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
    let res = null, err = null;
    try { res = scanText(ts, name, src); } catch (e) { err = String((e && e.stack) || e).split('\n').slice(0, 3).join(' | '); }
    if (err) { per[name] = { expected: want, observed: null, hits: [], verdict: 'RULER_ERROR', error: err.slice(0, 300), assertion_met: false, note }; ok = false; continue; }
    const good = want === 0 ? res.hits.length === 0 : res.hits.length >= 1;
    ok = ok && good;
    per[name] = { expected: want, observed: res.hits.length, hits: res.hits.map((h) => h.rule),
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
  return { ok, out: { schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R6_SELFTEST', ruler: RULER, typescript: ts.version,
    verdict: ok ? 'SELFTEST_PASS' : 'SELFTEST_FAIL', n_fixtures: all.length,
    n_clean_expected: all.filter((r) => r[2] === 0).length, n_bad_expected: all.filter((r) => r[2] !== 0).length,
    n_single_file_assertions_met: all.filter((r) => per[r[0]].assertion_met).length,
    n_cross_file_arms: CROSS_ARMS.length + CROSS_ARMS_EXTRA.length,
    n_mode_arms: MODE_ARMS.length,
    n_mode_arms_met: MODE_ARMS.filter((a) => modes[a.name].assertion_met).length,
    mode_arms: modes,
    n_cross_file_arms_met: CROSS_ARMS.concat(CROSS_ARMS_EXTRA).filter((a) => cross[a.name].assertion_met).length,
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
    process.stdout.write(JSON.stringify({ schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R4',
      verdict: 'TS_COMPILER_UNAVAILABLE', tried: TS_CANDIDATES,
      note: 'without the compiler API this ruler decides nothing; it never falls back to regex' }, null, 1) + '\n');
    return 9;
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
      process.stdout.write(JSON.stringify({ schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R5',
        verdict: 'RULER_ERROR', tree: args.tree,
        error: String((e && e.stack) || e).split(String.fromCharCode(10)).slice(0, 4).join(' | ') }, null, 1) + String.fromCharCode(10));
      return 8;
    }
    const perRule = {};
    for (const h of r.hits) perRule[h.rule] = (perRule[h.rule] || 0) + 1;
    const out = {
      schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R6', ruler: RULER, typescript: ts.version,
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
      verdict: r.hits.length ? 'EXPOSURE_SHAPE_FOUND' : 'NO_EXPOSURE_SHAPE_FOUND',
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
  for (const [label, text] of targets) {
    let res;
    try { res = scanText(ts, label, text); }
    catch (e) { failed++; hits.push({ rule: 'RULER_ERROR', file: label, line: 0, error: String((e && e.stack) || e).split('\n').slice(0, 3).join(' | ') }); continue; }
    diag += res.diagnostics;
    truncated += res.truncated || 0;
    perFile.push({ file: label, hits: res.hits.length, parse_diagnostics: res.diagnostics,
      depth_cut_lookups: res.truncated || 0, graph: res.graph });
    hits.push(...res.hits);
  }
  const perRule = {};
  for (const h of hits) perRule[h.rule] = (perRule[h.rule] || 0) + 1;
  const out = {
    schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R6', ruler: RULER, typescript: ts.version,
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
    resolution_depth_cap: Number(process.env.CNX_R4_MAXD || 40),
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
module.exports = { scanText, selftest, loadTs, FIXTURES_R3, FIXTURES_E, blobSha1 };
