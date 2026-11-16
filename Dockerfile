FROM node:20-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.13-slim
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/app ./app
COPY content /app/content
COPY --from=web /web/dist /app/frontend/dist

RUN useradd -m -u 1000 study && mkdir -p /app/data && chown study /app/data
USER study
ENV STUPY_HOST=0.0.0.0 STUPY_PORT=8765 STUPY_DATA_DIR=/app/data
EXPOSE 8765
HEALTHCHECK --interval=30s --timeout=3s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8765/api/health')"
CMD ["uv", "run", "--no-sync", "python", "-m", "app.main"]
