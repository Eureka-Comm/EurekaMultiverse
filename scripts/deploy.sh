#!/usr/bin/env bash
# EUREKA — despliegue en el VPS: comprobar -> respaldar -> actualizar -> reconstruir -> arrancar ->
# VERIFICAR -> (rollback documentado). NO toca data/ ni .env.
#
#   sudo bash deploy.sh --dry-run     # enseña el plan y NO ejecuta nada
#   sudo bash deploy.sh               # despliega
#
# Variables: DEPLOY_DIR (def: el checkout que contiene este script), REF (def origin/feature/deployment),
#            BRANCH (def feature/deployment), FRONT_PORT (def 5173), BACK_PORT (def 8000)
set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
REF="${REF:-origin/feature/deployment}"
BRANCH="${BRANCH:-feature/deployment}"
FRONT_PORT="${FRONT_PORT:-5173}"
BACK_PORT="${BACK_PORT:-8000}"
STAMP="$(date +%Y%m%d-%H%M%S)"
DRY=0
[ "${1:-}" = "--dry-run" ] && DRY=1

say() { printf '\n=== %s\n' "$*"; }
run() { if [ "$DRY" = "1" ]; then echo "  [dry-run] $*"; else eval "$@"; fi; }

say "0) Comprobaciones previas"
[ -d "$DEPLOY_DIR" ] || { echo "ERROR: no existe $DEPLOY_DIR (usa DEPLOY_DIR=...)"; exit 1; }
cd "$DEPLOY_DIR"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
  echo "ERROR: $DEPLOY_DIR no es un checkout git. Este script despliega con git;"
  echo "       si el codigo se copio a mano, clona el repo aqui o usa el procedimiento manual."; exit 1; }
[ -f docker-compose.yml ] || { echo "ERROR: falta $DEPLOY_DIR/docker-compose.yml"; exit 1; }
command -v git >/dev/null || { echo "ERROR: falta git"; exit 1; }
if [ "$DRY" != "1" ]; then command -v docker >/dev/null || { echo "ERROR: falta docker"; exit 1; }; fi
echo "  dir      : $DEPLOY_DIR"
echo "  rama     : $(git rev-parse --abbrev-ref HEAD)"
echo "  commit   : $(git log -1 --format='%h %s')"

# GUARDA: un deploy hace 'git reset --hard'. Si hay ficheros VERSIONADOS modificados en el servidor se
# perderian en silencio (paso una vez: un docker-compose.yml ajustado a mano con el montaje de datos).
DIRTY="$(git status --porcelain --untracked-files=no)"
if [ -n "$DIRTY" ]; then
  echo ""
  echo "ERROR: hay ficheros versionados MODIFICADOS en este servidor:"
  printf '%s\n' "$DIRTY" | sed 's/^/    /'
  echo "       'git reset --hard' los descartaria. Guardalos, commitealos, o repite con FORCE=1."
  if [ "${FORCE:-0}" = "1" ]; then echo "       FORCE=1: continuo y los descarto."; else exit 1; fi
fi

say "1) Datos y secretos (NO se tocan)"
if [ -d "$DEPLOY_DIR/data" ]; then
  echo "  data/    : $(du -sh "$DEPLOY_DIR/data" 2>/dev/null | cut -f1) — el despliegue NO lo modifica"
else
  echo "  AVISO: no encuentro $DEPLOY_DIR/data (¿montaje distinto?)"
fi
[ -f .env ] && echo "  .env     : presente (se conserva tal cual)" \
            || echo "  AVISO: no hay .env; DEEPSEEK_API_KEY quedaria vacia"

say "2) Que se va a desplegar"
run "git fetch --all --prune"
BEFORE="$(git rev-parse HEAD)"
TARGET="$(git rev-parse --verify --quiet "$REF" || true)"
if [ -z "$TARGET" ]; then
  echo "ERROR: no existe la referencia '$REF' en este checkout."
  echo "       Lo mas probable: los commits TODAVIA NO ESTAN EN EL REMOTO (falta el push)."
  echo "       Comprueba en tu PC:  git log --oneline origin/feature/deployment..HEAD"
  exit 1
fi
echo "  actual   : $(git log -1 --format='%h %s' "$BEFORE")"
echo "  destino  : $(git log -1 --format='%h %s' "$TARGET")"
if [ "$BEFORE" = "$TARGET" ]; then
  echo "  (nada nuevo: ya estas en $TARGET; se reconstruira igualmente)"
else
  if git merge-base --is-ancestor "$TARGET" "$BEFORE" 2>/dev/null; then
    echo ""
    echo "ERROR: este checkout esta POR DELANTE del destino."
    echo "       HEAD ya contiene $TARGET y tiene $(git rev-list --count "$TARGET..$BEFORE") commits locales que no estan en el remoto."
    echo "       Desplegar aqui haria 'git reset --hard' hacia atras y sacaria esos commits de la rama."
    echo "       Ejecuta este script EN EL SERVIDOR, o haz push primero desde tu equipo:"
    echo "         git push origin feature/deployment"
    exit 1
  fi
  echo "  commits nuevos:"
  git log --oneline "$BEFORE..$TARGET" | sed 's/^/    /'
fi

say "3) Respaldo para rollback"
run "docker tag eureka-backend:latest eureka-backend:rollback-$STAMP"
run "docker tag eureka-frontend:latest eureka-frontend:rollback-$STAMP"
run "cp -a docker-compose.yml docker-compose.yml.bak-$STAMP"
echo "  (las imagenes actuales quedan etiquetadas como :rollback-$STAMP)"

say "4) Actualizar el codigo y reconstruir"
run "git checkout $BRANCH"
run "git reset --hard $TARGET"
run "docker compose build backend frontend"

say "5) Arrancar"
run "docker compose up -d"

if [ "$DRY" = "1" ]; then
  say "DRY RUN: no se ha ejecutado nada"
  echo "  Ejecutalo sin --dry-run para desplegar de verdad."
  exit 0
fi

say "6) Verificacion del despliegue"
if ! command -v curl >/dev/null; then
  echo "  AVISO: curl no esta instalado; omito las comprobaciones HTTP."
  echo "  Comprueba a mano:  docker compose ps   y   http://<host>/api/health"
  exit 0
fi
CODE=""
for _ in $(seq 1 40); do
  CODE="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:$BACK_PORT/api/health" || true)"
  [ "$CODE" = "200" ] && break
  sleep 2
done
echo "  backend /api/health  -> $CODE"

# LA COMPROBACION QUE FALTABA: que la app VEA el almacen real. Sin el montaje ./data -> /app/data el
# contenedor arranca con un store VACIO, /api/health responde 200 y el login falla para todo el mundo.
MOUNTS="$(docker inspect eureka-backend --format '{{json .Mounts}}' 2>/dev/null || echo '[]')"
case "$MOUNTS" in
  *"/app/data"*) echo "  montaje de datos     -> OK (/app/data montado)" ;;
  *) echo "  ERROR: el contenedor NO tiene montado /app/data: correra con un almacen VACIO."
     echo "         mounts = $MOUNTS"
     echo "         Revisa 'volumes: - ./data:/app/data' en docker-compose.yml y vuelve a 'up -d'." ;;
esac
SEEN="$(docker exec eureka-backend python -c "import json,os
p='/app/data/identity/users.json'
print(len(json.load(open(p))) if os.path.exists(p) else 0)" 2>/dev/null || echo '?')"
echo "  cuentas que ve la app -> $SEEN"
case "$SEEN" in
  0) echo "    -> AVISO: la app no ve NINGUNA cuenta. Si el store tenia usuarios, falta el montaje." ;;
  '?') echo "    -> AVISO: no pude consultarlo (¿contenedor caido?)" ;;
  *) echo "    -> OK: la app esta leyendo el store persistente" ;;
esac

RST="$(curl -s -o /dev/null -w '%{http_code}' -X POST \
  "http://127.0.0.1:$BACK_PORT/api/admin/users/USR-NOPE/password" \
  -H 'Content-Type: application/json' -d '{"generate":true}' || true)"
echo "  POST /api/admin/users/{id}/password -> $RST"
case "$RST" in
  401|403) echo "    -> la ruta NUEVA existe (autenticacion exigida = codigo desplegado) OK" ;;
  404)     echo "    -> 404: el codigo VIEJO sigue activo; revisa el build" ;;
  *)       echo "    -> respuesta inesperada" ;;
esac
HTML="$(curl -s "http://127.0.0.1:$FRONT_PORT/" || true)"
ASSET="$(printf '%s' "$HTML" | grep -o 'assets/[A-Za-z0-9._-]*\.js' | head -1 || true)"
if [ -n "$ASSET" ]; then
  if curl -s "http://127.0.0.1:$FRONT_PORT/$ASSET" | grep -q 'Create user'; then
    echo "  frontend bundle      -> contiene 'Create user' OK"
  else
    echo "  frontend bundle      -> AVISO: no encuentro 'Create user' (¿cache del navegador?)"
  fi
else
  echo "  frontend             -> AVISO: no pude leer el bundle en el puerto $FRONT_PORT"
fi

say "7) Hecho"
echo "  commit desplegado: $(git log -1 --format='%h %s')"
echo ""
echo "  ROLLBACK si algo va mal:"
echo "    cd $DEPLOY_DIR"
echo "    docker tag eureka-backend:rollback-$STAMP eureka-backend:latest"
echo "    docker tag eureka-frontend:rollback-$STAMP eureka-frontend:latest"
echo "    git reset --hard $BEFORE"
echo "    docker compose up -d --force-recreate"
echo ""
echo "  Los datos (data/) y el .env no se han tocado en ningun momento."
