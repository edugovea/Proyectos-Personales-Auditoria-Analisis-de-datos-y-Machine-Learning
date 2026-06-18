-- ============================================================
-- Auditoria Continua ISO 27001 - Tabla findings + inmutabilidad (EPIC 3 / ISO-12)
-- Motor: PostgreSQL
-- ------------------------------------------------------------
-- findings es la SALIDA del motor de deteccion: un registro por hallazgo,
-- con trazabilidad al evento que lo origino, control ISO, severidad y evidencia.
-- Como es un registro de auditoria, se protege su INMUTABILIDAD:
--   * no se puede ELIMINAR un hallazgo,
--   * no se puede MODIFICAR la evidencia (solo avanza su 'estado' de tratamiento),
--   * no se puede TRUNCATE la tabla.
-- ============================================================

-- ------------------------------------------------------------
-- 1) Tabla findings
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS findings (
    finding_id   BIGSERIAL PRIMARY KEY,
    event_id     BIGINT      NOT NULL REFERENCES access_events(event_id),
    anomaly_code CHAR(2)     NOT NULL
                   CHECK (anomaly_code IN ('A1','A2','A3','A4')),
    control_iso  VARCHAR(10) NOT NULL,           -- ej: A.5.18 (snapshot al detectar)
    severidad    VARCHAR(10) NOT NULL
                   CHECK (severidad IN ('Baja','Media','Alta','Critica')),
    evidencia    TEXT        NOT NULL,           -- por que se marco: dato concreto del evento
    estado       VARCHAR(15) NOT NULL DEFAULT 'abierto'
                   CHECK (estado IN ('abierto','en_revision','cerrado','falso_positivo')),
    detected_at  TIMESTAMP   NOT NULL DEFAULT now(),
    -- Idempotencia: un mismo evento no se marca dos veces con el mismo codigo.
    -- Permite que el motor corra muchas veces con INSERT ... ON CONFLICT DO NOTHING.
    CONSTRAINT uq_finding UNIQUE (event_id, anomaly_code)
);

CREATE INDEX IF NOT EXISTS idx_findings_anomaly  ON findings(anomaly_code);
CREATE INDEX IF NOT EXISTS idx_findings_severidad ON findings(severidad);
CREATE INDEX IF NOT EXISTS idx_findings_estado    ON findings(estado);

-- ------------------------------------------------------------
-- 2) Trigger de inmutabilidad a nivel FILA (UPDATE / DELETE)
--    - DELETE: prohibido siempre.
--    - UPDATE: solo se permite cambiar 'estado' (flujo de tratamiento del hallazgo).
--      Cualquier cambio en columnas forenses se rechaza.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_findings_inmutable()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        RAISE EXCEPTION
            'Hallazgo inmutable: no se puede eliminar (finding_id=%).', OLD.finding_id;
    END IF;

    -- TG_OP = 'UPDATE': comparamos columnas forenses (IS DISTINCT FROM cubre NULLs)
    IF NEW.finding_id   IS DISTINCT FROM OLD.finding_id
       OR NEW.event_id     IS DISTINCT FROM OLD.event_id
       OR NEW.anomaly_code IS DISTINCT FROM OLD.anomaly_code
       OR NEW.control_iso  IS DISTINCT FROM OLD.control_iso
       OR NEW.severidad    IS DISTINCT FROM OLD.severidad
       OR NEW.evidencia    IS DISTINCT FROM OLD.evidencia
       OR NEW.detected_at  IS DISTINCT FROM OLD.detected_at THEN
        RAISE EXCEPTION
            'Hallazgo inmutable: solo se permite modificar la columna estado (finding_id=%).',
            OLD.finding_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS findings_inmutable ON findings;
CREATE TRIGGER findings_inmutable
    BEFORE UPDATE OR DELETE ON findings
    FOR EACH ROW
    EXECUTE FUNCTION trg_findings_inmutable();

-- ------------------------------------------------------------
-- 3) Trigger de inmutabilidad a nivel SENTENCIA (TRUNCATE)
--    Los triggers de fila NO se disparan con TRUNCATE; hace falta uno aparte.
-- ------------------------------------------------------------
CREATE OR REPLACE FUNCTION trg_findings_no_truncate()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'Hallazgo inmutable: la tabla findings no admite TRUNCATE.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS findings_no_truncate ON findings;
CREATE TRIGGER findings_no_truncate
    BEFORE TRUNCATE ON findings
    FOR EACH STATEMENT
    EXECUTE FUNCTION trg_findings_no_truncate();
