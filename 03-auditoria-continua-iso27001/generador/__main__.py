# ============================================================
# Generador - Orquestador (python -m generador)
# ------------------------------------------------------------
# Reconstruye el dataset completo de forma reproducible:
#   1) limpia las tablas        4) inyecta A1..A4 con ruido
#   2) genera usuarios          5) inserta todo en PostgreSQL
#   3) genera trafico normal    6) carga expected_findings (ground truth)
# Uso:
#   python -m generador            -> genera e inserta en la base (.env)
#   python -m generador --resumen  -> ademas imprime el desglose por anomalia
# ============================================================
import itertools
import random
import sys

from faker import Faker

from . import config, db, usuarios as mod_users, eventos as mod_eventos, anomalias


def construir_dataset():
    """Genera usuarios y eventos en memoria (sin tocar la base).

    Devuelve (usuarios, eventos). Los user_id aun NO estan asignados aqui;
    se asignan al insertar. Para la generacion de eventos se usan los user_id
    ya presentes en los dicts de usuario (ver flujo en main()).
    """
    rng = random.Random(config.SEED)
    fake = Faker("es_ES")
    Faker.seed(config.SEED)
    usuarios = mod_users.generar_usuarios(rng, fake)
    return rng, usuarios


def generar_eventos(rng, usuarios):
    """Eventos normales + las 4 anomalias con ruido. tx_seq compartido."""
    tx_seq = itertools.count(1)
    eventos = []
    eventos += mod_eventos.generar_eventos_normales(rng, usuarios, tx_seq)
    eventos += anomalias.inyectar_a1(rng, usuarios)
    eventos += anomalias.inyectar_a2(rng, usuarios)
    eventos += anomalias.inyectar_a3(rng, usuarios)
    eventos += anomalias.inyectar_a4(rng, usuarios, tx_seq)
    eventos.sort(key=lambda e: e["event_ts"])  # orden cronologico realista
    return eventos


def main():
    resumen = "--resumen" in sys.argv

    rng, usuarios = construir_dataset()

    conn = db.get_connection()
    try:
        with conn:
            with conn.cursor() as cur:
                db.limpiar_tablas(cur)
                db.insertar_usuarios(cur, usuarios)        # asigna user_id
                eventos = generar_eventos(rng, usuarios)   # usa esos user_id
                db.insertar_eventos(cur, eventos)          # asigna event_id
                n_expected = db.insertar_expected_findings(cur, eventos)
        # commit automatico al salir del 'with conn'
    finally:
        conn.close()

    n_viol = sum(1 for e in eventos if e.get("anomaly_code"))
    print("Dataset generado e insertado correctamente.")
    print(f"  usuarios           : {len(usuarios)}")
    print(f"  eventos de acceso  : {len(eventos)}")
    print(f"  violaciones reales : {n_viol}  (expected_findings: {n_expected})")

    if resumen:
        print("\nDesglose de violaciones por anomalia (ground truth):")
        for code in ("A1", "A2", "A3", "A4"):
            n = sum(1 for e in eventos if e.get("anomaly_code") == code)
            regla = config.REGLAS_DETECCION[code]
            print(f"  {code} [{regla['control_iso']} / {regla['severidad']}]: {n}")


if __name__ == "__main__":
    main()
