"""0.10.71: «Quién ve qué» y la presentación nombran los conteos y las lecturas automáticas de la galería; la
comisión 2 tiene su grupo de cursada."""
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent


def _texto(*partes):
    return (RAIZ.joinpath(*partes)).read_text(encoding="utf-8")


def test_quien_ve_que_nombra_los_conteos_y_las_lecturas_automaticas():
    t = _texto("static", "index.html")
    assert "que es tu comisión" in t and "estado y fecha de la última actividad" in t
    assert "cuántos con el equipo docente (tus consultas y sus respuestas)" in t
    assert "en el chat con la tutora y en tus consultas al docente" in t and "Son lecturas automáticas, no una nota" in t


def test_presentacion_nombra_los_conteos_y_las_lecturas_automaticas():
    t = _texto("static", "presentacion.html")
    assert "Cada grupo de cursada, una comisión," in t and "lecturas que la app calcula sola" in t


def test_la_tarjeta_aclara_que_el_indice_es_automatico():
    assert "en el chat con la tutora y en las consultas al docente: no es una nota" in _texto("static", "app.js")


def test_la_separacion_de_la_comision_2_es_controlada_y_reversible():
    s, r = _texto("sql", "0171_comision2.sql"), _texto("sql", "0171_comision2_reversa.sql")
    assert "ON_ERROR_STOP" in s and "id BETWEEN 95 AND 130" in s and "RAISE EXCEPTION" in s
    assert "CREATE TABLE respaldo_grupos_0171" in s and "Grupo A · comisión 2" in s
    assert "FROM respaldo_grupos_0171" in r and "u.grupo = 'Grupo A · comisión 2'" in r
