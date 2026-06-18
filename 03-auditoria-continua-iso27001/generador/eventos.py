# ============================================================
# Generador - Eventos de acceso normales (ISO-7)
# ------------------------------------------------------------
# Trafico legitimo: sesiones en dias habiles y horario laboral, y
# transacciones create+approve hechas por usuarios DISTINTOS.
# Disenado para NO disparar ninguna de las 4 reglas por accidente.
# ============================================================
import random

from . import config, util


def _activos(usuarios):
    return [u for u in usuarios if u["status"] == "activo"]


def generar_eventos_normales(rng: random.Random, usuarios, tx_seq):
    """Genera el trafico de fondo. Ningun evento lleva anomaly_code.

    `tx_seq` es un iterador (itertools.count) que entrega transaction_id unicos,
    compartido con la inyeccion de anomalias para que no haya colisiones.
    """
    eventos = []
    activos = _activos(usuarios)
    dias = util.dias_habiles(config.PERIODO_INICIO, config.PERIODO_FIN)

    # 1) Sesiones diarias: login + logout en horario laboral.
    for u in activos:
        for dia in dias:
            if rng.random() > config.PROB_SESION_DIA_HABIL:
                continue
            ts_login = util.hora_laboral(rng, dia)
            ip = util.ip_oficina(rng)
            eventos.append({
                "user_id": u["user_id"], "event_ts": ts_login,
                "event_type": "login", "resource": rng.choice(config.RECURSOS),
                "role_at_event": u["role"], "source_ip": ip,
                "success": True, "anomaly_code": None,
            })
            # logout algunas horas despues, sin pasar la medianoche
            ts_logout = ts_login.replace(
                hour=min(config.HORA_LABORAL_FIN - 1, ts_login.hour + rng.randint(1, 4))
            )
            eventos.append({
                "user_id": u["user_id"], "event_ts": ts_logout,
                "event_type": "logout", "resource": "sesion",
                "role_at_event": u["role"], "source_ip": ip,
                "success": True, "anomaly_code": None,
            })

    # 2) Transacciones legitimas: create + approve por usuarios DISTINTOS.
    #    Creador: empleado; Aprobador: supervisor/admin (segregacion correcta).
    empleados = [u for u in activos if u["role"] == "empleado"]
    aprobadores = [u for u in activos if u["role"] in ("supervisor", "admin")]
    for _ in range(config.N_TRANSACCIONES_NORMALES):
        creador = rng.choice(empleados)
        aprobador = rng.choice(aprobadores)
        tx_id = next(tx_seq)
        dia = rng.choice(dias)
        recurso = rng.choice(["erp_finanzas", "app_compras", "sistema_rrhh"])
        ts_create = util.hora_laboral(rng, dia)
        eventos.append({
            "user_id": creador["user_id"], "event_ts": ts_create,
            "event_type": "create_record", "resource": recurso,
            "transaction_id": tx_id, "role_at_event": creador["role"],
            "source_ip": util.ip_oficina(rng), "success": True,
            "anomaly_code": None,
        })
        # aprobacion el mismo dia, un poco mas tarde
        ts_approve = ts_create.replace(
            hour=min(config.HORA_LABORAL_FIN - 1, ts_create.hour + 1)
        )
        eventos.append({
            "user_id": aprobador["user_id"], "event_ts": ts_approve,
            "event_type": "approve_record", "resource": recurso,
            "transaction_id": tx_id, "role_at_event": aprobador["role"],
            "source_ip": util.ip_oficina(rng), "success": True,
            "anomaly_code": None,
        })

    # 3) Cambios de rol legitimos: a 'supervisor', SIEMPRE con ticket valido.
    #    (A3 solo marca escalamientos a admin sin ticket -> esto no aplica.)
    for _ in range(config.N_ROLE_CHANGES_NORMALES):
        u = rng.choice(empleados)
        dia = rng.choice(dias)
        eventos.append({
            "user_id": u["user_id"], "event_ts": util.hora_laboral(rng, dia),
            "event_type": "role_change", "resource": "panel_admin",
            "role_at_event": "supervisor", "approval_ticket_id": util.ticket(rng),
            "source_ip": util.ip_oficina(rng), "success": True,
            "anomaly_code": None,
        })

    return eventos
