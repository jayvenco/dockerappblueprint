# ---- build stage: install Python dependencies into an isolated prefix ----
FROM python:3.12-slim AS build
WORKDIR /src
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---- runtime stage ----
FROM python:3.12-slim

LABEL org.opencontainers.image.source="https://github.com/jayvenco/dockerappblueprint" \
      org.opencontainers.image.title="DockerAppBlueprint" \
      org.opencontainers.image.description="Wizard that builds ready-to-paste prompts for Docker-hosted apps (Claude Code / OpenAI Codex)"

ENV PYTHONUNBUFFERED=1 PYTHONDONTWRITEBYTECODE=1 PUID=99 PGID=100 TZ=UTC
WORKDIR /app
COPY --from=build /install /usr/local
COPY app ./app
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh && mkdir -p /app/data
VOLUME ["/app/data"]
EXPOSE 7773

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
  CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:7773/health', timeout=4).status == 200 else 1)"

ENTRYPOINT ["/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "7773", "--proxy-headers", "--forwarded-allow-ips", "*"]
