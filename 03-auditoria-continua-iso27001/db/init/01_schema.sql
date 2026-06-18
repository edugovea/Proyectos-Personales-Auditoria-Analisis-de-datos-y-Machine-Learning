-- ============================================================
-- Auditoria Continua ISO 27001 - Esquema base (EPIC 1 / ISO-3)
-- Motor: PostgreSQL 16
-- Crea las 3 tablas del generador de logs sinteticos.
-- La tabla findings (motor de deteccion) se agrega en EPIC 3 / ISO-12.
-- ============================================================

-- ------------------------------------------------------------
-- 1) users : directorio de personas (dimension)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    user_id          SERIAL PRIMARY KEY,
    username         VARCHAR(50)  NOT NULL UNIQUE,
    full_name        VARCHAR(120) NOT NULL,
    department       VARCHAR(60)  NOT NULL,
    role             VARCHAR(20)  NOT NULL
                       CHECK (role IN ('empleado', 'supervisor', 'admin')),
    status           VARCHAR(10)  NOT NULL DEFAULT 'activo'
                       CHECK (status IN ('activo', 'baja')),
    hire_date        DATE         NOT NULL,
    termination_date DATE,
    created_at       TIMESTAMP    NOT NULL DEFAULT now(),
    -- Coherencia: si esta de baja debe tener fecha de baja, y viceversa
    CONSTRAINT chk_baja_coherente CHECK (
        (status = 'baja'   AND termination_date IS NOT NULL) OR
        (status = 'activo' AND termination_date IS NULL)
    )
);

-- ------------------------------------------------------------
-- 2) access_events : hechos de acceso (tabla grande)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS access_events (
    event_id           BIGSERIAL PRIMARY KEY,
    user_id            INT NOT NULL REFERENCES users(user_id),
    event_ts           TIMESTAMP   NOT NULL,
    event_type         VARCHAR(30) NOT NULL
                         CHECK (event_type IN
                           ('login','logout','role_change','create_record','approve_record')),
    resource           VARCHAR(60) NOT NULL,
    transaction_id     BIGINT,                 -- agrupa create/approve de una operacion (A4)
    role_at_event      VARCHAR(20) NOT NULL
                         CHECK (role_at_event IN ('empleado','supervisor','admin')),
    approval_ticket_id VARCHAR(20),            -- ticket de aprobacion (A3); NULL = sin aprobacion
    source_ip          INET,
    success            BOOLEAN     NOT NULL DEFAULT true
);

-- Indices para acelerar las detecciones del motor (EPIC 3)
CREATE INDEX IF NOT EXISTS idx_events_user        ON access_events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_ts          ON access_events(event_ts);
CREATE INDEX IF NOT EXISTS idx_events_type        ON access_events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_transaction ON access_events(transaction_id);

-- ------------------------------------------------------------
-- 3) expected_findings : ground truth (verdad conocida)
--    El generador registra aca cada anomalia que inyecta a proposito.
--    El motor de deteccion NO lee esta tabla; sirve para validar (ISO-29).
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS expected_findings (
    id           SERIAL PRIMARY KEY,
    event_id     BIGINT NOT NULL REFERENCES access_events(event_id),
    anomaly_code CHAR(2) NOT NULL
                   CHECK (anomaly_code IN ('A1','A2','A3','A4')),
    note         TEXT
);

CREATE INDEX IF NOT EXISTS idx_expected_anomaly ON expected_findings(anomaly_code);
