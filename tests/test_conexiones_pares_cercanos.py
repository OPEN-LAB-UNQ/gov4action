from types import SimpleNamespace

from services import conexiones_texto


def proyecto(pid, titulo, area="Área de prueba", situacion=""):
    return SimpleNamespace(id=pid, titulo=titulo, organismo_area=area, situacion=situacion)


def test_detecta_proyectos_que_hablan_de_lo_mismo_y_dice_en_que_palabras():
    ps = [
        proyecto(1, "Validación de inscripciones a cursos", situacion="Controlar las inscripciones de estudiantes"),
        proyecto(2, "Seguimiento de inscripción a cursos", situacion="Seguir las inscripciones de estudiantes a cada curso"),
        proyecto(3, "Mapa de obras viales", situacion="Ubicar rutas y caminos rurales"),
        proyecto(4, "Calendario de licitaciones", situacion="Publicar fechas de apertura de ofertas"),
    ]
    pares = conexiones_texto.pares_cercanos(ps, umbral=0.2)
    assert [(p["a"], p["b"]) for p in pares] == [(1, 2)]
    assert "inscripciones" in pares[0]["palabras"] or "inscripción" in pares[0]["palabras"] or pares[0]["palabras"]
    assert 0 < pares[0]["similitud"] <= 1


def test_sin_proyectos_suficientes_o_sin_parecido_no_inventa_pares():
    assert conexiones_texto.pares_cercanos([proyecto(1, "Uno")]) == []
    ps = [proyecto(1, "Mapa de obras viales"), proyecto(2, "Calendario de licitaciones")]
    assert conexiones_texto.pares_cercanos(ps) == []


def test_no_usa_ia_ni_red():
    import inspect
    fuente = inspect.getsource(conexiones_texto)
    for prohibido in ("openai", "anthropic", "requests", "httpx", "urllib"):
        assert prohibido not in fuente.lower()
