# Stage 1 — Build frontend
FROM node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm ci
COPY frontend/ .
RUN npm run build

# Stage 2 — Python runtime
FROM python:3.14-slim
WORKDIR /app

COPY requirements.txt pyproject.toml ./
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir -r requirements.txt

# Copy the server package (modular structure)
COPY server/ server/
COPY server.py .
COPY SPEC.md .
COPY --from=build /app/dist /app/frontend/dist

RUN mkdir -p /app/archive && chmod -R a+rX /app

EXPOSE 8765
CMD ["uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8765"]
