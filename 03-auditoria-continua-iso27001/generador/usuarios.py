# ============================================================
# Generador - Usuarios (ISO-6)
# ------------------------------------------------------------
# Construye el directorio de personas: roles, departamentos y altas/bajas
# coherentes con el CHECK chk_baja_coherente del esquema.
# ============================================================
import random
import unicodedata
from datetime import timedelta

from faker import Faker

from . import config


def _slug(texto):
    """Normaliza a un username ascii sin espacios ni acentos."""
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return s.lower().replace(" ", ".").replace("..", ".")


def generar_usuarios(rng: random.Random, fake: Faker):
    """Devuelve una lista de dicts de usuarios lista para insertar.

    Reglas de coherencia:
    - role en {empleado, supervisor, admin} segun la distribucion de config.
    - hire_date anterior al periodo de simulacion (gente ya contratada).
    - N_BAJAS usuarios quedan en estado 'baja' con termination_date DENTRO
      del periodo, para que A1 (acceso post-baja) tenga sujetos validos.
    - El resto queda 'activo' con termination_date NULL.
    """
    # 1) Asignacion de roles segun la distribucion configurada
    roles = (
        ["admin"] * config.N_ADMINS
        + ["supervisor"] * config.N_SUPERVISORES
        + ["empleado"] * config.N_EMPLEADOS
    )
    rng.shuffle(roles)

    usuarios = []
    usernames_vistos = set()
    for i, role in enumerate(roles):
        nombre = fake.name()
        base = _slug(nombre)
        username = base
        # Evita colisiones de username (UNIQUE en el esquema)
        n = 1
        while username in usernames_vistos:
            n += 1
            username = f"{base}{n}"
        usernames_vistos.add(username)

        # Alta entre 4 y 1 anios antes del inicio del periodo
        dias_antes = rng.randint(365, 365 * 4)
        hire_date = config.PERIODO_INICIO - timedelta(days=dias_antes)

        usuarios.append({
            "username": username[:50],
            "full_name": nombre,
            "department": rng.choice(config.DEPARTAMENTOS),
            "role": role,
            "status": "activo",
            "hire_date": hire_date,
            "termination_date": None,
        })

    # 2) Marca N_BAJAS usuarios como dados de baja DENTRO del periodo.
    #    Se eligen entre empleados/supervisores (no admins, mas realista).
    candidatos = [u for u in usuarios if u["role"] != "admin"]
    bajas = rng.sample(candidatos, config.N_BAJAS)
    rango_dias = (config.PERIODO_FIN - config.PERIODO_INICIO).days
    for u in bajas:
        # baja en la primera mitad del periodo -> deja margen para eventos post-baja
        offset = rng.randint(5, rango_dias // 2)
        u["status"] = "baja"
        u["termination_date"] = config.PERIODO_INICIO + timedelta(days=offset)

    return usuarios
