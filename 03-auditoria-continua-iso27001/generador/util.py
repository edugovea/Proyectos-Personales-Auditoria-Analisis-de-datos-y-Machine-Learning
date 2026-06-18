# ============================================================
# Generador - Utilidades compartidas (tiempo e IPs)
# ------------------------------------------------------------
# Helpers usados por la generacion de eventos normales y la inyeccion de
# anomalias. Centralizados para que "que es horario laboral" y "que es una
# IP de oficina" tengan UNA sola definicion.
# ============================================================
import random
from datetime import datetime, timedelta, time

from . import config


def dias_habiles(inicio, fin):
    """Lista de dates lunes-viernes en [inicio, fin]."""
    dias = []
    d = inicio
    while d <= fin:
        if d.weekday() < 5:  # 0=lunes .. 4=viernes
            dias.append(d)
        d += timedelta(days=1)
    return dias


def dias_fin_de_semana(inicio, fin):
    """Lista de dates sabado/domingo en [inicio, fin]."""
    dias = []
    d = inicio
    while d <= fin:
        if d.weekday() >= 5:
            dias.append(d)
        d += timedelta(days=1)
    return dias


def hora_laboral(rng: random.Random, dia):
    """Timestamp en horario laboral pleno (08:00-17:59) sobre `dia`.

    Se mantiene varios minutos por debajo del cierre para que NINGUN evento
    normal caiga en la zona de tolerancia ni la cruce (evita falsos positivos).
    """
    hora = rng.randint(config.HORA_LABORAL_INICIO, config.HORA_LABORAL_FIN - 1)
    minuto = rng.randint(0, 59)
    segundo = rng.randint(0, 59)
    return datetime.combine(dia, time(hora, minuto, segundo))


def hora_en_tolerancia(rng: random.Random, dia):
    """Timestamp dentro de la gracia de cierre (18:01-18:14) -> NO es hallazgo.

    Se mantiene estrictamente por debajo de 18:15:00, que es el borde exacto
    de la regla A2, para que el ruido nunca cruce el limite.
    """
    minuto = rng.randint(1, config.TOLERANCIA_CIERRE_MIN - 1)
    segundo = rng.randint(0, 59)
    return datetime.combine(dia, time(config.HORA_LABORAL_FIN, minuto, segundo))


def hora_anomala(rng: random.Random, dia):
    """Timestamp claramente fuera de horario (madrugada o noche)."""
    franjas = [(0, 5), (20, 23)]  # 00:00-05:59 o 20:00-23:59
    desde, hasta = rng.choice(franjas)
    hora = rng.randint(desde, hasta)
    minuto = rng.randint(0, 59)
    segundo = rng.randint(0, 59)
    return datetime.combine(dia, time(hora, minuto, segundo))


def ip_oficina(rng: random.Random):
    """IP humana desde un rango de oficina."""
    return rng.choice(config.IP_OFICINA_PREFIJOS) + str(rng.randint(2, 254))


def ip_batch(rng: random.Random):
    """IP de proceso batch/servicio (rango excluido por la regla A1)."""
    return config.IP_BATCH_PREFIJO + str(rng.randint(2, 254))


def ticket(rng: random.Random):
    """Identificador de ticket de aprobacion, formato TCK-NNNNN."""
    return f"TCK-{rng.randint(10000, 99999)}"
