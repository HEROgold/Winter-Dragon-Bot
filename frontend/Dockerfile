FROM oven/bun:1 AS builder

WORKDIR /app

COPY package.json tsconfig.json index.html build.ts server.ts ./
COPY src ./src

RUN bun install
RUN bun run build

FROM oven/bun:1

WORKDIR /app

COPY --from=builder /app /app

EXPOSE 3000

CMD ["bun", "run", "server.ts"]