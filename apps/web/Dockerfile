# Volo web — Next.js reliability dashboard.
# Build context is the repo root (see docker-compose.yml).
#
#   docker build -f apps/web/Dockerfile -t volo-web .
#   docker run -p 3000:3000 -e NEXT_PUBLIC_VOLO_API=http://localhost:8080 volo-web
#
# Relies on `output: "standalone"` in next.config.ts.

FROM node:20-slim AS deps
WORKDIR /app
COPY apps/web/package.json apps/web/package-lock.json* apps/web/.npmrc ./
RUN npm install

FROM node:20-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY --from=deps /app/node_modules ./node_modules
COPY apps/web/ ./
RUN npm run build

FROM node:20-slim AS run
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000 \
    HOSTNAME=0.0.0.0
RUN useradd --create-home --uid 10001 nextjs
# Standalone output bundles only the traced runtime deps + a minimal server.
COPY --from=build --chown=nextjs:nextjs /app/.next/standalone ./
COPY --from=build --chown=nextjs:nextjs /app/.next/static ./.next/static
USER nextjs
EXPOSE 3000
CMD ["node", "server.js"]
