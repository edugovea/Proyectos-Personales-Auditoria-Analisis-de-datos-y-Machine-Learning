-- ============================================================
-- Motor de deteccion - Function A1: acceso post-baja (EPIC 3 / ISO-13)
-- Control ISO 27001:2022  A.5.18 (Derechos de acceso) | Severidad: Alta
-- ------------------------------------------------------------
-- Regla (contrato en generador/config.py -> REGLAS_DETECCION['A1']):
--   login exitoso cuya FECHA es posterior a users.termination_date,
--   EXCLUYENDO el rango de IP batch 10.10.0.0/24 (procesos de servicio).
--
-- Detalles de diseno:
--   * Es una FUNCTION que devuelve cuantos hallazgos NUEVOS inserto (INTEGER),
--     para poder testearla y encadenarla en la orquestadora (ISO-17).
--   * NO lee expected_findings: detecta a ciegas; la validacion es aparte.
--   * Idempotente: ON CONFLICT (event_id, anomaly_code) DO NOTHING permite
--     correrla muchas veces sin duplicar.
--   * La comparacion es por FECHA (event_ts::date > termination_date): un login
--     el mismo dia de la baja es el ultimo dia valido, NO un hallazgo.
--   * La exclusion de IP usa el operador de red <<  ("contenida en la subred"),
--     mas robusto que comparar texto y aprovechando el tipo INET.
-- ============================================================
CREATE OR REPLACE FUNCTION detectar_a1()
RETURNS INTEGER AS $$
DECLARE
    n_nuevos INTEGER;
BEGIN
    WITH nuevos AS (
        INSERT INTO findings (event_id, anomaly_code, control_iso, severidad, evidencia)
        SELECT
            e.event_id,
            'A1',
            'A.5.18',
            'Alta',
            format(
                'Usuario %s (baja %s) hizo login el %s desde %s',
                u.username, u.termination_date, e.event_ts, host(e.source_ip)
            )
        FROM access_events e
        JOIN users u ON u.user_id = e.user_id
        WHERE e.event_type = 'login'
          AND e.success
          AND u.status = 'baja'
          AND e.event_ts::date > u.termination_date
          -- excluye el rango batch; COALESCE: si la IP es NULL, NO la excluye
          AND NOT COALESCE(e.source_ip << inet '10.10.0.0/24', false)
        ON CONFLICT (event_id, anomaly_code) DO NOTHING
        RETURNING 1
    )
    SELECT count(*) INTO n_nuevos FROM nuevos;
    RETURN n_nuevos;
END;
$$ LANGUAGE plpgsql;
