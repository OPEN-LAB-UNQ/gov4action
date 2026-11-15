"""«3º Trim 10»: trimestre con año de dos dígitos (Boletín de Estadísticas Laborales, Ministerio de Capital Humano).

Caso que lo motivó (banco del 14/11/2026): en las planillas de ingresos y salarios los encabezados «3º Trim 10»,
«3º Trim 11»… no se leían como períodos, la hoja entera no se reconocía como serie y ni un valor multiplicado por
diez ni una celda vacía se señalaban."""
import io

import pytest
from openpyxl import Workbook

from scripts.ensayo_controles import analizar
from services.controles_excel import periodos


@pytest.mark.parametrize("texto,anio,trim", [
    ("3º Trim 10", 2010, 3), ("1º Trim 23", 2023, 1), ("4° trim 99", 1999, 4), ("2º Trim 2023", 2023, 2),
    ("T1 2024", 2024, 1), ("2024 T3", 2024, 3),
])
def test_trimestre_con_anio_de_dos_o_cuatro_digitos(texto, anio, trim):
    p = periodos.leer(texto)
    assert p and p["frecuencia"] == "trimestral" and p["anio"] == anio and p["sub"] == trim


def _libro(vacio=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "BEL"
    ws["A1"] = "Mercado de trabajo. Ingreso medio"
    ws["A3"] = "En pesos corrientes"
    anios = [10, 11, 12, 13, 14, 16, 17, 18, 19, 20, 21, 22]
    for j, a in enumerate(anios, 2):
        ws.cell(4, j, f"3º Trim {a}")
    for i, nombre in enumerate(["Total", "Varones", "Mujeres", "Asalariados", "Cuenta propia", "Otros"]):
        ws.cell(5 + i, 1, nombre)
        for j in range(len(anios)):
            ws.cell(5 + i, 2 + j, round((1500 + 311 * i) * (1.27 ** j) + 13 * j, 1))
    if vacio:
        ws[vacio] = None
    b = io.BytesIO()
    wb.save(b)
    return b.getvalue()


def test_una_celda_vacia_en_una_serie_trimestral_de_anio_corto_se_senala():
    hs, _ = analizar(_libro(vacio="G8"))
    assert any(h["evidencia"].get("regla") == "vacio_interior" and h["evidencia"].get("celda") == "G8" for h in hs)


def test_la_serie_sin_alterar_no_da_alarmas_altas():
    hs, _ = analizar(_libro())
    assert not [h for h in hs if h.get("severidad") == "alta" and h["evidencia"].get("naturaleza") == "control"]


@pytest.mark.parametrize("texto,anio,trim", [("2° Trim 07 1", 2007, 2), ("3° Trim 07 1 2", 2007, 3), ("4º Trim 2008 1", 2008, 4)])
def test_trimestre_con_llamada_a_nota_suelta(texto, anio, trim):
    """«2° Trim 07 1» (encuesta de hogares, Boletín de Estadísticas Laborales): el «1» final es la llamada a una nota, no parte del período."""
    p = periodos.leer(texto)
    assert p and p["anio"] == anio and p["sub"] == trim and p["frecuencia"] == "trimestral"


def test_periodo_faltante_en_el_encabezado_sale_una_sola_vez_por_celda():
    """Antes cada serie del cuadro repetía el mismo hallazgo del encabezado (seis copias idénticas)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "BEL"
    ws["A1"] = "Mercado de trabajo"
    anios = [10, 11, 12, 14, 15, 16]          # falta el 13
    for j, a in enumerate(anios, 2):
        ws.cell(4, j, f"3º Trim {a:02d}")
    for i in range(6):
        ws.cell(5 + i, 1, f"Categoría {i}")
        for j in range(len(anios)):
            ws.cell(5 + i, 2 + j, round(1000 * (1.2 ** j) + 37 * i, 1))
    b = io.BytesIO()
    ws.parent.save(b)
    hs, _ = analizar(b.getvalue())
    faltantes = [(h["evidencia"].get("hoja"), h["evidencia"].get("celda"), h["descripcion"]) for h in hs
                 if h["evidencia"].get("regla") == "periodo_faltante"]
    assert len(faltantes) == len(set(faltantes))
