# EUREKA — herramientas de operación (`scripts/`)

Cuatro utilidades que se ejecutan **en el servidor** (o en el checkout de despliegue). Están en el
repositorio a propósito: así llegan por `git` y **no hay que pegarlas a mano** en una terminal (los
pegados largos pierden líneas de forma silenciosa).

| Fichero | Para qué | ¿Escribe? |
|---|---|---|
| `deploy.sh` | Desplegar: comprobar → respaldar → actualizar → reconstruir → arrancar → **verificar** | Sí (código; **nunca** `data/` ni `.env`) |
| `reset_password.py` | Resetear UNA contraseña (offline, dentro de la imagen del backend) | Sí (con backup) |
| `reset-password.sh` | Envoltura cómoda del anterior: un comando por reset | Sí (vía el anterior) |
| `set_superadmin.py` | Conceder un rol (bootstrap del primer administrador) | Sí (con backup) |

## La regla que explica el diseño

El almacén de identidad (`identity/store.py`, `_JsonCollection`) **cachea cada JSON en memoria** y en
cada escritura reescribe **el fichero completo**. Por tanto, un cambio hecho por otro proceso mientras
el backend corre **se pierde en el siguiente login**. De ahí:

* los cambios de rol/contraseña se hacen **offline**: parar → escribir → arrancar;
* `deploy.sh` **no** toca `data/`: reconstruye las imágenes y reinicia, y el backend relee los ficheros
  al arrancar.

Y Argon2id (`argon2-cffi`) vive **en la imagen del backend**, no en el host: por eso los scripts de
identidad se ejecutan dentro de un contenedor desechable con la misma imagen y `data/` montado.

## Despliegue

```bash
sudo bash scripts/deploy.sh --dry-run   # enseña el plan y NO ejecuta nada
sudo bash scripts/deploy.sh             # despliega
```

Si algo va mal, al final imprime el **rollback** exacto (retag de las imágenes `:rollback-<fecha>` +
`git reset --hard <commit anterior>` + `up -d --force-recreate`).

Requisito: el commit a desplegar **tiene que estar en el remoto**. Si no lo está, el script lo dice
(`git log --oneline origin/feature/deployment..HEAD` desde el equipo de desarrollo).

## Contraseñas

```bash
sudo bash scripts/reset-password.sh --list                    # ver cuentas (no escribe)
sudo bash scripts/reset-password.sh <email>                   # la escribes tú (no se muestra)
sudo bash scripts/reset-password.sh --generate <email>        # la genera y la muestra UNA vez
```

* La contraseña viaja por **stdin**, nunca por argumento (no aparece en `ps` ni en el historial).
* Se lee como **bytes UTF-8 explícitos**: con `sys.stdin.read()` la página de códigos del proceso
  convertiría `ñ` en otra cadena y el hash se crearía de la contraseña equivocada.
* `--generate` produce una contraseña **ASCII** sin glifos ambiguos (0/O, 1/l/I): evita de raíz el
  problema NFC/NFD de los caracteres acentuados.
* El script limpia `failed_login_count` y `locked_until` (si no, el reset no devuelve el acceso) y
  **revoca las sesiones** del usuario. Al terminar **verifica** contra el hash guardado.

## Roles (bootstrap del primer administrador)

```bash
DATA_DIR=/opt/eureka/data/identity python3 scripts/set_superadmin.py --list
DATA_DIR=/opt/eureka/data/identity python3 scripts/set_superadmin.py --email <email>            # dry run
DATA_DIR=/opt/eureka/data/identity APPLY=1 python3 scripts/set_superadmin.py --email <email>    # aplica
```

**Parar el backend antes** (`docker stop eureka-backend`) y arrancarlo después. Este script es
Python puro de stdlib, así que corre en el host: no necesita la imagen.

Existe porque un despliegue nuevo se queda **sin ningún administrador** y todos los endpoints
`/api/admin/*` exigen uno ya existente: sin esta herramienta no hay forma de crear al primero.

## Auditoría

Los scripts de identidad añaden un evento a `auth_events.json` con `mode: OFFLINE_BOOTSTRAP` y
`actor_user_id: OFFLINE_BOOTSTRAP`, de modo que en la auditoría se distingue una acción hecha **fuera
de la API** de una hecha desde el panel. Cada fichero que se modifica deja un backup con marca de
tiempo al lado (`.bak-YYYYMMDD-HHMMSS`) y la escritura es atómica, preservando `uid/gid/modo`.
