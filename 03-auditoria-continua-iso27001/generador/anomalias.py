# ============================================================
# Generador - Inyeccion de anomalias con ruido (ISO-8 a ISO-11)
# ------------------------------------------------------------
# Por cada anomalia se inyectan:
#   - VIOLACIONES reales   -> llevan anomaly_code (van a expected_findings).
#   - RUIDO legitimo/ambiguo -> anomaly_code=None (NO va a expected_findings).
# El motor de deteccion (EPIC 3) debe encontrar TODAS las violaciones y
# NINGUN caso de ruido. Las reglas estan en config.REGLAS_DETECCION.
# ============================================================
import random
from datetime import timedelta

from . import config, util


# ------------------------------------------------------------------
# A1 - Acceso posterior a la baja (control A.5.18)
# ------------------------------------------------------------------
def inyectar_a1(rng: random.Random, usuarios):
    eventos = []
    bajas = [u for u in usuarios if u["status"] == "baja"]

    def _dia_habil_post_baja(u):
        candidatos = util.dias_habiles(
            u["termination_date"] + timedelta(days=1), config.PERIODO_FIN
        )
        return rng.choice(candidatos) if candidatos else None

    # VIOLACIONES: login con fecha > termination_date, desde IP humana.
    for u in rng.sample(bajas, min(config.N_VIOL_A1, len(bajas))):
        dia = _dia_habil_post_baja(u)
        if dia is None:
            continue
        eventos.append({
            "user_id": u["user_id"], "event_ts": util.hora_laboral(rng, dia),
            "event_type": "login", "resource": rng.choice(config.RECURSOS),
            "role_at_event": u["role"], "source_ip": util.ip_oficina(rng),
            "success": True, "anomaly_code": "A1",
            "note": "Login posterior a la baja desde IP de oficina",
        })

    # RUIDO 1: login EL MISMO DIA de la baja (ultimo dia valido, no es > fecha).
    for u in rng.sample(bajas, min(config.N_RUIDO_A1_ULTIMO_DIA, len(bajas))):
        eventos.append({
            "user_id": u["user_id"],
            "event_ts": util.hora_laboral(rng, u["termination_date"]),
            "event_type": "login", "resource": rng.choice(config.RECURSOS),
            "role_at_event": u["role"], "source_ip": util.ip_oficina(rng),
            "success": True, "anomaly_code": None,
        })

    # RUIDO 2: evento post-baja desde IP BATCH (proceso de servicio legitimo).
    for u in rng.sample(bajas, min(config.N_RUIDO_A1_BATCH, len(bajas))):
        dia = _dia_habil_post_baja(u)
        if dia is None:
            continue
        eventos.append({
            "user_id": u["user_id"], "event_ts": util.hora_laboral(rng, dia),
            "event_type": "login", "resource": "repositorio_docs",
            "role_at_event": u["role"], "source_ip": util.ip_batch(rng),
            "success": True, "anomaly_code": None,
        })

    return eventos


# ------------------------------------------------------------------
# A2 - Horario anomalo (control A.8.16)
# ------------------------------------------------------------------
def inyectar_a2(rng: random.Random, usuarios):
    eventos = []
    activos = [u for u in usuarios if u["status"] == "activo"]
    negocio = [u for u in activos if u["department"] not in config.DEPARTAMENTOS_24X7]
    it_users = [u for u in activos if u["department"] in config.DEPARTAMENTOS_24X7]

    habiles = util.dias_habiles(config.PERIODO_INICIO, config.PERIODO_FIN)
    finde = util.dias_fin_de_semana(config.PERIODO_INICIO, config.PERIODO_FIN)

    # VIOLACIONES: usuario de negocio fuera de horario o en fin de semana.
    for i, u in enumerate(rng.sample(negocio, min(config.N_VIOL_A2, len(negocio)))):
        if i % 2 == 0:  # madrugada/noche en dia habil
            ts = util.hora_anomala(rng, rng.choice(habiles))
            nota = "Login en horario nocturno (dia habil)"
        else:           # fin de semana
            ts = util.hora_laboral(rng, rng.choice(finde))
            nota = "Login en fin de semana (usuario de negocio)"
        eventos.append({
            "user_id": u["user_id"], "event_ts": ts, "event_type": "login",
            "resource": rng.choice(config.RECURSOS), "role_at_event": u["role"],
            "source_ip": util.ip_oficina(rng), "success": True,
            "anomaly_code": "A2", "note": nota,
        })

    # RUIDO 1: login dentro de la tolerancia de cierre (18:01-18:15).
    for u in rng.sample(negocio, min(config.N_RUIDO_A2_TOLERANCIA, len(negocio))):
        eventos.append({
            "user_id": u["user_id"],
            "event_ts": util.hora_en_tolerancia(rng, rng.choice(habiles)),
            "event_type": "login", "resource": rng.choice(config.RECURSOS),
            "role_at_event": u["role"], "source_ip": util.ip_oficina(rng),
            "success": True, "anomaly_code": None,
        })

    # RUIDO 2: usuario de IT (24x7 autorizado) accediendo fin de semana / noche.
    if it_users:
        for i in range(config.N_RUIDO_A2_IT_24X7):
            u = rng.choice(it_users)
            ts = (util.hora_laboral(rng, rng.choice(finde)) if i % 2 == 0
                  else util.hora_anomala(rng, rng.choice(habiles)))
            eventos.append({
                "user_id": u["user_id"], "event_ts": ts, "event_type": "login",
                "resource": "panel_admin", "role_at_event": u["role"],
                "source_ip": util.ip_oficina(rng), "success": True,
                "anomaly_code": None,
            })

    return eventos


# ------------------------------------------------------------------
# A3 - Escalamiento de privilegios (control A.8.2)
# ------------------------------------------------------------------
def inyectar_a3(rng: random.Random, usuarios):
    eventos = []
    activos = [u for u in usuarios if u["status"] == "activo"]
    elegibles = [u for u in activos if u["role"] != "admin"]
    habiles = util.dias_habiles(config.PERIODO_INICIO, config.PERIODO_FIN)

    def _base(u, role_destino, ticket_id, code, nota=None):
        return {
            "user_id": u["user_id"],
            "event_ts": util.hora_laboral(rng, rng.choice(habiles)),
            "event_type": "role_change", "resource": "panel_admin",
            "role_at_event": role_destino, "approval_ticket_id": ticket_id,
            "source_ip": util.ip_oficina(rng), "success": True,
            "anomaly_code": code, "note": nota,
        }

    # VIOLACIONES: role_change a admin SIN ticket.
    for u in rng.sample(elegibles, min(config.N_VIOL_A3, len(elegibles))):
        eventos.append(_base(u, "admin", None, "A3",
                             "Escalamiento a admin sin ticket de aprobacion"))

    # RUIDO 1: role_change a admin CON ticket valido (legitimo).
    for u in rng.sample(elegibles, min(config.N_RUIDO_A3_CON_TICKET, len(elegibles))):
        eventos.append(_base(u, "admin", util.ticket(rng), None))

    # RUIDO 2: role_change a supervisor SIN ticket (no es escalamiento a admin).
    for u in rng.sample(elegibles, min(config.N_RUIDO_A3_SUPERVISOR, len(elegibles))):
        eventos.append(_base(u, "supervisor", None, None))

    return eventos


# ------------------------------------------------------------------
# A4 - Segregacion de funciones / SoD (control A.5.3)
# ------------------------------------------------------------------
def inyectar_a4(rng: random.Random, usuarios, tx_seq):
    eventos = []
    activos = [u for u in usuarios if u["status"] == "activo"]
    habiles = util.dias_habiles(config.PERIODO_INICIO, config.PERIODO_FIN)

    def _par(creador, aprobador, recurso, dia, code_approve, nota=None):
        tx_id = next(tx_seq)
        ts_create = util.hora_laboral(rng, dia)
        ts_approve = ts_create.replace(
            hour=min(config.HORA_LABORAL_FIN - 1, ts_create.hour + 1)
        )
        eventos.append({
            "user_id": creador["user_id"], "event_ts": ts_create,
            "event_type": "create_record", "resource": recurso,
            "transaction_id": tx_id, "role_at_event": creador["role"],
            "source_ip": util.ip_oficina(rng), "success": True,
            "anomaly_code": None,
        })
        eventos.append({
            "user_id": aprobador["user_id"], "event_ts": ts_approve,
            "event_type": "approve_record", "resource": recurso,
            "transaction_id": tx_id, "role_at_event": aprobador["role"],
            "source_ip": util.ip_oficina(rng), "success": True,
            "anomaly_code": code_approve, "note": nota,
        })
        return tx_id

    # VIOLACIONES: el MISMO usuario crea y aprueba la MISMA transaccion.
    # El hallazgo se marca sobre el evento approve_record.
    candidatos = [u for u in activos if u["role"] in ("supervisor", "admin")] or activos
    for u in rng.sample(candidatos, min(config.N_VIOL_A4, len(candidatos))):
        _par(u, u, rng.choice(["erp_finanzas", "app_compras"]),
             rng.choice(habiles), "A4",
             "Mismo usuario crea y aprueba la transaccion (violacion SoD)")

    # RUIDO: el mismo usuario crea una tx y aprueba OTRA distinta (legitimo).
    otros = [u for u in activos if u["role"] in ("supervisor", "admin")]
    for _ in range(config.N_RUIDO_A4_DIST_TX):
        u = rng.choice(candidatos)
        o = rng.choice([x for x in otros if x["user_id"] != u["user_id"]])
        dia = rng.choice(habiles)
        # u crea tx1, o la aprueba   (creador != aprobador)
        _par(u, o, "erp_finanzas", dia, None)
        # o crea tx2, u la aprueba   -> u aprueba una tx distinta a la que creo
        _par(o, u, "app_compras", dia, None)

    return eventos
