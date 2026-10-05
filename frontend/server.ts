import { existsSync, readdirSync } from "node:fs";
import { extname, join } from "node:path";
import { buildApp } from "./build";

const rootDir = import.meta.dir;
const outdir = join(rootDir, "dist");
const templatePath = join(rootDir, "index.html");
const port = Number(process.env.PORT ?? 3000);
const apiBackendUrl = process.env.API_BACKEND_URL ?? "http://localhost:8001";

await buildApp();

const template = await Bun.file(templatePath).text();
const stylesheetName = readdirSync(outdir).find((entry) =>
  entry.endsWith(".css"),
);
const html = stylesheetName
  ? template.replace(
      "</head>",
      `    <link rel="stylesheet" href="/${stylesheetName}" />\n  </head>`,
    )
  : template;

Bun.serve({
  port,
  fetch(request) {
    const url = new URL(request.url);
    const pathname = url.pathname;

    // Proxy API requests to backend
    if (pathname.startsWith("/api/")) {
      const backendUrl = new URL(pathname + url.search, apiBackendUrl);
      return fetch(backendUrl, {
        method: request.method,
        headers: request.headers,
        body: request.body,
      });
    }

    if (pathname === "/index.html" || pathname === "/") {
      return new Response(html, {
        headers: {
          "Content-Type": "text/html; charset=utf-8",
        },
      });
    }

    const filePath = join(outdir, pathname.slice(1));
    if (!existsSync(filePath)) {
      return new Response(html, {
        headers: {
          "Content-Type": "text/html; charset=utf-8",
        },
      });
    }

    return new Response(Bun.file(filePath), {
      headers: {
        "Content-Type": getContentType(filePath),
      },
    });
  },
});

console.log(`WinterDragon frontend running at http://localhost:${port}`);
console.log(`API backend proxied to ${apiBackendUrl}`);

function getContentType(filePath: string): string {
  switch (extname(filePath)) {
    case ".css":
      return "text/css; charset=utf-8";
    case ".html":
      return "text/html; charset=utf-8";
    case ".js":
      return "application/javascript; charset=utf-8";
    case ".json":
      return "application/json; charset=utf-8";
    case ".svg":
      return "image/svg+xml";
    default:
      return "application/octet-stream";
  }
}
