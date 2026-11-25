"""0.10.77: Monitoreo tiene su propia pantalla. Antes era una tarjeta dentro de «Mi proyecto → Herramientas opcionales»
y el botón de Inicio llevaba a la Incubadora."""
import re
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from test_calibracion_registro import entorno  # noqa: F401  (fixture reutilizada)
from test_ver_como_0174 import _cliente, app_real, motor  # noqa: F401  (fixtures reutilizadas)

import models
from routers import monitoreo, proyectos_ia
from services import prototipos_incubadora as pi

STATIC = Path(__file__).resolve().parent.parent / "static"
COM2 = "Grupo A · comisión 2"


@pytest.fixture
def cuentas(entorno, monkeypatch):  # noqa: F811
    db, _ = entorno
    db.add_all([
        models.Usuario(id=3, email="alumna@test", nombre="Alumna", password_hash="x", rol="analista", grupo=COM2),
        models.Usuario(id=4, email="sinproyecto@test", nombre="Sin", password_hash="x", rol="analista", grupo=COM2),
        models.Usuario(id=5, email="equipo@test", nombre="Equipo", password_hash="x", rol="analista", grupo=COM2),
        models.Usuario(id=6, email="comision1@test", nombre="Uno", password_hash="x", rol="analista"),
        models.Usuario(id=7, email="cartera@test", nombre="Cartera", password_hash="x", rol="analista"),
    ])
    db.flush()
    db.add_all([models.ProyectoIA(id=66, usuario_id=3, titulo="Boletín", situacion="Queremos medir el tiempo de lectura."),
                models.ProyectoIA(id=67, usuario_id=7, titulo="En cartera", situacion="Vamos a medir el tiempo.")])
    db.flush()
    db.add(models.IntegranteProyectoIA(proyecto_id=66, usuario_id=5))
    db.commit()
    monkeypatch.setattr(pi, "_fichas", lambda: {})
    return db


def _u(db, ident):
    return db.get(models.Usuario, ident)


def test_trae_el_monitoreo_del_proyecto_propio(cuentas):
    datos = monitoreo.mi_monitoreo(cuentas, _u(cuentas, 3))
    assert datos["proyecto_id"] == 66 and datos["modo"] == "prueba" and datos["puede_registrar"] is True
    assert datos == monitoreo.listar_monitoreo(66, cuentas, _u(cuentas, 3))


def test_quien_integra_un_equipo_ve_el_monitoreo_de_ese_proyecto(cuentas):
    datos = monitoreo.mi_monitoreo(cuentas, _u(cuentas, 5))
    assert datos["proyecto_id"] == 66 and datos["puede_registrar"] is True


def test_en_cartera_con_proyecto_es_de_solo_lectura_y_sin_bloque_propio(cuentas):
    datos = monitoreo.mi_monitoreo(cuentas, _u(cuentas, 7))
    assert datos["proyecto_id"] == 67 and datos["modo"] == "cartera" and datos["puede_registrar"] is False
    assert datos["en_accion"] is None and datos["indicadores_registrados"] == []


@pytest.mark.parametrize("ident, modo", [(4, "prueba"), (6, "cartera")])
def test_sin_proyecto_no_lo_crea_y_avisa_el_modo_del_grupo(cuentas, ident, modo):
    antes = cuentas.query(models.ProyectoIA).count()
    datos = monitoreo.mi_monitoreo(cuentas, _u(cuentas, ident))
    assert datos["proyecto_id"] is None and datos["modo"] == modo and datos["puede_registrar"] is False
    assert datos["alcance"] == monitoreo.ALCANCE[modo]
    assert cuentas.query(models.ProyectoIA).count() == antes  # la pantalla sólo lee


def test_la_ruta_esta_registrada_como_get():
    rutas = {(r.path, tuple(sorted(r.methods))) for r in monitoreo.router.routes}
    assert ("/api/monitoreo/mio", ("GET",)) in rutas


def test_sin_sesion_pide_ingresar(app_real):  # noqa: F811
    assert _cliente(app_real).get("/api/monitoreo/mio").status_code == 401


def test_con_ver_como_trae_el_de_la_alumna_y_no_guarda_nada(app_real, motor):  # noqa: F811
    with Session(motor) as db:
        db.add(models.ProyectoIA(id=66, usuario_id=2, titulo="Boletín", situacion="Queremos medir el tiempo."))
        db.commit()
    r = _cliente(app_real, sesion=1, vista=(1, 2)).get("/api/monitoreo/mio")
    assert r.status_code == 200 and r.json()["proyecto_id"] == 66 and r.json()["modo"] == "prueba"
    r = _cliente(app_real, sesion=1, vista=(1, 4)).get("/api/monitoreo/mio")  # el alumno no tiene proyecto
    assert r.status_code == 200 and r.json()["proyecto_id"] is None
    with Session(motor) as db:
        assert db.scalar(select(func.count(models.ProyectoIA.id))) == 1
        assert db.scalar(select(func.count(models.RegistroMonitoreo.id))) == 0
        assert db.scalar(select(func.count(models.ActivityEvent.id)).where(models.ActivityEvent.usuario_id.in_([2, 4]))) == 0


def test_el_recorrido_sin_proyecto_ya_no_dice_que_monitoreo_se_usa_desde_el_proyecto(cuentas):
    rec = proyectos_ia.mi_recorrido(_u(cuentas, 4), cuentas)
    assert "Incubadora" in rec["monitoreo"]["detalle"] and "desde tu proyecto" not in rec["monitoreo"]["detalle"]


def _html():
    return (STATIC / "index.html").read_text(encoding="utf-8")


def _seccion(html, ident):
    desde = html.index(f'<section id="{ident}"')
    return html[desde:html.index("<!-- VISTA:", desde)]


def test_la_tarjeta_vive_en_su_pantalla_y_en_mi_proyecto_queda_el_enlace():
    html = _html()
    pantalla = _seccion(html, "view-monitoreo")
    assert 'id="proyecto-monitoreo-card"' in pantalla and 'id="form-monitoreo"' in pantalla
    assert 'id="monitoreo-vista-aviso"' in pantalla and 'id="monitoreo-vista-cuerpo"' in pantalla
    incubadora = _seccion(html, "view-proyecto-ia")
    assert 'id="proyecto-monitoreo-card"' not in incubadora
    assert re.search(r'id="proyecto-monitoreo-enlace"[\s\S]*?data-nav-target="monitoreo">Ir a\s+Monitoreo<', incubadora)


def test_el_boton_del_recorrido_4_va_a_monitoreo_y_no_a_la_incubadora():
    html = _html()
    tarjeta = html[html.index('course-entry-card-monitoring">'):]
    tarjeta = tarjeta[:tarjeta.index("</article>")]
    assert 'data-nav-target="monitoreo">Ir a Monitoreo</button>' in tarjeta
    assert 'data-nav-target="proyecto-ia"' not in tarjeta and "Ir a mi proyecto" not in html


def test_la_pantalla_dice_lo_que_corresponde_a_cada_grupo():
    import main
    comision2 = _seccion(main.index_para(models.Usuario(rol="analista", grupo=COM2)), "view-monitoreo")
    comision1 = _seccion(main.index_para(models.Usuario(rol="analista")), "view-monitoreo")
    grupo_b = _seccion(main.index_para(models.Usuario(rol="analista", grupo="Grupo B")), "view-monitoreo")
    otro = _seccion(main.index_para(models.Usuario(rol="analista", grupo="Grupo de prueba")), "view-monitoreo")
    # 0.10.80: Grupo B usa el modo prueba, como la comisión 2; los textos no suponen un prototipo.
    for prueba in (comision2, grupo_b):
        assert "Registrá lo que aprendés al probar tu proyecto" in prueba and "en cartera" not in prueba
        assert "probar tu prototipo" not in prueba and "ganador" not in prueba
    assert "proyecto ganador del piloto" in comision1 and "probar tu proyecto" not in comision1
    assert "no hay una implementación habilitada para tu grupo" not in comision1
    # Un grupo sin modo prueba ni proyecto ganador propio (0.10.62) lee un texto neutro.
    assert "ganador" not in otro and "no hay una implementación habilitada para tu grupo" in otro
    enlace = _seccion(main.index_para(models.Usuario(rol="analista", grupo="Grupo B")), "view-proyecto-ia")
    enlace = enlace[enlace.index('id="proyecto-monitoreo-enlace"'):]
    assert "ganador" not in enlace[:enlace.index("</details>")]


def test_la_marca_de_cache_cambio():
    html = _html()
    assert "app.js?v=20261124-prototipos-grupo_b" in html and "styles.css?v=20261113-g4a-logo" in html
