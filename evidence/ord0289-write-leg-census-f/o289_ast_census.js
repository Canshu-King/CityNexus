// ORD-0289 · AST census of fetch() call sites in frontend/src (no regex, no tree-sitter guesswork).
// Usage: node o289_ast_census.js <srcDir> <outJson> <typescriptLibDir>
//
// Method (declared, so the numbers can be re-derived):
//   * parse every .ts/.tsx with the TypeScript compiler API, walk the AST;
//   * a "fetch site" = CallExpression whose callee is Identifier `fetch` or PropertyAccess ending in `.fetch`;
//   * method = second argument's `method` property when it is a StringLiteral, or an Identifier/Shorthand that
//     resolves to a StringLiteral in the same file (top-level const/let or a same-function const); anything else
//     is reported as UNRESOLVED rather than guessed — that is exactly the hole in the regex+window口径;
//   * signal = the same options object carries a `signal` property (any value), or the call's second argument is
//     an object literal containing it;
//   * timer = within the SAME CallExpression subtree: AbortSignal.timeout(...) / AbortSignal.abort(...) with a
//     number, or a setTimeout(...) whose callback calls .abort( ; plus the enclosing-statement window is NOT used.
'use strict';
const fs = require('fs');
const path = require('path');

const srcDir = process.argv[2], outJson = process.argv[3], tsLib = process.argv[4];
const ts = require(path.join(tsLib, 'typescript.js'));

function walk(node, cb) {
  cb(node);
  ts.forEachChild(node, (c) => walk(c, cb));
}
function listFiles(dir) {
  let out = [];
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (e.name === 'node_modules' || e.name.startsWith('.')) continue;
    const p = path.join(dir, e.name);
    if (e.isDirectory()) out = out.concat(listFiles(p));
    else if (/\.(ts|tsx)$/.test(e.name) && !/\.d\.ts$/.test(e.name)) out.push(p);
  }
  return out;
}
function strOf(node) {
  if (!node) return null;
  if (ts.isStringLiteral(node) || ts.isNoSubstitutionTemplateLiteral(node)) return node.text;
  if (ts.isTemplateExpression(node) && node.head && node.head.text) return node.head.text;
  return null;
}
function collectStringConsts(sf) {
  // file-scope and function-scope const/let with string initializers, keyed by identifier name
  const map = new Map();
  walk(sf, (n) => {
    if (ts.isVariableDeclaration(n) && ts.isIdentifier(n.name)) {
      const s = strOf(n.initializer);
      if (s !== null) map.set(n.name.text, s);
    }
  });
  return map;
}
function optionsObj(call) {
  const a = call.arguments[1];
  if (!a) return null;
  if (ts.isObjectLiteralExpression(a)) return a;
  return { nonLiteral: a };
}
function prop(obj, name) {
  if (!obj || obj.nonLiteral || !obj.properties) return undefined;
  for (const p of obj.properties) {
    if (ts.isPropertyAssignment(p) && (ts.isIdentifier(p.name) || ts.isStringLiteral(p.name))
        && p.name.text === name) return p.initializer;
    if (ts.isShorthandPropertyAssignment(p) && p.name.text === name) return p.name;
    if (ts.isSpreadAssignment(p)) { /* spread: unknown → caller records it */ }
  }
  return undefined;
}
function hasSpread(obj) {
  return !!(obj && obj.properties && obj.properties.some((p) => ts.isSpreadAssignment(p)));
}
function textOf(node, consts) {
  if (!node) return { method: null, how: 'absent' };
  const lit = strOf(node);
  if (lit !== null) return { method: lit.toUpperCase(), how: 'literal' };
  if (ts.isIdentifier(node) && consts.has(node.text))
    return { method: consts.get(node.text).toUpperCase(), how: 'same-file-const:' + node.text };
  if (ts.isPropertyAccessExpression(node)) {
    const k = node.name.text.toUpperCase();
    if (/^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)$/.test(k)) return { method: k, how: 'member:' + node.getText().slice(0, 40) };
  }
  return { method: null, how: 'unresolved:' + node.getKindName() };
}
function timerInside(call) {
  let timer = null;
  walk(call, (n) => {
    if (ts.isCallExpression(n)) {
      const t = n.expression.getText();
      if (/^AbortSignal\.(timeout|abort)$/.test(t)) timer = timer || ('AbortSignal.' + n.expression.name.text);
      if (t === 'setTimeout') {
        const body = n.arguments[1];
        let aborts = false;
        if (body) walk(body, (x) => { if (ts.isCallExpression(x) && /(^|\.)abort$/.test(x.expression.getText())) aborts = true; });
        if (aborts) timer = timer || 'setTimeout+abort';
      }
    }
  });
  return timer;
}

const files = listFiles(srcDir);
const sites = [];
let parseErrors = [];
for (const f of files) {
  const text = fs.readFileSync(f, 'utf8');
  const sf = ts.createSourceFile(f, text, ts.ScriptTarget.Latest, true,
    f.endsWith('.tsx') ? ts.ScriptKind.TSX : ts.ScriptKind.TS);
  if (sf.parseDiagnostics && sf.parseDiagnostics.length)
    parseErrors.push({ file: path.relative(srcDir, f), n: sf.parseDiagnostics.length,
                       first: ts.flattenDiagnosticMessageText(sf.parseDiagnostics[0].messageText, ' ') });
  const consts = collectStringConsts(sf);
  walk(sf, (n) => {
    if (!ts.isCallExpression(n)) return;
    const callee = n.expression;
    const isFetch = (ts.isIdentifier(callee) && callee.text === 'fetch') ||
                    (ts.isPropertyAccessExpression(callee) && callee.name.text === 'fetch');
    if (!isFetch) return;
    const obj = optionsObj(n);
    const m = textOf(prop(obj, 'method'), consts);
    const pos = sf.getLineAndCharacterOfPosition(n.getStart());
    const fn = obj && obj.nonLiteral ? null : (obj ? prop(obj, 'signal') : null);
    const enclosing = (() => {
      let x = n;
      while (x && !(ts.isFunctionDeclaration(x) || ts.isArrowFunction(x) || ts.isFunctionExpression(x)
                   || ts.isMethodDeclaration(x) || ts.isConstructorDeclaration(x))) x = x.parent;
      if (!x) return '(module)';
      const d = ts.isMethodDeclaration(x) ? x.name.getText()
        : (x.parent && ts.isVariableDeclaration(x.parent) ? x.parent.name.getText() : '(anon)');
      return d + ':' + (sf.getLineAndCharacterOfPosition(x.getStart()).line + 1);
    })();
    sites.push({
      file: path.relative(srcDir, f).replace(/\\/g, '/'),
      line: pos.line + 1, col: pos.character + 1,
      callee: callee.getText(),
      method: m.method, method_how: m.how,
      second_arg: obj ? (obj.nonLiteral ? 'non-literal-expr' : 'object-literal') : 'absent',
      options_spread: hasSpread(obj),
      signal: !!fn || (obj && obj.nonLiteral ? /signal/.test(obj.nonLiteral.getText().slice(0, 400)) : false),
      signal_how: fn ? 'property' : (obj && obj.nonLiteral ? 'text-inside-expr' : 'absent'),
      timer: timerInside(n),
      enclosing_fn: enclosing,
    });
  });
}
const WRITE = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
const writes = sites.filter((s) => s.method && WRITE.has(s.method));
const unresolvedMethod = sites.filter((s) => !s.method && s.second_arg !== 'absent' && s.method_how.startsWith('unresolved'));
const noOpts = sites.filter((s) => s.second_arg === 'absent');
const summary = {
  files_scanned: files.length,
  fetch_sites: sites.length,
  write_sites: writes.length,
  write_with_signal: writes.filter((s) => s.signal).length,
  write_with_timer: writes.filter((s) => s.timer).length,
  read_sites: sites.filter((s) => s.method && !WRITE.has(s.method)).length,
  method_unresolved_with_options: unresolvedMethod.length,
  method_absent_no_options: noOpts.length,
  sites_with_spread_options: sites.filter((s) => s.options_spread).length,
  parse_error_files: parseErrors,
};
fs.writeFileSync(outJson, JSON.stringify({ summary, sites }, null, 1) + '\n');
console.log(JSON.stringify({ srcDir, summary,
  write_detail: writes.map((s) => s.file + ':' + s.line + ' ' + s.method + ' signal=' + s.signal + ' timer=' + s.timer) }, null, 1));
