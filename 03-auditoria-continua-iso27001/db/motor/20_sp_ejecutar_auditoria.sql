-- ============================================================
-- Motor de deteccion - Orquestadora (EPIC 3 / ISO-17)
-- ------------------------------------------------------------
-- Corre las 4 funciones de deteccion en orden y devuelve, por anomalia,
-- cuantos hallazgos NUEVOS sumo cada una en esta corrida.
--
-- Se implementa como FUNCTION que devuelve una tabla (en vez de un
-- PROCEDURE mudo) para que la corrida deje un reporte legible:
--     SELECT * FROM ejecutar_auditoria();
--
-- Es idempotente de punta a punta: cada detector usa ON CONFLICT, asi que
-- una segunda corrida devuelve 0 en todas las filas (no hay nada nuevo).
-- ============================================================
CREATE OR REPLACE FUNCTION ejecutar_auditoria()
RETURNS TABLE(anomalia TEXT, control_iso TEXT, hallazgos_nuevos INTEGER) AS $$
BEGIN
    RETURN QUERY SELECT 'A1'::text, 'A.5.18'::text, detectar_a1();
    RETURN QUERY SELECT 'A2'::text, 'A.8.16'::text, detectar_a2();
    RETURN QUERY SELECT 'A3'::text, 'A.8.2'::text,  detectar_a3();
    RETURN QUERY SELECT 'A4'::text, 'A.5.3'::text,  detectar_a4();
END;
$$ LANGUAGE plpgsql;
