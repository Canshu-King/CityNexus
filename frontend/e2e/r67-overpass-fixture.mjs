import { createServer } from "node:http";

const port = Number(process.env.CITYNEXUS_R67_OVERPASS_FIXTURE_PORT ?? 8367);
let requestCount = 0;

const server = createServer(async (request, response) => {
  if (request.method === "GET" && request.url === "/health") {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ status: "ready", mode: "TEST_FIXTURE" }));
    return;
  }
  if (request.method === "GET" && request.url === "/stats") {
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({ request_count: requestCount, mode: "TEST_FIXTURE" }));
    return;
  }
  if (request.method === "POST" && request.url?.endsWith("/interpreter")) {
    requestCount += 1;
    for await (const _chunk of request) {
      // Consume the bounded Overpass query without retaining the private coordinates.
    }
    response.writeHead(200, { "content-type": "application/json" });
    response.end(JSON.stringify({
      elements: [{
        type: "node",
        id: 987654321,
        lat: 5.1235,
        lon: 10.654,
        tags: { name: "R67 Fixture OSM Museum", tourism: "museum" },
      }],
    }));
    return;
  }
  response.writeHead(404, { "content-type": "application/json" });
  response.end(JSON.stringify({ error: "fixture route not found" }));
});

server.listen(port, "127.0.0.1");
