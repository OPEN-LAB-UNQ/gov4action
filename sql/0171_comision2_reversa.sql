-- Reversa de sql/0171_comision2.sql: devuelve a cada cuenta el grupo que tenía antes de la 0.10.71, sólo si sigue en
-- «Grupo A · comisión 2».
\set ON_ERROR_STOP on
BEGIN;
UPDATE usuarios u SET grupo = r.grupo FROM respaldo_grupos_0171 r
  WHERE u.id = r.id AND u.grupo = 'Grupo A · comisión 2';
COMMIT;
