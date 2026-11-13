#!/usr/bin/env bash
# Install or update DockerAppBlueprint on Unraid (manageable from the Docker tab afterwards).
#
# Pulls the image from GHCR, creates the container with Unraid labels (icon, WebUI button) and
# writes a user template so "Edit" in the Docker tab works. Running it again = update; your data
# in <appdata>/data is kept.
#
# Override with environment variables, e.g.:  HOST_PORT=9000 bash install-unraid.sh
#   Staging:  CONTAINER_NAME=dockerappblueprint-staging IMAGE_TAG=staging HOST_PORT=8934 bash install-unraid.sh
set -euo pipefail

NAME="${CONTAINER_NAME:-dockerappblueprint}"
IMAGE="${IMAGE:-ghcr.io/jayvenco/dockerappblueprint}"
TAG="${IMAGE_TAG:-latest}"
HOST_PORT="${HOST_PORT:-8834}"
CONTAINER_PORT=8000
APPDATA="${APPDATA:-/mnt/user/appdata/${NAME}}"
BRANCH="main"; [ "${TAG}" = "staging" ] && BRANCH="develop"
RAW="${RAW_URL:-https://raw.githubusercontent.com/jayvenco/dockerappblueprint/${BRANCH}/unraid}"
TEMPLATE_FILE="dockerappblueprint.xml"; [ "${TAG}" = "staging" ] && TEMPLATE_FILE="dockerappblueprint-staging.xml"
TEMPLATE_DIR="${TEMPLATE_DIR:-/boot/config/plugins/dockerMan/templates-user}"
# Optional app settings. If they are already set on the existing container they are carried over on
# update; a value you pass here wins.
OPTIONAL_VARS="TZ PUID PGID OPENAI_API_KEY DEFAULT_THEME BACKUP_ENABLED BACKUP_KEEP COOKIE_SECURE"

log() { printf '==> %s\n' "$*"; }

command -v docker >/dev/null 2>&1 || { echo "Docker not found. Run this script on the Unraid server." >&2; exit 1; }

# 1. Appdata folders (Unraid default owner nobody:users = 99:100)
log "Creating folders in ${APPDATA}"
mkdir -p "${APPDATA}/data"
chown -R 99:100 "${APPDATA}" 2>/dev/null || true

# 2. Optional GHCR login (only needed when the package is private)
if [ -n "${GHCR_USER:-}" ] && [ -n "${GHCR_TOKEN:-}" ]; then
  log "Logging in to ghcr.io as ${GHCR_USER}"
  printf '%s' "${GHCR_TOKEN}" | docker login ghcr.io -u "${GHCR_USER}" --password-stdin
fi

# 3. Pull the image
if [ "${SKIP_PULL:-0}" = "1" ]; then
  log "Skipping pull (SKIP_PULL=1), using local image ${IMAGE}:${TAG}"
else
  log "Pulling image: ${IMAGE}:${TAG}"
  docker pull "${IMAGE}:${TAG}"
fi

# 4. Replace an existing container (data lives on the volume and is kept)
if docker inspect "${NAME}" >/dev/null 2>&1; then
  OLD_ENV="$(docker inspect -f '{{range .Config.Env}}{{println .}}{{end}}' "${NAME}" 2>/dev/null || true)"
  for v in ${OPTIONAL_VARS}; do
    if [ -z "${!v:-}" ]; then
      old="$(printf '%s\n' "${OLD_ENV}" | sed -n "s/^${v}=//p" | head -n 1)"
      [ -n "${old}" ] && printf -v "${v}" '%s' "${old}" && log "Kept existing setting ${v}"
    fi
  done
  log "Stopping and removing existing container '${NAME}' (data is kept)"
  docker stop "${NAME}" >/dev/null 2>&1 || true
  docker rm "${NAME}" >/dev/null
fi

ENV_ARGS=()
for v in ${OPTIONAL_VARS}; do
  [ -n "${!v:-}" ] && ENV_ARGS+=(-e "${v}=${!v}")
done

# 5. Start the container with labels so Unraid shows it as its own container
log "Starting container '${NAME}' on port ${HOST_PORT}"
docker run -d \
  --name "${NAME}" \
  --restart unless-stopped \
  -p "${HOST_PORT}:${CONTAINER_PORT}" \
  -v "${APPDATA}/data:/app/data" \
  ${ENV_ARGS[@]+"${ENV_ARGS[@]}"} \
  --label "net.unraid.docker.managed=dockerman" \
  --label "net.unraid.docker.webui=http://[IP]:[PORT:${CONTAINER_PORT}]/" \
  --label "net.unraid.docker.icon=${RAW}/icon.png" \
  "${IMAGE}:${TAG}" >/dev/null

# 6. Write the user template so Edit in the Docker tab shows the right values
if [ -d "${TEMPLATE_DIR}" ]; then
  log "Saving template to ${TEMPLATE_DIR}/my-${NAME}.xml"
  TMP="$(mktemp)"
  if command -v curl >/dev/null 2>&1 && curl -fsSL "${RAW}/${TEMPLATE_FILE}" -o "${TMP}"; then
    esc() { printf '%s' "$1" | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g' -e 's/[\\&|]/\\&/g'; }
    setcfg() { sed -i -E "s|(Target=\"$1\"[^>]*>)[^<]*(</Config>)|\1$(esc "$2")\2|" "${TMP}"; }
    sed -i -E "s|<Name>[^<]*</Name>|<Name>$(esc "${NAME}")</Name>|" "${TMP}"
    setcfg "8000" "${HOST_PORT}"
    setcfg "/app/data" "${APPDATA}/data"
    for v in ${OPTIONAL_VARS}; do
      [ -n "${!v:-}" ] && setcfg "${v}" "${!v}"
    done
    install -m 600 "${TMP}" "${TEMPLATE_DIR}/my-${NAME}.xml"
  else
    echo "Warning: could not download the template; skipping (the container still works)." >&2
  fi
  rm -f "${TMP}"
else
  log "No dockerMan folder found (not Unraid?); template skipped"
fi

# 7. Wait for the healthcheck
log "Waiting for the app to become healthy..."
STATUS="starting"
for _ in $(seq 1 60); do
  STATUS="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}{{.State.Status}}{{end}}' "${NAME}" 2>/dev/null || echo missing)"
  case "${STATUS}" in healthy|running) break ;; unhealthy|exited|dead|missing) break ;; esac
  sleep 2
done
if [ "${STATUS}" != "healthy" ] && [ "${STATUS}" != "running" ]; then
  echo "Container is not healthy (status: ${STATUS}). Last log lines:" >&2
  docker logs --tail 30 "${NAME}" >&2 || true
  exit 1
fi

IP="$(hostname -I 2>/dev/null | awk '{print $1}' || true)"
log "Done! Open http://${IP:-<unraid-ip>}:${HOST_PORT}/"
echo "    First login: admin / admin (you must change it right away)."
echo "    From now on you can also manage it from the Docker tab (Edit, logs, autostart, update)."
