#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""EUREKA — reset ONE user's password (OFFLINE, runs inside the backend image).

WHY OFFLINE: the identity store caches each JSON file in memory and rewrites the whole file on any
write, so an edit made by a separate process while the backend runs can be silently reverted by the
next login. The supported procedure is: stop the backend, run this, start the backend.

WHY INSIDE THE IMAGE: Argon2id (argon2-cffi) lives in the backend image, not on the VPS host.

WHAT IT DOES (same semantics as the app's own reset path, without importing the API):
  * validates the new password against the declared policy (or GENERATES a compliant one)
  * hashes it with Argon2id (the app's own hash_password when importable)
  * clears failed_login_count and locked_until (otherwise the reset would not restore access)
  * REVOKES every live session of that user (the old credential dies with them)
  * appends ONE audit event: PASSWORD_RESET_COMPLETED, mode OFFLINE_BOOTSTRAP
  * never writes the password anywhere on disk

USAGE
  python3 reset_password.py --email <email> --stdin [--data-dir DIR]
  python3 reset_password.py --email <email> --generate [--apply]
  python3 reset_password.py --list
"""
from __future__ import annotations

import argparse
import json
import os
import random
import secrets
import shutil
import stat
import sys
import tempfile
import time

STAMP = time.strftime("%Y%m%d-%H%M%S")
NOW = time.strftime("%Y-%m-%dT%H:%M:%S+00:00", time.gmtime())

# Running this file by path puts ITS directory on sys.path, not the app root, so the app's own
# primitives would never be found. Add the likely roots so `src.eureka.identity.*` imports work when
# the process runs with the app's working directory (the backend image uses /app).
for _candidate in (os.getcwd(), "/app", os.path.dirname(os.path.dirname(os.path.abspath(__file__)))):
    if _candidate and os.path.isdir(_candidate) and _candidate not in sys.path:
        sys.path.insert(0, _candidate)

TRIVIAL = {"password", "password1", "password123", "12345678", "1234567890", "qwerty123",
           "letmein1", "admin123", "welcome1", "iloveyou1", "abc12345"}
ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"   # no 0/O, no 1/l/I
SYMBOLS = "!@#$%&*?-_"


# --------------------------------------------------------------------------- policy + hashing
def resolve_policy() -> dict:
    """Prefer the app's declared policy; fall back to the documented default."""
    try:
        from src.eureka.identity.config import identity_config
        return dict(identity_config().get("password_policy", {}))
    except Exception:                                                # noqa: BLE001
        try:
            from eureka.identity.config import identity_config
            return dict(identity_config().get("password_policy", {}))
        except Exception:                                            # noqa: BLE001
            return {"min_length": 12}


def resolve_crypto():
    """The app's own Argon2id primitives when importable; otherwise the same parameters inline."""
    try:
        from src.eureka.identity.security import hash_password, verify_password
        return hash_password, verify_password, "app(src.eureka.identity.security)"
    except Exception:                                                # noqa: BLE001
        try:
            from eureka.identity.security import hash_password, verify_password
            return hash_password, verify_password, "app(eureka.identity.security)"
        except Exception:                                            # noqa: BLE001
            from argon2 import PasswordHasher
            from argon2.exceptions import (InvalidHashError, VerificationError,
                                           VerifyMismatchError)
            hasher = PasswordHasher(time_cost=3, memory_cost=65536, parallelism=4)

            def _verify(password, stored):
                try:
                    return bool(hasher.verify(stored, password))
                except (VerifyMismatchError, VerificationError, InvalidHashError):
                    return False

            return (lambda pw: hasher.hash(pw)), _verify, "argon2-cffi inline (t=3, m=64MiB, p=4)"


def policy_issues(password: str, policy: dict, email: str) -> list:
    issues = []
    minimum = int(policy.get("min_length", 12))
    if len(password) < minimum:
        issues.append("minimo %d caracteres" % minimum)
    if not any(c.isalpha() for c in password):
        issues.append("al menos una letra")
    if not any(c.isdigit() for c in password):
        issues.append("al menos un digito")
    if password.lower() in TRIVIAL:
        issues.append("no puede ser una contrasena comun")
    if password.lower() == (email or "").strip().lower():
        issues.append("no puede ser el email de la cuenta")
    return issues


def generate_password(minimum: int) -> str:
    length = max(int(minimum), 16)
    pool = ALPHABET + SYMBOLS
    while True:
        chars = [secrets.choice("ABCDEFGHJKLMNPQRSTUVWXYZ"),
                 secrets.choice("abcdefghijkmnopqrstuvwxyz"),
                 secrets.choice("23456789")]
        chars += [secrets.choice(pool) for _ in range(length - len(chars))]
        secrets.SystemRandom().shuffle(chars)
        candidate = "".join(chars)
        if any(c.isupper() for c in candidate) and any(c.islower() for c in candidate) \
                and any(c.isdigit() for c in candidate):
            return candidate


# --------------------------------------------------------------------------- store I/O
def load(path: str) -> dict:
    if not os.path.exists(path):
        sys.exit("ERROR: no existe " + path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except Exception as exc:                                         # noqa: BLE001
        sys.exit("ERROR: %s corrupto: %s" % (path, exc))
    if not isinstance(data, dict):
        sys.exit("ERROR: %s no es un objeto JSON" % path)
    return data


def save(path: str, data: dict) -> None:
    """Byte-identical style to the app (indent=2, ensure_ascii=False) + atomic + uid/gid/mode kept."""
    original = os.stat(path)
    handle, tmp = tempfile.mkstemp(dir=os.path.dirname(os.path.abspath(path)), prefix=".reset-")
    with os.fdopen(handle, "w", encoding="utf-8") as out:
        json.dump(data, out, indent=2, ensure_ascii=False)
    os.chmod(tmp, stat.S_IMODE(original.st_mode))
    try:
        os.chown(tmp, original.st_uid, original.st_gid)
        owner = "%s:%s preservado" % (original.st_uid, original.st_gid)
    except Exception:                                                # noqa: BLE001
        owner = "propietario sin cambios (no root); era %s:%s" % (original.st_uid, original.st_gid)
    os.replace(tmp, path)
    print("    escrito %s (modo %s, %s)" % (path, oct(stat.S_IMODE(original.st_mode)), owner))


def main() -> int:
    parser = argparse.ArgumentParser(description="Reset one EUREKA password (offline).")
    parser.add_argument("--data-dir", default=os.environ.get("EUREKA_IDENTITY_STORAGE_DIR",
                                                             "/app/data/identity"))
    parser.add_argument("--email", default=None)
    parser.add_argument("--stdin", action="store_true", help="read the new password from stdin")
    parser.add_argument("--generate", action="store_true", help="let this script generate the password")
    parser.add_argument("--apply", action="store_true",
                        help="with --generate: write it (otherwise dry run)")
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args()

    users_path = os.path.join(args.data_dir, "users.json")
    sessions_path = os.path.join(args.data_dir, "sessions.json")
    events_path = os.path.join(args.data_dir, "auth_events.json")
    policy = resolve_policy()
    hash_password, verify_password, hasher_label = resolve_crypto()

    print("EUREKA reset de contrasena — OFFLINE")
    print("  data dir : %s" % args.data_dir)
    print("  hasher   : %s" % hasher_label)
    print("  politica : min_length=%s" % policy.get("min_length", 12))
    print()

    users = load(users_path)
    if args.list or not args.email:
        print("%-20s %-42s %-13s %-9s %s" % ("USER_ID", "EMAIL", "ROLE", "STATUS", "FALLOS"))
        print("-" * 100)
        for uid, rec in sorted(users.items(), key=lambda kv: str(kv[1].get("email", ""))):
            print("%-20s %-42s %-13s %-9s %s" % (uid, str(rec.get("email", ""))[:42], rec.get("role"),
                                                 rec.get("status"), rec.get("failed_login_count")))
        if not args.email:
            print("\nNada que hacer: pasa --email <cuenta>.")
        return 0

    want = args.email.strip().lower()
    hits = [(uid, rec) for uid, rec in users.items()
            if str(rec.get("email", "")).strip().lower() == want]
    if not hits:
        sys.exit("ERROR: no hay ninguna cuenta con el email " + args.email)
    if len(hits) > 1:
        sys.exit("ERROR: %d cuentas coinciden con %s" % (len(hits), args.email))
    uid, record = hits[0]

    print("CUENTA")
    print("  user_id : %s" % uid)
    print("  email   : %s" % record.get("email"))
    print("  rol     : %s | estado: %s" % (record.get("role"), record.get("status")))
    print("  fallos  : %s | locked_until: %s" % (record.get("failed_login_count"),
                                                 record.get("locked_until")))
    if record.get("status") != "ACTIVE":
        print("\n  AVISO: el estado no es ACTIVE: la contrasena nueva NO le dejara entrar todavia.")

    generated = False
    if args.generate:
        password = generate_password(policy.get("min_length", 12))
        generated = True
    elif args.stdin:
        # Read BYTES and decode UTF-8 explicitly. Using sys.stdin.read() would decode with the
        # process locale (cp1252 on Windows, POSIX/C in a bare container) and silently turn a
        # password containing e.g. 'n-tilde' into a different string — hashed as the wrong secret.
        password = sys.stdin.buffer.read().decode("utf-8").rstrip("\r\n")
        if not password:
            sys.exit("ERROR: no se recibio ninguna contrasena por stdin")
    else:
        sys.exit("ERROR: indica --stdin (leer la contrasena) o --generate")

    issues = policy_issues(password, policy, str(record.get("email", "")))
    if issues:
        print("\nERROR: la contrasena no cumple la politica: %s" % "; ".join(issues))
        return 2

    if generated and not args.apply:
        print("\nGENERADA (dry run, no se ha escrito nada): %s" % password)
        print("Re-ejecuta con --generate --apply para aplicarla.")
        return 0

    print("\nAPLICANDO")
    shutil.copy2(users_path, "%s.bak-%s" % (users_path, STAMP))
    print("    backup %s.bak-%s" % (users_path, STAMP))
    old_hash = str(record.get("password_hash", ""))
    record["password_hash"] = hash_password(password)
    record["failed_login_count"] = 0
    record["locked_until"] = None
    record["updated_at"] = NOW
    users[uid] = record
    save(users_path, users)

    revoked = 0
    if os.path.exists(sessions_path):
        sessions = load(sessions_path)
        shutil.copy2(sessions_path, "%s.bak-%s" % (sessions_path, STAMP))
        for sid, session in sessions.items():
            if session.get("user_id") == uid and not session.get("revoked_at"):
                session["revoked_at"] = NOW
                sessions[sid] = session
                revoked += 1
        if revoked:
            save(sessions_path, sessions)
        print("    sesiones revocadas: %d" % revoked)

    events = load(events_path) if os.path.exists(events_path) else {}
    if os.path.exists(events_path):
        shutil.copy2(events_path, "%s.bak-%s" % (events_path, STAMP))
    event_id = "AE-BOOT-%012X" % random.getrandbits(48)
    events[event_id] = {"event_id": event_id, "user_id": uid,
                        "event_type": "PASSWORD_RESET_COMPLETED", "timestamp": NOW, "success": True,
                        "session_id": None,
                        "metadata": {"actor_user_id": "OFFLINE_BOOTSTRAP", "target_user_id": uid,
                                     "mode": "OFFLINE_BOOTSTRAP",
                                     "password_generated": generated,
                                     "sessions_revoked": revoked}}
    save(events_path, events)

    print("\nVERIFICACION (releido del disco)")
    final = load(users_path).get(uid, {})
    new_hash = str(final.get("password_hash", ""))
    checks = {
        "el hash cambio": new_hash != old_hash and new_hash.startswith("$argon2"),
        "la contrasena NUEVA valida contra el hash guardado": verify_password(password, new_hash),
        "la contrasena nueva NO valida contra el hash viejo": not verify_password(password, old_hash),
        "fallos y bloqueo limpiados": final.get("failed_login_count") == 0
                                      and not final.get("locked_until"),
    }
    print("  hash actualizado : %s" % (new_hash[:18] + "..."))
    print("  fallos / locked  : %s / %s" % (final.get("failed_login_count"), final.get("locked_until")))
    print("  evento auditoria : %s" % event_id)
    for label, value in checks.items():
        print("  [%s] %s" % ("OK" if value else "FALLO", label))
    if generated:
        print("\nCONTRASENA NUEVA (se muestra UNA vez; NO queda en disco): %s" % password)
    ok = all(checks.values())
    print("\nRESULTADO: %s" % ("OK" if ok else "REVISAR"))
    print("Arranca el backend y prueba el login.")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
