"""Quien ya empezó un proyecto puede dejarlo para sumarse a un equipo, y recuperarlo. Pedido del 26/11/2026
(Grupo B: varias personas con proyecto propio querían trabajar juntas en uno). Dejar no borra nada."""
import importlib.util
from pathlib import Path

import pytest

import models
from config import settings
from routers import proyectos_ia
from services import uso_publico
from tests import test_recorrido_propio
from tests.test_equipos_0167 import _como, _sembrar, _sumar

entorno = test_recorrido_propio.entorno
RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture(autouse=True)
def _sin_aprendizajes(monkeypatch):
    monkeypatch.setattr(proyectos_ia, "_registrar_aprendizajes_auto", lambda *a, **k: None)
    monkeypatch.setattr(settings, "openai_api_key", "")


def _preparar(client, db):
    """«Cinco» (id 5) tiene un proyecto empezado (id 5); «Una» (id 1) quiere sumarle."""
    _sembrar(db)
    db.add(models.MensajeProyectoIA(proyecto_id=5, usuario_id=5, remitente="participante", contenido="Mi aporte previo."))
    db.commit()


def test_con_proyecto_en_curso_no_se_suma_y_el_mensaje_dice_como(entorno):
    client, db = entorno
    _preparar(client, db)
    r = _sumar(client, "cinco@example.test")
    assert r.status_code == 409 and "Dejar mi proyecto" in r.json()["detail"]


def test_deja_se_suma_sale_y_recupera_sin_perder_nada(entorno):
    client, db = entorno
    _preparar(client, db)
    _como(client, db, 5)
    assert client.get("/proyectos-ia/mio").json()["equipo"]["puede_dejar"]
    r = client.post("/proyectos-ia/mio/dejar")
    assert r.status_code == 200 and r.json()["id"] == 5 and r.json()["retirado_en"]
    assert not r.json()["equipo"]["puede_sumar"] and not r.json()["equipo"]["puede_dejar"]
    _como(client, db, 1)
    assert _sumar(client, "cinco@example.test").status_code == 200
    _como(client, db, 5)
    assert client.get("/proyectos-ia/mio").json()["id"] == 1
    assert client.post("/proyectos-ia/mio/recuperar").status_code == 409  # primero sale del equipo
    assert client.delete("/proyectos-ia/mio/equipo/5").status_code == 200
    assert client.get("/proyectos-ia/mio").json()["retirado_en"]
    r = client.post("/proyectos-ia/mio/recuperar")
    assert r.status_code == 200 and r.json()["id"] == 5 and r.json()["retirado_en"] is None
    assert r.json()["titulo"] == "Otro trabajo" and r.json()["estado"] == "en_proceso"
    assert any(m["contenido"] == "Mi aporte previo." for m in r.json()["mensajes"])
    acciones = {e.accion for e in db.query(models.ActivityEvent).all()}
    assert {"proyecto_dejado", "proyecto_recuperado"} <= acciones


def test_un_proyecto_dejado_es_de_solo_lectura_pero_admite_consultar_al_docente(entorno):
    client, db = entorno
    _preparar(client, db)
    _como(client, db, 5)
    client.post("/proyectos-ia/mio/dejar")
    assert client.patch("/proyectos-ia/mio", json={"titulo": "Cambio"}).status_code == 409
    assert client.post("/proyectos-ia/mio/mensajes", json={"mensaje": "Otra idea para el proyecto."}).status_code == 409
    assert client.post("/proyectos-ia/mio/criterios/datos/cerrar").status_code == 409
    assert _sumar(client, "dos@example.test").status_code == 409
    assert client.post("/proyectos-ia/mio/docente", json={"mensaje": "¿Está bien que lo haya dejado?"}).status_code == 200
    assert db.get(models.ProyectoIA, 5).titulo == "Otro trabajo"


def test_sale_de_la_galeria_y_de_los_conteos(entorno):
    client, db = entorno
    _preparar(client, db)
    _como(client, db, 5)
    antes = uso_publico.calcular(db)["proyectos"]
    assert 5 in [c["id"] for c in client.get("/proyectos-ia/casos").json()]
    client.post("/proyectos-ia/mio/dejar")
    assert 5 not in [c["id"] for c in client.get("/proyectos-ia/casos").json()]
    assert client.get("/proyectos-ia/casos/5").status_code == 404
    assert uso_publico.calcular(db)["proyectos"] == antes - 1


def test_no_se_deja_un_proyecto_con_integrantes_ni_uno_sin_empezar_ni_estando_en_equipo(entorno):
    client, db = entorno
    _preparar(client, db)
    _como(client, db, 2)  # abierto, sin aportes
    assert client.post("/proyectos-ia/mio/dejar").status_code == 400
    _como(client, db, 3)  # sin proyecto: dejar no lo crea
    assert client.post("/proyectos-ia/mio/dejar").status_code == 400
    assert db.query(models.ProyectoIA).filter_by(usuario_id=3).count() == 0
    _como(client, db, 1)
    assert _sumar(client, "dos@example.test").status_code == 200
    r = client.post("/proyectos-ia/mio/dejar")
    assert r.status_code == 409 and "integrantes" in r.json()["detail"]
    _como(client, db, 2)
    assert client.post("/proyectos-ia/mio/dejar").status_code == 409


def test_la_migracion_sigue_a_la_ultima_y_es_la_cabeza():
    ruta = RAIZ / "alembic" / "versions" / "20261126_retiro.py"
    spec = importlib.util.spec_from_file_location("m_retiro", ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.down_revision == "20261121_r1_v12" and len(m.revision) <= 32
