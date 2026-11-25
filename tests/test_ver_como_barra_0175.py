"""0.10.75: «Ver como» en la barra de arriba: la cuenta administradora elige a cualquier participante."""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles, deregister
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import models
from core.auth import COOKIE_NAME, VER_COMO_COOKIE, hash_password, make_token, make_ver_como
from database import get_db
from routers import auth

STATIC = Path(__file__).resolve().parent.parent / "static"
COM2 = "Grupo A · comisión 2"


@pytest.fixture
def entorno():
    @compiles(JSONB, "sqlite")
    def json_sqlite(element, compiler, **kw):
        return "JSON"
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            models.Usuario(id=1, email="admin@t", nombre="Docente", password_hash=hash_password("x"), rol="admin"),
            models.Usuario(id=2, email="alumna@t", nombre="Alumna", password_hash=hash_password("x"), rol="analista",
                           grupo=COM2),
            models.Usuario(id=3, email="sinproyecto@t", nombre="Sin Proyecto", password_hash=hash_password("x"),
                           rol="analista", grupo=COM2),
            models.Usuario(id=4, email="original@t", nombre="Original", password_hash=hash_password("x"), rol="analista"),
            models.Usuario(id=5, email="otra-admin@t", nombre="Otra", password_hash=hash_password("x"), rol="admin"),
            models.Usuario(id=6, email="equipo@t", nombre="Integrante", password_hash=hash_password("x"),
                           rol="analista", grupo=COM2),
        ])
        db.add(models.ProyectoIA(id=60, usuario_id=2, titulo="Búsqueda de dictámenes", estado="en_proceso"))
        db.flush()
        db.add(models.IntegranteProyectoIA(proyecto_id=60, usuario_id=6, agregado_por_id=2))
        db.commit()
        app = FastAPI()
        app.include_router(auth.router)
        app.dependency_overrides[get_db] = lambda: db
        yield app
    engine.dispose()
    deregister(JSONB)


def _cliente(app, sesion, vista=None):
    c = TestClient(app, base_url="https://testserver")
    c.cookies.set(COOKIE_NAME, make_token(sesion))
    if vista:
        c.cookies.set(VER_COMO_COOKIE, make_ver_como(*vista))
    return c


def test_la_lista_trae_a_todos_los_participantes_con_o_sin_proyecto_y_ninguna_cuenta_administradora(entorno):
    r = _cliente(entorno, 1).get("/api/admin/ver-como/cuentas")
    assert r.status_code == 200
    por_id = {c["id"]: c for c in r.json()}
    assert set(por_id) == {2, 3, 4, 6}
    # sólo estos datos: ningún hash ni token
    assert set(por_id[2]) == {"id", "nombre", "email", "grupo", "activo", "proyecto"}
    assert set(por_id[2]["proyecto"]) == {"id", "titulo", "estado", "en_equipo"}
    assert por_id[2]["grupo"] == COM2 and por_id[2]["proyecto"]["id"] == 60
    assert por_id[2]["proyecto"]["titulo"] == "Búsqueda de dictámenes" and por_id[2]["proyecto"]["en_equipo"] is False
    # quien integra un equipo figura con ese proyecto, como lo ve en «Mi proyecto»
    assert por_id[6]["proyecto"]["id"] == 60 and por_id[6]["proyecto"]["en_equipo"] is True
    assert por_id[3]["proyecto"] is None  # también se puede mirar a quien todavía no abrió su proyecto
    assert por_id[4]["grupo"] is None  # el grupo original llega sin nombre y la pantalla lo rotula


def test_la_lista_es_sólo_para_la_cuenta_administradora_y_fuera_de_una_vista(entorno):
    assert _cliente(entorno, 2).get("/api/admin/ver-como/cuentas").status_code == 403
    # durante una vista la cuenta actual es la del participante: no puede pedir la lista
    assert _cliente(entorno, 1, vista=(1, 2)).get("/api/admin/ver-como/cuentas").status_code == 403


def test_se_puede_abrir_la_vista_de_quien_no_tiene_proyecto(entorno):
    r = _cliente(entorno, 1).post("/api/admin/ver-como", json={"usuario_id": 3})
    assert r.status_code == 200 and r.json()["usuario"]["email"] == "sinproyecto@t"


def test_la_pantalla_pone_el_boton_en_la_barra_y_la_vista_arranca_por_inicio():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    for frase in ("function montarBotonVerComo", 'boton.textContent = "Ver como";', 'getElementById("usuario-actual")?.after(boton)',
                  "async function abrirSelectorVerComo", "/admin/ver-como/cuentas", 'window.location.href = "/#/inicio";'):
        assert frase in js, frase
    assert "app.js?v=20261124-prototipos-grupo_b" in (STATIC / "index.html").read_text(encoding="utf-8")
    assert ".ver-como-boton" in (STATIC / "styles.css").read_text(encoding="utf-8")
