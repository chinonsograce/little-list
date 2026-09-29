FROM node:22-bookworm-slim AS frontend
WORKDIR /app
RUN npm install --global pnpm@11.19.0
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY index.html vite.config.js ./
COPY src ./src
COPY public ./public
RUN pnpm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TODO_DB_PATH=/app/data/tasks.sqlite3
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend ./backend
COPY --from=frontend /app/dist ./dist
RUN useradd --create-home appuser && mkdir -p /app/data && chown -R appuser:appuser /app
USER appuser
EXPOSE 10000
CMD ["sh", "-c", "exec uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-10000}"]
