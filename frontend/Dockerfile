ARG NODE_VERSION=22.18.0

FROM node:${NODE_VERSION}-bookworm-slim AS base

ENV PNPM_HOME=/pnpm
ENV PATH="${PNPM_HOME}:${PATH}"

RUN npm install --global corepack@latest \
	&& corepack enable \
	&& corepack prepare pnpm@11.20.0 --activate

WORKDIR /app

FROM base AS dependencies

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile

FROM dependencies AS build

COPY . .
RUN pnpm build

FROM node:${NODE_VERSION}-bookworm-slim AS runtime

ENV NODE_ENV=production \
	HOST=0.0.0.0 \
	PORT=3000 \
	PNPM_HOME=/pnpm \
	PATH="/pnpm:${PATH}"

RUN npm install --global corepack@latest \
	&& corepack enable \
	&& corepack prepare pnpm@11.20.0 --activate \
	&& useradd --create-home --uid 10001 appuser

WORKDIR /app

COPY --from=build --chown=appuser:appuser /app/build ./build
COPY --from=build --chown=appuser:appuser /app/package.json ./package.json
COPY --from=build --chown=appuser:appuser /app/node_modules ./node_modules

USER appuser

EXPOSE 3000

CMD ["node", "build"]
