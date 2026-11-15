-- 0.10.71: la comisión 2 del grupo A pasa a su propio grupo de cursada, para que vea sólo su galería y su votación.
-- Son las 36 cuentas sin grupo dadas de alta desde el 01/10/2026 (al 07/11: id 95 a 130, altas del 13/10 al 27/10).
-- Nada se borra: el grupo anterior queda en respaldo_grupos_0171 y sql/0171_comision2_reversa.sql lo restituye.
\set ON_ERROR_STOP on
BEGIN;
CREATE TABLE respaldo_grupos_0171 AS
  SELECT id, grupo, now() AS respaldado_en FROM usuarios
  WHERE rol <> 'admin' AND coalesce(trim(grupo), '') = '' AND creado_en >= '2026-10-01' AND id BETWEEN 95 AND 130;
DO $$
BEGIN
  IF (SELECT count(*) FROM respaldo_grupos_0171) <> 36 THEN
    RAISE EXCEPTION 'Se esperaban 36 cuentas y hay %', (SELECT count(*) FROM respaldo_grupos_0171);
  END IF;
END $$;
UPDATE usuarios SET grupo = 'Grupo A · comisión 2' WHERE id IN (SELECT id FROM respaldo_grupos_0171);
SELECT count(*) AS en_comision_2 FROM usuarios WHERE grupo = 'Grupo A · comisión 2';
COMMIT;
