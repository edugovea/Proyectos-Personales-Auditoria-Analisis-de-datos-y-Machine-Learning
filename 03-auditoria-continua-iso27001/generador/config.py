# ============================================================
# Generador de logs sinteticos - Configuracion central (ISO-5/ISO-6..11)
# ------------------------------------------------------------
# Toda constante que afecte la reproducibilidad o el diseno de
# las anomalias vive aca. Cambiar SEED cambia el dataset entero.
# ============================================================
from datetime import date

# --- Reproducibilidad -------------------------------------------------------
SEED = 42  # semilla unica para random y Faker -> dataset estable para los tests

# --- Ventana temporal de simulacion ----------------------------------------
# Periodo FIJO (no usar "hoy") para que el dataset sea identico en cada corrida.
PERIODO_INICIO = date(2025, 1, 1)
PERIODO_FIN    = date(2025, 3, 31)   # 90 dias, ~64 dias habiles

# --- Horario laboral (base de la regla A2) ----------------------------------
HORA_LABORAL_INICIO   = 8    # 08:00 inclusive
HORA_LABORAL_FIN      = 18   # 18:00
TOLERANCIA_CIERRE_MIN = 15   # gracia hasta 18:15 -> no es hallazgo (caso ambiguo)

# --- Poblacion de usuarios --------------------------------------------------
N_USUARIOS = 60
# Distribucion de roles (debe sumar N_USUARIOS)
N_ADMINS       = 4
N_SUPERVISORES = 12
N_EMPLEADOS    = N_USUARIOS - N_ADMINS - N_SUPERVISORES  # 44
N_BAJAS        = 6   # usuarios dados de baja (subconjunto, con termination_date)

DEPARTAMENTOS = ["Finanzas", "RRHH", "IT", "Operaciones", "Compras", "Legal"]
# Deptos con acceso autorizado 24x7 -> EXCLUIDOS de la regla de horario (A2).
# Mecanismo explicito porque el esquema no tiene un flag "de guardia".
DEPARTAMENTOS_24X7 = {"IT"}

RECURSOS = [
    "erp_finanzas", "sistema_rrhh", "repositorio_docs",
    "panel_admin", "app_compras", "portal_legal",
]

# --- Redes IP ---------------------------------------------------------------
# Las IP humanas salen de rangos de oficina; los procesos batch de un rango
# de servicio dedicado. La regla A1 excluye el rango batch.
IP_OFICINA_PREFIJOS = ["192.168.10.", "192.168.20.", "200.50.30."]
IP_BATCH_PREFIJO    = "10.10.0."          # rango de procesos batch/servicio
IP_BATCH_CIDR       = "10.10.0.0/24"      # documentado para la regla del motor

# --- Volumen de eventos normales --------------------------------------------
# Probabilidad de que un usuario activo tenga sesion en un dia habil dado.
PROB_SESION_DIA_HABIL = 0.55
# Transacciones legitimas (create+approve por usuarios distintos) a generar.
N_TRANSACCIONES_NORMALES = 120
# Cambios de rol legitimos (con ticket de aprobacion).
N_ROLE_CHANGES_NORMALES = 8

# --- Conteos de ANOMALIAS (violaciones reales -> expected_findings) ----------
N_VIOL_A1 = 4   # acceso post-baja
N_VIOL_A2 = 5   # horario anomalo (usuario de negocio)
N_VIOL_A3 = 3   # escalamiento a admin sin ticket
N_VIOL_A4 = 4   # mismo usuario crea y aprueba la misma transaccion

# --- Conteos de RUIDO (casos legitimos/ambiguos -> NO van a expected) --------
N_RUIDO_A1_ULTIMO_DIA = 2   # login el mismo dia de la baja (ultimo dia valido)
N_RUIDO_A1_BATCH      = 3   # evento post-baja desde IP batch (proceso legitimo)
N_RUIDO_A2_TOLERANCIA = 3   # login 18:01-18:15 (dentro de la gracia)
N_RUIDO_A2_IT_24X7    = 3   # usuario IT accediendo fin de semana / de noche
N_RUIDO_A3_CON_TICKET = 3   # role_change a admin CON ticket valido
N_RUIDO_A3_SUPERVISOR = 2   # role_change a supervisor sin ticket (no es escalamiento a admin)
N_RUIDO_A4_DIST_TX    = 3   # mismo usuario crea y aprueba TRANSACCIONES DISTINTAS

# ============================================================
# CONTRATO DE DETECCION
# ------------------------------------------------------------
# Definicion canonica de cada regla. El generador inyecta los datos para que
# se cumplan exactamente estas reglas; el motor de deteccion (EPIC 3) las
# implementa en SQL. Mantener ambos lados sincronizados con este diccionario.
# ============================================================
REGLAS_DETECCION = {
    "A1": {
        "control_iso": "A.5.18",
        "severidad": "Alta",
        "descripcion": (
            "Acceso posterior a la baja: evento de login exitoso cuya FECHA "
            "(event_ts::date) es estrictamente posterior a users.termination_date. "
            "Se EXCLUYE el rango de IP batch (10.10.0.0/24): esos accesos son de "
            "procesos de servicio conocidos, no de la persona dada de baja."
        ),
    },
    "A2": {
        "control_iso": "A.8.16",
        "severidad": "Media",
        "descripcion": (
            "Horario anomalo: login exitoso fuera de la ventana laboral "
            "(08:00 a 18:15, con 15 min de tolerancia) o en fin de semana. "
            "Se EXCLUYE el departamento IT, con acceso autorizado 24x7."
        ),
    },
    "A3": {
        "control_iso": "A.8.2",
        "severidad": "Critica",
        "descripcion": (
            "Escalamiento de privilegios: evento role_change cuyo rol resultante "
            "(role_at_event) es 'admin' y NO tiene approval_ticket_id. "
            "Los cambios a admin CON ticket son legitimos; los cambios a "
            "supervisor quedan fuera de esta regla."
        ),
    },
    "A4": {
        "control_iso": "A.5.3",
        "severidad": "Alta",
        "descripcion": (
            "Segregacion de funciones (SoD): un mismo user_id registra "
            "create_record y approve_record para el MISMO transaction_id. "
            "El hallazgo se marca sobre el evento approve_record. Que un usuario "
            "cree y apruebe TRANSACCIONES DISTINTAS es legitimo."
        ),
    },
}
