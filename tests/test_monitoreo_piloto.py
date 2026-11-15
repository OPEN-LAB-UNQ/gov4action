"""Monitoreo: el piloto real y, desde la 0.10.72, el modo prueba para los demás proyectos."""
import pytest
from fastapi import HTTPException
from test_calibracion_registro import entorno  # noqa: F401  (fixture reutilizada)

import models
from routers import monitoreo


@pytest.fixture
def piloto(entorno, monkeypatch):  # noqa: F811
    db, _ = entorno
    for ident in (2, 3, 4, 5):
        # La 3 es de un grupo con modo prueba (la comisión 2); la 2 (dueña del piloto), la 4 y la 5 son del grupo por defecto.
        grupo = "Grupo A · comisión 2" if ident == 3 else None
        db.add(models.Usuario(id=ident, email=f"persona{ident}@test", nombre="Persona", password_hash="x", rol="analista", grupo=grupo))
    db.flush()
    ganador = models.ProyectoIA(usuario_id=2, titulo="Piloto confirmado")
    cartera = models.ProyectoIA(usuario_id=3, titulo="En cartera")
    db.add_all([ganador, cartera])
    db.flush()
    registro = models.RegistroMonitoreo(proyecto_id=cartera.id, usuario_id=3, tipo="avance", titulo="Historial",
                                        contenido="Contenido anterior", estado="abierto")
    db.add(registro)
    db.commit()
    monkeypatch.setattr(monitoreo.settings, "monitoreo_proyecto_id", ganador.id)
    return db, ganador, cartera, registro


def test_cartera_registra_en_modo_prueba_y_el_historial_queda_de_solo_lectura(piloto):
    db, ganador, cartera, registro = piloto
    usuario = db.get(models.Usuario, 3)
    historial = monitoreo.listar_monitoreo(cartera.id, db, usuario)
    assert historial["habilitado"] is False and historial["modo"] == "prueba" and historial["puede_registrar"] is True
    assert "Modo prueba" in historial["alcance"] and "piloto chico, reversible y autorizado" in historial["alcance"]
    assert historial["registros"][0]["etapa"] == "anterior"  # sin etapa: anterior a la 0.10.72
    with pytest.raises(HTTPException) as e:
        monitoreo.actualizar_estado_monitoreo(registro.id, {"estado": "resuelto"}, db, usuario)
    assert e.value.status_code == 403
    db.refresh(registro)
    assert registro.estado == "abierto"
    resultado = monitoreo.registrar_monitoreo(
        cartera.id, {"tipo": "aprendizaje", "titulo": "Con el prototipo", "contenido": "La regla marcó bien"}, db, usuario)
    nuevo = resultado["registros"][0]
    assert nuevo["etapa"] == "prueba" and nuevo["metadata"]["etapa"] == "prueba"
    assert monitoreo.actualizar_estado_monitoreo(nuevo["id"], {"estado": "resuelto"}, db, usuario)["estado"] == "resuelto"


@pytest.mark.parametrize("usuario_id", [1, 2])
def test_ganador_registra_en_el_piloto_y_cierra_con_traza(piloto, usuario_id):
    db, ganador, cartera, registro = piloto
    usuario = db.get(models.Usuario, usuario_id)
    resultado = monitoreo.registrar_monitoreo(ganador.id, {"tipo": "avance", "titulo": "Prueba", "contenido": "Avance comprobado"}, db, usuario)
    assert resultado["habilitado"] is True and resultado["modo"] == "piloto"
    nuevo = resultado["registros"][0]
    assert nuevo["etapa"] == "piloto"
    cerrado = monitoreo.actualizar_estado_monitoreo(nuevo["id"], {"estado": "resuelto"}, db, usuario)
    assert cerrado["estado"] == "resuelto"
    assert cerrado["metadata"]["cambios_estado"][0]["usuario_id"] == usuario_id


def test_ser_ganador_no_permite_acceso_a_otra_persona(piloto):
    db, ganador, cartera, registro = piloto
    otro = db.get(models.Usuario, 3)
    with pytest.raises(HTTPException) as e:
        monitoreo.listar_monitoreo(ganador.id, db, otro)
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:
        monitoreo.registrar_monitoreo(ganador.id, {}, db, otro)
    assert e.value.status_code == 403


def test_integrante_del_equipo_entra_al_monitoreo(piloto):
    db, ganador, cartera, registro = piloto
    db.add(models.IntegranteProyectoIA(proyecto_id=ganador.id, usuario_id=4))
    db.commit()
    integrante = db.get(models.Usuario, 4)
    assert monitoreo.listar_monitoreo(ganador.id, db, integrante)["modo"] == "piloto"
    resultado = monitoreo.registrar_monitoreo(ganador.id, {"tipo": "riesgo", "titulo": "Riesgo", "contenido": "Hay que mirarlo"}, db, integrante)
    assert resultado["registros"][0]["usuario_id"] == 4


def test_sin_piloto_la_comision_2_sigue_en_modo_prueba_y_los_demas_en_cartera(piloto, monkeypatch):
    db, ganador, cartera, registro = piloto
    monkeypatch.setattr(monitoreo.settings, "monitoreo_proyecto_id", None)
    duena = db.get(models.Usuario, 2)
    datos = monitoreo.listar_monitoreo(ganador.id, db, duena)
    assert datos["habilitado"] is False and datos["modo"] == "cartera" and datos["puede_registrar"] is False
    with pytest.raises(HTTPException) as e:
        monitoreo.registrar_monitoreo(ganador.id, {"tipo": "avance", "titulo": "T", "contenido": "C"}, db, duena)
    assert e.value.status_code == 403
    assert monitoreo.listar_monitoreo(cartera.id, db, db.get(models.Usuario, 3))["modo"] == "prueba"


def test_un_proyecto_de_la_comision_1_queda_en_cartera_como_antes(piloto):
    db, ganador, cartera, registro = piloto
    otro = models.ProyectoIA(usuario_id=5, titulo="Comisión 1")
    db.add(otro)
    db.commit()
    duena = db.get(models.Usuario, 5)
    datos = monitoreo.listar_monitoreo(otro.id, db, duena)
    assert datos["modo"] == "cartera" and datos["puede_registrar"] is False and "En cartera" in datos["alcance"]
    with pytest.raises(HTTPException) as e:
        monitoreo.registrar_monitoreo(otro.id, {"tipo": "avance", "titulo": "T", "contenido": "C"}, db, duena)
    assert e.value.status_code == 403 and "en cartera" in e.value.detail


def test_en_modo_prueba_el_docente_lee_y_no_escribe(piloto):
    db, ganador, cartera, registro = piloto
    admin = db.get(models.Usuario, 1)
    datos = monitoreo.listar_monitoreo(cartera.id, db, admin)
    assert datos["modo"] == "prueba" and datos["puede_registrar"] is False
    with pytest.raises(HTTPException) as e:
        monitoreo.registrar_monitoreo(cartera.id, {"tipo": "avance", "titulo": "T", "contenido": "C"}, db, admin)
    assert e.value.status_code == 403


def test_nadie_ajeno_cambia_el_estado_de_un_registro(piloto):
    db, ganador, cartera, registro = piloto
    nuevo = monitoreo.registrar_monitoreo(cartera.id, {"tipo": "avance", "titulo": "T", "contenido": "C"}, db,
                                          db.get(models.Usuario, 3))["registros"][0]
    with pytest.raises(HTTPException) as e:
        monitoreo.actualizar_estado_monitoreo(nuevo["id"], {"estado": "resuelto"}, db, db.get(models.Usuario, 2))
    assert e.value.status_code == 403


def test_si_el_proyecto_pasa_a_piloto_su_prueba_queda_de_solo_lectura(piloto, monkeypatch):
    db, ganador, cartera, registro = piloto
    duena = db.get(models.Usuario, 3)
    nuevo = monitoreo.registrar_monitoreo(cartera.id, {"tipo": "avance", "titulo": "T", "contenido": "C"}, db, duena)["registros"][0]
    monkeypatch.setattr(monitoreo.settings, "monitoreo_proyecto_id", cartera.id)
    assert monitoreo.listar_monitoreo(cartera.id, db, duena)["modo"] == "piloto"
    with pytest.raises(HTTPException) as e:
        monitoreo.actualizar_estado_monitoreo(nuevo["id"], {"estado": "resuelto"}, db, duena)
    assert e.value.status_code == 403
    with pytest.raises(HTTPException) as e:  # el registro anterior tampoco revive al pasar a piloto
        monitoreo.actualizar_estado_monitoreo(registro.id, {"estado": "resuelto"}, db, duena)
    assert e.value.status_code == 403


def test_proyecto_de_seguimiento_propio_registra_como_piloto_sin_ser_el_ganador(piloto, monkeypatch):
    db, ganador, cartera, registro = piloto
    admin = models.Usuario(id=9, email="admin9@test", nombre="Admin", password_hash="x", rol="admin")
    db.add(admin)
    db.flush()
    propio = models.ProyectoIA(usuario_id=9, titulo="Gov4Action Multilente")
    db.add(propio)
    db.commit()
    antes = monitoreo.listar_monitoreo(propio.id, db, admin)
    assert antes["habilitado"] is False and antes["modo"] == "cartera" and antes["puede_registrar"] is False
    monkeypatch.setattr(monitoreo.settings, "monitoreo_proyectos_propios", f"{propio.id}, x,")
    resultado = monitoreo.registrar_monitoreo(propio.id, {"tipo": "indicador", "titulo": "Pruebas", "contenido": "Fuente: validación del 14/11",
                                                          "valor_indicador": 2819}, db, admin)
    assert resultado["habilitado"] is True and resultado["modo"] == "piloto" and resultado["propio"] is True
    assert "Seguimiento propio" in resultado["alcance"] and "ganador" in resultado["alcance"]
    assert resultado["registros"][0]["etapa"] == "piloto" and resultado["indicadores_registrados"][0]["valor"] == 2819
    # el piloto sigue siendo el de siempre: el proyecto propio no pasa a ser «ganador» y el otro no se vuelve propio
    assert monitoreo.listar_monitoreo(ganador.id, db, admin)["propio"] is False
    assert monitoreo.proyectos_propios() == {propio.id}
