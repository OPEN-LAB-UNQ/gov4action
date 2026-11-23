"""Regresión: integrantes guardaban su proyecto pero recibían 403 al recargar R-1."""

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
from routers import certificaciones as routes
from services import certificaciones


@pytest.fixture
def team_client():
    @compiles(JSONB, "sqlite")
    def json_sqlite(element, compiler, **kw):
        return "JSON"

    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    tables = [
        models.Usuario,
        models.Area,
        models.Informe,
        models.ProyectoIA,
        models.IntegranteProyectoIA,
        models.MensajeProyectoIA,
        models.ActivityEvent,
        models.VersionProtocolo,
        models.DefinicionControl,
        models.EvaluacionCertificacion,
        models.ResultadoControl,
        models.EvidenciaControl,
        models.HistorialResultadoControl,
        models.SelloCertificacion,
    ]
    models.Base.metadata.create_all(engine, tables=[t.__table__ for t in tables])
    try:
        with Session(engine) as db:
            users = [
                models.Usuario(
                    id=i,
                    email=f"u{i}@example.test",
                    nombre=f"Persona {i}",
                    password_hash="unused",
                    rol="admin" if i == 4 else "analista",
                    grupo="Grupo B",
                )
                for i in range(1, 5)
            ]
            db.add_all(users)
            db.flush()
            p = models.ProyectoIA(id=1, usuario_id=1, titulo="Proyecto compartido", situacion="Caso de prueba")
            db.add(p)
            db.flush()
            db.add(models.IntegranteProyectoIA(proyecto_id=1, usuario_id=2, agregado_por_id=1))
            db.commit()
            app = FastAPI()
            app.include_router(routes.router)
            app.dependency_overrides[get_db] = lambda: db
            current = {"id": 2}
            app.dependency_overrides[get_current_user] = lambda: db.get(models.Usuario, current["id"])
            with TestClient(app) as client:
                yield db, client, current, p
    finally:
        engine.dispose()
        deregister(JSONB)


def test_equipo_sin_evaluacion_y_revocacion_de_pertenencia(team_client):
    db, client, current, p = team_client
    for uid in (1, 2, 4):
        current["id"] = uid
        r = client.get("/certificaciones/proyectos/1/evaluacion")
        assert r.status_code == 200 and r.json() is None
    current["id"] = 3
    assert client.get("/certificaciones/proyectos/1/evaluacion").status_code == 403
    db.delete(db.query(models.IntegranteProyectoIA).one())
    db.commit()
    db.expire_all()
    current["id"] = 2
    assert client.get("/certificaciones/proyectos/1/evaluacion").status_code == 403


def test_equipo_lee_r1_sin_recibir_permisos_docentes_ni_de_otros_objetos(team_client):
    db, client, current, p = team_client
    protocol = models.VersionProtocolo(
        codigo="R-1",
        version="1",
        nombre="R-1",
        tipo_objeto="proyecto_ia",
        descripcion="Prueba",
        activo=True,
        model_policy={},
        matriz_lentes=[],
    )
    db.add(protocol)
    db.flush()
    snapshot, fingerprint = certificaciones.snapshot_proyecto(p)
    evaluation = models.EvaluacionCertificacion(
        protocolo_id=protocol.id,
        proyecto_id=p.id,
        creado_por_id=4,
        estado="en_revision",
        hash_objeto=fingerprint,
        snapshot_objeto=snapshot,
        manifiesto_modelos=[],
    )
    db.add(evaluation)
    db.flush()
    control = models.DefinicionControl(
        protocolo_id=protocol.id,
        codigo="R1-01",
        nombre="Prueba",
        descripcion="Control",
        lente="ajedrecista",
        obligatorio=True,
        criticidad="alta",
        orden=1,
    )
    db.add(control)
    db.flush()
    result = models.ResultadoControl(
        evaluacion_id=evaluation.id, control_id=control.id, aplica=True, estado="no_evaluable"
    )
    db.add(result)
    db.commit()
    base = f"/certificaciones/evaluaciones/{evaluation.id}"
    paths = ["/certificaciones/proyectos/1/evaluacion", base, base + "/reporte", base + "/anexos/ajedrecista"]
    for uid in (1, 2, 4):
        current["id"] = uid
        for path in paths:
            assert client.get(path).status_code == (404 if "/anexos/" in path else 200), (
                path
            )  # R-1 no tiene anexos por lente.
    current["id"] = 3
    for path in paths:
        assert client.get(path).status_code == 403, path
    current["id"] = 2
    assert client.post("/certificaciones/proyectos/1/evaluacion").status_code == 403
    assert (
        client.post(base + "/emitir", json={"alcance_del_analisis": "Prueba", "excluidos_del_analisis": []}).status_code
        == 403
    )
    assert (
        client.post(
            f"/certificaciones/resultados/{result.id}/evidencias", json={"tipo": "nota", "descripcion": "Prueba"}
        ).status_code
        == 403
    )
    # Ser integrante de un proyecto no habilita informes personales de su titular.
    report = models.Informe(usuario_id=1)
    assert not routes._puede_leer_objeto(db.get(models.Usuario, 2), report)
