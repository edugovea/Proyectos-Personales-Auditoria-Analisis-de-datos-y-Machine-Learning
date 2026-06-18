-- ============================================================
-- Motor de deteccion - Function A2: horario anomalo (EPIC 3 / ISO-14)
-- Control ISO 27001:2022  A.8.16 (Actividades de monitoreo) | Severidad: Media
-- ------------------------------------------------------------
-- Regla (contrato en generador/config.py -> REGLAS_DETECCION['A2']):
--   login exitoso FUERA de la ventana laboral 08:00-18:15 (15 min de
--   tolerancia al cierre) O en fin de semana, EXCLUYENDO el depto IT (24x7).
--
-- Notas de diseno:
--   * La tolerancia se modela como un borde duro a las 18:15:00: un login
--     a las 18:14 es legitimo; a las 18:15 o mas, es hallazgo.
--   * IT queda excluido porque tiene acceso autorizado 24x7 (decision de
--     auditoria); cualquier otro departamento si esta sujeto al horario.
--   * Mismo patron que A1: FUNCTION que devuelve los hallazgos nuevos,
--     idempotente via ON CONFLICT, sin leer expected_findings.
-- ============================================================
CREATE OR REPLACE FUNCTION detectar_a2()
RETURNS INTEGER AS $$
DECLARE
    n_nuevos INTEGER;
BEGIN
    WITH nuevos AS (
        INSERT INTO findings (event_id, anomaly_code, control_iso, severidad, evidencia)
        SELECT
            e.event_id,
            'A2',
            'A.8.16',
            'Media',
            format(
                'Usuario %s (%s) hizo login fuera de horario el %s (%s)',
                u.username, u.department, e.event_ts,
                CASE WHEN EXTRACT(ISODOW FROM e.event_ts) >= 6
                     THEN 'fin de semana' ELSE 'horario nocturno' END
            )
        FROM access_events e
        JOIN users u ON u.user_id = e.user_id
        WHERE e.event_type = 'login'
          AND e.success
          AND u.department <> 'IT'                        -- IT: acceso 24x7 autorizado
          AND (
                EXTRACT(ISODOW FROM e.event_ts) >= 6      -- sabado (6) o domingo (7)
             OR e.event_ts::time <  TIME '08:00'          -- antes de la apertura
             OR e.event_ts::time >= TIME '18:15'          -- pasada la tolerancia de cierre
          )
        ON CONFLICT (event_id, anomaly_code) DO NOTHING
        RETURNING 1
    )
    SELECT count(*) INTO n_nuevos FROM nuevos;
    RETURN n_nuevos;
END;
$$ LANGUAGE plpgsql;
