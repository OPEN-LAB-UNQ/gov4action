"""0.10.73: los enlaces del sitio de prototipos («/?ir=…») abren su pantalla, también después del ingreso.

Los destinos son una lista cerrada: lo que llega en el pedido nunca se copia a la redirección.
"""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles, deregister
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import core.auth as core_auth
import models
from core.auth import DESTINOS_INGRESO, destino_ingreso, hash_password, login_html
from database import get_db
from main import app as aplicacion
from routers import auth

STATIC = Path(__file__).resolve().parent.parent / "static"
AJENOS = (None, "", "inicio", "proyecto-ia", "//otro.sitio", "https://otro.sitio/", "monitoreo/../x", '"><script>')


@pytest.fixture
def entorno(monkeypatch):
    # Los intentos fallidos se cuentan en memoria por proceso: cada prueba arranca sin los de otras.
    monkeypatch.setattr(core_auth, "_login_intentos_fallidos", {})

    @compiles(JSONB, "sqlite")
    def json_sqlite(element, compiler, **kw):
        return "JSON"
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(models.Usuario(id=2, email="alumno@t", nombre="Alumno", password_hash=hash_password("clave-alumno"),
                              rol="analista"))
        db.commit()
        app = FastAPI()
        app.include_router(auth.router)
        app.dependency_overrides[get_db] = lambda: db
        yield TestClient(app, base_url="https://testserver")
    engine.dispose()
    deregister(JSONB)


def test_los_destinos_son_una_lista_cerrada():
    assert DESTINOS_INGRESO == {"proyecto": "/#/proyecto-ia", "monitoreo": "/#/monitoreo", "conexiones": "/#/conexiones"}
    assert destino_ingreso(" Monitoreo ") == "monitoreo"
    for ajeno in AJENOS:
        assert destino_ingreso(ajeno) is None, ajeno


def test_el_formulario_lleva_el_destino_solo_si_es_de_la_lista():
    assert '<input type="hidden" name="ir" value="monitoreo" />' in login_html(ir="monitoreo")
    for ajeno in AJENOS:
        html = login_html(ir=ajeno)
        assert 'name="ir"' not in html and "otro.sitio" not in html and "<script>" not in html, ajeno


def test_la_pagina_de_ingreso_recibe_el_destino(entorno):
    assert 'name="ir" value="conexiones"' in entorno.get("/login?ir=conexiones").text
    html = entorno.get("/login?ir=https://otro.sitio/").text
    assert 'name="ir"' not in html and "otro.sitio" not in html


def test_el_ingreso_vuelve_a_la_pantalla_pedida(entorno):
    for clave, destino in DESTINOS_INGRESO.items():
        r = entorno.post("/login", data={"email": "alumno@t", "password": "clave-alumno", "ir": clave},
                         follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == destino, clave


def test_sin_destino_o_con_uno_ajeno_el_ingreso_va_al_inicio(entorno):
    for ajeno in AJENOS:
        datos = {"email": "alumno@t", "password": "clave-alumno"}
        if ajeno is not None:
            datos["ir"] = ajeno
        r = entorno.post("/login", data=datos, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/#/inicio", ajeno


def test_un_ingreso_fallido_conserva_el_destino(entorno):
    r = entorno.post("/login", data={"email": "alumno@t", "password": "otra", "ir": "monitoreo"}, follow_redirects=False)
    assert r.status_code == 401 and 'name="ir" value="monitoreo"' in r.text


def test_sin_sesion_la_raiz_con_destino_pasa_por_el_ingreso(monkeypatch):
    monkeypatch.setattr(core_auth, "active_token", lambda token: False)
    cliente = TestClient(aplicacion, base_url="https://testserver")
    for clave in DESTINOS_INGRESO:
        for raiz in ("/", "/index.html"):
            r = cliente.get(f"{raiz}?ir={clave}", follow_redirects=False)
            assert r.status_code == 303 and r.headers["location"] == f"/login?ir={clave}", (raiz, clave)
    for ajeno in ("https://otro.sitio/", "//otro.sitio", "inicio"):
        r = cliente.get("/", params={"ir": ajeno}, follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == "/login", ajeno


def test_con_sesion_la_raiz_con_destino_abre_la_pantalla(monkeypatch):
    monkeypatch.setattr(core_auth, "active_token", lambda token: True)
    cliente = TestClient(aplicacion, base_url="https://testserver")
    for clave, destino in DESTINOS_INGRESO.items():
        r = cliente.get(f"/?ir={clave}", follow_redirects=False)
        assert r.status_code == 303 and r.headers["location"] == destino, clave


def test_el_script_se_renueva():
    # Cómo se abre Monitoreo (desde la 0.10.77, su pantalla propia) lo prueba tests/destino_monitoreo_ui.cjs.
    assert "app.js?v=20261108-aviso-alumno" in (STATIC / "index.html").read_text(encoding="utf-8")
