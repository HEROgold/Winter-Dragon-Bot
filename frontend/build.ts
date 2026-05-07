import { mkdir } from "node:fs/promises";
import { join } from "node:path";
import tsrxReact from "@tsrx/bun-plugin-react";

const rootDir = import.meta.dir;
const outdir = join(rootDir, "dist");
const entrypoint = join(rootDir, "src/main.tsx");
const htmlSource = join(rootDir, "index.html");

export async function buildApp(): Promise<void> {
  const result = await Bun.build({
    entrypoints: [entrypoint],
    outdir,
    target: "browser",
    plugins: [tsrxReact()],
    sourcemap: "external",
  });

  if (!result.success) {
    throw new Error("WinterDragon frontend build failed.");
  }

  await mkdir(outdir, { recursive: true });
  await Bun.write(join(outdir, "index.html"), Bun.file(htmlSource));
}

if (import.meta.main) {
  await buildApp();
}