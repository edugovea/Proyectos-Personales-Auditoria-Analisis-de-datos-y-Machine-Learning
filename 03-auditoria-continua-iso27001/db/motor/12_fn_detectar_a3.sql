-- ============================================================
-- Motor de deteccion - Function A3: escalamiento de privilegios (EPIC 3 / ISO-15)
-- Control ISO 27001:2022  A.8.2 (Derechos de acceso privilegiado) | Severidad: Critica
-- ------------------------------------------------------------
-- Regla (contrato en generador/config.py -> REGLAS_DETECCION['A3']):
--   evento role_change cuyo rol resultante (role_at_event) es 'admin'
--   y que NO tiene approval_ticket_id.
--   * role_change a admin CON ticket  -> legitimo (no se marca).
--   * role_change a supervisor         -> fuera de esta regla (no es admin).
--
-- Mismo patron que A1/A2: FUNCTION que devuelve los hallazgos nuevos,
-- idempotente via ON CONFLICT, sin leer expected_findings.
-- ============================================================
CREATE OR REPLACE FUNCTION detectar_a3()
RETURNS INTEGER AS $$
DECLARE
    n_nuevos INTEGER;
BEGIN
    WITH nuevos AS (
        INSERT INTO findings (event_id, anomaly_code, control_iso, severidad, evidencia)
        SELECT
            e.event_id,
            'A3',
            'A.8.2',
            'Critica',
            format(
                'Usuario %s cambio a rol admin SIN ticket de aprobacion el %s',
                u.username, e.event_ts
            )
        FROM access_events e
        JOIN users u ON u.user_id = e.user_id
        WHERE e.event_type = 'role_change'
          AND e.role_at_event = 'admin'
          AND e.approval_ticket_id IS NULL
        ON CONFLICT (event_id, anomaly_code) DO NOTHING
        RETURNING 1
    )
    SELECT count(*) INTO n_nuevos FROM nuevos;
    RETURN n_nuevos;
END;
$$ LANGUAGE plpgsql;
