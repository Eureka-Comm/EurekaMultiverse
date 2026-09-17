"""Compact, paste-able version of the offline role grant (VPS).

Guarantees kept: DRY RUN by default (APPLY=1 to write), timestamped backups, atomic write preserving
uid/gid/mode (the app user must keep ownership), ONE audit event marked OFFLINE_BOOTSTRAP, email
normalisation (a non-normalised email cannot sign in), and fail-closed on a missing/corrupt store.

Env: DATA_DIR (default /opt/eureka/data/identity), EMAIL, ROLE (default SUPER_ADMIN), APPLY (0/1).
"""
import json
import os
import random
import shutil
import stat
import sys
import tempfile
import time

DATA = os.environ.get("DATA_DIR", "/opt/eureka/data/identity")
EMAIL = os.environ.get("EMAIL", "aguilar.hugo55@gmail.com")
ROLE = os.environ.get("ROLE", "SUPER_ADMIN")
APPLY = os.environ.get("APPLY", "0") == "1"
UP = os.path.join(DATA, "users.json")
EP = os.path.join(DATA, "auth_events.json")
STAMP = time.strftime("%Y%m%d-%H%M%S")
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())


def load(path):
    if not os.path.exists(path):
        sys.exit("ERROR: no existe " + path)
    try:
        data = json.load(open(path, encoding="utf-8"))
    except Exception as exc:
        sys.exit("ERROR: %s corrupto: %s" % (path, exc))
    if not isinstance(data, dict):
        sys.exit("ERROR: %s no es un objeto JSON" % path)
    return data


def save(path, data):
    st = os.stat(path)
    handle, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".setrole-")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=2, ensure_ascii=False)
    os.chmod(tmp, stat.S_IMODE(st.st_mode))
    try:
        os.chown(tmp, st.st_uid, st.st_gid)
        owner = "propietario %s:%s preservado" % (st.st_uid, st.st_gid)
    except Exception as exc:
        owner = "AVISO: propietario sin preservar (%s); era %s:%s" % (exc, st.st_uid, st.st_gid)
    os.replace(tmp, path)
    print("  escrito %s (modo %s, %s)" % (path, oct(stat.S_IMODE(st.st_mode)), owner))


print("EUREKA role grant — %s" % ("APPLY (escribe)" if APPLY else "DRY RUN (no escribe nada)"))
users = load(UP)
want = EMAIL.strip().lower()
hits = [(uid, rec) for uid, rec in users.items() if (rec.get("email") or "").strip().lower() == want]
if not hits:
    sys.exit("ERROR: no hay ninguna cuenta con el email " + EMAIL)
if len(hits) > 1:
    sys.exit("ERROR: %d cuentas coinciden con %s" % (len(hits), EMAIL))

uid, rec = hits[0]
old_role = rec.get("role")
needs_email_fix = rec.get("email") != want
print("objetivo  : %s" % uid)
print("email     : %s%s" % (rec.get("email"),
                            "   <-- SIN normalizar: esta cuenta NO puede entrar" if needs_email_fix else ""))
print("rol       : %s  ->  %s" % (old_role, ROLE))
print("estado    : %s | mfa=%s | verificado=%s | fallos=%s | locked=%s"
      % (rec.get("status"), rec.get("mfa_enabled"), rec.get("email_verified"),
         rec.get("failed_login_count"), rec.get("locked_until")))
if rec.get("status") != "ACTIVE":
    print("AVISO: el estado no es ACTIVE: el rol por si solo NO le dejara entrar")
if old_role == ROLE and not needs_email_fix:
    print("\nNada que cambiar (ya es %s y el email esta normalizado)." % ROLE)
    sys.exit(0)
if not APPLY:
    print("\nDRY RUN: no se ha escrito nada. Repite con APPLY=1 para aplicar.")
    sys.exit(0)

print("\nAPLICANDO")
shutil.copy2(UP, "%s.bak-%s" % (UP, STAMP))
print("  backup %s.bak-%s" % (UP, STAMP))
rec["role"] = ROLE
if needs_email_fix:
    rec["email"] = want
rec["updated_at"] = NOW
users[uid] = rec
save(UP, users)

if os.path.exists(EP):
    shutil.copy2(EP, "%s.bak-%s" % (EP, STAMP))
    print("  backup %s.bak-%s" % (EP, STAMP))
events = load(EP) if os.path.exists(EP) else {}
event_id = "AE-BOOT-%012X" % random.getrandbits(48)
events[event_id] = {"event_id": event_id, "user_id": uid, "event_type": "ROLE_CHANGED",
                    "timestamp": NOW, "success": True, "session_id": None,
                    "metadata": {"actor_user_id": "OFFLINE_BOOTSTRAP", "target_user_id": uid,
                                 "from": old_role, "to": ROLE, "mode": "OFFLINE_BOOTSTRAP"}}
save(EP, events)

final = json.load(open(UP, encoding="utf-8")).get(uid, {})
ok = final.get("role") == ROLE and (not needs_email_fix or final.get("email") == want)
print("\nVERIFICACION (releido del disco): rol=%s email=%s evento=%s"
      % (final.get("role"), final.get("email"), event_id))
print("RESULTADO: %s" % ("OK" if ok else "REVISAR"))
sys.exit(0 if ok else 1)
