"""Un valor fuera de orden en una serie que sólo sube: tramo corrido de lugar (14/11/2026)."""
from services.controles_excel import orden_serie


def serie(valores, etiqueta="Salario", cuadro="C1", acumulada=False):
    n = len(valores)
    return dict(archivo="a.xlsx", hoja="BEL", cuadro=cuadro, etiqueta=etiqueta, valores=valores,
                periodos=[str(2000 + i) for i in range(n)], ordinales=list(range(n)),
                celdas=[f"{chr(66 + i)}5" for i in range(n)], acumulada=acumulada, periodos_validos=True)


BASE = [100, 130, 170, 230, 300, 410, 560, 760, 1000, 1400]


def corrida(vals, desde, largo):
    v = list(vals)
    v[desde:desde + largo] = v[desde + 1:desde + largo] + [v[desde]]
    return v


def test_bloque_corrido_se_senala_con_el_tramo_completo():
    hs = orden_serie.analizar([serie(corrida(BASE, 3, 4))])
    assert len(hs) == 1
    h = hs[0]
    ev = h["evidencia"]
    assert ev["regla"] == "valor_fuera_de_orden" and h["lente"] == "cronista"
    assert ev["celda"] == "H5"                      # el valor que quedó fuera de orden
    assert ev["celdas_participantes"] == ["BEL!E5", "BEL!F5", "BEL!G5", "BEL!H5"]  # el tramo corrido
    assert ev["periodo_correspondiente"] == "2003"
    assert h["severidad"] == "alta"


def test_dos_valores_intercambiados_son_media():
    v = list(BASE)
    v[4], v[5] = v[5], v[4]
    hs = orden_serie.analizar([serie(v)])
    assert len(hs) == 1 and hs[0]["severidad"] == "media"


def test_valor_demasiado_alto_se_senala_en_ese_valor():
    hs = orden_serie.analizar([serie([100, 130, 600, 230, 300, 410, 560, 760, 1000, 1400])])
    assert len(hs) == 1
    assert hs[0]["evidencia"]["celda"] == "D5"
    assert "supera" in hs[0]["descripcion"]


def test_serie_ordenada_no_dice_nada():
    assert orden_serie.analizar([serie(BASE)]) == []


def test_serie_que_sube_y_baja_no_tiene_orden():
    assert orden_serie.analizar([serie([5, 3, 8, 2, 9, 4, 10, 6, 12, 7])]) == []


def test_dos_caidas_no_se_senalan():
    assert orden_serie.analizar([serie([100, 130, 120, 230, 300, 280, 560, 760, 1000, 1400])]) == []


def test_serie_corta_acumulada_o_sin_tendencia_no_se_senalan():
    assert orden_serie.analizar([serie([100, 130, 120, 230, 300])]) == []
    assert orden_serie.analizar([serie(corrida(BASE, 3, 4), acumulada=True)]) == []
    plana = [100, 101, 102, 101, 103, 104, 105, 106, 107, 108]
    assert orden_serie.analizar([serie(plana)]) == []


def test_serie_que_baja_no_se_senala():
    assert orden_serie.analizar([serie(corrida(BASE, 3, 4)[::-1])]) == []


def test_misma_caida_en_tres_series_del_archivo_es_causa_comun():
    series = [serie(corrida(BASE, 3, 4), etiqueta=f"S{i}", cuadro=f"C{i}") for i in range(3)]
    assert orden_serie.analizar(series) == []
    assert len(orden_serie.analizar(series[:2])) == 2


def test_huecos_y_periodos_desordenados():
    con_hueco = corrida(BASE, 3, 4)
    con_hueco[0] = None
    assert len(orden_serie.analizar([serie(con_hueco)])) == 1
    s = serie(corrida(BASE, 3, 4))
    s["ordinales"] = [0, 1, 2, 4, 3, 5, 6, 7, 8, 9]
    assert orden_serie.analizar([s]) == []


def test_texto_llano_de_la_regla():
    from services.reportes import lenguaje_llano as L
    t = L.PLANTILLAS["valor_fuera_de_orden"](dict(indicador="Salario", periodo="2003", periodo_correspondiente="2000"))
    assert "Salario" in t and "2003" in t and "2000" in t


def test_primer_y_ultimo_valor_no_se_senalan():
    assert orden_serie.analizar([serie([900, 130, 170, 230, 300, 410, 560, 760, 1000, 1400])]) == []
    assert orden_serie.analizar([serie([100, 130, 170, 230, 300, 410, 560, 760, 1000, 500])]) == []


def test_una_caida_de_centesimas_es_una_revision_no_un_corrimiento():
    assert orden_serie.analizar([serie([100, 130, 170, 230, 300, 299, 301, 760, 1000, 1400])]) == []


def test_un_valor_suelto_que_baja_poco_no_se_senala_pero_un_tramo_corrido_si():
    # 439 contra 481: una oscilación del 9 %, como las de cualquier serie real.
    assert orden_serie.analizar([serie([300, 481.7, 439.4, 520, 560, 610, 680, 760, 840, 930])]) == []
    assert len(orden_serie.analizar([serie(corrida(BASE, 3, 4))])) == 1


def test_el_valor_fuera_de_orden_no_absorbe_la_conciliacion():
    from services.controles_excel import consolidar
    punto = orden_serie.analizar([serie(corrida(BASE, 3, 4))])[0]
    rel = dict(lente="conciliador", severidad="media", descripcion="no suma",
               evidencia=dict(archivo_origen="a.xlsx", naturaleza="control", regla="conciliacion_aritmetica", hoja="BEL",
                              celda="H5", celdas_participantes=["BEL!H5"], ubicaciones_excel=["BEL!H5"],
                              puntaje_prioridad=60, factores_prioridad=[]))
    salida = consolidar([punto], [rel])
    assert sorted(h["evidencia"]["regla"] for h in salida) == ["conciliacion_aritmetica", "valor_fuera_de_orden"]
