"""0.10.72: Conexiones muestra lo que comparten los prototipos de los proyectos visibles."""
from pathlib import Path
from types import SimpleNamespace

from services import prototipos_incubadora as pi

RAIZ = Path(__file__).resolve().parent.parent


def _p(i, titulo=""):
    return SimpleNamespace(id=i, titulo=titulo)


def test_agrupa_los_prototipos_visibles_por_base_y_componente():
    r = pi.conexiones([_p(66, "Boletín"), _p(72), _p(67), _p(60), _p(59), _p(999)])
    bases = {b["clave"]: b for b in r["bases"]}
    assert set(bases) == {"documentos", "consultas"}
    assert [c["id"] for c in bases["documentos"]["casos"]] == [66, 72, 67, 60]
    assert bases["documentos"]["casos"][0]["titulo"] == "Boletín" and bases["documentos"]["casos"][1]["titulo"] == "Caso en definición"
    nombres = [c["nombre"] for c in r["componentes"]]
    assert "Una sola base de normas" in nombres and "El circuito de una ley" in nombres
    assert "Clasificar y derivar" not in nombres  # sólo un proyecto visible: no hay conexión
    assert all(c["url"].startswith(pi.SITIO + "/") for b in r["bases"] for c in b["casos"])
    assert "datos ficticios" in r["aviso"]


def test_sin_prototipos_visibles_no_muestra_nada():
    assert pi.conexiones([_p(6), _p(999)]) == {"aviso": pi.AVISO_CONEXIONES, "bases": [], "componentes": []}


def test_las_bases_y_los_componentes_usan_proyectos_con_prototipo():
    ids = {i for _, _, grupo in pi.BASES + pi.COMPONENTES for i in grupo}
    assert ids <= set(pi.PROTOTIPOS)


def test_pantallas():
    app = (RAIZ / "static" / "app.js").read_text(encoding="utf-8")
    assert "function renderPrototiposConexiones" in app and "<strong>Modo prueba</strong>" in app
    inicio = (RAIZ / "static" / "index.html").read_text(encoding="utf-8")
    assert "Cada proyecto de tu comisión usa Monitoreo en modo prueba" in inicio and "app.js?v=20261126-dejar-proyecto" in inicio


def test_la_pagina_principal_elige_el_texto_de_monitoreo_por_grupo():
    import main
    import models

    comision2 = main.index_para(models.Usuario(rol="analista", grupo="Grupo A · comisión 2"))
    comision1 = main.index_para(models.Usuario(rol="analista"))
    grupo_b = main.index_para(models.Usuario(rol="analista", grupo="Grupo B"))
    otro_grupo = main.index_para(models.Usuario(rol="analista", grupo="Grupo de prueba"))
    # 0.10.80: Grupo B también usa el modo prueba; un grupo sin modo prueba sigue con la implementación real.
    for prueba in (comision2, grupo_b):
        assert "Cada proyecto de tu comisión usa Monitoreo en modo prueba" in prueba and "Implementación real" not in prueba
    for otro in (comision1, otro_grupo):
        assert "modo prueba" not in otro.lower() and "Implementación real" in otro
    assert "Los demás proyectos permanecen en cartera" in comision1
