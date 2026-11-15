"""Pares de proyectos que se parecen, por palabras en común. No usa IA.

Similitud de coseno sobre vectores TF-IDF de título, área y situación. Es una hipótesis para que los
equipos la conversen: no evalúa proyectos ni a sus autores, y no ve sinónimos.
"""
from __future__ import annotations

import collections
import math
import re
import unicodedata
from typing import Any

UMBRAL = 0.25
MAX_PARES = 30
PALABRAS_COMUNES = frozenset(
    "para como esta este esto estos desde entre sobre tambien cada todo todos todas puede pueden mediante donde "
    "cuando segun hacia ademas asi una unos unas del los las con por que sus mas sin ser son hay muy otros otras "
    "otro otra desarrollo proyecto area areas gestion publica publico publicas publicos ministerio secretaria "
    "direccion nacional informacion datos sistema inteligencia artificial herramienta herramientas proceso procesos".split()
)


def _palabras(texto: str) -> list[str]:
    t = unicodedata.normalize("NFD", (texto or "").lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return [w for w in re.findall(r"[a-z]{4,}", t) if w not in PALABRAS_COMUNES]


def _raiz(palabra: str) -> str:
    return palabra[:6] if len(palabra) > 6 else palabra


def pares_cercanos(proyectos, umbral: float = UMBRAL, maximo: int = MAX_PARES) -> list[dict[str, Any]]:
    """Devuelve [{a, b, similitud, palabras}] ordenado de mayor a menor similitud."""
    docs: dict[int, list[str]] = {}
    visibles: dict[str, str] = {}
    for p in proyectos:
        texto = " ".join([getattr(p, "titulo", "") or "", getattr(p, "organismo_area", "") or "", getattr(p, "situacion", "") or ""])
        raices = []
        for palabra in _palabras(texto):
            raiz = _raiz(palabra)
            raices.append(raiz)
            visibles.setdefault(raiz, palabra)
        docs[int(p.id)] = raices
    n = len(docs)
    if n < 2:
        return []
    df = collections.Counter(w for d in docs.values() for w in set(d))
    vec: dict[int, dict[str, float]] = {}
    for pid, d in docs.items():
        tf = collections.Counter(d)
        v = {w: (1 + math.log(c)) * math.log((n + 1) / (df[w] + 1)) for w, c in tf.items() if 2 <= df[w] <= max(2, n * 0.25)}
        norma = math.sqrt(sum(x * x for x in v.values())) or 1.0
        vec[pid] = {w: x / norma for w, x in v.items()}
    ids = sorted(vec)
    pares = []
    for i, a in enumerate(ids):
        for b in ids[i + 1:]:
            comunes = set(vec[a]) & set(vec[b])
            s = sum(vec[a][w] * vec[b][w] for w in comunes)
            if s >= umbral:
                pares.append({"a": a, "b": b, "similitud": round(s, 2),
                              "palabras": sorted(visibles[w] for w in comunes)[:6]})
    pares.sort(key=lambda x: (-x["similitud"], x["a"], x["b"]))
    return pares[:maximo]
