"""0.10.69: el docente puede marcar que una consulta no requiere respuesta (p. ej., un agradecimiento)."""
import datetime as dt

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
from routers.proyectos_ia import _consulta_docente_pendiente, _consulta_marcada_sin_respuesta
from services import aviso_docente

BASE = dt.datetime(2026, 11, 1, 12, 0)
RUTA = "/proyectos-ia/7/consultas/no-requiere-respuesta"


@pytest.fixture
def entorno():
    @compiles(JSONB, "sqlite")
    def json_sqlite(element, compiler, **kw):
        return "JSON"

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(models.Usuario(id=1, email="alumna@prueba.test", nombre="Alumna Prueba", password_hash="x", rol="analista"))
        db.add(models.Usuario(id=9, email="docente@prueba.test", nombre="Docente", password_hash="x", rol="admin"))
        db.add(models.ProyectoIA(id=7, usuario_id=1, titulo="Tablero de expedientes"))
        db.commit()
        app = FastAPI()
        app.include_router(proyectos_ia.router)
        app.dependency_overrides[get_db] = lambda: db
        app.dependency_overrides[get_current_user] = lambda: db.get(models.Usuario, 1)
        with TestClient(app) as client:
            yield client, db
    engine.dispose()
    deregister(JSONB)


def _mensajes(db, pares):
    for i, (remitente, dia) in enumerate(pares):
        db.add(models.MensajeProyectoIA(proyecto_id=7, remitente=remitente, contenido=f"m{i}",
                                        creado_en=BASE + dt.timedelta(days=dia)))
    db.commit()


def _como_docente(client, db):
    client.app.dependency_overrides[proyectos_ia.require_admin] = lambda: db.get(models.Usuario, 9)


def test_marcar_saca_la_consulta_de_pendientes_y_del_recordatorio(entorno):
    client, db = entorno
    _mensajes(db, [("consulta_docente", 0), ("docente", 1), ("consulta_docente", 2), ("consulta_docente", 2)])
    antes = db.query(models.MensajeProyectoIA).count()
    ahora = BASE + dt.timedelta(days=6)
    assert len(aviso_docente.consultas_sin_respuesta(db, ahora=ahora, mas_de_dias=2)) == 2
    _como_docente(client, db)
    r = client.post(RUTA)
    assert r.status_code == 200 and r.json()["consultas"] == 2
    assert aviso_docente.consultas_sin_respuesta(db, ahora=ahora) == []
    assert db.query(models.MensajeProyectoIA).count() == antes  # no se borra ni se agrega nada
    evento = db.query(models.ActivityEvent).filter_by(accion=aviso_docente.ACCION_SIN_RESPUESTA).one()
    assert evento.usuario_id == 9 and evento.proyecto_id == 7
    fila = next(p for p in client.get("/proyectos-ia").json() if p["id"] == 7)
    assert fila["consulta_docente_pendiente"] is False and fila["consulta_marcada_sin_respuesta"] is True
    detalle = client.get("/proyectos-ia/7").json()
    assert detalle["consulta_docente_pendiente"] is False and detalle["consulta_marcada_sin_respuesta"] is True
    assert client.get("/proyectos-ia/escucha/metricas").json()["consultas_docente_pendientes"] == 0


def test_una_consulta_posterior_vuelve_a_quedar_pendiente(entorno):
    client, db = entorno
    _mensajes(db, [("consulta_docente", 0)])
    _como_docente(client, db)
    assert client.post(RUTA).status_code == 200
    _mensajes(db, [("consulta_docente", 3)])
    pendientes = aviso_docente.consultas_sin_respuesta(db, ahora=BASE + dt.timedelta(days=4))
    assert [p["dias"] for p in pendientes] == [1]
    fila = next(p for p in client.get("/proyectos-ia").json() if p["id"] == 7)
    assert fila["consulta_docente_pendiente"] is True and fila["consulta_marcada_sin_respuesta"] is False


def test_sin_consultas_pendientes_responde_409(entorno):
    client, db = entorno
    _como_docente(client, db)
    assert client.post(RUTA).status_code == 409
    _mensajes(db, [("consulta_docente", 0), ("docente", 1)])
    assert client.post(RUTA).status_code == 409
    assert client.post("/proyectos-ia/999/consultas/no-requiere-respuesta").status_code == 404


def test_solo_el_docente_puede_marcar(entorno):
    client, db = entorno
    _mensajes(db, [("consulta_docente", 0)])
    assert client.post(RUTA).status_code in (401, 403)
    assert db.query(models.ActivityEvent).filter_by(accion=aviso_docente.ACCION_SIN_RESPUESTA).count() == 0


def test_regla_del_pendiente_con_la_marca():
    def m(remitente, id_):
        return models.MensajeProyectoIA(id=id_, proyecto_id=7, remitente=remitente, contenido="x")
    canal = [m("consulta_docente", 1), m("docente", 2), m("consulta_docente", 5)]
    assert _consulta_docente_pendiente(canal) is True
    assert _consulta_docente_pendiente(canal, 5) is False and _consulta_marcada_sin_respuesta(canal, 5) is True
    assert _consulta_docente_pendiente(canal, 4) is True and _consulta_marcada_sin_respuesta(canal, 4) is False
    assert _consulta_docente_pendiente(canal[:2], 0) is False and _consulta_marcada_sin_respuesta(canal[:2], 9) is False
