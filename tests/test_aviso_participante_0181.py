"""0.10.81: aviso por correo al participante cuando el equipo docente le escribe en su proyecto."""
from pathlib import Path

import models
from core.auth import get_current_user
from services import aviso_docente
from tests.test_aviso_docente import TITULO, _SMTPFalso, entorno  # noqa: F401 (el fixture se usa por nombre)

TEXTO_DOCENTE = "Revisá el indicador 3: los legajos 4521 no se pueden usar con datos reales."
STATIC = Path(__file__).resolve().parents[1] / "static"


def _como_docente(client, db):
    client.app.dependency_overrides[get_current_user] = lambda: db.get(models.Usuario, 9)


def _avisos(db):
    return db.query(models.ActivityEvent).filter_by(accion=aviso_docente.ACCION_AVISO_PARTICIPANTE).all()


def test_el_mensaje_docente_avisa_por_correo_a_quien_lo_abrio(entorno):  # noqa: F811
    client, db, _ = entorno
    _como_docente(client, db)
    r = client.post("/proyectos-ia/7/docente", json={"mensaje": TEXTO_DOCENTE})
    assert r.status_code == 200 and r.json()["aviso"] is True and r.json()["avisos"] == 1
    assert len(_SMTPFalso.enviados) == 1
    msg = _SMTPFalso.enviados[0]
    assert msg["To"] == "alumna@prueba.test" and msg["Subject"] == "Gov4Action · Tenés un mensaje del equipo docente"
    cuerpo = msg.get_content()
    assert TITULO in cuerpo and "https://gobernanza.prueba.test/?ir=proyecto" in cuerpo
    for prohibido in ("indicador 3", "legajos", "4521", "datos reales"):
        assert prohibido not in msg.as_string() + cuerpo  # el texto del mensaje no viaja en el correo
    db.expire_all()
    evento = _avisos(db)[0]
    assert evento.metadata_evento["estado"] == "enviada" and evento.metadata_evento["destinatarios"] == 1
    assert "alumna@prueba.test" not in str(evento.metadata_evento)  # la bitácora no guarda direcciones


def test_el_docente_puede_no_avisar(entorno):  # noqa: F811
    client, db, _ = entorno
    _como_docente(client, db)
    r = client.post("/proyectos-ia/7/docente", json={"mensaje": TEXTO_DOCENTE, "avisar": False})
    assert r.status_code == 200 and r.json()["aviso"] is False and r.json()["avisos"] == 0
    assert _SMTPFalso.enviados == [] and _avisos(db) == []


def test_un_mensaje_un_aviso_y_la_consulta_del_alumno_no_avisa_al_alumno(entorno):  # noqa: F811
    client, db, engine = entorno
    client.post("/proyectos-ia/mio/docente", json={"mensaje": "Una consulta"})  # la alumna consulta: avisa al docente
    assert [m["To"] for m in _SMTPFalso.enviados] == ["docente@prueba.test"]
    _como_docente(client, db)
    client.post("/proyectos-ia/7/docente", json={"mensaje": TEXTO_DOCENTE})
    mensaje = db.query(models.MensajeProyectoIA).filter_by(remitente="docente").one()
    assert aviso_docente.avisar_mensaje_docente(engine, mensaje.id) == "duplicado"
    assert len(_SMTPFalso.enviados) == 2


def test_el_equipo_recibe_un_correo_por_persona_y_nunca_la_administracion(entorno, monkeypatch):  # noqa: F811
    from config import settings

    monkeypatch.setattr(settings, "usuarios_excluidos_metricas", "prueba@prueba.test")
    client, db, _ = entorno
    db.add_all([
        models.Usuario(id=2, email="companera@prueba.test", nombre="Compañera", password_hash="x", rol="analista"),
        models.Usuario(id=3, email="baja@prueba.test", nombre="De baja", password_hash="x", rol="analista", activo=False),
        models.Usuario(id=4, email="Prueba@Prueba.test", nombre="Cuenta de prueba", password_hash="x", rol="analista"),
        models.Usuario(id=5, email="mal escrito@prueba.test", nombre="Con espacio", password_hash="x", rol="analista"),
    ])
    db.add_all([models.IntegranteProyectoIA(proyecto_id=7, usuario_id=uid) for uid in (2, 3, 4, 5, 9)])  # 9 es la administración
    db.commit()
    _como_docente(client, db)
    client.post("/proyectos-ia/7/docente", json={"mensaje": TEXTO_DOCENTE})
    assert sorted(m["To"] for m in _SMTPFalso.enviados) == ["alumna@prueba.test", "companera@prueba.test"]


def test_el_mensaje_se_guarda_aunque_falle_el_correo(entorno):  # noqa: F811
    client, db, _ = entorno
    _SMTPFalso.falla = True
    _como_docente(client, db)
    assert client.post("/proyectos-ia/7/docente", json={"mensaje": TEXTO_DOCENTE}).status_code == 200
    db.expire_all()
    assert db.query(models.MensajeProyectoIA).filter_by(remitente="docente").count() == 1
    assert _avisos(db)[0].metadata_evento["estado"] == "error"


def test_la_pantalla_del_docente_tiene_la_casilla_y_la_privacidad_lo_dice():
    indice = (STATIC / "index.html").read_text(encoding="utf-8")
    assert 'id="proyecto-docente-avisar" type="checkbox" checked' in indice
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert 'const casilla = document.getElementById("proyecto-docente-avisar");' in js
    assert "const avisar = casilla?.checked !== false;" in js and "if (casilla) casilla.checked = true;" in js
    assert "no hay a quién avisar por correo" in js and "Avisar por correo a quienes integran el proyecto" in indice
    assert "JSON.stringify({ mensaje, avisar })" in js
    privacidad = (STATIC / "privacidad-body.html").read_text(encoding="utf-8")
    assert "avisarte que el equipo docente te escribió en tu proyecto" in privacidad


def test_sin_titulo_el_aviso_dice_tu_proyecto_de_la_incubadora(entorno):  # noqa: F811
    client, db, _ = entorno
    db.get(models.ProyectoIA, 7).titulo = None
    db.commit()
    _como_docente(client, db)
    client.post("/proyectos-ia/7/docente", json={"mensaje": TEXTO_DOCENTE})
    cuerpo = _SMTPFalso.enviados[0].get_content()
    assert "en tu proyecto de la Incubadora." in cuerpo and "#7" not in cuerpo


def test_un_rechazo_queda_como_parcial_y_sin_direcciones(entorno, monkeypatch):  # noqa: F811
    import smtplib

    from services import notificaciones

    class _Rechaza(_SMTPFalso):
        def send_message(self, msg):
            if msg["To"].startswith("rechazo"):
                raise smtplib.SMTPRecipientsRefused({msg["To"]: (550, b"no existe")})
            super().send_message(msg)

    monkeypatch.setattr(notificaciones.smtplib, "SMTP", _Rechaza)
    client, db, _ = entorno
    db.add(models.Usuario(id=2, email="rechazo@prueba.test", nombre="Rechazo", password_hash="x", rol="analista"))
    db.add(models.IntegranteProyectoIA(proyecto_id=7, usuario_id=2))
    db.commit()
    _como_docente(client, db)
    client.post("/proyectos-ia/7/docente", json={"mensaje": TEXTO_DOCENTE})
    assert [m["To"] for m in _SMTPFalso.enviados] == ["alumna@prueba.test"]
    db.expire_all()
    evento = _avisos(db)[0].metadata_evento
    assert evento["estado"] == "parcial" and evento["destinatarios"] == 2
    assert "rechazo@prueba.test" not in str(evento) and "[dirección]" in evento["error"]
