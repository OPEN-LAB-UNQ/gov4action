"""Un valor fuera de orden en una serie que, salvo ese tramo, sólo sube (o sólo baja).

Series como salarios o precios nominales de una época con inflación crecen en todos los períodos. Si una sola
vez el valor cae por debajo de los anteriores, y ese valor quedaría exactamente en orden en otro lugar de la serie,
es una señal precisa: un tramo cargado corrido de lugar (los valores de un bloque desplazados una columna) o un
valor mal ubicado. La señal nombra qué valor y entre qué períodos le correspondería estar.

No se dice nada si la serie no es casi monótona (una serie que sube y baja no tiene un «orden»), si hay más de una
caída, si el corrimiento no se arregla moviendo un solo valor, o si la misma caída (el mismo período) aparece en tres o más series
del archivo (causa común: un período en el que todo cae o se cambia de base, no un valor corrido).
"""
from collections import Counter

from .comun import es_numero, hallazgo, numero, referencia

MINIMO_VALORES = 8
MAXIMO_BLOQUE = 6
MINIMO_CRECIMIENTO = 1.5  # el último valor es al menos 1,5 veces el primero: una serie con tendencia, no una meseta
SERIES_CON_LA_MISMA_CAIDA = 3
# La caída tiene que ser material. Un tramo de 3 o más valores fuera de lugar (el valor cae por debajo de dos o más
# anteriores) es más difícil de explicar como una oscilación real que un valor suelto que baja un poco.
CAIDA_MINIMA = 0.10
CAIDA_MINIMA_DOS_VALORES = 0.25


def _ordenada(xs):
    return all(a <= b for a, b in zip(xs, xs[1:]))


def corrimiento(xs):
    """(pos_del_valor_fuera_de_orden, pos_donde_debería_estar, largo_del_tramo) o None.

    xs son los valores ya orientados para que la serie suba. Hay exactamente una caída entre vecinos y se arregla
    sacando uno solo de los dos valores que la forman y reubicándolo."""
    caidas = [i for i in range(len(xs) - 1) if xs[i + 1] < xs[i]]
    if len(caidas) != 1:
        return None
    d = caidas[0]
    sin_bajo = xs[:d + 1] + xs[d + 2:]       # sin el valor que quedó demasiado bajo
    sin_alto = xs[:d] + xs[d + 1:]           # sin el valor que quedó demasiado alto
    if _ordenada(sin_bajo):
        bajo = xs[d + 1]
        destino = next(j for j, v in enumerate(sin_bajo) if v > bajo)
        return d + 1, destino, d + 1 - destino + 1
    if _ordenada(sin_alto):
        alto = xs[d]
        destino = max(j for j, v in enumerate(sin_alto) if v < alto) + 1
        return d, destino, destino - d + 1
    return None


def _candidata(s):
    if s.get("acumulada") or s.get("periodos_validos") is False:
        return None
    puntos = [(i, numero(v)) for i, v in enumerate(s["valores"])]
    puntos = [(i, v) for i, v in puntos if v is not None]
    if len(puntos) < MINIMO_VALORES:
        return None
    ordinales = s.get("ordinales")
    if ordinales:
        usados = [ordinales[i] for i, _ in puntos if ordinales[i] is not None]
        if len(usados) != len(puntos) or any(b <= a for a, b in zip(usados, usados[1:])):
            return None
    valores = [v for _, v in puntos]
    pasos = len(valores) - 1
    suben = sum(b > a for a, b in zip(valores, valores[1:]))
    bajan = sum(b < a for a, b in zip(valores, valores[1:]))
    if suben < bajan:
        return None  # sólo series que suben: una serie que baja casi siempre es un saldo o un stock que se agota
    xs = valores
    if suben < 0.8 * pasos or valores[0] <= 0 or valores[-1] < MINIMO_CRECIMIENTO * valores[0]:
        return None
    r = corrimiento(xs)
    if r is None:
        return None
    pos, destino, largo = r
    d = pos - 1 if destino < pos else pos  # la caída está entre xs[d] y xs[d + 1]
    if xs[d] - xs[d + 1] < (CAIDA_MINIMA if largo >= 3 else CAIDA_MINIMA_DOS_VALORES) * xs[d]:
        return None
    if largo > MAXIMO_BLOQUE:
        return None
    # La primera y la última cifra de una serie son especiales (un año base distinto, un último período incompleto):
    # que estén fuera de orden no alcanza para hablar de un tramo corrido.
    if pos == 0 or pos == len(puntos) - 1:
        return None
    return dict(puntos=puntos, pos=pos, destino=destino, largo=largo)


def analizar(series):
    candidatas = []
    for s in series:
        c = _candidata(s)
        if c:
            i = c["puntos"][c["pos"]][0]
            candidatas.append((s, c, (s["archivo"], s["periodos"][i])))
    comunes = Counter(clave for _, _, clave in candidatas)
    salida = []
    for s, c, clave in candidatas:
        if comunes[clave] >= SERIES_CON_LA_MISMA_CAIDA:
            continue
        puntos, pos, destino, largo = c["puntos"], c["pos"], c["destino"], c["largo"]
        i = puntos[pos][0]
        tramo = sorted({puntos[k][0] for k in range(min(pos, destino), max(pos, destino) + 1)})
        celdas = [referencia(s, k) for k in tramo]
        valor = puntos[pos][1]
        sube_despues = destino > pos  # el valor quedó demasiado alto: no baja, supera al que le sigue
        vecino = puntos[pos + 1][1] if sube_despues else (puntos[pos - 1][1] if pos > 0 else None)
        periodo_destino = s["periodos"][puntos[destino][0]]
        lado = (f"supera a {es_numero(vecino, 2)}, el valor que le sigue" if sube_despues
                else f"queda por debajo de {es_numero(vecino, 2)}, el valor anterior")
        detalle = (
            f"la serie «{s['etiqueta']}» sube en todos los períodos menos en este: {es_numero(valor, 2)} {lado}. "
            f"Ese valor estaría en orden en {periodo_destino}; puede ser un tramo cargado corrido de lugar "
            f"({len(tramo)} celdas: {celdas[0]} a {celdas[-1]}) o un valor mal ubicado.")
        h = hallazgo(
            s, i, "valor_fuera_de_orden", detalle, 82 if largo >= 3 else 70,
            calculo={"periodo_correspondiente": periodo_destino, "celdas_en_desorden": largo,
                     "valores_de_la_serie": len(puntos)},
            participantes=celdas,
            accion="Verificar en la fuente si el tramo está corrido de lugar o si el valor está bien ubicado.",
            lente="cronista",
        )
        h["evidencia"]["ubicaciones_excel"] = celdas
        salida.append(h)
    return salida
