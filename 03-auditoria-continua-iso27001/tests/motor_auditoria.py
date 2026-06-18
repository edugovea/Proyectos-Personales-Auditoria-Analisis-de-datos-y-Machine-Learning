# ============================================================
# tests/motor_auditoria.py  -  Ejemplo de POO aplicado al proyecto (ISO-29)
# ------------------------------------------------------------
# Una CLASE agrupa DATOS (aca: la conexion a la base) y ACCIONES sobre esos
# datos (los METODOS: ejecutar el motor, contar hallazgos, intentar borrar...).
# En vez de pasar la conexion suelta a cada funcion, creamos UN objeto que la
# guarda adentro (self.conn) y le pedimos cosas con notacion de punto:
#       motor = MotorAuditoria()
#       motor.ejecutar()
#       motor.falsos_positivos()
# Eso es Programacion Orientada a Objetos: un "objeto" que sabe sus datos y
# sabe operar sobre ellos.
# ============================================================
import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

# Carga DATABASE_URL desde el .env del proyecto (la misma que usa el generador)
load_dotenv(Path(__file__).resolve().parent.parent / ".env")


class MotorAuditoria:
    """Envuelve la conexion y las operaciones del motor de deteccion."""

    def __init__(self, database_url=None):
        # __init__ es el "constructor": corre al crear el objeto y prepara
        # su estado interno. Aca abre y guarda la conexion en self.conn.
        url = database_url or os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("Falta DATABASE_URL (.env).")
        self.conn = psycopg2.connect(url)
        self.conn.autocommit = True

    # --- acciones del motor -------------------------------------------------
    def cargar_sql(self, ruta):
        """Ejecuta el contenido de un archivo .sql (idempotente: CREATE OR REPLACE)."""
        with open(ruta, encoding="utf-8") as fh, self.conn.cursor() as cur:
            cur.execute(fh.read())

    def ejecutar(self):
        """Corre la orquestadora y devuelve {anomalia: hallazgos_nuevos}."""
        with self.conn.cursor() as cur:
            cur.execute("SELECT anomalia, hallazgos_nuevos FROM ejecutar_auditoria();")
            return {fila[0]: fila[1] for fila in cur.fetchall()}

    # --- lecturas de control ------------------------------------------------
    def findings_por_codigo(self):
        with self.conn.cursor() as cur:
            cur.execute("SELECT anomaly_code, count(*) FROM findings GROUP BY anomaly_code;")
            return {fila[0].strip(): fila[1] for fila in cur.fetchall()}

    def total_findings(self):
        return self._scalar("SELECT count(*) FROM findings;")

    def total_expected(self):
        return self._scalar("SELECT count(*) FROM expected_findings;")

    def falsos_positivos(self):
        """Hallazgos que el motor marco pero NO estan en la verdad conocida."""
        return self._scalar(
            "SELECT count(*) FROM findings f "
            "WHERE NOT EXISTS (SELECT 1 FROM expected_findings e "
            "                  WHERE e.event_id=f.event_id AND e.anomaly_code=f.anomaly_code);"
        )

    def falsos_negativos(self):
        """Violaciones reales que el motor NO detecto."""
        return self._scalar(
            "SELECT count(*) FROM expected_findings e "
            "WHERE NOT EXISTS (SELECT 1 FROM findings f "
            "                  WHERE f.event_id=e.event_id AND f.anomaly_code=e.anomaly_code);"
        )

    # --- pruebas de inmutabilidad del trigger -------------------------------
    def un_finding_id(self):
        return self._scalar("SELECT finding_id FROM findings ORDER BY finding_id LIMIT 1;")

    def borrar_bloqueado(self, finding_id):
        """True si el trigger IMPIDIO el DELETE (lo esperado)."""
        return self._operacion_bloqueada(
            "DELETE FROM findings WHERE finding_id=%s", (finding_id,))

    def modificar_evidencia_bloqueado(self, finding_id):
        """True si el trigger IMPIDIO alterar la evidencia (lo esperado)."""
        return self._operacion_bloqueada(
            "UPDATE findings SET evidencia='ALTERADA' WHERE finding_id=%s", (finding_id,))

    def cerrar(self):
        self.conn.close()

    # --- helpers internos (el guion bajo indica "uso interno") --------------
    def _scalar(self, sql, params=None):
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchone()[0]

    def _operacion_bloqueada(self, sql, params):
        try:
            with self.conn.cursor() as cur:
                cur.execute(sql, params)
            return False   # paso -> NO esta bloqueado
        except psycopg2.Error:
            return True    # el trigger lanzo excepcion -> bloqueado
