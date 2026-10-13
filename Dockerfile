FROM node:24-alpine AS web
WORKDIR /build
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
COPY .prettierrc.json ../.prettierrc.json
RUN npm run build

FROM python:3.14-slim
ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 FORGESIGHT_ROOT=/app
WORKDIR /app
COPY pyproject.toml requirements.lock requirements-torch-cpu.txt README.md LICENSE ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir -r requirements-torch-cpu.txt \
    && python -m pip install --no-cache-dir -c requirements.lock . \
    && useradd --create-home --uid 10001 inspector \
    && mkdir -p /app/data /app/artifacts /app/reports \
    && chown -R inspector:inspector /app
COPY --from=web /build/dist ./web/dist
USER inspector
EXPOSE 8010
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/api/health', timeout=3)" || exit 1
ENTRYPOINT ["python", "-m", "forgesight.cli"]
CMD ["serve", "--host", "0.0.0.0", "--port", "8010"]
