"""0.10.80: la comisión 2 del grupo A y la primera comisión del grupo B no usan votación, y el grupo B registra en
Monitoreo en modo prueba (decisión de Maxi, 08/11/2026: «voy a implementar a todos»)."""
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from main import app, index_para
from routers import monitoreo
from services import grupos, votacion

STATIC = Path(__file__).resolve().parents[1] / "static"
HACIENDA = SimpleNamespace(id=9001, rol="analista", grupo="Grupo B")
COMISION_2 = SimpleNamespace(id=9002, rol="analista", grupo="Grupo A · comisión 2")
POR_DEFECTO = SimpleNamespace(id=9003, rol="analista", grupo=None)
ADMIN = SimpleNamespace(id=9004, rol="admin", grupo=None)


def test_quien_usa_votacion():
    assert grupos.sin_votacion() == {"Grupo A · comisión 2", "Grupo B"}
    assert not grupos.con_votacion(HACIENDA) and not grupos.con_votacion(COMISION_2)
    assert grupos.con_votacion(POR_DEFECTO) and grupos.con_votacion(ADMIN) and grupos.con_votacion(None)


@pytest.mark.parametrize("usuario", [HACIENDA, COMISION_2])
def test_los_grupos_sin_votacion_no_reciben_la_votacion(usuario):
    html = index_para(usuario)
    assert 'id="view-segunda-vuelta"' not in html and 'class="vote-guidance"' not in html
    assert "Votación pedagógica" not in html and "Ir a la segunda vuelta" not in html
    assert "sin tu nombre ni las conversaciones o devoluciones." in html and "y puede votarlo" not in html
    assert 'id="view-casos"' in html and 'id="view-conexiones"' in html  # la galería y el mapa siguen


@pytest.mark.parametrize("usuario", [POR_DEFECTO, ADMIN])
def test_el_grupo_por_defecto_y_la_administracion_conservan_la_votacion(usuario):
    html = index_para(usuario)
    assert 'id="view-segunda-vuelta"' in html and 'class="vote-guidance"' in html and ", y puede votarlo" in html


def test_el_servidor_no_acepta_votos_de_esos_grupos():
    assert votacion.activa_del_grupo(None, HACIENDA) is None  # ni consulta la base
    with pytest.raises(HTTPException) as error:
        votacion.activa(None, usuario=COMISION_2)
    assert error.value.status_code == 409 and "no usa votación" in error.value.detail


def test_hacienda_registra_en_modo_prueba_sin_suponer_un_prototipo():
    assert "Grupo B" in monitoreo.grupos_prueba() and "Grupo A · comisión 2" in monitoreo.grupos_prueba()
    proyecto = SimpleNamespace(id=987654, usuario=HACIENDA)
    assert monitoreo.modo_de(proyecto) == "prueba"
    html = index_para(HACIENDA)
    assert "Cada proyecto de tu comisión usa Monitoreo en modo prueba" in html
    assert "probar tu prototipo" not in html and "con su prototipo, si lo tiene" in html


def test_la_pantalla_no_vota_ni_consulta_la_votacion_si_el_grupo_no_la_usa():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert 'return Boolean(document.getElementById("view-segunda-vuelta"));' in js
    assert 'const VISTAS_POR_GRUPO = new Set(["segunda-vuelta", "sintesis"]);' in js
    assert '(!VISTAS_POR_GRUPO.has(item.view) || Boolean(document.getElementById(`view-${item.view}`)))' in js
    assert "document.getElementById('view-sintesis')?.addEventListener" in js  # sin la vista, no se rompe el arranque
    assert 'grupoConVotacion() ? apiFetch("/proyectos-ia/votos/estado") : Promise.resolve(null)' in js
    assert 'async function cargarRotuloVotacion() {\n  if (!grupoConVotacion()) return;' in js
    assert 'if (!document.getElementById("view-" + nombre)) { nombre = "inicio"; actualizarUrl = true; }' in js
    assert '"Para orientar el voto" : "Para comparar"' in js and '"probar tu prototipo' not in js


def test_la_presentacion_dice_que_la_votacion_es_del_grupo_que_la_usa():
    html = TestClient(app).get("/presentacion").text
    assert "y, si el grupo la usa, su propia votación" in html
    assert "En dos grupos de cursada, cada proyecto registra en modo prueba" in html


@pytest.mark.parametrize("usuario", [HACIENDA, COMISION_2])
def test_las_tres_sintesis_no_llegan_a_los_otros_grupos(usuario):
    html = index_para(usuario)
    assert 'id="view-sintesis"' not in html and "Tres desarrollos conjuntos" not in html
    assert html.count("<section") == html.count("</section>")  # el recorte no deja secciones abiertas


@pytest.mark.parametrize("usuario", [POR_DEFECTO, ADMIN])
def test_las_tres_sintesis_siguen_en_el_grupo_por_defecto(usuario):
    html = index_para(usuario)
    assert 'id="view-sintesis"' in html and "Tres desarrollos conjuntos" in html


def test_monitoreo_y_la_galeria_no_suponen_prototipo_ni_votacion():
    from routers import proyectos_ia

    assert "prototipo, si tiene uno" in monitoreo.ALCANCE["prueba"] and "con el prototipo y sus datos" not in monitoreo.ALCANCE["prueba"]
    alta = {"puntaje_claridad": 5}
    assert proyectos_ia._madurez_votacion(alta) == "Alta: formulación sólida para comparar y votar."
    assert "votar" not in proyectos_ia._madurez_votacion(alta, False)
    assert "votar" not in proyectos_ia._madurez_votacion({"puntaje_claridad": 2}, False)
