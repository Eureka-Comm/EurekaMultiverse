#!/usr/bin/env bash
# EUREKA — reset de contrasena OFFLINE (VPS). Un comando por reset.
#
#   sudo bash scripts/reset-password.sh --list
#   sudo bash scripts/reset-password.sh <email>            # te pide la contrasena (no se muestra)
#   sudo bash scripts/reset-password.sh --generate <email> # la genera el script y la muestra UNA vez
#
# Por que offline: el almacen de identidad CACHEA los JSON en memoria y reescribe el fichero completo
# en cada escritura, asi que un cambio hecho por otro proceso mientras el backend corre se pierde en
# el siguiente login. Por eso: parar -> resetear -> arrancar (el trap garantiza que siempre arranca).
#
# Por que en un contenedor: Argon2id vive en la imagen del backend, no en el host del VPS. Se usa la
# MISMA imagen, con data/ montado, y el script Python que acompania a este fichero.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
IMAGE="${IMAGE:-eureka-backend:latest}"
DATA="${DATA:-/opt/eureka/data}"
DATA_DIR="${DATA_DIR:-/app/data/identity}"
PY="$HERE/reset_password.py"
EMAIL=""
MODE="typed"

[ -f "$PY" ] || { echo "ERROR: no encuentro $PY"; exit 1; }

restore() {
  echo ""
  echo "Arrancando el backend..."
  docker start eureka-backend >/dev/null 2>&1 || true
}
trap 'restore' EXIT

case "${1:-}" in
  --list)
    trap - EXIT
    docker run --rm -v "$DATA":/app/data -v "$PY":/tmp/reset.py:ro \
      --entrypoint python "$IMAGE" /tmp/reset.py --data-dir "$DATA_DIR" --list
    exit $?
    ;;
  --generate)
    MODE="generate"; shift; EMAIL="${1:-}"
    ;;
  ""|--help|-h)
    sed -n '2,8p' "$0"
    exit 0
    ;;
  *)
    EMAIL="$1"
    ;;
esac

chmod 0644 "$PY" 2>/dev/null || true

if [ "$MODE" = "generate" ]; then
  if [ -z "$EMAIL" ]; then read -rp "Email de la cuenta: " EMAIL; fi
  docker run --rm -i -v "$DATA":/app/data -v "$PY":/tmp/reset.py:ro \
    --entrypoint python "$IMAGE" /tmp/reset.py --data-dir "$DATA_DIR" --email "$EMAIL" --generate --apply
  exit $?
fi

if [ -z "$EMAIL" ]; then read -rp "Email de la cuenta: " EMAIL; fi
printf 'Contrasena nueva (no se muestra): '; read -rs PW1; echo
printf 'Repite la contrasena: '; read -rs PW2; echo
if [ "$PW1" != "$PW2" ]; then echo "ERROR: no coinciden. No se ha tocado nada."; exit 2; fi
if [ -z "$PW1" ]; then echo "ERROR: vacia. No se ha tocado nada."; exit 2; fi

echo ""
echo "Parando el backend (obligatorio: cachea los JSON en memoria)..."
docker stop eureka-backend >/dev/null

printf '%s' "$PW1" | docker run --rm -i -v "$DATA":/app/data -v "$PY":/tmp/reset.py:ro \
  --entrypoint python "$IMAGE" /tmp/reset.py --data-dir "$DATA_DIR" --email "$EMAIL" --stdin
unset PW1 PW2
