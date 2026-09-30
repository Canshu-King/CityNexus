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

const RULER = {
  name: 'ui_exposure_taint_ast_r8.cjs',
  supersedes: 'ui_exposure_taint_ast_r7b4.cjs (blob cefcb38c8d01a5996f3f705531a127c85f16c0b3), which superseded '
    + 'ui_exposure_taint_ast_r7b.cjs (blob d3f66ce9fecd0790981a4fcdeb5e36b1c0fd10f2)',
  supersedes_blob: 'cefcb38c8d01a5996f3f705531a127c85f16c0b3',
  /* ORD-0371's sibling order, one change only: the fold anchor was recognised only in the literal
     `data-cnx-field="..."` spelling, so a compliant element that names its contract field through a
     spread - `{...(notice.field ? { "data-cnx-field": notice.field } : {})}` - was reported as an
     unpaired addition. That cost a real product commit: candidate 25396236063f13827312c33960be0b9510845fc3,
     cell RecoveryRequiredPanel.tsx|UPSTREAM_TEXT_VIA_HELPER_TO_DOM at line 298 (preflight blob
     7d81a39bc11a101333e664b7e737d23fbc7d4cfa). Nothing else about the rule moved: the attribute slot,
     the six fields, and the double trigger all stay, and a spread anchor is honoured ONLY together with
     a provenance label in the same fold. */
  also_supersedes_r4: { file: 'ui_exposure_taint_ast_r1.cjs', blob: 'eb262f59e54d5142ad0e8041704e751eac473ace' },
  rule_lineage: 'r1 regex -> r2 regex -> r3 regex -> r4 AST per-file -> r5 module graph -> r6 scope+prose/structure '
    + '-> r7 attribute slot (Q71) + attributed-fold exoneration (Q67=1 / Q75) '
    + '-> r7b a cell identity that does not move when the file\'s lines move '
    + '-> r7b1 a fold anchor recognised through a spread, but only beside a provenance label '
    + '-> r7b4 ORD-0408 ruling A: a *_code cell is exonerated only by the closed set that the contract in the '
    + 'scanned tree names for that field, never by the field name; a contract declaring no enum for the field is '
    + 'a named red (CONTRACT_MISSING_ENUM) and the cell is not handed to the fold either '
    + '-> r8 ORD-0536: every exemption is looked up in a frozen, in-code table keyed by '
    + '(rule x sink-shape family x origin_kind) plus one measured evidence predicate; every cell is reported '
    + 'before exemption, so an exemption changes a cell\'s verdict and never the denominator, and the table\'s '
    + 'schema is incapable of naming a file, a line or a cell id - which is what "not by the commander\'s hand" '
    + 'means in an instrument',
  order: 'ORD-0536 (structured exemption, this revision) on top of ORD-0408 (r7b4) + ORD-0354 '
    + '(attribute slot + line-independent cell identity) + ORD-0348 (fold exoneration) '
    + '+ the r7b spread-anchor follow-up filed 2026-09-28 03:2x',
  also_supersedes: { r3: 'ui_exposure_field_check_r3.py', r3_blob: '44e062e6ce9c7b5d97d78e09e432072da102292c' },
  generation: 'r8 / AST taint, module graph, both DOM surfaces, exemptions only from the frozen shape table, '
    + 'every cell reported with its verdict',
  /* The local filename now says what generation it is. r4/r5/r6 were published from files named r1/r2/r3,
     which is how a lane can quote a blob and still have nobody know which bytes ran; the mismatch stops here. */
  naming: 'local file name == published generation name from r7 onward',
};

/* ------------------------------------------------------------------ ORD-0536: the exemption table */
/* The order's sentence, in full: "豁免必须由结构化条件决定（哪条规则、哪种 sink 形状、哪个 origin_kind
   组合算已披露），不接受「人在块里写一句就算豁免」".  Two things had to change for that to be true of
   this instrument rather than of a conversation:

   1. Before r8 an exemption was written into the control flow at the point it was discovered
      (`if (ev.ok) ... continue`), so the set of things that could ever be exempted was whatever the
      last revision happened to implement, and there was no single place to read - or to audit.  It is
      now one frozen table, keyed exactly by the three axes the order names.
   2. Before r8 an exempted cell left `hits` and joined a different list, so the denominator moved with
      the exemption: the door-pinned r7b reads 6 cells on the current tip and r7b4 reads 5, and the
      difference is one fold-attributed cell that nobody printed a basis for.  That is the same shape as
      the Q64 arm's absolute-count flaw the commander named in ORD-0536: a comparison on a number that
      moves when the instrument's bookkeeping moves is not a measurement.  In r8 EVERY cell is reported
      with a verdict; an exemption can only change a verdict, never `cells_total`.

   The table cannot express a human decision, and that is the point.  Each entry may carry only
   `id / rules / sink_shape_families / origin_kinds / evidence`, and `validateExemptionTable` refuses
   the file outright (exit 3) if any value looks like a path, a line number, or a cell id - so a lane
   OR the commander cannot add "RecoveryRequiredPanel.tsx line 299 is fine" without the ruler dying on
   the way in.  `evidence` names one of the predicates in EVIDENCE_PREDICATES below; those predicates
   read the rendered structure or the contract in the scanned tree, and there are exactly two of them
   because those are the two disclosures this project has ever ruled on (Q67/Q75 fold-with-anchor, and
   ORD-0408 ruling A's contract-declared closed set).  A third would need an order that names the
   structure, not a wish. */
const EXEMPTION_ENTRY_KEYS = ['id', 'rules', 'sink_shape_families', 'origin_kinds', 'evidence'];

/* The closed set of disclosures this instrument can measure.  A name here must have an implementation in
   `evidenceFor` inside the analyzer, or the run refuses rather than quietly exempting nothing. */
const EVIDENCE_PREDICATES = {
  contract_closed_enum: 'the cell\'s own element names a `*_code` contract field, the contract file in the '
    + 'scanned tree declares a closed enum for it, and no literal on the value\'s chain falls outside that set '
    + '(ORD-0408 ruling A)',
  attributed_fold: 'the nearest enclosing fold element (a <details>, or any element carrying data-cnx-fold) '
    + 'holds a data-cnx-field anchor naming one of the six allowed measured fields, and the value sits in the '
    + 'text position inside that same fold (Q67=1 as ruled by Q75, bounded by Q71)',
};

/* The two disclosures that exist, as data. `evidence` is a key into EVIDENCE_PREDICATES, resolved at
   classification time inside the analyzer, because both predicates need the cell's own AST node. */
const EXEMPTION_TABLE = Object.freeze([
  Object.freeze({
    id: 'EX-1-CONTRACT-CLOSED-ENUM',
    /* ORD-0408 ruling A.  A cell whose own element names a `*_code` contract field is disclosed when the
       contract in THIS tree declares a closed enum for that field and nothing carried on the value's
       chain falls outside it.  Rule-agnostic and slot-agnostic on purpose: the contract set is what
       decides, so the shape axes stay open - but the predicate itself only ever fires when the element
       names a `*_code` field, which is the narrow part. */
    rules: ['*'], sink_shape_families: ['*'],
    origin_kinds: ['raw-body', 'prose', 'named-prose-member', 'exception'],
    evidence: 'contract_closed_enum',
  }),
  Object.freeze({
    id: 'EX-2-ATTRIBUTED-FOLD',
    /* Q67=1 as ruled by Q75, and Q71's boundary: an attributed server sentence is compliant
       attribution only in a TEXT position inside a fold that names which measured field spoke.  The
       family list is the whole of that boundary - `text-in` is the JSX text position; `attribute`
       (a data-attribute or aria-attribute slot) is absent, so an attribute slot can never be folded away, and
       `markup`/`dom` (innerHTML, textContent writes) are absent for the same reason. */
    rules: ['UPSTREAM_TEXT_VIA_HELPER_TO_DOM', 'RAW_BODY_TO_DOM', 'UPSTREAM_READ_DIRECT',
      'UPSTREAM_EXCEPTION_TO_DOM'],
    sink_shape_families: ['text-in', 'text'],
    origin_kinds: ['raw-body', 'prose', 'exception'],
    evidence: 'attributed_fold',
  }),
]);

/* The table's own identity, printed so a later reader can tell whether the bytes that exempted their
   cell are the bytes that are on the shelf now. */
function exemptionTableDigest(table) {
  const canonical = (table || []).map((e) => [e.id, (e.rules || []).join(','),
    (e.sink_shape_families || []).join(','), (e.origin_kinds || []).join(','), e.evidence].join('|'));
  return crypto.createHash('sha1').update(canonical.join('\n')).digest('hex');
}

/* A schema with teeth: reject a table that could name a cell.  Nothing here consults the cell list, the
   file names or the run - it only asks whether an entry is *expressible* as a shape. */
const CELL_SHAPED_VALUE_TESTS = [
  ['PATH_SHAPED', /(^|[\/\\])[\w.-]+[\/\\][\w.\/-]*[\/\\]?/],
  ['FILE_EXTENSION_SHAPED', /\.(tsx?|jsx?|json|ya?ml|md)\b/],
  ['LINE_NUMBER_SHAPED', /(?:^|[^A-Za-z$])\d{2,}(?:$|[^%])/],
  ['CELL_ID_SHAPED', /(^|[^0-9a-f])[0-9a-f]{8,}([^0-9a-f]|$)/],
];
/* The part of a sink shape that a table entry may name: `text-in:p testid=x` is the family `text-in`.
   Used by the validator to reject a whole sink shape in an entry, which would be a cell in disguise. */
function sinkShapeFamily(shape) {
  const s = String(shape || '');
  const i = s.indexOf(':');
  return i < 0 ? s : s.slice(0, i);
}
function validateExemptionTable(table) {
  const problems = [];
  if (!Array.isArray(table) || !table.length) {
    problems.push({ entry: '-', problem: 'EMPTY_TABLE', detail: 'an empty exemption table would exempt nothing, '
      + 'and a ruler that silently exempts nothing has no audit trail; the table is required to be explicit' });
    return { ok: false, problems: problems };
  }
  const seenIds = [];
  for (const entry of table) {
    const id = (entry && entry.id) || '-';
    if (seenIds.indexOf(id) >= 0) problems.push({ entry: id, problem: 'DUPLICATE_ID', detail: id });
    seenIds.push(id);
    for (const k of Object.keys(entry || {})) {
      if (EXEMPTION_ENTRY_KEYS.indexOf(k) < 0) {
        problems.push({ entry: id, problem: 'UNKNOWN_KEY', detail: k + ': an exemption entry may carry only '
          + EXEMPTION_ENTRY_KEYS.join(' / ') });
      }
    }
    if (!/^EX-\d+-[A-Z0-9-]+$/.test(String(id))) {
      problems.push({ entry: id, problem: 'ID_SHAPE', detail: 'expected EX-<n>-<SHAPE-NAME>' });
    }
    if (Object.keys(EVIDENCE_PREDICATES).indexOf(entry.evidence) < 0) {
      problems.push({ entry: id, problem: 'EVIDENCE_NOT_IMPLEMENTED',
        detail: String(entry.evidence) + ': every exemption must be decided by a measured predicate that exists '
          + 'in the analyzer, not by a name' });
    }
    for (const axis of ['rules', 'sink_shape_families', 'origin_kinds']) {
      const v = entry[axis];
      if (!Array.isArray(v) || !v.length) {
        problems.push({ entry: id, problem: 'AXIS_NOT_A_LIST', detail: axis });
        continue;
      }
      for (const item of v) {
        const detail = cellShapedReason(String(item));
        if (detail) problems.push({ entry: id, problem: 'AXIS_NAMES_A_CELL',
          detail: axis + ' carries ' + JSON.stringify(item) + ' which is ' + detail
            + '; an exemption entry may name a rule, a sink-shape family or an origin kind - never a file, '
            + 'a line or a cell id' });
        /* `text-in:p testid=code:plan-ai-reason` is one element on one screen, not a family.  A table
           entry that names a whole sink shape is a per-cell allowlist with the serial numbers filed off,
           so the family axis accepts families only. */
        if (axis === 'sink_shape_families' && item !== '*' && String(item).indexOf(':') >= 0) {
          problems.push({ entry: id, problem: 'FAMILY_NAMES_ONE_SINK',
            detail: axis + ' carries ' + JSON.stringify(item) + '; a family has no `:` in it - '
              + sinkShapeFamily(item) + ' would be the family' });
        }
      }
    }
  }
  return { ok: problems.length === 0, problems: problems };
}
function cellShapedReason(value) {
  if (value === '*') return null;
  for (const [name, re] of CELL_SHAPED_VALUE_TESTS) if (re.test(value)) return name;
  return null;
}

/* What the ruler will not accept from anyone: an input channel for a waiver.  The CLI is the only way a
   caller can talk to this instrument, so the flag list is closed and a waiver-shaped flag is named. */
const CLI_FLAGS_WITH_VALUE = ['tree', 'file', 'ref', 'path', 'out', 'contract'];
const CLI_BOOLEAN_FLAGS = ['selftest'];
const WAIVER_SHAPED_FLAG = /(^|-)(waiv|allow|exempt|baseline|suppress|ignore|approve|accept|skip|known|disclosed)(e|s|-|$)/i;
function parseCliArguments(argv) {
  const args = {};
  const refusals = [];
  for (let i = 0; i < argv.length; i++) {
    const token = String(argv[i]);
    if (token.indexOf('--') !== 0) { refusals.push({ token: token, reason: 'POSITIONAL_ARGUMENT_NOT_ACCEPTED' }); continue; }
    const flag = token.slice(2);
    if (CLI_FLAGS_WITH_VALUE.indexOf(flag) >= 0) { args[flag] = argv[i + 1]; i++; continue; }
    if (CLI_BOOLEAN_FLAGS.indexOf(flag) >= 0) { args[flag] = true; continue; }
    refusals.push({ token: token,
      reason: WAIVER_SHAPED_FLAG.test(flag) ? 'HUMAN_DECLARED_WAIVER_IS_NOT_AN_INPUT_CHANNEL'
        : 'UNRECOGNISED_FLAG',
      accepted: CLI_FLAGS_WITH_VALUE.map((f) => '--' + f).concat(CLI_BOOLEAN_FLAGS.map((f) => '--' + f)),
      note: 'an exemption comes from the frozen shape table applied to what is on the tree, never from an '
        + 'argument, a comment, a class name or a sentence in a ledger block' });
  }
  return { args: args, refusals: refusals };
}

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
  /* Per-cell classification notes, keyed by the node so two cells on one line keep separate facts.  Only
     the exemption pass uses it, and it never survives the run. */
  const cellShapeCache = new Map();
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
  /* r7b1: a spread may be how a component writes the field name the literal spelling would have put
     there. Only syntax that is statically visible resolves: an object literal's own keys, the two
     branches of a conditional, and a single same-file `const x = { ... }` for `{...x}`. Anything
     looser (a prop, a merged object, two candidate declarations) resolves to nothing and is NOT an
     anchor, so this cannot be opened by writing the anchor indirectly. */
  function staticObjectKeys(expr, depth) {
    const d = depth || 0;
    const e = d > 3 ? null : unwrap(expr);
    if (!e) return [];
    if (ts.isObjectLiteralExpression(e)) {
      return e.properties.filter((p) => ts.isPropertyAssignment(p) && p.name).map((p) => ({
        name: p.name.getText(sf).replace(/^["'`]|["'`]$/g, ''), value: p.initializer }));
    }
    if (ts.isConditionalExpression(e))
      return staticObjectKeys(e.whenTrue, d + 1).concat(staticObjectKeys(e.whenFalse, d + 1));
    if (ts.isParenthesizedExpression(e)) return staticObjectKeys(e.expression, d + 1);
    if (ts.isBinaryExpression(e)
        && (e.operatorToken.kind === ts.SyntaxKind.BarBarToken
            || e.operatorToken.kind === ts.SyntaxKind.QuestionQuestionToken))
      return staticObjectKeys(e.right, d + 1);
    if (ts.isIdentifier(e)) {
      const decls = nodes.filter((n) => ts.isVariableDeclaration(n) && n.name && n.name.getText(sf) === e.text
          && n.initializer);
      if (decls.length !== 1) return [];      // ambiguous, or declared elsewhere: not honoured
      /* One declaration is not one value. A `let` that is assigned again later can hold a different
         object at render time, so it names nothing statically and opens nothing - the arm
         R7B1_6 exists because the first version of this guard checked the declaration count only and
         let `let anchor = {...}` plus `anchor = {...}` through. */
      const name = e.text;
      if (nodes.some((n) => ts.isBinaryExpression(n)
          && n.operatorToken.kind === ts.SyntaxKind.EqualsToken
          && n.left.getText(sf) === name)) return [];
      return staticObjectKeys(decls[0].initializer, d + 1);
    }
    return [];
  }
  /* The second half of the double trigger for a dynamically-named field: someone has to say WHO is
     speaking. In the shipped shape that is an i18n label whose key ends in reason/origin/source
     (`recovery.serverReason`, `recovery.deviceReason`), rendered inside the same fold. */
  function provenanceLabelInside(node) {
    let hit = null;
    const walk = (n) => {
      if (hit) return;
      if (ts.isCallExpression(n) && /\bt$|\.t$/.test(n.expression.getText(sf)) && n.arguments.length === 1) {
        const a = unwrap(n.arguments[0]);
        if (a && (ts.isStringLiteral(a) || ts.isNoSubstitutionTemplateLiteral(a))
            && /(^|\.)([a-z]*)(reason|origin|source)$/i.test(a.text)) {
          hit = { key: a.text, line: lineOf(n) };
        }
      }
      if (!hit) ts.forEachChild(n, walk);
    };
    walk(node);
    return hit;
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
      if (ts.isJsxSpreadAttribute(n)) {
        for (const k of staticObjectKeys(n.expression)) {
          if (k.name !== 'data-cnx-field') continue;
          const v = k.value ? unwrap(k.value) : null;
          if (v && (ts.isStringLiteral(v) || ts.isNoSubstitutionTemplateLiteral(v))) {
            // a literal outside the six fields still opens nothing (arm R7_10 keeps that shut)
            if (ANCHOR_FIELDS.indexOf(v.text) >= 0) found.push({ field: v.text, line: lineOf(n) });
            continue;
          }
          found.push({ field: null, dynamic: true, line: lineOf(n),
                       expression: k.value ? k.value.getText(sf).slice(0, 40) : null });
        }
      }
      ts.forEachChild(n, walk);
    };
    walk(node);
    return found.filter((f) => !f.dynamic)[0] || found[0] || null;
  }
  /* ORD-0348 (Q67=1 as ruled by Q75): a server sentence that is *attributed* and *folded* is compliant
     attribution, and the ruler has to be able to tell that apart from the same sentence on the face of
     the screen. The decision is read off the rendered structure: the nearest enclosing fold element --
     a `<details>` or anything carrying `data-cnx-fold` -- decides, and it exonerates only when that
     same container holds an anchor naming which measured field spoke. No fold, or a fold whose label
     was removed, is a hit. The nearest fold decides on purpose: letting an outer container vouch for an
     inner one would be a loophole with a shape a lane could grow. */
  /* Which `*_code` field this cell's OWN element names, if any.  Only the innermost enclosing
     element is consulted, so a code value rendered inside an unrelated shell does not inherit that
     shell's field name; the two readings (the span and the div around it) are two cells. */
  function cnxFieldNamedOnCell(node) {
    for (let cur = node; cur; cur = cur.parent) {
      if (!ts.isJsxElement(cur)) continue;
      const attrs = (cur.openingElement.attributes.properties || [])
        .filter((p) => ts.isJsxAttribute(p));
      for (const at of attrs) {
        if (!at.name || at.name.getText(sf) !== 'data-cnx-field' || !at.initializer) continue;
        let v = at.initializer;
        if (ts.isJsxExpression(v)) v = v.expression;
        if (v && v.kind === ts.SyntaxKind.StringLiteral && /^[a-z][a-z0-9_]*_code$/.test(v.text)) {
          return v.text;
        }
      }
      return null;
    }
    return null;
  }

  function foldContext(node) {
    for (let cur = node.parent; cur; cur = cur.parent) {
      if (!ts.isJsxElement(cur)) continue;
      const tag = cur.openingElement.tagName.getText(sf);
      const isFold = tag === 'details'
        || jsxAttrsOf(cur).some((a) => a.name && a.name.getText(sf) === 'data-cnx-fold');
      if (!isFold) continue;
      const anchor = anchorInside(cur);
      if (!anchor) return { blocked: 'fold_without_attribution_anchor', container: tag,
                            container_line: lineOf(cur.openingElement) };
      /* r7b1: a spread that names the contract field dynamically is honoured, but only beside a
         provenance label - the double trigger survives the new spelling. */
      if (anchor.dynamic) {
        const label = provenanceLabelInside(cur);
        if (!label) return { blocked: 'spread_anchor_without_provenance_label', container: tag,
                             container_line: lineOf(cur.openingElement), anchor_line: anchor.line };
        return { container: tag, container_line: lineOf(cur.openingElement),
                 anchor_field: 'dynamic:' + anchor.expression, anchor_line: anchor.line,
                 provenance_label: label.key, provenance_label_line: label.line };
      }
      return { container: tag, container_line: lineOf(cur.openingElement),
               anchor_field: anchor.field, anchor_line: anchor.line };
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
    /* ORD-0536: the exception, looked up in the table.  A cell that is exempted does not leave the report -
       it keeps its slot in `cells` with a verdict and the basis, so an exemption can never move the
       denominator the pre-landing door compares, and a reader can check the ruling against the file
       instead of trusting the ruler. */
    const cells = [];
    for (const h of m.values()) {
      cells.push(classifyCell(h));
    }
    const kept = cells.filter((c) => c.verdict === 'RED');
    const exempt = cells.filter((c) => c.verdict === 'EXEMPTED');
    /* The r7b4 record shapes stay filled, from this one classification, so a caller that still reads them
       reads the same partition it read before - just with the cell id and the basis now attached. */
    const folded = exempt.filter((c) => c.exemption_id === 'EX-2-ATTRIBUTED-FOLD').map(toFoldRecord);
    const contract_exempted = exempt.filter((c) => c.exemption_id === 'EX-1-CONTRACT-CLOSED-ENUM').map(toContractRecord);
    const contract_blocked = [];
    const foldless = [];
    for (const c of kept) {
      if (c.near_miss && c.near_miss.entry_id === 'EX-1-CONTRACT-CLOSED-ENUM') contract_blocked.push(toBlockedContractRecord(c));
      if (c.near_miss && c.near_miss.entry_id === 'EX-2-ATTRIBUTED-FOLD' && c.near_miss.fold_without_anchor) {
        foldless.push(toFoldlessRecord(c));
      }
    }
    for (const h of kept) delete h._node;
    for (const c of exempt) delete c._node;
    return { hits: kept.sort((a, b) => a.line - b.line), cells: cells, exempted: exempt,
      attributed_in_fold: folded,
      contract_exempted: contract_exempted, contract_blocked: contract_blocked,
      contract: { path: CONTRACT.path, readable: CONTRACT.readable, bytes: CONTRACT.bytes,
        blob: CONTRACT.blob, fields_with_enum: Object.keys(CONTRACT.enums), enums: CONTRACT.enums,
        enum_lines: CONTRACT.enum_lines, enum_forms: CONTRACT.enum_forms,
        auto_discovered: !!CONTRACT.auto, note: CONTRACT.note },
      fold_without_anchor: foldless,
      diagnostics, truncated,
      crossingCuts: crossingCuts,
      graph: { bindings: bindings.length, functions: fnOf.size, call_sites: callSites.length,
        state_pairs: statePairs.map((p) => p.get.name + '/' + p.set.name), sinks: sinkList().length } };
  }
  /* One cell, one verdict, one printed reason.  The table is read in order; the first entry whose three
     shape axes match AND whose evidence predicate measures a disclosure decides.  A cell that matches an
     entry's shape but fails its evidence is reported red *with that entry named*, because "which
     exemption did this one just miss" is the question a lane has to be able to ask without reading the
     analyzer's source. */
  function classifyCell(h) {
    const st = h.structural || {};
    const family = sinkShapeFamily(st.sink_shape || '');
    const origin = st.origin_kind || h.origin_kind || '';
    cellShapeCache.set(h, { family: family, origin: origin });
    let matchedFirst = null;
    const matched = [];
    const misses = [];
    h.sink_shape_family = family;
    h.matched_exemption_entries = matched;
    for (const entry of EXEMPTION_TABLE) {
      const shapeMatches = axisAccepts(entry.rules, h.rule) && axisAccepts(entry.sink_shape_families, family)
        && axisAccepts(entry.origin_kinds, origin);
      if (!shapeMatches) continue;
      matched.push(entry.id);
      const ev = evidenceFor(entry.evidence, h, matchedFirst);
      if (ev.ok) {
        h.verdict = 'EXEMPTED';
        h.exemption_id = entry.id;
        h.exemption_evidence = entry.evidence;
        h.exemption_basis = ev.basis;
        h.exemption_detail = ev.detail;
        h.red_because = null;
        h.near_miss = null;
        return h;
      }
      if (entry.evidence === 'contract_closed_enum' && ev.code_field_named) {
        /* ORD-0408's boundary, kept as a fact about the cell rather than as control flow: a cell whose own
           element names a `*_code` field and cannot show the closed set is red, and it is not for sale to
           the fold either. */
        matchedFirst = { entry_id: entry.id, code_field: ev.field, why: ev.why,
                         examples: ev.examples || [], enum_size: ev.set_size,
                         contract: ev.contract, contract_blob: ev.contract_blob || null,
                         fields_with_enum: ev.fields_with_enum || [] };
        cellShapeCache.set(h, { family: family, origin: origin, contractBlocked: matchedFirst });
      }
      misses.push({ entry_id: entry.id, evidence: entry.evidence,
        why: ev.why || 'EVIDENCE_NOT_MEASURED',
        detail: ev.detail || null, examples: ev.examples || null });
    }
    h.verdict = 'RED';
    h.exemption_id = null;
    h.exemption_evidence = null;
    h.exemption_basis = null;
    h.exemption_detail = null;
    h.red_detail = misses.slice();
    h.red_because = matched.length
      ? 'shape-matched ' + matched.join(' + ') + ' but ' + misses.map(function (x) { return x.why; }).join(' + ')
      : 'no entry of the exemption table covers this shape: rule ' + h.rule + ', sink-shape family '
        + family + ', origin kind ' + (origin || '(none)')
        + '. A red with no candidate entry is Q64 saying the value is on the screen with nothing declared '
        + 'about it - which is the shape this ruler exists to keep visible, not to negotiate';
    h.near_miss = matchedFirst || (matched.length ? nearMissFor(h, matched) : null);
    return h;
  }
  function nearMissFor(h, matchedIds) {
    const blocked = cellShapeCache.get(h) || {};
    if (blocked.contractBlocked) return blocked.contractBlocked;
    if (matchedIds.indexOf('EX-2-ATTRIBUTED-FOLD') >= 0) {
      const ev = evidenceFor('attributed_fold', h, null);
      if (ev.fold_without_anchor) {
        return { entry_id: 'EX-2-ATTRIBUTED-FOLD', fold_without_anchor: true,
                 why: ev.why, fold_container: ev.container, fold_container_line: ev.container_line };
      }
    }
    return null;
  }
  function axisAccepts(list, value) {
    if (!Array.isArray(list)) return false;
    if (list.indexOf('*') >= 0) return true;
    return list.indexOf(value) >= 0;
  }
  /* The only two ways a cell can be shown to be already disclosed.  Both read the tree: one the rendered
     structure, one the contract file.  Neither reads a comment, a class name, a test id, an argument or a
     sentence in any ledger - and `refuse_fold_because_contract` is what keeps ORD-0408's boundary from
     being reopened by the entry that follows it in the table. */
  function evidenceFor(name, h, refuseFoldBecauseContract) {
    if (name === 'contract_closed_enum') {
      const field = cnxFieldNamedOnCell(h._node);
      if (!field) return { ok: false, code_field_named: false, why: 'NO_CODE_FIELD_NAMED_ON_THIS_CELL' };
      const ev = enumTokenEvidence(h, field);
      if (!ev.ok) return { ok: false, code_field_named: true, field: field, why: ev.why,
                           examples: ev.examples || [], enum_size: ev.set_size, contract: ev.contract,
                           contract_blob: ev.contract_blob || null, fields_with_enum: ev.fields_with_enum || [] };
      return { ok: true, basis: ev.basis, detail: { field: field, tokens_seen: ev.tokens,
        enum_size: ev.set_size, contract: ev.contract, contract_blob: ev.contract_blob,
        contract_enum_line: ev.contract_line } };
    }
    if (name === 'attributed_fold') {
      const blocked = (cellShapeCache.get(h) || {}).contractBlocked;
      if (blocked) return { ok: false, why: 'ORD-0408_BOUNDARY_NOT_FOR_SALE_TO_THE_FOLD',
                            detail: { contract_block: blocked } };
      /* The r7b4 boundary is the sink kind, not the family string: only a JSX text child may be folded. */
      if (h.sink !== 'jsx-text') {
        return { ok: false, why: 'SINK_IS_NOT_A_TEXT_POSITION', detail: { sink: h.sink } };
      }
      const context = foldContext(h._node);
      if (!context) return { ok: false, why: 'NO_FOLD_CONTAINER' };
      if (context.blocked) return { ok: false, fold_without_anchor: true, why: context.blocked,
                                    container: context.container, container_line: context.container_line };
      if (context.anchor_field) {
        return { ok: true, basis: 'attributed_fold', detail: { fold_container: context.container,
          fold_container_line: context.container_line, attribution_anchor_field: context.anchor_field,
          attribution_anchor_line: context.anchor_line } };
      }
      return { ok: false, why: 'FOLD_WITHOUT_ANCHOR' };
    }
    throw new Error('EVIDENCE_NOT_IMPLEMENTED:' + name);
  }
  function toFoldRecord(c) {
    return { file_line: c.line, rule: c.rule, sink: c.sink, snippet: c.snippet, taint_chain: c.taint_chain,
      cell_id: c.cell_id, exemption_id: c.exemption_id, exemption_basis: c.exemption_basis,
      fold_container: (c.exemption_detail || {}).fold_container,
      fold_container_line: (c.exemption_detail || {}).fold_container_line,
      attribution_anchor_field: (c.exemption_detail || {}).attribution_anchor_field,
      attribution_anchor_line: (c.exemption_detail || {}).attribution_anchor_line };
  }
  function toContractRecord(c) {
    const d = c.exemption_detail || {};
    return { file_line: c.line, rule: c.rule, sink: c.sink, snippet: c.snippet, taint_chain: c.taint_chain,
      cell_id: c.cell_id, exemption_id: c.exemption_id, basis: c.exemption_basis, field: d.field,
      tokens_seen: d.tokens_seen, enum_size: d.enum_size, contract: d.contract,
      contract_blob: d.contract_blob, contract_enum_line: d.contract_enum_line };
  }
  function toBlockedContractRecord(c) {
    const n = c.near_miss || {};
    return { file_line: c.line, rule: c.rule, sink: c.sink, snippet: c.snippet, cell_id: c.cell_id,
      field: n.code_field, why: n.why, examples: n.examples || [], enum_size: n.enum_size,
      contract: n.contract, contract_blob: n.contract_blob || null,
      fields_with_enum: n.fields_with_enum || [], verdict: 'RED',
      red_because: c.red_because, matched_exemption_entries: c.matched_exemption_entries };
  }
  function toFoldlessRecord(c) {
    const n = c.near_miss || {};
    return { file_line: c.line, rule: c.rule, why: n.why, cell_id: c.cell_id, verdict: 'RED',
      fold_container: n.fold_container, fold_container_line: n.fold_container_line };
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
    const cells = [];
    const perFile = [];
    const folded = [], foldless = [], cex = [], cbk = [];
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
      /* Identity is attached to EVERY cell now, exempted ones included: an exemption that is keyed by
         nothing is an exemption nobody can audit, and the caller that compares two trees compares ids. */
      for (const c of r.cells) { c.file = k; cellIdentity(k, c); }
      cells.push.apply(cells, r.cells);
      for (const f of r.attributed_in_fold) { f.file = k; folded.push(f); }
      for (const f of r.fold_without_anchor) { f.file = k; foldless.push(f); }
      for (const f of (r.contract_exempted || [])) { f.file = k; cex.push(f); }
      for (const f of (r.contract_blocked || [])) { f.file = k; cbk.push(f); }
      hits.push.apply(hits, r.hits);
      perFile.push({ file: k, hits: r.hits.length, cells: r.cells.length,
        exempted: r.cells.length - r.hits.length,
        parse_diagnostics: r.diagnostics,
        attributed_in_fold: r.attributed_in_fold.length,
        contract_exempted: (r.contract_exempted || []).length,
        contract_blocked: (r.contract_blocked || []).length,
        depth_cut_lookups: r.truncated || 0, imports: m.analyzer.importBindings.length,
        exports: m.analyzer.exportedNames.size + m.analyzer.reexportFrom.size + m.analyzer.starFrom.length,
        graph: r.graph });
    }
    hits.sort(function (a, b) { return a.file < b.file ? -1 : a.file > b.file ? 1 : a.line - b.line; });
    cells.sort(function (a, b) { return a.file < b.file ? -1 : a.file > b.file ? 1 : a.line - b.line; });
    return { hits: hits, cells: cells, attributed_in_fold: folded, fold_without_anchor: foldless,
      contract_exempted: cex, contract_blocked: cbk,
      contract: { path: CONTRACT.path, readable: CONTRACT.readable,
        bytes: CONTRACT.bytes, blob: CONTRACT.blob,
        fields_with_enum: Object.keys(CONTRACT.enums), enums: CONTRACT.enums, enum_lines: CONTRACT.enum_lines,
        enum_forms: CONTRACT.enum_forms,
        auto_discovered: !!CONTRACT.auto, note: CONTRACT.note },
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
  for (const c of r.cells) { c.file = label; cellIdentity(label, c); }
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
  /* r7b1: the fold anchor written as a spread. The first two are the acceptance the commander asked
     for on the shipped file (candidate 25396236063f13827312c33960be0b9510845fc3): with the provenance
     label present the cell moves into `attributed_in_fold`; delete that label and it comes back.
     The rest are the boundaries: a `{...obj}` is honoured only when obj resolves to one local object
     literal, and a literal field outside the six still opens nothing, spread or not. */
  { name: "R7B1_1_shipped_shape_spread_anchor_beside_a_provenance_label", file: "r7b1_1.tsx",
    expect_hits: 0, expect_folded: 1,
    src: R7_SERVER + 'export function X({ notice }: { notice: { quote: string | null; field: string } }) {\n'
      + '  const sentence = serverReasonSentence(body);\n'
      + '  return <details data-testid="recovery-technical"><summary>x</summary>'
      + '<span data-testid="recovery-detail-kind">{notice.field === "server" ? t("recovery.serverReason")'
      + ' : t("recovery.deviceReason")}</span>'
      + '<code data-testid="recovery-reason"'
      + '{...(notice.field ? { "data-cnx-field": notice.field } : {})}>{sentence}</code></details>;\n}\n' },
  { name: "R7B1_2_the_provenance_label_deleted_so_the_cell_returns", file: "r7b1_2.tsx",
    expect_hits: 1, expect_folded: 0,
    src: R7_SERVER + 'export function X({ notice }: { notice: { quote: string | null; field: string } }) {\n'
      + '  const sentence = serverReasonSentence(body);\n'
      + '  return <details data-testid="recovery-technical"><summary>x</summary>'
      + '<code data-testid="recovery-reason"'
      + '{...(notice.field ? { "data-cnx-field": notice.field } : {})}>{sentence}</code></details>;\n}\n' },
  { name: "R7B1_3_object_spread_resolved_to_one_local_literal", file: "r7b1_3.tsx",
    expect_hits: 0, expect_folded: 1,
    src: R7_SERVER + 'const reasonAnchor = { "data-cnx-field": "http_status", "data-testid": "r" };\n'
      + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <details><summary>x</summary><code {...reasonAnchor}>{sentence}</code></details>;\n}\n' },
  { name: "R7B1_4_an_unresolvable_spread_opens_nothing", file: "r7b1_4.tsx", expect_hits: 1, expect_folded: 0,
    src: R7_SERVER + 'export function X({ extra }: { extra: Record<string, string> }) {\n'
      + '  const sentence = serverReasonSentence(body);\n'
      + '  return <details><summary>x</summary><code {...extra}>{sentence}</code></details>;\n}\n' },
  /* The single-declaration requirement is what stops `{...obj}` from becoming "whichever object the
     author meant": with two candidates in the same file the spread resolves to nothing and the cell
     stays. This arm exists because the mutation harness found the `decls.length === 1` guard had no
     test at all - R7B1_4 exercises a prop, which is the zero-candidate case, not the ambiguous one. */
  { name: "R7B1_6_two_candidate_declarations_resolve_to_nothing", file: "r7b1_6.tsx",
    expect_hits: 1, expect_folded: 0,
    src: R7_SERVER + 'let reasonAnchor = { "data-cnx-field": "http_status" };\n'
      + 'reasonAnchor = { "data-cnx-field": "body_bytes" };\n'
      + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <details><summary>x</summary><code {...reasonAnchor}>{sentence}</code></details>;\n}\n' },
  { name: "R7B1_5_a_literal_field_outside_the_six_opens_nothing_via_spread", file: "r7b1_5.tsx",
    expect_hits: 1, expect_folded: 0,
    src: R7_SERVER + 'const wrongAnchor = { "data-cnx-field": "server_message" };\n'
      + 'export function X() { const sentence = serverReasonSentence(body);\n'
      + '  return <details><summary>x</summary><code {...wrongAnchor}>{sentence}</code></details>;\n}\n' },
  /* Two declarations sharing a name is the other way a `{...obj}` anchor could be asserted without
     saying which object speaks; the resolution refuses to guess, and this arm is what keeps the
     "exactly one declaration" guard from rotting into "whichever one the walker found first". */
  { name: "R7B1_7_two_declarations_with_one_name_resolve_to_nothing", file: "r7b1_7.tsx",
    expect_hits: 1, expect_folded: 0,
    src: R7_SERVER + 'function A() { const anchor = { "data-cnx-field": "http_status" };\n'
      + '  return <p>{anchor["data-cnx-field"]}</p>;\n}\n'
      + 'export function X() { const anchor = { "data-testid": "b" };\n'
      + '  const sentence = serverReasonSentence(body);\n'
      + '  return <details><summary>x</summary><code {...anchor}>{sentence}</code></details>;\n}\n' },
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

/* ------------------------------------------------------------------ ORD-0536 report shapes */
/* One row per cell, so a caller can compare two trees by identity and see the verdict that goes with
   each id.  `hits` stays the red list for the pre-landing door's existing readers. */
function describeCellForReport(c) {
  const st = c.structural || {};
  return { cell_id: c.cell_id, cell_identity: c.cell_identity, rule: c.rule, file: c.file, line: c.line,
    sink: c.sink, sink_shape: st.sink_shape, sink_shape_family: c.sink_shape_family,
    origin_kind: c.origin_kind, verdict: c.verdict, exemption_id: c.exemption_id || null,
    exemption_evidence: c.exemption_evidence || null, exemption_basis: c.exemption_basis || null,
    red_because: c.red_because || null, red_detail: c.red_detail || null, snippet: c.snippet,
    matched_exemption_entries: (c.matched_exemption_entries || []).slice() };
}
function exemptionLedger(cells) {
  return (cells || []).filter(function (c) { return c.verdict === 'EXEMPTED'; })
    .map(function (c) {
      const st = c.structural || {};
      return { rule: c.rule, file: c.file, line: c.line, cell_id: c.cell_id,
        sink_shape: st.sink_shape, sink_shape_family: c.sink_shape_family, origin_kind: c.origin_kind,
        exemption_id: c.exemption_id, evidence: c.exemption_evidence, basis: c.exemption_basis,
        measured_on_tree: c.exemption_detail || null, snippet: c.snippet,
        taint_chain: c.taint_chain };
    });
}
/* The table reports on itself every run: its digest, its entries as data, and the verdict of the schema
   check that keeps it shape-only.  A reader can therefore tell which bytes exempted a cell, and can see
   that a per-cell entry would not have been loadable. */
function tableSelftest() {
  return { file: RULER.name, digest_sha1: exemptionTableDigest(EXEMPTION_TABLE),
    entry_count: EXEMPTION_TABLE.length,
    entries: EXEMPTION_TABLE.map(function (e) { return {
      id: e.id, rules: e.rules.slice(), sink_shape_families: e.sink_shape_families.slice(),
      origin_kinds: e.origin_kinds.slice(), evidence: e.evidence }; }),
    entry_schema: EXEMPTION_ENTRY_KEYS,
    evidence_predicates: Object.keys(EVIDENCE_PREDICATES),
    evidence_definitions: EVIDENCE_PREDICATES,
    schema_check: validateExemptionTable(EXEMPTION_TABLE),
    cell_naming: 'rejected_by_schema',
    cli_accepts: CLI_FLAGS_WITH_VALUE.map(function (f) { return '--' + f; })
      .concat(CLI_BOOLEAN_FLAGS.map(function (f) { return '--' + f; })),
    waiver_input: 'no command-line flag, environment variable, comment, class name, test id or ledger '
      + 'sentence is read by this ruler; a waiver-shaped flag is refused with a named reason' };
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
  /* ---------------------------------------------------------------- ORD-0536: the exemption arms.
     Each arm is a pair: the same cell with the disclosure present, and without it.  A single-direction
     arm could be satisfied by a table that exempts everything or by one that exempts nothing, and the
     order explicitly asks for both directions ("一格应当豁免、一格不应当"). */
  let exemptions = {};
  let savedContract = null;
  try {
    savedContract = CONTRACT;
    const verdictsOf = (res) => (res.cells || []).map((c) => ({
      verdict: c.verdict, rule: c.rule, line: c.line, cell_id: c.cell_id,
      exemption_id: c.exemption_id || null, why: c.verdict === 'RED' ? c.red_because : c.exemption_basis,
      measured: c.exemption_detail || null, near_miss: c.near_miss || null }));
    const foldPair = {
      with_anchor: R7_SERVER + 'export function X({ status }: { status: number }) { const sentence = serverReasonSentence(body);\n'
        + '  return <details><summary>x</summary><span data-cnx-field="http_status">{String(status)}</span>'
        + '<span>{sentence}</span></details>; }',
      comment_only: R7_SERVER + 'export function X({ status }: { status: number }) { const sentence = serverReasonSentence(body);\n'
        + '  return <details><summary>x</summary>{/* data-cnx-field="http_status" */}'
        + '<span>{sentence}</span></details>; }',
      class_only: R7_SERVER + 'export function X({ status }: { status: number }) { const sentence = serverReasonSentence(body);\n'
        + '  return <details className="cnx-fold" data-cnx-anchor="http_status"><summary>x</summary>'
        + '<span>{sentence}</span></details>; }',
    };
    const run1 = scanText(ts, 'frontend/src/exemption/FoldWithAnchor.tsx', foldPair.with_anchor);
    const run2 = scanText(ts, 'frontend/src/exemption/FoldCommentOnly.tsx', foldPair.comment_only);
    exemptions.fold_pair = {
      expected: 'one cell each; the anchored fold is EXEMPTED by EX-2-ATTRIBUTED-FOLD, the comment-spelled '
        + 'anchor stays RED with the fold named as the near miss',
      with_anchor: { cells: run1.cells.length, red: run1.hits.length, verdicts: verdictsOf(run1) },
      comment_only: { cells: run2.cells.length, red: run2.hits.length, verdicts: verdictsOf(run2) },
      cell_ids_are_the_same_shapeapart_from_the_anchor: run1.cells[0] && run2.cells[0]
        ? run1.cells[0].cell_id !== run2.cells[0].cell_id : false,
      denominator_did_not_move: run1.cells.length === run2.cells.length,
      assertion_met: run1.cells.length === 1 && run1.hits.length === 0 && run1.cells[0].exemption_id === 'EX-2-ATTRIBUTED-FOLD'
        && run2.cells.length === 1 && run2.hits.length === 1 && run2.hits[0].near_miss
        && run2.hits[0].near_miss.entry_id === 'EX-2-ATTRIBUTED-FOLD'
        && run2.hits[0].near_miss.fold_without_anchor === true,
      fixture_blobs: Object.keys(foldPair).map((k) => ({ name: k, sha1: blobSha1(foldPair[k]) })),
    };
    /* A class name is not a fold marker and an attribute-spelled anchor on the container is not an
       inside-fold anchor: the third reading stays red for a different named reason. */
    const run3 = scanText(ts, 'frontend/src/exemption/FoldClassOnly.tsx', foldPair.class_only);
    exemptions.class_name_opens_nothing = { cells: run3.cells.length, red: run3.hits.length,
      verdicts: verdictsOf(run3),
      assertion_met: run3.cells.length === 1 && run3.hits.length === 1
        && run3.hits[0].near_miss && run3.hits[0].near_miss.fold_without_anchor === true,
      note: 'className="cnx-fold" is a style hook and data-cnx-anchor is not data-cnx-field; the fold must be '
        + 'a <details> or carry data-cnx-fold, and the anchor must name one of the six measured fields' };
    /* EX-1 in both directions, on a fixture whose cell is LIVE - verified before it was written in here:
       the helper must hand the value over across a function boundary from a caught cause, or a
       `*_code` span produces no cell and the arm would "pass" by measuring nothing (the trap my own
       ORD-0408 instrument names).  The closed set is installed for the arm and restored straight after,
       so the reading cannot drift with whatever the product contract declares on the day. */
    const CODE_HELPER = 'function refusalReasonCode(cause: unknown): string | null {\n'
      + '  if (typeof cause !== "object" || cause === null) return null;\n'
      + '  const env = (cause as { envelope?: unknown }).envelope;\n'
      + '  if (typeof env !== "object" || env === null) return null;\n'
      + '  const error = (env as Record<string, unknown>).error;\n'
      + '  if (typeof error === "object" && error !== null) {\n'
      + '    const c = (error as Record<string, unknown>).reason_code;\n'
      + '    if (typeof c === "string" && c.trim()) return c;\n  }\n'
      + '  const top = (env as Record<string, unknown>).reason_code;\n'
      + '  return typeof top === "string" && top.trim() ? top : null;\n}\n';
    const CODE_PRINT = 'export function X() { let code: string | null = null;\n'
      + '  try { doIt(); } catch (cause) { code = refusalReasonCode(cause); }\n'
      + '  return <span data-cnx-field="reason_code">{String(code)}</span>; }\n';
    const CODE_WITH_INVENTED_TOKEN = CODE_PRINT.replace('refusalReasonCode(cause);',
      'refusalReasonCode(cause) || "NOT_A_REAL_CODE";');
    const FOLDED_CODE_PRINT = 'export function X({ status }: { status: number }) { let code: string | null = null;\n'
      + '  try { doIt(); } catch (cause) { code = refusalReasonCode(cause) || "NOT_A_REAL_CODE"; }\n'
      + '  return <details><summary>x</summary><span data-cnx-field="http_status">{String(status)}</span>'
      + '<span data-cnx-field="reason_code">{String(code)}</span></details>; }\n';
    const syntheticSetOf = function (tokens, line) {
      return { path: 'synthetic://contracts/openapi.yaml', readable: true, bytes: 0, blob: null,
        enums: { reason_code: tokens }, enum_lines: { reason_code: line },
        enum_forms: { reason_code: 'inline' }, forms: {}, note: 'SYNTHETIC_FOR_SELFTEST_ARM' };
    };
    CONTRACT = syntheticSetOf(['JOURNEY_NOT_FOUND', 'PLACE_NOT_FOUND'], 7);
    const runIn = scanText(ts, 'frontend/src/exemption/CodeInSet.tsx', CODE_HELPER + CODE_PRINT);
    const runOutside = scanText(ts, 'frontend/src/exemption/CodeOutsideSet.tsx', CODE_HELPER + CODE_WITH_INVENTED_TOKEN);
    const runFolded = scanText(ts, 'frontend/src/exemption/CodeFoldedButOutsideTheSet.tsx', CODE_HELPER + FOLDED_CODE_PRINT);
    CONTRACT = syntheticSetOf([], 0);
    const runNoSet = scanText(ts, 'frontend/src/exemption/CodeWithNoDeclaredSet.tsx', CODE_HELPER + CODE_PRINT);
    CONTRACT = savedContract;
    exemptions.contract_pair = {
      expected: 'a cell whose own element names a `*_code` field and whose contract declares the closed set '
        + 'is EXEMPTED by EX-1-CONTRACT-CLOSED-ENUM, printing the enum line; a token outside the set, and a '
        + 'field with no declared set, both stay RED',
      inside_the_set: { cells: runIn.cells.length, red: runIn.hits.length, verdicts: verdictsOf(runIn) },
      token_outside_the_set: { cells: runOutside.cells.length, red: runOutside.hits.length,
        verdicts: verdictsOf(runOutside) },
      no_set_declared: { cells: runNoSet.cells.length, red: runNoSet.hits.length, verdicts: verdictsOf(runNoSet) },
      denominators_do_not_move: runIn.cells.length === runOutside.cells.length
        && runOutside.cells.length === runNoSet.cells.length,
      assertion_met: runIn.cells.length === 1 && runIn.hits.length === 0
        && runIn.cells[0].exemption_id === 'EX-1-CONTRACT-CLOSED-ENUM'
        && !!runIn.cells[0].exemption_detail && runIn.cells[0].exemption_detail.contract_enum_line === 7
        && runOutside.cells.length === 1 && runOutside.hits.length === 1
        && !!runOutside.hits[0].near_miss
        && runOutside.hits[0].near_miss.why === 'value_not_in_the_contract_set'
        && runNoSet.cells.length === 1 && runNoSet.hits.length === 1
        && !!runNoSet.hits[0].near_miss && runNoSet.hits[0].near_miss.why === 'CONTRACT_MISSING_ENUM',
      contract_note: 'the live product contract is not consulted by this arm; the set is installed for the '
        + 'arm and restored, so the reading cannot change because the product file changed',
    };
    /* The ORD-0408 interlock stated as a table property: EX-2 sits AFTER EX-1, and a cell the contract
       named red must not be rescued on shape alone by the entry that follows it.  This fixture is the
       blocked cell wrapped in a fold that carries a legal anchor, which is the most tempting rescue
       available in the table. */
    CONTRACT = syntheticSetOf(['JOURNEY_NOT_FOUND'], 7);
    const runInterlocked = scanText(ts, 'frontend/src/exemption/ContractBlocksWithTheFold.tsx',
      CODE_HELPER + FOLDED_CODE_PRINT);
    CONTRACT = savedContract;
    exemptions.contract_is_not_for_sale_to_the_fold = {
      cells: runInterlocked.cells.length, red: runInterlocked.hits.length,
      verdicts: verdictsOf(runInterlocked),
      assertion_met: runInterlocked.cells.length === 1 && runInterlocked.hits.length === 1
        && !!runInterlocked.hits[0].near_miss
        && runInterlocked.hits[0].near_miss.entry_id === 'EX-1-CONTRACT-CLOSED-ENUM',
      note: 'the fold and its http_status anchor are both present and legal; the cell still reads red '
        + 'because the contract refused it first' };
    /* Why the attribute slot has no rescue: the family axis of the fold entry does not include it.  This
       is Q71 kept as data rather than as control flow, and it is the reason the tip's attribute cell is
       reported red with a named reason instead of being argued about. */
    exemptions.fold_family_excludes_the_attribute_slot = {
      ex2_families: (EXEMPTION_TABLE.filter(function (e) { return e.id === 'EX-2-ATTRIBUTED-FOLD'; })
        [0] || {}).sink_shape_families,
      attribute_family_is_its_own: sinkShapeFamily('attribute:data-cnx-field') === 'attribute',
      assertion_met: ((EXEMPTION_TABLE.filter(function (e) { return e.id === 'EX-2-ATTRIBUTED-FOLD'; })[0] || {})
        .sink_shape_families || []).indexOf('attribute') < 0,
    };
    /* The interlock that ORD-0408 bought, tested here because the fold shape is virtual-safe: a cell the
       contract names red must not be rescued by the fold entry that follows it in the table.  The shipped
       panel's own cell shows the same thing on real bytes, but this arm keeps it inside `--selftest`. */
    const anchorFieldsOf = ['http_status', 'content_type', 'body_bytes', 'response_received', 'elapsed_ms',
      'request_id'];
    exemptions.fold_family_excludes_the_attribute_slot = {
      /* Why this belongs to an exemption order at all: the one shape that used to be able to argue its way
         out of an attribute cell was "it is only a data- attribute, nobody reads it".  Q71 closed that, and
         the table keeps it closed - no family on the fold entry is `attribute`. */
      ex2_families: (EXEMPTION_TABLE.filter(function (e) { return e.id === 'EX-2-ATTRIBUTED-FOLD'; })
        [0] || {}).sink_shape_families,
      attribute_is_a_family_of_its_own: anchorFieldsOf.length > 0
        && sinkShapeFamily('attribute:data-cnx-field') === 'attribute'
        && ((EXEMPTION_TABLE.filter(function (e) { return e.id === 'EX-2-ATTRIBUTED-FOLD'; })[0] || {})
          .sink_shape_families || []).indexOf('attribute') < 0,
      assertion_met: ((EXEMPTION_TABLE.filter(function (e) { return e.id === 'EX-2-ATTRIBUTED-FOLD'; })[0] || {})
        .sink_shape_families || []).indexOf('attribute') < 0,
    };
    /* The table itself: it must not be able to say anything as narrow as one cell. */
    const rejected = [
      { id: 'EX-9-FILE', rules: ['RAW_BODY_TO_DOM'], sink_shape_families: ['text-in'],
        origin_kinds: ['raw-body'], evidence: 'attributed_fold', file: 'features/poster/Poster.tsx' },
      { id: 'EX-9-LINE', rules: ['RAW_BODY_TO_DOM'], sink_shape_families: ['text-in'],
        origin_kinds: ['raw-body'], evidence: 'attributed_fold', line: 299 },
      { id: 'EX-9-CELL', rules: ['RAW_BODY_TO_DOM'], sink_shape_families: ['text-in'],
        origin_kinds: ['raw-body'], evidence: 'attributed_fold', cell_id: '3da2ddc1783bb8e4' },
      { id: 'EX-9-SHAPE', rules: ['RAW_BODY_TO_DOM'],
        sink_shape_families: ['text-in:details testid=code:plan-ai-reason'],
        origin_kinds: ['raw-body'], evidence: 'attributed_fold' },
      { id: 'EX-9-EVIDENCE', rules: ['RAW_BODY_TO_DOM'], sink_shape_families: ['text-in'],
        origin_kinds: ['raw-body'], evidence: 'commander_said_so' },
    ];
    const rejects = rejected.map((entry) => ({ attempted: entry.id,
      problems: validateExemptionTable([entry]).problems.map((p) => p.problem) }));
    exemptions.table_cannot_name_a_cell = {
      live_table_check: validateExemptionTable(EXEMPTION_TABLE),
      rejected_attempts: rejects,
      assertion_met: validateExemptionTable(EXEMPTION_TABLE).ok
        && rejects.every((r) => r.problems.length > 0)
        && rejects[0].problems.indexOf('UNKNOWN_KEY') >= 0
        && rejects[1].problems.indexOf('UNKNOWN_KEY') >= 0
        && rejects[2].problems.indexOf('UNKNOWN_KEY') >= 0
        && rejects[3].problems.indexOf('FAMILY_NAMES_ONE_SINK') >= 0
        && rejects[4].problems.indexOf('EVIDENCE_NOT_IMPLEMENTED') >= 0,
    };
    /* And the input channel: a waiver-shaped flag must be refused rather than ignored. */
    const waiver = parseCliArguments(['--tree', 'x', '--waive-cell', '--approve-ruler']);
    const unknown = parseCliArguments(['--tree', 'x', '--colour']);
    const legit = parseCliArguments(['--tree', 'x', '--out', 'y.json']);
    const waiversNamed = waiver.refusals.filter((r) => r.reason === 'HUMAN_DECLARED_WAIVER_IS_NOT_AN_INPUT_CHANNEL');
    exemptions.no_waiver_input_channel = {
      waiver_refusals: waiver.refusals, unknown_refusals: unknown.refusals, legit_refusals: legit.refusals,
      waiver_shaped_flags_refused: waiversNamed.map((r) => r.token),
      assertion_met: waiversNamed.length === 2
        && unknown.refusals.length === 1 && unknown.refusals[0].reason === 'UNRECOGNISED_FLAG'
        && legit.refusals.length === 0 && Object.keys(legit.args).length === 2,
      note: 'the accepted flag list is closed; a waiver-shaped flag is refused with its own named reason, an '
        + 'unknown flag is refused rather than ignored, and a real run accepts only what it recognises',
    };
    /* The shape the commander named as the hard one: a candidate that opens a new upstream-prose path into
       a SHARED helper gains cells in files it never touched.  No entry of the table may clear those, and
       this arm proves the ruler reports them red on a three-module tree rather than by a file-authorship
       rule (which the table cannot express). */
    const sharedHelperTree = {
      'frontend/src/features/shared/helper.ts': 'export function helper(b: unknown): string {\n'
        + '  const d = (b as { detail?: unknown } | null)?.detail;\n'
        + '  if (typeof d === "string") return d;\n  return "";\n}\n',
      'frontend/src/features/trip/TripItinerary.tsx': 'import { helper } from "../shared/helper";\n'
        + 'export function Row({ body }: { body: unknown }) { return <p>{helper(body)}</p>; }\n',
      'frontend/src/features/checkin/CheckInPanel.tsx': 'import { helper } from "../shared/helper";\n'
        + 'export function Panel({ body }: { body: unknown }) { return <p data-testid="ci">{helper(body)}</p>; }\n',
    };
    const sharedRun = scanTree(ts, virtualTree(sharedHelperTree));
    const sharedRed = (sharedRun.cells || []).filter((c) => c.verdict === 'RED');
    const sharedFiles = Array.from(new Set((sharedRun.cells || []).map((c) => c.file)));
    exemptions.new_call_site_into_a_shared_helper_is_not_exemptible = {
      cells: sharedRun.cells.length, red: sharedRed.length, files: sharedFiles,
      red_cells: sharedRed.map((c) => c.file + ':' + c.line + ' ' + c.rule + ' ' + c.red_because).slice(0, 4),
      assertion_met: sharedRun.cells.length >= 2 && sharedRed.length === sharedRun.cells.length
        && sharedFiles.length >= 2,
      note: 'the same helper prints the answer\'s words in two files at once; every cell is red in both, '
        + 'including in the file a candidate never opened - which is the ORD-0500 shape, and the table has '
        + 'no entry that could clear it because authorship is not one of the three axes',
    };
    /* No capability drift: r8 claims to only *re-describe* what r7b4 decided, so for every published
       fold/slot arm the partition must come back the same way - the cells that used to reach `hits` are
       still RED, the ones that used to reach `attributed_in_fold` are now EXEMPTED with a basis.  An
       exemption table that quietly widened would fail here, and one that quietly narrowed would too. */
    const driftRows = [];
    for (const arm of R7_ARMS) {
      const res = scanText(ts, arm.file, arm.src);
      driftRows.push({ arm: arm.name, expect_red: arm.expect_hits, observed_red: res.hits.length,
        expect_exempted: arm.expect_folded, observed_exempted: res.cells.length - res.hits.length,
        cells_total: res.cells.length,
        met: res.hits.length === arm.expect_hits
          && res.cells.length === arm.expect_hits + arm.expect_folded });
    }
    exemptions.no_drift_against_the_published_partition = {
      arms: driftRows.length, met: driftRows.filter((r) => r.met).length,
      mismatches: driftRows.filter((r) => !r.met),
      assertion_met: driftRows.every((r) => r.met),
      note: 'compared against the R7_ARMS expectations shipped in the published ruler, not against a number '
        + 'this revision wrote',
    };
    const EXEMPTION_ARM_NAMES = ['fold_pair', 'class_name_opens_nothing', 'contract_pair',
      'contract_is_not_for_sale_to_the_fold', 'fold_family_excludes_the_attribute_slot',
      'table_cannot_name_a_cell', 'no_waiver_input_channel',
      'new_call_site_into_a_shared_helper_is_not_exemptible',
      'no_drift_against_the_published_partition'];
    exemptions.arm_names = EXEMPTION_ARM_NAMES;
    exemptions.n_arms = EXEMPTION_ARM_NAMES.length;
    exemptions.n_arms_met = EXEMPTION_ARM_NAMES.filter((k) => exemptions[k] && exemptions[k].assertion_met).length;
    exemptions.assertion_met = exemptions.n_arms_met === EXEMPTION_ARM_NAMES.length;
    ok = ok && Boolean(exemptions.assertion_met);
  } catch (e) {
    if (savedContract) CONTRACT = savedContract;
    exemptions = { assertion_met: false,
      error: String((e && e.stack) || e).split(String.fromCharCode(10)).slice(0, 4).join(' | ') };
    ok = false;
  }
  return { ok, out: { schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R8_SELFTEST', ruler: RULER, typescript: ts.version,
    exemption_arms: exemptions,
    n_exemption_arms: exemptions.n_arms || 0,
    n_exemption_arms_met: exemptions.n_arms_met || 0,
    exemption_table_under_test: tableSelftest(),

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

let CONTRACT_PATH = null;
let CONTRACT = { path: null, readable: false, bytes: 0, blob: null, enums: {}, enum_lines: {},
                 note: 'no contract file was read' };

/* ORD-0408 ruling A, module scope.  The contract is the one place a server-side reason code can be
   NAMED without trusting the value that arrives.  `enums` maps a property name to the closed set
   declared for it, read from either an inline `enum: [A, B]` or a block `enum:` followed by `- A`
   lines, and `enum_lines` remembers where that set is written so an exoneration can be pointed at a
   contract line and a blob instead of at a sentence.  A field with no declared set is not exonerated
   at all: the ruler prints the missing contract by name.  The field name below is a lookup key into
   the contract, never a permission - ruling B's exempt-by-field-name was rejected. */

function cjsDirname(p) {
  const q = String(p).replace(/\\/g, '/').replace(/\/+$/, '');
  const i = q.lastIndexOf('/');
  return i > 0 ? q.slice(0, i) : '';
}

/* The contract is read from the SAME tree as the code being scanned.  An exemption pinned to a
   generation of openapi.yaml from another checkout would be a claim about a contract the branch
  under review never had; `--contract` overrides, otherwise the target directory is walked upward. */
function contractFromTarget(target) {
  let dir = cjsDirname(target);
  for (let up = 0; dir && up < 8; up++) {
    const cand = dir + '/contracts/openapi.yaml';
    if (fs.existsSync(cand)) return cand;
    const parent = cjsDirname(dir);
    if (!parent || parent === dir) break;
    dir = parent;
  }
  return null;
}

/* A schema keyword is a modifier of the property it sits under, never a property name of its own.
   Without this list a block-form set is attributed to `type` or `description`, which is exactly how
   the B5 arm reported CONTRACT_MISSING_ENUM on a contract that does declare the set. */
const CNX_SCHEMA_KEYS = {
  type: 1, enum: 1, description: 1, format: 1, default: 1, example: 1, examples: 1, nullable: 1,
  items: 1, properties: 1, required: 1, additionalProperties: 1, pattern: 1, title: 1, maximum: 1,
  minimum: 1, minLength: 1, maxLength: 1, allOf: 1, anyOf: 1, oneOf: 1, ref: 1, $ref: 1, const: 1,
  readOnly: 1, writeOnly: 1, deprecated: 1, discriminator: 1, mapping: 1, x: 1
};

function readContract(path) {
  const out = { path: path, readable: false, bytes: 0, blob: null, enums: {}, enum_lines: {},
                enum_forms: {}, forms: {}, note: null };
  if (!path || !fs.existsSync(path)) { out.note = 'CONTRACT_FILE_ABSENT'; return out; }
  let txt;
  try { txt = fs.readFileSync(path, 'utf8'); } catch (e) { out.note = 'CONTRACT_UNREADABLE'; return out; }
  out.readable = true;
  out.bytes = Buffer.byteLength(txt, 'utf8');
  out.blob = blobSha1(txt);
  const lines = txt.split(/\r?\n/);
  const stack = [];                       /* enclosing NON-schema keys: {indent, name}, outer first */
  for (let i = 0; i < lines.length; i++) {
    const m = lines[i].match(/^( *)([A-Za-z_$][A-Za-z0-9_$]*) *:(.*)$/);
    if (m) {
      const ind = m[1].length, key = m[2], rest = m[3];
      while (stack.length && stack[stack.length - 1].indent >= ind) stack.pop();
      const ancestor = stack.length ? stack[stack.length - 1].name : null;
      const inline = rest.match(/enum: *\[([^\]]*)\]/);
      const bracket = key === 'enum' ? rest.match(/^\s*\[([^\]]*)\]/) : null;
      const blockHead = key === 'enum' && !rest.trim();
      let vals = [];
      if (inline) {
        /* `reason_code: {type: string, enum: [A, B]}` - the field name and the set share the line */
        vals = inline[1].split(',').map(function (x) { return x.trim().replace(/^['"]|['"]$/g, ''); });
        if (!CNX_SCHEMA_KEYS[key]) stack.push({ indent: ind, name: key });
        out.forms.inline_on_field_line = (out.forms.inline_on_field_line || 0) + 1;
        addSet(out, CNX_SCHEMA_KEYS[key] ? ancestor : key, vals, i + 1, 'inline_on_field_line');
        continue;
      }
      if (!CNX_SCHEMA_KEYS[key]) stack.push({ indent: ind, name: key });
      if (bracket) {
        /* `enum: [A, B]` on a line of its own, indented under the field: the same closed set written
           one step further down, and the real contract does this at its ai-availability cell */
        vals = bracket[1].split(',').map(function (x) { return x.trim().replace(/^['"]|['"]$/g, ''); });
        out.forms.enum_key_with_bracket = (out.forms.enum_key_with_bracket || 0) + 1;
        addSet(out, ancestor, vals, i + 1, 'enum_key_with_bracket');
        continue;
      }
      if (blockHead) {
        /* `enum:` alone on its line belongs to the nearest enclosing field name, not to the schema
           keyword beside it; the members are the `- A` lines indented deeper than the key */
        for (let j = i + 1; j < lines.length; j++) {
          const item = lines[j].match(/^( +)- *(.+?) *$/);
          if (!item || item[1].length <= ind) break;
          vals.push(item[2].replace(/^['"]|['"]$/g, ''));
        }
        out.forms.enum_key_block = (out.forms.enum_key_block || 0) + 1;
        addSet(out, ancestor, vals, i + 1, 'enum_key_block');
      }
      continue;
    }
    /* a flow-mapping enum written on a line the key regex cannot see (a long `description:` string
       containing `enum: [..]`) is deliberately NOT read: a sentence is not a declaration */
  }
  out.note = Object.keys(out.enums).length
    + ' contract field(s) carry a named closed set'
    + (out.enums.reason_code ? ', reason_code among them' : ', reason_code not among them')
    + ' (inline_on_field_line ' + (out.forms.inline_on_field_line || 0)
    + ', enum_key_with_bracket ' + (out.forms.enum_key_with_bracket || 0)
    + ', enum_key_block ' + (out.forms.enum_key_block || 0) + ')';
  return out;
}

/* only enum-shaped members join a closed set: `enum: [false]` and a lowercase locale pair are not a
   code alphabet and must not be mistaken for one */
function addSet(out, field, vals, line, form) {
  if (!field) return;
  const keep = (vals || []).filter(function (v) { return /^[A-Z][A-Z0-9_]{3,}$/.test(v); });
  if (!keep.length) return;
  if (!out.enums[field]) { out.enums[field] = []; out.enum_lines[field] = line; out.enum_forms[field] = form; }
  for (const v of keep) if (out.enums[field].indexOf(v) < 0) out.enums[field].push(v);
}

/* Exact field only - no union across the document. */
function contractSetFor(field) {
  const s = CONTRACT.enums[field];
  return (s && s.length) ? s : null;
}

/* What the scanned file itself says about the value a `*_code` cell renders.  Only enum-shaped
   literals count as candidate codes: a chain step carries neighbouring source text too, and a
   lowercase discriminator such as `kind: "already"` is not a reason code.  When an unrelated
   uppercase token shares the chain this errs RED and names both the token and the set, because a
   false red is a sentence a lane can answer while a false green is a defect nobody sees. */
/* A hit carries the chain twice over and in two different shapes: `taint_chain` is the single
   rendered string ("... -> ... -> rendered here"), `taint_trace` is the array of the same hops.
   Reading the string as an array iterates one character at a time and finds nothing, which would
   silently push every code cell into the "no literal on the chain" branch.  Both shapes are
   normalised here rather than at the call site. */
function chainSteps(hit) {
  const out = [];
  const push = function (v) { if (v) out.push(String(v)); };
  if (Array.isArray(hit.taint_chain)) hit.taint_chain.forEach(push); else push(hit.taint_chain);
  if (Array.isArray(hit.taint_trace)) hit.taint_trace.forEach(push); else push(hit.taint_trace);
  return out;
}

function enumTokenEvidence(hit, field) {
  if (!CONTRACT.readable) {
    return { ok: false, why: contractUnreadableReason(), contract: CONTRACT.path, set_size: 0 };
  }
  const set = contractSetFor(field);
  if (!set) {
    return { ok: false, why: 'CONTRACT_MISSING_ENUM', field: field, contract: CONTRACT.path,
             contract_blob: CONTRACT.blob, fields_with_enum: Object.keys(CONTRACT.enums), enums: CONTRACT.enums,
             set_size: 0 };
  }
  const seen = [];
  for (const step of chainSteps(hit)) {
    for (const q of (String(step).match(/"([^"\n]{1,80})"/g) || [])) {
      const v = q.slice(1, -1);
      if (/^[A-Z][A-Z0-9_]{3,}$/.test(v) && seen.indexOf(v) < 0) seen.push(v);
    }
  }
  for (const q of (String(hit.snippet || '').match(/"([A-Z][A-Z0-9_]{3,})"/g) || [])) {
    const v = q.slice(1, -1);
    if (seen.indexOf(v) < 0) seen.push(v);
  }
  const bad = seen.filter(function (v) { return set.indexOf(v) < 0; });
  if (bad.length) {
    return { ok: false, why: 'value_not_in_the_contract_set', examples: bad.slice(0, 3),
             contract: CONTRACT.path, contract_blob: CONTRACT.blob, set_size: set.length };
  }
  return { ok: true,
           basis: seen.length ? 'literal_on_the_chain_checked_against_the_named_set'
                              : 'no_literal_on_the_chain_and_the_contract_names_the_closed_set',
           tokens: seen.slice(0, 6), set_size: set.length, contract: CONTRACT.path,
           contract_blob: CONTRACT.blob, contract_line: CONTRACT.enum_lines[field] };
}

/* CONTRACT_UNREADABLE is not one defect: a tree with no contracts/openapi.yaml at all and a file
   the disk refused to hand over need different fixes, so the two carry different names. */
function contractUnreadableReason() {
  return CONTRACT.note === 'CONTRACT_FILE_ABSENT' ? 'CONTRACT_FILE_ABSENT' : 'CONTRACT_UNREADABLE';
}

function main() {
  const argv = process.argv.slice(2);
  const parsed = parseCliArguments(argv);
  if (parsed.refusals.length) {
    /* A caller cannot ask this instrument to look the other way, and the refusal says so in one named
       reason per token rather than falling back to a default that would quietly ignore it. */
    process.stdout.write(JSON.stringify({ schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R8',
      verdict: 'REFUSED', ruler: RULER.name, refusals: parsed.refusals,
      accepted_flags: CLI_FLAGS_WITH_VALUE.map(function (f) { return '--' + f; })
        .concat(CLI_BOOLEAN_FLAGS.map(function (f) { return '--' + f; })),
      note: 'an exemption is decided by the frozen shape table against what is on the tree; there is no input '
        + 'channel for a declared waiver' }, null, 1) + '\n');
    return 2;
  }
  const args = parsed.args;
  const tableCheck = validateExemptionTable(EXEMPTION_TABLE);
  if (!tableCheck.ok) {
    process.stdout.write(JSON.stringify({ schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R8',
      verdict: 'REFUSED', ruler: RULER.name, reason: 'EXEMPTION_TABLE_SCHEMA_REJECTED',
      problems: tableCheck.problems,
      note: 'an exemption entry may name a rule, a sink-shape family and an origin kind only; a table that '
        + 'can name a file, a line or a cell id is a hand-placed waiver with the shape of a rule' }, null, 1) + '\n');
    return 3;
  }
  const firstTarget = args.contract ? null : (args.tree || (args.file || '').split(',')[0] || null);
  const contractPath = args.contract
    || (firstTarget ? contractFromTarget(firstTarget) : null)
    || (fs.existsSync('contracts/openapi.yaml') ? 'contracts/openapi.yaml' : null);
  CONTRACT = readContract(contractPath || CONTRACT_PATH);
  if (args.contract) CONTRACT_PATH = args.contract;
  if (!contractPath) CONTRACT = { path: CONTRACT_PATH, readable: false, bytes: 0, blob: null,
    enums: {}, enum_lines: {}, note: 'CONTRACT_FILE_ABSENT' };
  if (contractPath && CONTRACT.readable) CONTRACT.auto = !args.contract;
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
    for (const c of r.cells) perRule[c.rule] = (perRule[c.rule] || 0) + 1;
    /* ORD-0354's two denominators stay apart, and r8 adds a third axis that the pre-landing door needs:
       a cell in front of the eye and a cell in an attribute are different defects with different fixes,
       and a cell that is exempted is still a cell. */
    const bySlot = { text_position: 0, attribute_position: 0, markup: 0, dom_write: 0 };
    const redBySlot = { text_position: 0, attribute_position: 0, markup: 0, dom_write: 0 };
    const slotOf = (c) => (c.sink === 'jsx-text' ? 'text_position'
      : c.sink === 'dom-attribute' ? 'attribute_position'
        : c.sink === 'inner-html' ? 'markup' : 'dom_write');
    for (const c of r.cells) bySlot[slotOf(c)] += 1;
    for (const c of r.hits) redBySlot[slotOf(c)] += 1;
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
      cells_by_slot: bySlot, red_by_slot: redBySlot,
      /* The denominator is every cell the analysis produced, before any exemption.  It is deliberately not
         the red count: a comparison that moves when an exemption is added is not a measurement, and the
         pre-landing door's growth arm compares absolute counts (preflight_and_land_r7.py:384). */
      cells_total: r.cells.length,
      cells_by_verdict: { RED: r.hits.length, EXEMPTED: r.cells.length - r.hits.length },
      red_after_exemption_count: r.hits.length,
      exempted_count: r.cells.length - r.hits.length,
      denominator_definition: 'cells_total counts every cell the taint analysis produced, exempted ones '
        + 'included; red_after_exemption_count counts the ones the frozen exemption table could not clear. '
        + 'Compare two trees by cell_id, never by these two numbers alone.',
      cells: r.cells.map(describeCellForReport),
      /* ORD-0536's named report-back: the exempted cells, one row each, with the rule, the file, the line,
         the entry of the table that cleared it and the fact that was measured on the tree. */
      exemption_ledger: exemptionLedger(r.cells),
      exemption_ledger_count: exemptionLedger(r.cells).length,
      red_ledger: r.hits.map(function (c) { return {
        rule: c.rule, file: c.file, line: c.line, cell_id: c.cell_id, sink_shape: (c.structural || {}).sink_shape,
        sink_shape_family: c.sink_shape_family, origin_kind: c.origin_kind,
        matched_exemption_entries: (c.matched_exemption_entries || []).slice(), red_because: c.red_because,
        near_miss: c.near_miss }; }),
      attributed_in_fold: r.attributed_in_fold,
      attributed_in_fold_count: r.attributed_in_fold.length,
      fold_without_anchor: r.fold_without_anchor,
      fold_without_anchor_count: r.fold_without_anchor.length,
      contract_exempted: r.contract_exempted,
      contract_exempted_count: (r.contract_exempted || []).length,
      contract_blocked: r.contract_blocked,
      contract_blocked_count: (r.contract_blocked || []).length,
      contract: { path: CONTRACT.path, readable: CONTRACT.readable, bytes: CONTRACT.bytes,
        blob: CONTRACT.blob, fields_with_enum: Object.keys(CONTRACT.enums), enums: CONTRACT.enums,
        enum_lines: CONTRACT.enum_lines, enum_forms: CONTRACT.enum_forms,
        auto_discovered: !!CONTRACT.auto, note: CONTRACT.note },
      exemption_table: tableSelftest(),
      exception_definition: 'an exemption is looked up in EXEMPTION_TABLE, which is frozen in this file and '
        + 'keyed by (rule x sink-shape family x origin kind); the entry only clears a cell once one of the two '
        + 'measured predicates (contract_closed_enum, attributed_fold) finds the disclosure on the tree. '
        + 'The table cannot express a file, a line or a cell id, and no command-line argument, comment, class '
        + 'name, test id or sentence in a ledger block is an input to it.',
      verdict: r.hits.length ? 'EXPOSURE_SHAPE_FOUND'
        : (r.cells.length ? 'ALL_CELLS_CLEARED_BY_STRUCTURED_EXEMPTION' : 'NO_EXPOSURE_SHAPE_FOUND'),
      interpretation_limit: 'a hit names a shape to justify, not a defect verdict; unresolved_import_specs '
        + 'lists what this run could not see through; an exempted cell is a cell this ruler could tie to a '
        + 'declared structure, which is not the same claim as "the screen reads well" - that is a screen '
        + 'ruler\'s job and stays one',
      claim_kind: 'pattern_determined', claimed_result: null, derived_result: null,
    };
    out.claimed_result = out.verdict + ' over ' + out.modules_in_graph + ' modules: ' + r.cells.length
      + ' cell(s), ' + r.hits.length + ' red after the exemption table '
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
    process.stdout.write('usage: node ui_exposure_taint_ast_r2.cjs --tree <dir> | --file a,b,c | --ref <sha> --path <in-tree path> [--contract <path to contracts/openapi.yaml>] | --selftest  [--out <json>]\n');
    return 2;
  }
  const hits = [];
  const perFile = [];
  let failed = 0, diag = 0, truncated = 0;
  const folded = [], foldless = [], cex = [], cbk = [];
  const cells = [];
  for (const [label, text] of targets) {
    let res;
    try { res = scanText(ts, label, text); }
    catch (e) { failed++; hits.push({ rule: 'RULER_ERROR', file: label, line: 0, error: String((e && e.stack) || e).split('\n').slice(0, 3).join(' | ') }); continue; }
    diag += res.diagnostics;
    truncated += res.truncated || 0;
    for (const c of res.cells) cells.push(c);
    for (const f of res.attributed_in_fold) { f.file = label; folded.push(f); }
    for (const f of res.fold_without_anchor) { f.file = label; foldless.push(f); }
    for (const f of (res.contract_exempted || [])) { f.file = label; cex.push(f); }
    for (const f of (res.contract_blocked || [])) { f.file = label; cbk.push(f); }
    perFile.push({ file: label, hits: res.hits.length, cells: res.cells.length,
      exempted: res.cells.length - res.hits.length,
      parse_diagnostics: res.diagnostics,
      attributed_in_fold: res.attributed_in_fold.length,
      contract_exempted: (res.contract_exempted || []).length,
      contract_blocked: (res.contract_blocked || []).length,
      depth_cut_lookups: res.truncated || 0, graph: res.graph });
    hits.push(...res.hits);
  }
  const perRule = {};
  for (const c of cells) perRule[c.rule] = (perRule[c.rule] || 0) + 1;
  const bySlot = { text_position: 0, attribute_position: 0, markup: 0, dom_write: 0 };
  const redBySlot = { text_position: 0, attribute_position: 0, markup: 0, dom_write: 0 };
  const slotOf2 = (c) => (c.sink === 'jsx-text' ? 'text_position'
    : c.sink === 'dom-attribute' ? 'attribute_position'
      : c.sink === 'inner-html' ? 'markup' : 'dom_write');
  for (const c of cells) bySlot[slotOf2(c)] += 1;
  for (const c of hits) redBySlot[slotOf2(c)] += 1;
  const out = {
    schema: 'CNX_CMDR_UI_EVIDENCE_EXPOSURE_GATE_V1_R8', ruler: RULER, typescript: ts.version,
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
    contract_exempted: cex, contract_exempted_count: cex.length,
    contract_blocked: cbk, contract_blocked_count: cbk.length,
    contract: { path: CONTRACT.path, readable: CONTRACT.readable, bytes: CONTRACT.bytes,
      blob: CONTRACT.blob, fields_with_enum: Object.keys(CONTRACT.enums), enums: CONTRACT.enums,
      enum_lines: CONTRACT.enum_lines, enum_forms: CONTRACT.enum_forms,
        auto_discovered: !!CONTRACT.auto, note: CONTRACT.note },
    /* r6's published bytes print 40 here while the analyzer runs with MAXD; that self-report fault is
       declared in the r6 receipt and is fixed in this revision rather than back-ported. */
    resolution_depth_cap: MAXD,
    resolution_truncated_total: truncated,
    truncated_meaning: 'how many times a lookup ran out of depth and had to answer "unknown" - a clean verdict with a nonzero value here is NOT a proven clean verdict',
    targets_scanned: targets.map((t) => t[0]), hits,
    cells: cells.map(describeCellForReport),
    cells_by_slot: bySlot, red_by_slot: redBySlot,
    cells_total: cells.length,
    cells_by_verdict: { RED: hits.length, EXEMPTED: cells.length - hits.length },
    red_after_exemption_count: hits.length,
    exempted_count: cells.length - hits.length,
    exemption_ledger: exemptionLedger(cells),
    exemption_table: tableSelftest(),
    denominator_definition: 'cells_total counts every cell this run produced, exempted ones included; the red '
      + 'list is what the frozen table could not clear. Compare by cell_id.',
    verdict: hits.length ? 'EXPOSURE_SHAPE_FOUND'
      : (cells.length ? 'ALL_CELLS_CLEARED_BY_STRUCTURED_EXEMPTION' : 'NO_EXPOSURE_SHAPE_FOUND'),
    interpretation_limit: 'a hit names a shape to justify, not a defect verdict',
    claim_kind: 'pattern_determined',
    claimed_result: null, derived_result: null,
  };
  out.claimed_result = out.verdict + ' across ' + targets.length + ' scanned file(s): ' + cells.length
    + ' cell(s), ' + hits.length + ' red after the exemption table '
    + JSON.stringify(Array.from(new Set(hits.map((h) => h.rule + '@' + String(h.file).split(/[/:]/).pop() + ':' + h.line)))).slice(0, 400);
  emit(out);
  return 0;
}

if (require.main === module) process.exit(main());
module.exports = { scanText, selftest, loadTs, FIXTURES_R3, FIXTURES_E, blobSha1, cellIdentity,
  EXEMPTION_TABLE, validateExemptionTable, exemptionTableDigest, sinkShapeFamily, parseCliArguments,
  exemptionLedger, describeCellForReport };
