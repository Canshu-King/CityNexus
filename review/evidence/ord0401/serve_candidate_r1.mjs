/**
 * ORD-0401 -- serve the candidate build on this lane's own port, with /api read-only proxied to the
 * preview chain that already holds the data.
 *
 * The candidate must be measured as a built artifact (the same bytes a traveller would get), not as
 * a dev-server transform. `dist` here comes from the `git archive` snap that the tsc and vite gates
 * ran in, so what is measured is what the gate compiled.
 *
 * The proxy forwards GETs only. Anything else answers 405 from this server, and the probe withholds
 * mutating legs in the browser as well -- two independent doors, so "no writes" is a property of the
 * stack, not a claim in a receipt.
 */
import { createServer } from "node:http";
import { readFile, stat } from "node:fs/promises";
import { extname, join, resolve, sep } from "node:path";
import { request as upstream } from "node:http";

const DIST = process.env.ORD0401_DIST ?? "D:/moodle/_qoder_q_ord0401/snap/frontend/dist";
const PORT = Number(process.env.ORD0401_PORT ?? 4301);
const API_TARGET = process.env.ORD0401_API ?? "http://127.0.0.1:4781";

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

const proxyGet = (url, res, req) => {
  const target = new URL(url, API_TARGET);
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
    res.end('{"detail":"lane-proxy upstream unavailable"}');
  });
  req.pipe(p);
};

const server = createServer(async (req, res) => {
  const path = decodeURIComponent((req.url || "/").split("?")[0]);
  if (path.startsWith("/api/")) {
    if (req.method !== "GET") {
      res.writeHead(405, { "content-type": "application/json" });
      res.end('{"detail":"ORD-0401 lane server: GET only"}');
      return;
    }
    proxyGet(path, res, req);
    return;
  }
  /* Windows: `join` yields backslashes while DIST was written with slashes, so the containment test
     has to compare resolved paths on the platform's own separator or it rejects every real file. */
  const root = resolve(DIST);
  const file = resolve(join(root, path === "/" ? "index.html" : path));
  if (file !== root && !file.startsWith(root + sep)) {
    res.writeHead(403);
    res.end("nope");
    return;
  }
  try {
    const s = await stat(file);
    if (s.isDirectory()) throw new Error("dir");
    const body = await readFile(file);
    res.writeHead(200, {
      "content-type": MIME[extname(file)] ?? "application/octet-stream",
      "cache-control": "no-store",
      "x-served-asset": file.split(/[\\/]/).pop(),
    });
    res.end(body);
  } catch {
    /* SPA document fallback: /v8/hub is a client route, not a file. */
    try {
      const body = await readFile(join(DIST, "index.html"));
      res.writeHead(200, { "content-type": MIME[".html"], "cache-control": "no-store" });
      res.end(body);
    } catch {
      res.writeHead(404);
      res.end("not found");
    }
  }
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`ORD-0401 lane server on http://127.0.0.1:${PORT} dist=${DIST} api=${API_TARGET}`);
});
