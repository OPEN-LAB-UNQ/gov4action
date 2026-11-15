"""0.10.78: cuatro ejes, cada uno con su entidad (pedido de Maxi, 08/11/2026).

Multilente, Incubadora, Conexiones y Monitoreo: el nombre nombra a los cuatro, la presentación les da una tarjeta y una
sección a cada uno, e Inicio los numera como ejes.
"""
import re
from pathlib import Path

from fastapi.testclient import TestClient

from core.auth import login_html
from main import LANDING_NAV, app

NOMBRE = "Gov4Action: Multilente, Incubadora, Conexiones y Monitoreo"
EJES = ["Multilente", "Incubadora", "Conexiones", "Monitoreo"]
STATIC = Path(__file__).resolve().parents[1] / "static"
client = TestClient(app)


def _main(html: str) -> str:
    return html.split("  <main>", 1)[1].split("  </main>", 1)[0]


def _seccion(html: str, sid: str) -> str:
    return html.split(f'id="{sid}"', 1)[1].split("</section>", 1)[0]


def test_presentacion_con_una_tarjeta_por_eje_que_lleva_a_su_seccion():
    html = _main(client.get("/presentacion").text)
    ejes = _seccion(html, "ejes")
    assert '<div class="section-kicker">Cuatro ejes</div>' in ejes
    assert "Dos ejes" not in html and "dos ejes" not in html
    assert ejes.count("<article>") == 4
    assert re.findall(r"<h3>([^<:]+):", ejes) == EJES
    for destino in ("#como-funciona", "#incubadora", "#conexiones", "#monitoreo"):
        assert f'href="{destino}"' in ejes, destino
    for sid in ("incubadora", "conexiones", "monitoreo"):
        bloque = _seccion(html, sid)
        assert f'<div class="section-kicker">{sid.capitalize()}</div>' in bloque, sid
        assert bloque.count("<h2>") == 1 and bloque.count("<article>") == 3, sid
    assert '<div class="section-kicker">Multilente · El problema y la idea</div>' in _seccion(html, "sintesis")
    assert 'href="#ejes"' in LANDING_NAV and 'href="#incubadora"' not in LANDING_NAV


def test_conexiones_cuenta_la_galeria_y_dice_que_propone_hipotesis():
    html = _main(client.get("/presentacion").text)
    conexiones = _seccion(html, "conexiones")
    for texto in ("su propia votación", "que no son una nota", "sin IA", "conecta proyectos, no personas",
                  "Hipótesis, no decisiones", "datos ficticios", "está operativa", 'href="/?ir=conexiones"'):
        assert texto in conexiones, texto
    assert "su propia votación" not in _seccion(html, "incubadora")


def test_monitoreo_dice_sus_dos_etapas_y_que_no_evalua_personas():
    monitoreo = _seccion(_main(client.get("/presentacion").text), "monitoreo")
    for texto in ("modo prueba", "datos ficticios", "piloto chico, reversible y autorizado",
                  "todavía no tienen un piloto real",
                  "Avance, riesgo, decisión, indicador y aprendizaje", "no mide el desempeño de las personas",
                  "Es optativo y no lleva nota", 'href="/?ir=monitoreo"'):
        assert texto in monitoreo, texto
    # Revisión independiente: la tarjeta no dice que cada proyecto pasa por modo prueba y piloto real.
    tarjeta = _seccion(_main(client.get("/presentacion").text), "ejes").split("<h3>Monitoreo:", 1)[1].split("</article>", 1)[0]
    assert "de cada proyecto: primero en modo prueba" not in tarjeta and "en dos grupos de cursada" in tarjeta


def test_inicio_numera_los_cuatro_ejes():
    indice = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "Gov4Action y sus cuatro ejes" in indice and "sus módulos" not in indice
    assert "(Eje 2)" in indice and "son para explorar y comparar" not in indice  # Monitoreo no compara proyectos
    for n in range(1, 5):
        assert f"<span>Eje {n}</span>" in indice
    assert not re.search(r"Recorrido [1-4]", indice)  # «Recorrido propuesto» de las síntesis no es un eje
    js = (STATIC / "app.js").read_text(encoding="utf-8")
    assert not re.search(r'titulo: "Recorrido \d"', js)
    assert len(re.findall(r'titulo: "Eje [1-4]"', js)) == 5


def test_el_nombre_nombra_los_cuatro_ejes_en_cada_superficie():
    presentacion = client.get("/presentacion").text
    assert f"<title>{NOMBRE}</title>" in presentacion and f"<span>{NOMBRE}</span>" in presentacion
    acceso = login_html()
    assert '<h1>Gov<span class="brand-four">4</span>Action</h1>' in acceso
    assert "los cuatro ejes: Multilente, la Incubadora, Conexiones y Monitoreo" in acceso
    privacidad = client.get("/privacidad").text
    assert f"{NOMBRE} · privacidad" in privacidad
    assert app.title == NOMBRE
    for superficie in (presentacion, acceso, privacidad, (STATIC / "index.html").read_text(encoding="utf-8")):
        assert "Gov4Action Multilente e Incubadora" not in superficie
