-- ============================================================
-- Motor de deteccion - Function A4: segregacion de funciones / SoD (EPIC 3 / ISO-16)
-- Control ISO 27001:2022  A.5.3 (Segregacion de funciones) | Severidad: Alta
-- ------------------------------------------------------------
-- Regla (contrato en generador/config.py -> REGLAS_DETECCION['A4']):
--   un mismo user_id registra create_record Y approve_record para el MISMO
--   transaction_id. El hallazgo se marca sobre el evento approve_record
--   (el momento en que la persona aprueba lo que ella misma creo).
--   * Crear y aprobar TRANSACCIONES DISTINTAS es legitimo (no se marca).
--   * Creador y aprobador distintos en la misma tx es lo normal (no se marca).
--
-- Mismo patron que el resto: FUNCTION idempotente que devuelve los nuevos.
-- ============================================================
CREATE OR REPLACE FUNCTION detectar_a4()
RETURNS INTEGER AS $$
DECLARE
    n_nuevos INTEGER;
BEGIN
    WITH violaciones AS (
        -- approve_record cuya misma transaccion fue creada por el MISMO usuario
        SELECT ap.event_id, ap.user_id, ap.transaction_id, ap.event_ts
        FROM access_events ap
        WHERE ap.event_type = 'approve_record'
          AND EXISTS (
              SELECT 1
              FROM access_events cr
              WHERE cr.transaction_id = ap.transaction_id
                AND cr.event_type = 'create_record'
                AND cr.user_id = ap.user_id
          )
    ),
    nuevos AS (
        INSERT INTO findings (event_id, anomaly_code, control_iso, severidad, evidencia)
        SELECT
            v.event_id,
            'A4',
            'A.5.3',
            'Alta',
            format(
                'Usuario %s creo Y aprobo la transaccion %s (violacion de segregacion de funciones) el %s',
                u.username, v.transaction_id, v.event_ts
            )
        FROM violaciones v
        JOIN users u ON u.user_id = v.user_id
        ON CONFLICT (event_id, anomaly_code) DO NOTHING
        RETURNING 1
    )
    SELECT count(*) INTO n_nuevos FROM nuevos;
    RETURN n_nuevos;
END;
$$ LANGUAGE plpgsql;
