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
const EXCEPTION_FIELDS = new Set(['message', 'stack', 'trace', 'componentStack', 'component_stack']);
// Methods that hand back data derived from their receiver (boolean answers deliberately absent).
const PASS_THROUGH = new Set(['then', 'catch', 'finally', 'map', 'filter', 'flatMap', 'forEach', 'reduce', 'join',
  'split', 'trim', 'trimStart', 'trimEnd', 'toUpperCase', 'toLowerCase', 'slice', 'substring', 'substr',
  'replace', 'replaceAll', 'concat', 'padStart', 'padEnd', 'toString', 'charAt', 'at', 'reverse', 'sort',
  'find', 'repeat', 'normalize']);

const RULER = {
  name: 'ui_exposure_taint_ast_r1.cjs',
  supersedes: 'ui_exposure_field_check_r3.py',
  supersedes_blob: '44e062e6ce9c7b5d97d78e09e432072da102292c',
  generation: 'r4 / AST taint',
};

/* ------------------------------------------------------------------ analyzer */

function makeAnalyzer(ts, fileName, text) {
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

  const MAXD = Number(process.env.CNX_R4_MAXD || 150);
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
    if (ts.isCallExpression(n)) return callOrigin(n, fn, tail, d);
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
    return o;
  }
  function paramFromCallSites(b, tail, d) {
    const f = b.fn;
    let o = null;
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
      if (b && b.initNode) { const direct = fnOf.get(unwrap(b.initNode)); if (direct) return { f: direct, viaParamOf: b }; }
      for (const f of fnOf.values()) if (f.name === callee.text) return { f };
      if (b && b.kind === 'param') return { fnParam: b };
      return null;
    }
    if (ts.isPropertyAccessExpression(callee)) {
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
    // an unresolvable function: what went in can come out
    let o = null;
    const calleeName = ts.isIdentifier(recvCallee) ? recvCallee.text
      : (ts.isPropertyAccessExpression(recvCallee) ? recvCallee.name.text : null);
    const builtin = calleeName && BUILTIN_FUNCS.has(calleeName);
    for (const a of (call.arguments || [])) {
      const t = valueOf(a, fn, tail, d + 1);
      if (t) { o = through(t, lineOf(call), 'passed through ' + brief(call.expression) + '()', builtin ? false : true); break; }
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
        if (o && o.level === 'envelope') o = through(o, lineOf(s.node), 'the object itself was handed to the DOM, where it is read as text', false);
        if (!o) continue;
        hits.push(mkHit(ruleFor(o, s.kind), s, o));
      }
    }
    const m = new Map();
    for (const h of hits) { const k = h.line + '|' + h.rule; if (!m.has(k)) m.set(k, h); }
    return { hits: Array.from(m.values()).sort((a, b) => a.line - b.line), diagnostics, truncated,
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
  return { run, sf, diagnostics, lineOf, srcOf };
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
  return { ok, out: { schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R4_SELFTEST', ruler: RULER, typescript: ts.version,
    verdict: ok ? 'SELFTEST_PASS' : 'SELFTEST_FAIL', n_fixtures: all.length,
    n_clean_expected: all.filter((r) => r[2] === 0).length, n_bad_expected: all.filter((r) => r[2] !== 0).length,
    n_assertions_met: all.filter((r) => per[r[0]].assertion_met).length, fixtures: per } };
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
    process.stdout.write('usage: node ui_exposure_taint_ast_r1.cjs --file a,b,c | --ref <sha> --path <in-tree path> | --selftest  [--out <json>]\n');
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
    schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R4', ruler: RULER, typescript: ts.version,
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
