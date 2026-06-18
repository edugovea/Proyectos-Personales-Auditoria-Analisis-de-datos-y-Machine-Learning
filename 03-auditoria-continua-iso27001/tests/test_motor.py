# ============================================================
# tests/test_motor.py  -  Tests del motor de deteccion (ISO-29)
# ------------------------------------------------------------
# Validan las dos promesas del proyecto:
#   1) el motor detecta TODAS las violaciones reales (sin falsos negativos),
#   2) y NO marca el ruido legitimo (sin falsos positivos).
# Ademas: conteos por anomalia, idempotencia e inmutabilidad de findings.
#
# Como correrlos (desde la carpeta del proyecto, con el venv activo):
#       .venv\Scripts\python.exe -m pytest -v
# ============================================================
import subprocess
import sys
from pathlib import Path

import pytest

from motor_auditoria import MotorAuditoria

PROJECT_ROOT = Path(__file__).resolve().parent.parent
MOTOR_SQL = PROJECT_ROOT / "db" / "motor"
ESPERADO_POR_CODIGO = {"A1": 4, "A2": 5, "A3": 3, "A4": 4}


@pytest.fixture(scope="session")
def motor():
    """Prepara un escenario limpio una sola vez para todos los tests:
    1) regenera los datos sinteticos (el generador deja findings vacia),
    2) asegura las funciones del motor cargadas,
    3) corre la auditoria completa una vez.
    """
    # 1) datos frescos y reproducibles (semilla fija dentro del generador)
    subprocess.run([sys.executable, "-m", "generador"], cwd=PROJECT_ROOT, check=True)

    m = MotorAuditoria()

    # 2) cargar las 4 funciones + la orquestadora (CREATE OR REPLACE: idempotente)
    for archivo in ("10_fn_detectar_a1", "11_fn_detectar_a2",
                    "12_fn_detectar_a3", "13_fn_detectar_a4",
                    "20_sp_ejecutar_auditoria"):
        m.cargar_sql(MOTOR_SQL / f"{archivo}.sql")

    # 3) correr el motor
    m.ejecutar()

    yield m
    m.cerrar()


def test_motor_sin_falsos_negativos(motor):
    # No se le escapa ninguna violacion real
    assert motor.falsos_negativos() == 0


def test_motor_sin_falsos_positivos(motor):
    # No marca ninguno de los casos de ruido legitimo
    assert motor.falsos_positivos() == 0


def test_conteo_por_anomalia(motor):
    assert motor.findings_por_codigo() == ESPERADO_POR_CODIGO


def test_total_coincide_con_ground_truth(motor):
    assert motor.total_findings() == 16
    assert motor.total_expected() == 16


def test_motor_es_idempotente(motor):
    # Correr la auditoria de nuevo no debe sumar hallazgos
    nuevos = motor.ejecutar()
    assert nuevos == {"A1": 0, "A2": 0, "A3": 0, "A4": 0}


def test_finding_no_se_puede_borrar(motor):
    # El trigger de inmutabilidad debe impedir el DELETE
    assert motor.borrar_bloqueado(motor.un_finding_id()) is True


def test_evidencia_es_inmutable(motor):
    # El trigger debe impedir alterar la evidencia
    assert motor.modificar_evidencia_bloqueado(motor.un_finding_id()) is True
