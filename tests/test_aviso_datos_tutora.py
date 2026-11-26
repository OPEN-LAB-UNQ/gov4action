"""Aviso de datos personales antes de enviar a la tutora, y quién redacta la devolución (25/11/2026)."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
STATIC = RAIZ / "static"
APP = (STATIC / "app.js").read_text(encoding="utf-8")
BLOQUE = APP[APP.index("function cuitConDigitoValido("):APP.index("function confirmarEnvioConDatosPersonales(")]


def _detectar(textos):
    guion = BLOQUE + "\nprocess.stdout.write(JSON.stringify(JSON.parse(process.argv[1]).map(datosPersonalesEnTexto)));"
    salida = subprocess.run([shutil.which("node"), "-e", guion, json.dumps(textos)], capture_output=True, text=True, check=True)
    return json.loads(salida.stdout)


@pytest.mark.parametrize("texto,tipo", [
    ("El CUIL es 20-12345678-6", "CUIT"), ("cuit 20123456786", "CUIT"), ("figura 20123456786 en la base", "CUIT"),
    ("DNI 30.123.456", "documento"), ("documento nro 30123456", "documento"),
    ("escribime a persona@ejemplo.gob.ar", "correo"), ("tel: 11 4555 1234", "teléfono"), ("llamar al 11-4555-1234", "teléfono"),
])
def test_detecta_datos_personales(texto, tipo):
    assert any(tipo in x for x in _detectar([texto])[0]), texto


@pytest.mark.parametrize("texto", [
    "El crédito vigente es $ 1.500.000 y el devengado 30.123.456", "Programa 16-001-0001, ejercicio 2019-2020",
    "Son 20123456789 pesos acumulados", "Verificar 60 participantes por curso", "Ley 24.156 y resolución 25/95",
    "El documento tiene 12 páginas", "", "Cruzar comprobantes de devengado y pagado",
])
def test_no_avisa_con_cifras_ni_textos_comunes(texto):
    assert _detectar([texto])[0] == [], texto


def test_se_revisa_antes_de_llamar_a_la_tutora():
    envio = APP[APP.index("async function enviarMensajeProyectoIA("):APP.index("async function consultarDocenteProyectoIA(")]
    assert envio.index("confirmarEnvioConDatosPersonales(") < envio.index('"/proyectos-ia/mio/mensajes"')
    assert "state.proyectoIA?.entrega_final" in envio
    consulta = APP[APP.index("async function consultarDocenteProyectoIA("):APP.index("const MAX_ENTREGA_CHARS")]
    assert "confirmarEnvioConDatosPersonales" not in consulta  # la consulta al docente no pasa por la tutora (el aviso cubre sólo la tutoría)


def test_los_textos_dicen_que_la_devolucion_se_redacta_con_ia_y_la_revisa_una_persona():
    for nombre in ("privacidad-body.html", "presentacion.html", "portal/incubadora.html"):
        html = (STATIC / nombre).read_text(encoding="utf-8")
        assert "con asistencia de IA y la revisa una persona" in html, nombre
        assert "escribe una persona del equipo docente" not in html and "escribe la devolución final" not in html, nombre


def test_la_privacidad_nombra_al_asistente_que_ayuda_a_redactar():
    html = (STATIC / "privacidad-body.html").read_text(encoding="utf-8")
    assert "Claude, de Anthropic" in html and "devoluciones docentes y las respuestas a las consultas" in html
    assert "una persona revisa cada texto antes de publicarlo" in html
