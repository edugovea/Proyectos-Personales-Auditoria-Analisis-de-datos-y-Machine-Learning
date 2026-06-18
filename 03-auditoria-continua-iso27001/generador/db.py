# ============================================================
# Generador - Capa de acceso a datos (psycopg2)
# ------------------------------------------------------------
# Conexion via DATABASE_URL (.env) e inserciones masivas con execute_values.
# ============================================================
import os

import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

load_dotenv()  # lee .env del directorio del proyecto si existe


def get_connection():
    """Abre una conexion a PostgreSQL usando DATABASE_URL del entorno."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "Falta DATABASE_URL. Copia .env.example a .env y completa la cadena "
            "de conexion (ej: postgresql://auditor:clave@localhost:5432/iso27001)."
        )
    return psycopg2.connect(url)


def limpiar_tablas(cur):
    """Vacia las tablas y reinicia las secuencias (corrida idempotente).

    findings es inmutable (triggers que bloquean UPDATE/DELETE/TRUNCATE). Pero
    un reseed COMPLETO del entorno sintetico es una operacion de SETUP, no del
    sistema de auditoria en marcha: aca levantamos el guardia solo durante el
    reset y lo restauramos enseguida. Si findings aun no existe (no se corrio
    02_findings.sql), se limpian solo las 3 tablas de datos.
    """
    cur.execute("SELECT to_regclass('public.findings');")
    hay_findings = cur.fetchone()[0] is not None

    if hay_findings:
        cur.execute("ALTER TABLE findings DISABLE TRIGGER USER;")
        cur.execute(
            "TRUNCATE findings, expected_findings, access_events, users "
            "RESTART IDENTITY CASCADE;"
        )
        cur.execute("ALTER TABLE findings ENABLE TRIGGER USER;")
    else:
        cur.execute(
            "TRUNCATE expected_findings, access_events, users "
            "RESTART IDENTITY CASCADE;"
        )


def insertar_usuarios(cur, usuarios):
    """Inserta usuarios y devuelve la lista con el user_id asignado.

    `usuarios` es una lista de dicts. Devuelve la misma lista enriquecida
    con la clave 'user_id' (en el orden de insercion).
    """
    filas = [
        (
            u["username"], u["full_name"], u["department"], u["role"],
            u["status"], u["hire_date"], u["termination_date"],
        )
        for u in usuarios
    ]
    ids = execute_values(
        cur,
        """
        INSERT INTO users
            (username, full_name, department, role, status, hire_date, termination_date)
        VALUES %s
        RETURNING user_id
        """,
        filas,
        fetch=True,
    )
    for u, (uid,) in zip(usuarios, ids):
        u["user_id"] = uid
    return usuarios


def insertar_eventos(cur, eventos):
    """Inserta eventos de acceso y devuelve los event_id en orden de insercion.

    Cada evento es un dict. Devuelve la misma lista enriquecida con 'event_id'.
    """
    filas = [
        (
            e["user_id"], e["event_ts"], e["event_type"], e["resource"],
            e.get("transaction_id"), e["role_at_event"],
            e.get("approval_ticket_id"), e["source_ip"], e.get("success", True),
        )
        for e in eventos
    ]
    ids = execute_values(
        cur,
        """
        INSERT INTO access_events
            (user_id, event_ts, event_type, resource, transaction_id,
             role_at_event, approval_ticket_id, source_ip, success)
        VALUES %s
        RETURNING event_id
        """,
        filas,
        fetch=True,
    )
    for e, (eid,) in zip(eventos, ids):
        e["event_id"] = eid
    return eventos


def insertar_expected_findings(cur, eventos):
    """Carga el ground truth: un registro por evento con anomaly_code != None."""
    filas = [
        (e["event_id"], e["anomaly_code"], e.get("note"))
        for e in eventos
        if e.get("anomaly_code")
    ]
    if not filas:
        return 0
    execute_values(
        cur,
        "INSERT INTO expected_findings (event_id, anomaly_code, note) VALUES %s",
        filas,
    )
    return len(filas)
