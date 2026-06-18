-- ============================================================
-- Motor de deteccion - Vistas para Power BI (EPIC 3 / ISO-18)
-- ------------------------------------------------------------
-- Una VISTA (view) es una consulta SQL guardada con nombre: se comporta como
-- una tabla virtual, NO duplica datos. Power BI se conecta a estas vistas y
-- lee la informacion ya preparada, sin tener que armar joins por su cuenta.
--
--   * vw_resumen_ejecutivo : KPIs agregados (para el dashboard de gerencia).
--   * vw_detalle_hallazgos : un renglon por hallazgo, con el contexto de
--                            usuario y evento (para el dashboard operativo).
-- ============================================================

-- ------------------------------------------------------------
-- 1) Vista EJECUTIVA: resumen para KPIs
--    Una fila por anomalia, con el desglose por estado de tratamiento.
--    count(*) FILTER (WHERE ...) cuenta condicionalmente en una sola pasada.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_resumen_ejecutivo AS
SELECT
    f.anomaly_code,
    f.control_iso,
    f.severidad,
    count(*)                                            AS total_hallazgos,
    count(*) FILTER (WHERE f.estado = 'abierto')        AS abiertos,
    count(*) FILTER (WHERE f.estado = 'en_revision')    AS en_revision,
    count(*) FILTER (WHERE f.estado = 'cerrado')        AS cerrados,
    count(*) FILTER (WHERE f.estado = 'falso_positivo') AS falsos_positivos
FROM findings f
GROUP BY f.anomaly_code, f.control_iso, f.severidad
ORDER BY f.anomaly_code;

-- ------------------------------------------------------------
-- 2) Vista OPERATIVA: detalle de cada hallazgo
--    Cruza findings con el evento que lo origino y con el usuario, para que
--    el analista vea en una sola fila QUE paso, QUIEN y CUANDO.
-- ------------------------------------------------------------
CREATE OR REPLACE VIEW vw_detalle_hallazgos AS
SELECT
    f.finding_id,
    f.anomaly_code,
    f.control_iso,
    f.severidad,
    f.estado,
    f.detected_at,
    u.username,
    u.full_name,
    u.department,
    e.event_ts,
    e.event_type,
    e.resource,
    e.source_ip,
    f.evidencia
FROM findings f
JOIN access_events e ON e.event_id = f.event_id
JOIN users u         ON u.user_id  = e.user_id
ORDER BY
    CASE f.severidad
        WHEN 'Critica' THEN 1
        WHEN 'Alta'    THEN 2
        WHEN 'Media'   THEN 3
        ELSE 4
    END,
    f.detected_at DESC;
