"""0.10.69: las salidas adecuadas se llaman «más sencilla», no «más simple»."""
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"


def test_ficha_dice_solucion_mas_sencilla():
    ficha = (STATIC / "detalle-body.html").read_text(encoding="utf-8")
    assert "conviene una solución más sencilla o no incorporar tecnología" in ficha
    assert "más simple" not in ficha


def test_conclusion_r1_dice_automatizacion_sencilla():
    app = (STATIC / "app.js").read_text(encoding="utf-8")
    assert 'automatizacion_simple: "Conviene una automatización sencilla"' in app
    assert "Conviene una automatización simple" not in app


def test_la_incubadora_no_da_por_hecho_que_se_usa_ia():
    pantalla = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "El asistente te ayuda a decidir si conviene usar IA y, si conviene, a hacerlo sin saltear la gobernanza." in pantalla
    assert "te ayuda a implementar IA" not in pantalla and "antes de implementar IA." not in pantalla
    assert "que querés mejorar con IA responsable" not in pantalla
    tutora = (STATIC.parent / "routers" / "proyectos_ia.py").read_text(encoding="utf-8")
    assert "no obliga a incorporar IA en la solución" in tutora
    assert "qué haría la IA si corresponde usarla" in tutora


def test_la_pantalla_dice_quien_ve_que():
    pantalla = (STATIC / "index.html").read_text(encoding="utf-8")
    assert "<strong>Quién ve qué:</strong> el equipo docente lee tu proyecto, la conversación con la tutora y tus consultas." in pantalla
    assert 'id="btn-docente-sin-respuesta"' in pantalla
