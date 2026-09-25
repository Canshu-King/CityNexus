
const fs = require("fs");
const path = require("path");
const ts = require(process.argv[3]);
const root = process.argv[2];
const files = [];
(function walk(dir) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== "node_modules") walk(p); }
    else if (/\.(ts|tsx)$/.test(e.name) && !/\.d\.ts$/.test(e.name)) files.push(p);
  }
})(root);
const VERBS = ["POST", "PUT", "PATCH", "DELETE"];
// the string WITHOUT quotes: TS 5.9 leaves `.value` undefined on a plain parsed source file
const lit = (n) => (n && ts.isStringLiteral(n) ? n.text.replace(/^["'`]|["'`]$/g, "") : null);
const out = [];
const keyedMethods = new Map();   // client method name -> where it is defined
const callSites = [];             // every call by name, to join the keyed methods against
for (const f of files) {
  const src = fs.readFileSync(f, "utf8");
  const sf = ts.createSourceFile(f, src, ts.ScriptTarget.Latest, true);
  const rel = path.relative(root, f).replace(/\\/g, "/");
  const textOf = (n) => (n ? n.getText(sf) : null);
  function visit(n, enclosing) {
    let scope = enclosing;
    if (ts.isFunctionDeclaration(n) || ts.isMethodDeclaration(n) || ts.isFunctionExpression(n)
        || ts.isArrowFunction(n)) {
      scope = (n.name && n.name.getText(sf)) || enclosing;
    }
    if (ts.isCallExpression(n)) {
      const callee = n.expression;
      const cname = ts.isPropertyAccessExpression(callee) ? callee.name.getText(sf)
                  : ts.isIdentifier(callee) ? callee.getText(sf) : null;
      if (cname) callSites.push({ file: rel, line: sf.getLineAndCharacterOfPosition(n.getStart()).line + 1,
                                  name: cname, definedIn: scope });
      const init = n.arguments[1] && ts.isObjectLiteralExpression(n.arguments[1]) ? n.arguments[1] : null;
      const isFetch = cname === "fetch";
      const isHelper = cname === "requestJson" || cname === "requestJsonInner" || cname === "postJson";
      if ((isFetch || isHelper) && init) {
        let verb = null, verbShape = "absent", headers = null, signal = false, body = false;
        for (const p of init.properties) {
          if (!ts.isPropertyAssignment(p)) continue;
          const pn = p.name.getText(sf);
          if (pn === "method") { verb = lit(p.initializer);
                                 verbShape = verb === null ? "non-literal" : "literal"; }
          if (pn === "headers") headers = textOf(p.initializer);
          if (pn === "signal") signal = true;
          if (pn === "body") body = true;
        }
        if (verb === null && isHelper && n.arguments[0]) verb = null;
        if (verb && VERBS.includes(String(verb).toUpperCase())) {
          const keyed = /Idempotency-Key/i.test(textOf(n)) || /idempotencyKey/i.test(textOf(n));
          out.push({ file: rel, line: sf.getLineAndCharacterOfPosition(n.getStart()).line + 1,
                     callee: cname, verb: verb, verb_shape: verbShape, keyed: keyed,
                     key_source: keyed ? headers : null, signal: signal, has_body: body,
                     defined_in: scope,
                     via_client_helper: isHelper,
                     text: textOf(n).slice(0, 200) });
        } else if (verbShape === "non-literal") {
          out.push({ file: rel, line: sf.getLineAndCharacterOfPosition(n.getStart()).line + 1,
                     callee: cname, verb: null, verb_shape: verbShape, keyed: false, unresolved: true,
                     defined_in: scope, text: textOf(n).slice(0, 200) });
        }
      }
      // a client method that TAKES an idempotency key as a parameter is a keyed leg even when the call
      // site passes it through
      if ((ts.isMethodDeclaration(n) || ts.isFunctionDeclaration(n)) && scope) {
        const t = textOf(n);
        if (/Idempotency-Key/i.test(t)) {
          keyedMethods.set(scope, { file: rel,
                                    line: sf.getLineAndCharacterOfPosition(n.getStart()).line + 1 });
        }
      }
    }
    ts.forEachChild(n, (c) => visit(c, scope));
  }
  visit(sf, null);
  // top-level object literals of the client: methods are PropertyAssignment -> arrow functions
  function visit2(n, enclosing) {
    let scope = enclosing;
    if (ts.isPropertyAssignment(n) && ts.isArrowFunction(n.initializer)) scope = n.name.getText(sf);
    if (ts.isCallExpression(n) && /Idempotency-Key/i.test(n.getText(sf))) {
      keyedMethods.set(scope || "?", { file: rel,
          line: sf.getLineAndCharacterOfPosition(n.getStart()).line + 1, call_text: n.getText(sf).slice(0, 120) });
    }
    ts.forEachChild(n, (c) => visit2(c, scope));
  }
  visit2(sf, null);
}
const km = [...keyedMethods.entries()].map(([k, v]) => ({ method: k, ...v }));
const consumers = [];
for (const m of km) {
  for (const c of callSites) {
    if (c.name === m.method && !(c.file === m.file && c.line === m.line)) {
      consumers.push({ method: m.method, called_from_file: c.file, called_from_line: c.line });
    }
  }
}
console.log(JSON.stringify({ root: root, files: files.length, write_sites: out,
                             keyed_client_methods: km, keyed_method_consumers: consumers }));
