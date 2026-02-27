import { serve } from "bun";
import index from "./index.html";
import { join } from "path";

const server = serve({
  routes: {
    // Serve node_modules content (HTMX library)
    "/node_modules/*": async (req) => {
      const pathname = req.url.split("/node_modules")[1];
      const filePath = join(import.meta.dir, "..", "node_modules", pathname);
      const file = (await Bun.file(filePath).exists())
        ? Bun.file(filePath)
        : null;
      if (!file) return new Response("Not Found", { status: 404 });
      return new Response(file);
    },

    // Serve index.html for all unmatched routes.
    "/*": index,

    "/api/hello": {
      async GET(req) {
        return new Response(
          JSON.stringify({
            message: "Hello, world!",
            method: "GET",
            timestamp: new Date().toISOString(),
          }),
          {
            headers: { "Content-Type": "application/json" },
          },
        );
      },
      async PUT(req) {
        return Response.json({
          message: "Hello, world!",
          method: "PUT",
        });
      },
    },

    "/api/hello/:name": async (req) => {
      const name = req.params.name;
      return Response.json({
        message: `Hello, ${name}!`,
      });
    },
  },

  development: process.env.NODE_ENV !== "production" && {
    // Enable browser hot reloading in development
    hmr: true,

    // Echo console logs from the browser to the server
    console: true,
  },
});

console.log(`🚀 Server running at ${server.url}`);
