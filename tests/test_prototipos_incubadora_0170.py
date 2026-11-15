"""0.10.70: cada proyecto de la Incubadora que tiene prototipo lo enlaza (galería y «Tu caso»)."""
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
from core.auth import get_current_user
from database import get_db
from routers import proyectos_ia
from services import prototipos_incubadora as prototipos

RAIZ = Path(__file__).resolve().parents[1]


@pytest.fixture
def entorno():
    @compiles(JSONB, "sqlite")
    def json_sqlite(element, compiler, **kw):
        return "JSON"

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(models.Usuario(id=1, email="alumna@prueba.test", nombre="Alumna Prueba", password_hash="x", rol="analista"))
        db.add(models.Usuario(id=2, email="alumno@prueba.test", nombre="Alumno Prueba", password_hash="x", rol="analista"))
        db.add(models.Usuario(id=9, email="docente@prueba.test", nombre="Docente", password_hash="x", rol="admin"))
        db.add(models.ProyectoIA(id=66, usuario_id=1, titulo="Seguimiento de normas"))
        db.add(models.ProyectoIA(id=7, usuario_id=2, titulo="Tablero de expedientes"))
        db.commit()
        app = FastAPI()
        app.include_router(proyectos_ia.router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: db.get(models.Usuario, 1)
        with TestClient(app) as client:
            yield client, db
    engine.dispose()
    deregister(JSONB)


def test_tabla_de_prototipos():
    assert len(prototipos.PROTOTIPOS) == 15
    assert set(prototipos.PROTOTIPOS) == {59, 60, 61, 62, 63, 64, 65, 66, 67, 68, 70, 71, 72, 74, 78}
    assert len(set(prototipos.PROTOTIPOS.values())) == 15  # un prototipo por proyecto
    for numero in prototipos.PROTOTIPOS:
        enlace = prototipos.de(numero)
        assert enlace["url"].startswith(prototipos.SITIO + "/") and enlace["url"].endswith("/")
        assert "datos ficticios" in enlace["aviso"] and "no usa tu cuenta de Gov4Action" in enlace["aviso"]
    assert prototipos.de(66)["url"] == "https://proyectos.entornodepruebas.com.ar/boletin-oficial/"
    assert prototipos.de(7) is None and prototipos.de(None) is None


def test_tu_caso_lleva_el_enlace_a_su_prototipo(entorno):
    client, _db = entorno
    datos = client.get("/proyectos-ia/mio").json()
    assert datos["id"] == 66
    assert datos["prototipo"] == prototipos.de(66)


def test_la_galeria_lleva_el_enlace_solo_donde_hay_prototipo(entorno):
    client, _db = entorno
    casos = {c["id"]: c for c in client.get("/proyectos-ia/casos").json()}
    assert casos[66]["prototipo"]["url"].endswith("/boletin-oficial/")
    assert casos[7]["prototipo"] is None


def test_el_detalle_docente_lleva_el_enlace(entorno):
    client, db = entorno
    client.app.dependency_overrides[proyectos_ia.require_admin] = lambda: db.get(models.Usuario, 9)
    assert client.get("/proyectos-ia/66").json()["prototipo"] == prototipos.de(66)
    assert client.get("/proyectos-ia/7").json()["prototipo"] is None


def test_la_pantalla_solo_muestra_el_sitio_de_prototipos():
    app_js = (RAIZ / "static" / "app.js").read_text(encoding="utf-8")
    assert f'const SITIO_PROTOTIPOS = "{prototipos.SITIO}/";' in app_js
    assert "if (!url.startsWith(SITIO_PROTOTIPOS)) return" in app_js
    assert 'target="_blank" rel="noopener noreferrer">Probar el prototipo</a>' in app_js
    assert "enlacePrototipoHtml(caso.prototipo)" in app_js and "enlacePrototipoHtml(data.prototipo)" in app_js
    index = (RAIZ / "static" / "index.html").read_text(encoding="utf-8")
    assert '<p id="proyecto-prototipo" class="hint" hidden></p>' in index
