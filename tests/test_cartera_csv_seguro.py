import asyncio
import csv
import io
from copy import deepcopy

import pytest

from core.csv_seguro import celda_csv
from routers import proyectos_ia


@pytest.mark.parametrize("value", ["=1+1", "+1+1", "-1+1", "@SUM(A1)", "  =1+1", "\t=1+1", "\r=1+1", "\n=1+1"])
def test_formula_is_text(value):
    assert celda_csv(value) == "'" + value


@pytest.mark.parametrize("value", ["Título normal", "Área, con coma", "Línea 1\nLínea 2", "", 12])
def test_ordinary_text_and_numbers_preserved(value):
    assert celda_csv(value) == str(value)


def test_actual_cartera_export_protects_all_text_and_keeps_data(monkeypatch):
    item = dict(
        id=1,
        nombre="=1+1",
        email="+correo@example.invalid",
        titulo="@SUM(A1)",
        organismo_area="-1+1",
        tema="\t=1+1",
        estado="\r=1+1",
        madurez="  =1+1",
        checkpoint=dict(completos=1, total=2, faltantes=["=1+1"]),
        entrega_final=True,
        interacciones_docente=2,
        mensajes_chat_ia=3,
        proximo_foco="\n=1+1",
        ultimo_movimiento="2026-11-26",
    )
    original = deepcopy(item)
    monkeypatch.setattr(
        proyectos_ia, "cartera_proyectos", lambda *args: dict(candidatos_implementacion=[item], segunda_vuelta=[item])
    )
    response = proyectos_ia.exportar_cartera_proyectos(admin=object(), db=object())

    async def collect():
        return "".join([chunk async for chunk in response.body_iterator])

    rows = list(csv.reader(io.StringIO(asyncio.run(collect()))))
    assert len(rows) == 2 and len(rows[0]) == len(rows[1]) == 14
    assert rows[1][0] == "1"
    for index in [1, 2, 3, 4, 5, 6, 7, 12, 13]:
        assert rows[1][index].startswith("'")
    assert rows[1][8:12] == ["1/2", "si", "2", "3"]
    assert item == original
