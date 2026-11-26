"""0.10.67: proyectos en equipo de la Incubadora. Un proyecto, varias personas, cada aporte con su nombre.

Pedido del 04/11/2026 a partir de una consulta de la comisión del grupo B: «los tres tenemos que interactuar con
la IA, pero el proyecto sería uno solo». Quien abrió el proyecto suma por correo a gente de su grupo; para sumarse
no hay que tener un proyecto propio con aportes; al salir, lo escrito queda en el proyecto con su nombre.
"""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.exc import IntegrityError

import models
from config import settings
from core.auth import get_current_user
from routers import proyectos_ia, votos_proyectos_ia
from services import memoria_incubadora
from tests import test_recorrido_propio

entorno = test_recorrido_propio.entorno
JUSTIFICACION = "Propuesta sólida, con indicadores medibles y datos que el área ya tiene."


@pytest.fixture(autouse=True)
def _sin_aprendizajes(monkeypatch):
    # El registro automático de aprendizajes usa operadores JSON de PostgreSQL que SQLite no tiene.
    monkeypatch.setattr(proyectos_ia, "_registrar_aprendizajes_auto", lambda *a, **k: None)


def _sembrar(db):
    """La persona que consulta (id 1, «Una», Grupo A) abre el proyecto; las demás son posibles integrantes."""
    db.add_all([
        models.Usuario(id=2, email="dos@example.test", nombre="Dos", password_hash="x", rol="analista"),
        models.Usuario(id=3, email="tres@example.test", nombre="Tres", password_hash="x", rol="analista"),
        models.Usuario(id=4, email="cuatro@example.test", nombre="Cuatro", password_hash="x", rol="analista", grupo="Grupo B"),
        models.Usuario(id=5, email="cinco@example.test", nombre="Cinco", password_hash="x", rol="analista"),
        models.Usuario(id=9, email="admin@example.test", nombre="Admin", password_hash="x", rol="admin"),
    ])
    db.add(models.ProyectoIA(id=1, usuario_id=1, titulo="Consultas de PyMEs", situacion="Las consultas llegan por tres vías.",
                             estado="en_proceso"))
    db.add(models.ProyectoIA(id=2, usuario_id=2, estado="en_proceso"))  # abierto, sin aportes
    db.add(models.ProyectoIA(id=5, usuario_id=5, titulo="Otro trabajo", situacion="Ya empezado.", estado="en_proceso"))
    db.commit()


def _como(client, db, usuario_id):
    client.app.dependency_overrides[get_current_user] = lambda: db.get(models.Usuario, usuario_id)


def _sumar(client, email):
    return client.post("/proyectos-ia/mio/equipo", json={"email": email})


def test_quien_abrio_suma_y_todos_trabajan_en_el_mismo_proyecto(entorno):
    client, db = entorno
    _sembrar(db)
    respuesta = _sumar(client, " DOS@example.test ")
    assert respuesta.status_code == 200
    equipo = respuesta.json()["equipo"]
    assert equipo["en_equipo"] and equipo["soy_titular"] and equipo["puede_sumar"]
    assert [(p["nombre"], p["abrio_el_proyecto"]) for p in equipo["integrantes"]] == [("Una", True), ("Dos", False)]
    _como(client, db, 2)
    mio = client.get("/proyectos-ia/mio").json()
    assert mio["id"] == 1 and mio["titulo"] == "Consultas de PyMEs"
    assert not mio["equipo"]["soy_titular"] and not mio["equipo"]["puede_sumar"]
    assert "correo" not in str(mio["equipo"]) and "example.test" not in str(mio["equipo"])


def test_cada_mensaje_queda_con_el_nombre_de_quien_lo_escribio(entorno, monkeypatch):
    client, db = entorno
    _sembrar(db)
    monkeypatch.setattr(settings, "openai_api_key", "")
    _sumar(client, "dos@example.test")
    assert client.post("/proyectos-ia/mio/mensajes", json={"mensaje": "Las consultas llegan por correo, teléfono y mesa de entradas."}).status_code == 200
    _como(client, db, 2)
    assert client.post("/proyectos-ia/mio/mensajes", json={"mensaje": "Agrego que el área tarda unos cinco días en responder."}).status_code == 200
    mensajes = client.get("/proyectos-ia/mio").json()["mensajes"]
    autores = [(m["autor"], m["usuario_id"]) for m in mensajes if m["remitente"] == "participante"]
    assert autores == [("Una", 1), ("Dos", 2)]
    assert all(m["autor"] is None for m in mensajes if m["remitente"] == "ia")


def test_un_proyecto_individual_no_muestra_autores(entorno, monkeypatch):
    client, db = entorno
    _sembrar(db)
    monkeypatch.setattr(settings, "openai_api_key", "")
    client.post("/proyectos-ia/mio/mensajes", json={"mensaje": "Las consultas llegan por correo, teléfono y mesa de entradas."})
    mio = client.get("/proyectos-ia/mio").json()
    assert not mio["equipo"]["en_equipo"]
    assert all(m["autor"] is None for m in mio["mensajes"])


class _OpenAIFalso:
    pedidos = []

    def __init__(self, **_kw):
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._crear))

    def _crear(self, **kw):
        _OpenAIFalso.pedidos.append(kw["messages"])
        mensaje = SimpleNamespace(content="Gracias. ¿Cuántas consultas llegan por semana?")
        return SimpleNamespace(choices=[SimpleNamespace(message=mensaje, finish_reason="stop")])


def test_la_tutora_sabe_quien_aporto_que(entorno, monkeypatch):
    client, db = entorno
    _sembrar(db)
    _sumar(client, "dos@example.test")
    monkeypatch.setattr(settings, "openai_api_key", "clave-de-prueba")
    monkeypatch.setattr("openai.OpenAI", _OpenAIFalso)
    _OpenAIFalso.pedidos.clear()
    _como(client, db, 2)
    assert client.post("/proyectos-ia/mio/mensajes", json={"mensaje": "El área tarda unos cinco días en responder."}).status_code == 200
    contenidos = [m["content"] for m in _OpenAIFalso.pedidos[-1]]
    assert any("Este proyecto es de un equipo: Una y Dos" in c for c in contenidos)
    assert any(c.startswith("[Dos] El área tarda") for c in contenidos)
    fuentes = memoria_incubadora.fuentes_participante(db.get(models.ProyectoIA, 1))["fuentes"]
    assert any(f["origen"] == "mensaje de Dos (integrante del equipo)" for f in fuentes.values())


def test_solo_quien_abrio_suma_integrantes(entorno):
    client, db = entorno
    _sembrar(db)
    _sumar(client, "dos@example.test")
    _como(client, db, 2)
    respuesta = _sumar(client, "tres@example.test")
    assert respuesta.status_code == 403
    assert db.query(models.IntegranteProyectoIA).count() == 1


@pytest.mark.parametrize("email, estado, texto", [
    ("cuatro@example.test", 400, "otro grupo"),
    ("cinco@example.test", 409, "tiene un proyecto propio en curso"),
    ("nadie@example.test", 404, "No hay una cuenta"),
    ("admin@example.test", 400, "cuenta docente"),
    ("una@example.test", 409, "ya está en el equipo"),
])
def test_reglas_para_sumarse(entorno, email, estado, texto):
    client, db = entorno
    _sembrar(db)
    respuesta = _sumar(client, email)
    assert respuesta.status_code == estado and texto in respuesta.json()["detail"]
    assert db.query(models.IntegranteProyectoIA).count() == 0
    assert db.get(models.ProyectoIA, 5).situacion == "Ya empezado."  # el trabajo de la otra persona no se toca


def test_una_persona_integra_un_solo_equipo(entorno):
    client, db = entorno
    _sembrar(db)
    _sumar(client, "dos@example.test")
    _como(client, db, 3)
    client.get("/proyectos-ia/mio")
    respuesta = _sumar(client, "dos@example.test")
    assert respuesta.status_code == 409 and "otro equipo" in respuesta.json()["detail"]


def test_quien_abrio_un_equipo_no_se_suma_a_otro(entorno):
    client, db = entorno
    _sembrar(db)
    db.get(models.ProyectoIA, 1).titulo = None
    db.get(models.ProyectoIA, 1).situacion = None
    db.commit()
    _sumar(client, "dos@example.test")
    _como(client, db, 3)
    client.get("/proyectos-ia/mio")
    respuesta = _sumar(client, "una@example.test")
    assert respuesta.status_code == 409 and "ya abrió un proyecto en equipo" in respuesta.json()["detail"]


def test_el_equipo_tiene_un_tope(entorno, monkeypatch):
    client, db = entorno
    _sembrar(db)
    monkeypatch.setattr(settings, "incubadora_max_integrantes", 2)
    assert _sumar(client, "dos@example.test").status_code == 200
    respuesta = _sumar(client, "tres@example.test")
    assert respuesta.status_code == 409 and "el máximo" in respuesta.json()["detail"]


def test_al_salir_lo_escrito_queda_y_vuelve_a_su_proyecto(entorno, monkeypatch):
    client, db = entorno
    _sembrar(db)
    monkeypatch.setattr(settings, "openai_api_key", "")
    _sumar(client, "dos@example.test")
    _como(client, db, 2)
    client.post("/proyectos-ia/mio/mensajes", json={"mensaje": "Agrego que el área tarda unos cinco días en responder."})
    respuesta = client.delete("/proyectos-ia/mio/equipo/2")
    assert respuesta.status_code == 200 and respuesta.json()["id"] == 2  # su proyecto propio, vacío
    db.expire_all()
    escritos = [m for m in db.get(models.ProyectoIA, 1).mensajes if m.remitente == "participante"]
    assert [m.usuario_id for m in escritos] == [2]
    acciones = {e.accion for e in db.query(models.ActivityEvent).all()}
    assert {"equipo_integrante_sumado", "equipo_integrante_salio"} <= acciones
    _como(client, db, 1)
    assert not client.get("/proyectos-ia/mio").json()["equipo"]["en_equipo"]


def test_quien_abrio_no_sale_y_un_integrante_no_quita_a_otro(entorno):
    client, db = entorno
    _sembrar(db)
    _sumar(client, "dos@example.test")
    client.get("/proyectos-ia/mio")
    _como(client, db, 3)
    client.get("/proyectos-ia/mio")
    _como(client, db, 1)
    _sumar(client, "tres@example.test")
    assert client.delete("/proyectos-ia/mio/equipo/1").status_code == 400
    _como(client, db, 2)
    assert client.delete("/proyectos-ia/mio/equipo/3").status_code == 403
    _como(client, db, 1)
    assert client.delete("/proyectos-ia/mio/equipo/3").status_code == 200
    assert db.query(models.IntegranteProyectoIA).count() == 1


def test_galeria_y_recorrido_reconocen_el_proyecto_del_equipo(entorno):
    client, db = entorno
    _sembrar(db)
    _sumar(client, "dos@example.test")
    _como(client, db, 2)
    casos = {c["id"]: c for c in client.get("/proyectos-ia/casos").json()}
    assert casos[1]["es_propio"] and casos[1]["integrantes"] == 2
    assert "nombre" not in casos[1] and "equipo" not in casos[1]  # la galería sigue sin nombres
    proyectos_antes = db.query(models.ProyectoIA).count()
    assert client.get("/proyectos-ia/mi-recorrido").status_code == 200
    assert db.query(models.ProyectoIA).count() == proyectos_antes


def test_nadie_vota_el_proyecto_de_su_equipo(entorno):
    client, db = entorno
    _sembrar(db)
    client.app.include_router(votos_proyectos_ia.router)
    _sumar(client, "dos@example.test")
    db.add(models.ActividadVotacion(id=1, cohorte="Grupo A · noviembre", activa=True, primera_vuelta_abierta=True,
                                    proyectos_ids=[1, 5], finalistas=[]))
    db.commit()
    _como(client, db, 2)
    respuesta = client.post("/proyectos-ia/votos", json={"proyecto_id": 1, "justificacion": JUSTIFICACION})
    assert respuesta.status_code == 400 and "de tu equipo" in respuesta.json()["detail"]
    assert client.post("/proyectos-ia/votos", json={"proyecto_id": 5, "justificacion": JUSTIFICACION}).status_code == 200


def test_la_supervision_docente_ve_el_equipo_y_puede_armarlo(entorno):
    client, db = entorno
    _sembrar(db)
    _como(client, db, 9)
    assert client.post("/proyectos-ia/1/equipo", json={"email": "dos@example.test"}).status_code == 200
    resumen = client.post("/proyectos-ia/1/equipo", json={"email": "tres@example.test"}).json()
    assert [p["nombre"] for p in resumen["integrantes"]] == ["Una", "Dos", "Tres"]
    lista = {p["id"]: p for p in client.get("/proyectos-ia").json()}
    assert lista[1]["equipo"] == ["Una", "Dos", "Tres"]
    assert lista[2]["integra_equipo"] == 1 and lista[2]["equipo"] == []
    detalle = client.get("/proyectos-ia/1").json()
    assert detalle["equipo"]["en_equipo"]
    assert client.delete("/proyectos-ia/1/equipo/3").status_code == 200
    assert db.query(models.IntegranteProyectoIA).count() == 1


def test_la_pantalla_muestra_el_equipo_y_el_autor():
    js = Path("static/app.js").read_text(encoding="utf-8")
    html = Path("static/index.html").read_text(encoding="utf-8")
    assert 'id="proyecto-equipo"' in html
    assert "function renderProyectoEquipo" in js and "renderProyectoEquipo(data);" in js
    assert "m.autor ||" in js and '"/proyectos-ia/mio/equipo"' in js
    assert "Salir del equipo" in js and "Integra el equipo del proyecto" in js


def test_migracion_crea_y_quita_la_tabla_sin_tocar_proyectos():
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    ruta = Path(__file__).resolve().parents[1] / "alembic" / "versions" / "20261104_equipos.py"
    spec = importlib.util.spec_from_file_location("m_equipos", ruta)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    assert m.down_revision == "20261029_grupos" and len(m.revision) <= 32
    engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.exec_driver_sql("CREATE TABLE usuarios (id INTEGER PRIMARY KEY, email VARCHAR(200))")
        conn.exec_driver_sql("CREATE TABLE proyectos_ia (id INTEGER PRIMARY KEY, usuario_id INTEGER)")
        conn.exec_driver_sql("INSERT INTO usuarios (id, email) VALUES (1, 'a@example.test'), (2, 'b@example.test')")
        conn.exec_driver_sql("INSERT INTO proyectos_ia (id, usuario_id) VALUES (1, 1)")
        with Operations.context(MigrationContext.configure(conn)):
            m.upgrade()
            conn.exec_driver_sql("INSERT INTO integrantes_proyecto_ia (proyecto_id, usuario_id, creado_en) VALUES (1, 2, '2026-11-04')")
            with pytest.raises(IntegrityError):
                conn.exec_driver_sql("INSERT INTO integrantes_proyecto_ia (proyecto_id, usuario_id, creado_en) VALUES (1, 2, '2026-11-04')")
            m.downgrade()
            assert "integrantes_proyecto_ia" not in sa_inspect(conn).get_table_names()
            assert conn.exec_driver_sql("SELECT id, usuario_id FROM proyectos_ia").all() == [(1, 1)]
    engine.dispose()
