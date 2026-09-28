/**
 * ORD-0402 slice 2 -- serve the candidate build on this lane's own port, with /api pointed at this
 * lane's own uvicorn.
 *
 * Nothing here touches the preview chain: the upstream is 127.0.0.1:8714, a process this lane started
 * over a sqlite file this lane created (see review/ord0402/stack_receipt_r1.json for the proof).
 */
import { createServer, request as upstream } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, resolve, sep } from "node:path";

const DIST = process.env.ORD0402_DIST ?? "D:/moodle/_qoder_q_ord0402/snap/frontend/dist";
const PORT = Number(process.env.ORD0402_PORT ?? 4302);
const API_TARGET = process.env.ORD0402_API ?? "http://127.0.0.1:8714";

const MIME = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".svg": "image/svg+xml",
  ".webmanifest": "application/manifest+json",
  ".png": "image/png",
  ".ico": "image/x-icon",
  ".map": "application/json",
};

const proxy = (req, res) => {
  const target = new URL(req.url, API_TARGET);
  const p = upstream(
    {
      method: req.method,
      hostname: target.hostname,
      port: target.port,
      path: target.pathname + target.search,
      headers: { ...req.headers, host: `${target.hostname}:${target.port}` },
    },
    (up) => {
      res.writeHead(up.statusCode ?? 502, up.headers);
      up.pipe(res);
    },
  );
  p.on("error", () => {
    res.writeHead(502, { "content-type": "application/json" });
    res.end('{"detail":"lane proxy upstream unavailable"}');
  });
  req.pipe(p);
};

const root = resolve(DIST);
createServer(async (req, res) => {
  const path = decodeURIComponent((req.url || "/").split("?")[0]);
  if (path.startsWith("/api/")) return proxy(req, res);
  const file = resolve(join(root, path === "/" ? "index.html" : path));
  if (file !== root && !file.startsWith(root + sep)) {
    res.writeHead(403);
    return res.end("nope");
  }
  try {
    const s = await stat(file);
    if (s.isDirectory()) throw new Error("dir");
    const body = await readFile(file);
    res.writeHead(200, {
      "content-type": MIME[extname(file)] ?? "application/octet-stream",
      "cache-control": "no-store",
    });
    res.end(body);
  } catch {
    try {
      res.writeHead(200, { "content-type": MIME[".html"], "cache-control": "no-store" });
      res.end(await readFile(join(root, "index.html")));
    } catch {
      res.writeHead(404);
      res.end("not found");
    }
  }
}).listen(PORT, "127.0.0.1", () => console.log(`ORD-0402 lane server :${PORT} -> ${API_TARGET} dist=${DIST}`));
