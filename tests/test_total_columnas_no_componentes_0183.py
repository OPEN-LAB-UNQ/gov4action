"""Una columna «Total» que es la suma de sólo algunas de las otras columnas numéricas.

Caso que lo motivó (prueba del 14/11/2026, informe de ocupación del sector público, hoja «J-G W»): el total
es PERSONAL PERMANENTE + PERSONAL CONTRATADO; «Cargos financiados» y «Horas cátedra» son otra unidad. Las filas
de desagregación por sexo traen «s/d» en esas dos columnas, así que sólo allí «todas las columnas» sumaban el
total y la fila principal salía como «no cierra» (13 casos de prioridad alta, todos falsos).
"""
import io

from openpyxl import Workbook

from services import carga_archivos, controles_excel, excel_cobertura
from services.sanitizacion import sanear

NOMBRE = "ocupacion_publica.xlsx"
ORGANISMOS = ["Poder Judicial", "Presidencia", "Jefatura de Gabinete", "Ministerio de Salud", "Ministerio de Educación",
              "Ministerio de Justicia"]


def _planilla(error_en=None):
    wb = Workbook()
    ws = wb.active
    ws.title = "J-G W"
    ws["A1"] = "Ocupación en el sector público nacional. Cuadro 6"
    for col, rotulo in zip("DEFGH", ["Cargos financiados", "Horas cátedra", "Personal permanente y transitorio",
                                      "Personal contratado", "Total"]):
        ws[f"{col}4"] = rotulo
    fila = 5
    for i, nombre in enumerate(ORGANISMOS):
        perm, contr = 900 + 137 * i, 300 + 61 * i
        cargos, horas = 1200 + 411 * i, 5000 + 1733 * i
        ws[f"C{fila}"] = nombre
        ws[f"D{fila}"], ws[f"E{fila}"] = cargos, horas
        ws[f"F{fila}"], ws[f"G{fila}"] = perm + (700 if error_en == i else 0), contr
        ws[f"H{fila}"] = perm + contr
        for sexo, parte in (("Femenino", 0.45), ("Masculino", 0.55)):
            fila += 1
            ws[f"C{fila}"] = sexo
            ws[f"D{fila}"], ws[f"E{fila}"] = "s/d", "s/d"
            ws[f"F{fila}"], ws[f"G{fila}"] = round(perm * parte), round(contr * parte)
            ws[f"H{fila}"] = round(perm * parte) + round(contr * parte)
        fila += 1
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _controles(contenido):
    datos, cobertura = carga_archivos.parse_archivos_con_cobertura([(NOMBRE, contenido)])
    saneados, reporte, _ = excel_cobertura.preparar(datos, cobertura, lambda f: (f, {}), sanear)
    return controles_excel.analizar([(NOMBRE, contenido)], saneados, reporte["excel"])


def _reglas(hs, regla):
    return [h for h in hs if h["evidencia"]["regla"] == regla]


def test_columnas_de_otra_unidad_no_generan_fila_no_cierra_total():
    hs = _controles(_planilla())
    assert not _reglas(hs, "fila_no_cierra_total")


def test_un_componente_alterado_sigue_senalando_la_fila():
    hs = _controles(_planilla(error_en=2))
    fila = _reglas(hs, "fila_no_cierra_total") + _reglas(hs, "columna_total_no_cierra")
    assert fila, "el error real en la fila 2 debe seguir apareciendo"
    assert any("H" in str(h["evidencia"].get("celda", "")) or "G" in str(h["evidencia"].get("celda", "")) for h in fila)
