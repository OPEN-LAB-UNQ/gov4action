"""0.10.74: «ver como». La cuenta administradora mira Gov4Action como la ve un participante, en sólo lectura."""
import time
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles, deregister
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

import core.auth as core_auth
import database
import models
from core.auth import (
    COOKIE_NAME,
    VER_COMO_COOKIE,
    VER_COMO_SOLO_LECTURA,
    VER_COMO_VENCIDA,
    hash_password,
    make_token,
    make_ver_como,
    ver_como_info,
)
from database import get_db
from main import app as aplicacion
from routers import auth

STATIC = Path(__file__).resolve().parent.parent / "static"
COM2 = "Grupo A · comisión 2"


def _pedido(**cookies):
    return SimpleNamespace(cookies=cookies)


def _cuentas():
    return [
        models.Usuario(id=1, email="admin@t", nombre="Docente", password_hash=hash_password("clave-admin"), rol="admin"),
        models.Usuario(id=2, email="alumna@t", nombre="Alumna", password_hash=hash_password("x"), rol="analista",
                       grupo=COM2),
        models.Usuario(id=3, email="otra-admin@t", nombre="Otra", password_hash=hash_password("x"), rol="admin"),
        models.Usuario(id=4, email="alumno@t", nombre="Alumno", password_hash=hash_password("x"), rol="analista",
                       grupo=COM2),
    ]


@pytest.fixture
def motor():
    @compiles(JSONB, "sqlite")
    def json_sqlite(element, compiler, **kw):
        return "JSON"
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    models.Base.metadata.create_all(engine)
    yield engine
    engine.dispose()
    deregister(JSONB)


@pytest.fixture
def entorno(motor, monkeypatch):
    monkeypatch.setattr(core_auth, "_login_intentos_fallidos", {})
    with Session(motor) as db:
        db.add_all(_cuentas())
        db.commit()
        app = FastAPI()
        app.include_router(auth.router)
        app.dependency_overrides[get_db] = lambda: db
        yield db, app


@pytest.fixture
def app_real(motor, monkeypatch):
    """La aplicación entera (con su middleware) sobre una base SQLite: el camino middleware → get_db → rollback."""
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=motor, autoflush=False))
    monkeypatch.setattr(core_auth, "active_token", lambda token: True)
    with Session(motor) as db:
        db.add_all(_cuentas())
        db.commit()
    return aplicacion


def _cliente(app, sesion=None, vista=None):
    c = TestClient(app, base_url="https://testserver")
    if sesion is not None:
        c.cookies.set(COOKIE_NAME, make_token(sesion))
    if vista is not None:
        c.cookies.set(VER_COMO_COOKIE, make_ver_como(*vista))
    return c


def test_el_token_de_la_vista_esta_atado_a_la_sesion_de_la_cuenta_administradora(monkeypatch):
    vista = make_ver_como(1, 2)
    assert ver_como_info(_pedido(**{COOKIE_NAME: make_token(1), VER_COMO_COOKIE: vista})) == (1, 2)
    # otra sesión, sin sesión, firma tocada o el token de sesión usado como vista: nada
    assert ver_como_info(_pedido(**{COOKIE_NAME: make_token(2), VER_COMO_COOKIE: vista})) is None
    assert ver_como_info(_pedido(**{VER_COMO_COOKIE: vista})) is None
    tocada = vista[:-1] + ("1" if vista[-1] == "0" else "0")  # siempre distinta de la original
    assert ver_como_info(_pedido(**{COOKIE_NAME: make_token(1), VER_COMO_COOKIE: tocada})) is None
    assert ver_como_info(_pedido(**{COOKIE_NAME: make_token(1), VER_COMO_COOKIE: make_token(1)})) is None
    # vence a los 30 minutos
    ahora = time.time()
    monkeypatch.setattr(core_auth.time, "time", lambda: ahora + 31 * 60)
    assert ver_como_info(_pedido(**{COOKIE_NAME: make_token(1), VER_COMO_COOKIE: vista})) is None


def test_solo_la_cuenta_administradora_abre_la_vista_y_queda_registrado(entorno):
    db, app = entorno
    r = _cliente(app, sesion=1).post("/api/admin/ver-como", json={"usuario_id": 2})
    assert r.status_code == 200 and r.json()["usuario"]["grupo"] == COM2
    assert VER_COMO_COOKIE in r.headers.get("set-cookie", "")
    marca = db.scalars(select(models.ActivityEvent).where(models.ActivityEvent.accion == "ver_como_inicio")).all()
    assert len(marca) == 1 and marca[0].usuario_id == 1
    assert _cliente(app, sesion=2).post("/api/admin/ver-como", json={"usuario_id": 4}).status_code == 403
    assert _cliente(app, sesion=1).post("/api/admin/ver-como", json={"usuario_id": 3}).status_code == 400
    assert _cliente(app, sesion=1).post("/api/admin/ver-como", json={"usuario_id": 99}).status_code == 404


def test_con_la_vista_la_cuenta_administradora_ve_como_el_participante(entorno):
    _, app = entorno
    c = _cliente(app, sesion=1, vista=(1, 2))
    assert c.get("/api/me").json()["email"] == "alumna@t"
    estado = c.get("/api/admin/ver-como").json()
    assert estado["activo"] is True and estado["valida"] is True
    assert estado["usuario"]["id"] == 2 and estado["usuario"]["grupo"] == COM2
    assert abs(estado["vence_en"] - (time.time() + 30 * 60) * 1000) < 60_000
    assert _cliente(app, sesion=1).get("/api/me").json()["email"] == "admin@t"
    assert _cliente(app, sesion=1).get("/api/admin/ver-como").json() == {"activo": False}


def test_la_vista_no_sirve_con_otra_sesion_ni_para_mirar_como_otra_cuenta_administradora(entorno):
    _, app = entorno
    # la cookie de una vista no le sirve a la sesión de otra cuenta: la alumna sigue viéndose a sí misma
    robada = _cliente(app, sesion=2, vista=(1, 4))
    assert robada.get("/api/me").json()["email"] == "alumna@t"
    assert robada.get("/api/admin/ver-como").json() == {"activo": False}
    # una vista firmada a nombre de una cuenta que no es administradora tampoco cambia a quién se ve
    assert _cliente(app, sesion=2, vista=(2, 4)).get("/api/me").json()["email"] == "alumna@t"
    # nunca como otra cuenta administradora; el aviso dice que la vista ya no es válida
    otra = _cliente(app, sesion=1, vista=(1, 3))
    assert otra.get("/api/me").json()["email"] == "admin@t"
    estado = otra.get("/api/admin/ver-como").json()
    assert estado["activo"] is True and estado["valida"] is False and estado["usuario"] is None


def test_entrar_de_nuevo_borra_una_vista_vieja(entorno):
    _, app = entorno
    c = TestClient(app, base_url="https://testserver")
    r = c.post("/login", data={"email": "admin@t", "password": "clave-admin"}, follow_redirects=False)
    assert r.status_code == 303
    assert any(h.startswith(f"{VER_COMO_COOKIE}=") for h in r.headers.get_list("set-cookie"))


def test_el_servidor_frena_toda_escritura_durante_la_vista_salvo_salir(monkeypatch):
    monkeypatch.setattr(core_auth, "active_token", lambda token: True)
    c = _cliente(aplicacion, sesion=1, vista=(1, 2))
    for metodo, ruta in (("post", "/api/proyectos-ia/mio/mensajes"), ("patch", "/api/monitoreo/registros/1"),
                         ("delete", "/api/proyectos-ia/1"), ("put", "/api/me/password"), ("post", "/api/admin/ver-como")):
        r = getattr(c, metodo)(ruta)
        assert r.status_code == 403 and r.json()["detail"] == VER_COMO_SOLO_LECTURA, (metodo, ruta)
    r = c.post("/api/admin/ver-como/salir")
    assert r.status_code == 200 and VER_COMO_COOKIE in r.headers.get("set-cookie", "")


def test_si_la_vista_vencio_la_escritura_marcada_por_la_pantalla_no_se_guarda(monkeypatch):
    monkeypatch.setattr(core_auth, "active_token", lambda token: True)
    c = _cliente(aplicacion, sesion=1)  # la cookie de la vista ya no está: venció
    r = c.post("/api/proyectos-ia/mio/mensajes", headers={"X-Ver-Como": "1"})
    assert r.status_code == 403 and r.json()["detail"] == VER_COMO_VENCIDA
    assert c.post("/api/admin/ver-como/salir", headers={"X-Ver-Como": "1"}).status_code == 200


def test_abrir_mi_proyecto_en_la_vista_no_deja_rastro_en_la_base(app_real, motor):
    r = _cliente(app_real, sesion=1, vista=(1, 2)).get("/api/proyectos-ia/mio")
    assert r.status_code == 200 and r.json().get("id")  # la pantalla ve el proyecto que vería la alumna
    with Session(motor) as db:
        assert db.scalar(select(func.count(models.ProyectoIA.id))) == 0
        assert db.scalar(select(func.count(models.ActivityEvent.id)).where(models.ActivityEvent.usuario_id == 2)) == 0
    # sin la vista, abrir «Mi proyecto» sí crea el proyecto: la prueba de arriba mide algo
    assert _cliente(app_real, sesion=2).get("/api/proyectos-ia/mio").status_code == 200
    with Session(motor) as db:
        assert db.scalar(select(func.count(models.ProyectoIA.id))) == 1


def test_salir_de_la_sesion_durante_la_vista_revoca_el_token(app_real, motor):
    r = _cliente(app_real, sesion=1, vista=(1, 2)).get("/logout", follow_redirects=False)
    assert r.status_code == 303
    with Session(motor) as db:
        assert db.get(models.Usuario, 1).sesiones_desde is not None


def test_get_db_no_guarda_nada_durante_la_vista(motor, monkeypatch):
    monkeypatch.setattr(database, "SessionLocal", sessionmaker(bind=motor, autoflush=False))

    def usar(vista, email):
        gen = database.get_db(SimpleNamespace(state=SimpleNamespace(ver_como=vista)))
        db = next(gen)
        db.add(models.Usuario(email=email, nombre="x", password_hash="x", rol="analista"))
        db.commit()  # como haría una pantalla al abrirse
        assert db.scalar(select(func.count(models.Usuario.id))) == 1  # dentro del pedido se ve
        gen.close()

    usar((1, 2), "vista@t")
    with Session(motor) as db:
        assert db.scalar(select(func.count(models.Usuario.id))) == 0
    usar(None, "normal@t")
    with Session(motor) as db:
        assert db.scalar(select(func.count(models.Usuario.id))) == 1


def test_la_pantalla_tiene_el_aviso_el_boton_y_los_archivos_se_renuevan():
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    for frase in ("function cargarVerComo", "Sólo lectura: nada de lo que hagas se guarda.", "btn-ver-como",
                  "Ver como esta persona", "async function salirVerComo", '"X-Ver-Como": "1"'):
        assert frase in js, frase
    assert "#\\/ver-como\\/" not in js  # la vista no se abre sola desde un enlace
    index = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "app.js?v=20261108-aviso-alumno" in index and "styles.css?v=20261113-g4a-logo" in index
    css = (STATIC / "styles.css").read_text(encoding="utf-8")
    assert ".ver-como-aviso" in css and "body.ver-como nav.top-nav" in css
