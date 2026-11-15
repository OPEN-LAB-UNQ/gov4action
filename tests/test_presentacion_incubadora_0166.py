"""0.10.66: la presentación muestra los ejes y el nombre es el mismo en
cada superficie pública; «Gov4Action Multilente» sigue nombrando la revisión de informes.
Desde 0.10.78 son cuatro ejes y el nombre los nombra a los cuatro (ver test_cuatro_ejes_0178.py)."""
from pathlib import Path

from fastapi.testclient import TestClient

from core.auth import login_html
from main import LANDING_NAV, app

NOMBRE = "Gov4Action: Multilente, Incubadora, Conexiones y Monitoreo"
STATIC = Path(__file__).resolve().parents[1] / "static"
client = TestClient(app)


def test_presentacion_muestra_los_dos_ejes_y_la_incubadora():
    html = client.get("/presentacion").text
    assert f"<span>{NOMBRE}</span>" in html
    assert f"<strong>{NOMBRE}</strong> · Concreta. Honesta. Humana." in html  # el pie, igual que el encabezado
    assert html.index('id="video"') < html.index('id="ejes"') < html.index('id="sintesis"')  # video primero (0.10.41.7)
    assert html.index('id="probalo"') < html.index('id="incubadora"') < html.index('id="conexiones"') \
        < html.index('id="monitoreo"') < html.index('id="prototipos"') < html.index('id="uso"')
    assert 'href="#ejes"' in LANDING_NAV and LANDING_NAV.index("#ejes") < LANDING_NAV.index("#criterio")
    for criterio in ("problema", "usuarios", "evidencia", "datos", "flujo actual", "rol de la IA", "supervisión",
                     "riesgos", "indicador", "próximo paso"):
        assert criterio in html, criterio
    seccion = html[html.index('id="incubadora"'):html.index('id="conexiones"')]
    for texto in ("un segundo modelo verifica cada cita", "la IA nunca emite un sello",
                  "no recibe archivos", "La tutoría usa OpenAI", "/privacidad#proveedores"):
        assert texto in seccion, texto
    # 0.10.78: la galería y la votación por grupo se cuentan en Conexiones, donde están en la aplicación.
    assert "su propia votación" in html[html.index('id="conexiones"'):html.index('id="monitoreo"')]
    assert "¿Tiene informes cerrados" not in html and "¿Tenés informes cerrados" in html


def test_el_nombre_es_el_mismo_en_acceso_aplicacion_privacidad_y_api():
    acceso = login_html()
    assert f"<title>{NOMBRE} · acceso</title>" in acceso and '<h1>Gov<span class="brand-four">4</span>Action</h1>' in acceso
    assert "Conocer Gov4Action y sus cuatro ejes" in acceso
    indice = (STATIC / "index.html").read_text(encoding="utf-8")
    assert f"<title>{NOMBRE}</title>" in indice and '<h1>Gov<span class="brand-four">4</span>Action</h1>' in indice
    privacidad = client.get("/privacidad").text
    assert f"{NOMBRE} · privacidad" in privacidad and "responsable de Gov4Action (Multilente, Incubadora, Conexiones y Monitoreo)" in privacidad
    assert app.title == NOMBRE


def test_multilente_sigue_nombrando_la_revision_de_informes():
    assert "<title>Ficha técnica · Gov4Action Multilente</title>" in client.get("/detalle").text
    assert "(charla)</title>" in client.get("/multilente").text


def test_presentacion_tiene_espacio_propio_para_los_prototipos():
    html = client.get("/presentacion").text
    seccion = html[html.index('id="prototipos"'):html.index('id="uso"')]
    for texto in ("17 proyectos", "datos ficticios", "https://proyectos.entornodepruebas.com.ar/",
                  "la IA propone, las reglas comprueban y la persona decide"):
        assert texto in seccion, texto
    assert 'href="#prototipos"' in LANDING_NAV
