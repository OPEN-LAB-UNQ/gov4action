"""Prototipos de los proyectos de la Incubadora (0.10.70).

Varios proyectos de la Incubadora tienen un prototipo con datos ficticios en el sitio de proyectos del
entorno de pruebas. Gov4Action sólo enlaza: no comparte sesión, cuentas ni datos con ese sitio, que es
abierto y anónimo. La tabla va por número de proyecto (``proyectos_ia.id``), el mismo número que usa el
catálogo de ese sitio («incubadora-NN»).

Los proyectos del grupo nuevo tienen su propio sitio, gemelo del anterior, con su tabla y sus fichas.
"""
from __future__ import annotations

import json
import threading
import time
import urllib.request
from typing import Any

SITIO = "https://proyectos.entornodepruebas.com.ar"
# 0.10.76: las fichas públicas del sitio (cómo mide cada prototipo y dónde). El sitio corre en el mismo servidor:
# se le pide por la red local, con un tiempo máximo corto y una copia en memoria. Si no responde, vale la última copia
# buena y, si nunca hubo una, Monitoreo muestra sólo el enlace al prototipo.
FICHAS_URL = "http://127.0.0.1:6186/api/fichas"
FICHAS_VIGENCIA = 15 * 60
FICHAS_REINTENTO = 60
_fichas_cache: dict[str, Any] = {"hasta": 0.0, "fichas": {}}
_fichas_pidiendo = threading.Lock()  # un solo pedido a la vez: los demás usan la copia que haya

SITIO_GRUPO_B = "https://proyectos-grupo-b.example.org"
FICHAS_URL_GRUPO_B = "http://127.0.0.1:6192/api/fichas"
_grupo_b_cache: dict[str, Any] = {"hasta": 0.0, "fichas": {}}
_grupo_b_pidiendo = threading.Lock()

# Número de proyecto -> dirección del prototipo en el sitio.
PROTOTIPOS: dict[int, str] = {
    59: "consultas-pymes",
    60: "dictamenes",
    61: "subsidios",
    62: "guardias",
    63: "capacitaciones",
    64: "clubes",
    65: "patrimonio",
    66: "boletin-oficial",
    67: "expedientes",
    68: "mesa-de-ayuda",
    70: "biblioteca",
    71: "facturas",
    72: "proyectos-de-ley",
    74: "obras",
    78: "causas-nuevas",
}

# Lo mismo para los proyectos del grupo B, en su sitio.
PROTOTIPOS_GRUPO_B: dict[int, str] = {
    79: "lotes-de-informacion-salarial",
    81: "comparador-de-proyectos-de-ley",
    82: "cartera-anual-sin-duplicados",
    83: "proyeccion-gasto-en-personal",
    84: "analisis-documental-gasto-en-personal",
    85: "borrador-nota-excepciones-contratacion",
    86: "verificacion-de-cursos-previos",
    87: "alertas-de-inscripcion-a-cursos",
    88: "eliminaciones-entre-entidades-del-sector",
    89: "envio-de-remanentes-por-organismo",
    90: "relevamiento-de-cambios-institucionales",
    91: "requerimientos-parlamentarios",
    92: "armonizacion-estados-financieros",
    93: "remision-trimestral-morosidad",
    94: "estados-contables-comparados",
    95: "entes-excluidos-ejecucion-alertas",
    96: "resumen-diario-deuda-alertas",
    98: "copiloto-mesa-de-soporte",
    99: "biblioteca-de-procedimientos-registracion",
    100: "diccionario-de-datos-abiertos",
    101: "documentacion-de-tableros-bi",
    103: "validacion-datos-dotacion-personal",
    105: "digesto-normativo-financiero",
    107: "consistencia-visualizaciones-portal-presupuestario",
    112: "agente-consulta-interna-oficina",
    113: "revision-borrador-pliego-tecnico",
    114: "seguimiento-temas-pendientes-plataforma",
    115: "seguimiento-presentaciones-causas-judiciales",
    116: "busqueda-conceptos-en-presupuesto",
    118: "distribucion-techos-de-caja-mensuales",
    119: "informe-historico-modificaciones-presupuestarias",
    121: "notas-automaticas-solicitudes-de-cobranza",
}

AVISO = (
    "Prototipo con datos ficticios, en el entorno de pruebas. "
    "Se abre en otra pestaña y no usa tu cuenta de Gov4Action."
)


def _ubicacion(proyecto_id: int) -> tuple[str, str] | None:
    """Sitio y dirección del prototipo de un proyecto, o None si no tiene."""
    for sitio, tabla in ((SITIO, PROTOTIPOS), (SITIO_GRUPO_B, PROTOTIPOS_GRUPO_B)):
        if proyecto_id in tabla:
            return sitio, tabla[proyecto_id]
    return None


def de(proyecto_id: int | None) -> dict[str, Any] | None:
    """Enlace al prototipo de un proyecto, o None si el proyecto no tiene prototipo."""
    if proyecto_id is None:
        return None
    ubicacion = _ubicacion(int(proyecto_id))
    if not ubicacion:
        return None
    sitio, ruta = ubicacion
    return {"url": f"{sitio}/{ruta}/", "aviso": AVISO}


def _pedir_fichas() -> Any:
    """El pedido al sitio de prototipos (aparte, para que las pruebas lo reemplacen y nunca salgan a la red)."""
    with urllib.request.urlopen(FICHAS_URL, timeout=1.5) as r:  # noqa: S310 — dirección fija de la red local
        return json.loads(r.read().decode("utf-8"))


def _pedir_fichas_grupo_b() -> Any:
    """El mismo pedido, al sitio de prototipos del grupo B."""
    with urllib.request.urlopen(FICHAS_URL_GRUPO_B, timeout=1.5) as r:  # noqa: S310 — dirección fija de la red local
        return json.loads(r.read().decode("utf-8"))


def _copia(cache: dict[str, Any], pidiendo: Any, pedir: Any) -> dict[str, dict[str, Any]]:
    """Las fichas de un sitio por slug, con una copia en memoria (si el sitio no responde, se reintenta en un minuto y
    mientras tanto vale la última copia buena, o ninguna)."""
    if time.monotonic() < cache["hasta"]:
        return cache["fichas"]
    if not pidiendo.acquire(blocking=False):  # otro pedido ya está consultando: no esperar
        return cache["fichas"]
    try:
        datos = pedir()
        fichas = {f["slug"]: f for f in datos if isinstance(f, dict) and isinstance(f.get("slug"), str)}
        cache.update(hasta=time.monotonic() + FICHAS_VIGENCIA, fichas=fichas)
    except Exception:  # noqa: BLE001 — sin el sitio, Monitoreo sigue andando con la última copia buena
        cache["hasta"] = time.monotonic() + FICHAS_REINTENTO
    finally:
        pidiendo.release()
    return cache["fichas"]


def _fichas() -> dict[str, dict[str, Any]]:
    return _copia(_fichas_cache, _fichas_pidiendo, _pedir_fichas)


def _fichas_grupo_b() -> dict[str, dict[str, Any]]:
    return _copia(_grupo_b_cache, _grupo_b_pidiendo, _pedir_fichas_grupo_b)


def en_accion(proyecto_id: int | None) -> dict[str, Any] | None:
    """0.10.76: el prototipo del proyecto en acción, para Monitoreo: el enlace, la página donde mide y cómo mide."""
    base = de(proyecto_id)
    if not base:
        return None
    sitio, slug = _ubicacion(int(proyecto_id))
    ficha = (_fichas_grupo_b() if sitio == SITIO_GRUPO_B else _fichas()).get(slug) or {}
    ruta = ficha.get("medicion_ruta")
    texto = ficha.get("medicion")
    # Sólo una página del propio prototipo: lo que llega del sitio nunca arma una dirección a otro lado.
    valida = (isinstance(ruta, str) and ruta.startswith(f"/{slug}/") and ".." not in ruta
              and not any(c in ruta for c in "%\\?#") and all(c.isascii() and c.isprintable() for c in ruta))
    medicion_url = f"{sitio}{ruta}" if valida else None
    return {**base, "medicion_url": medicion_url,
            "medicion_texto": texto.strip()[:600] if isinstance(texto, str) and texto.strip() else None}


# 0.10.72: lo que comparten los prototipos, para Conexiones. Las bases son las del sitio de prototipos; los
# componentes son piezas que ya funcionan compartidas entre prototipos (todo con datos ficticios).
BASES: list[tuple[str, str, tuple[int, ...]]] = [
    ("documentos", "Leer, clasificar y resumir documentos", (66, 72, 67, 78, 60)),
    ("cruces", "Cruzar datos y marcar lo que no cierra", (71, 64, 61, 70)),
    ("tableros", "Tableros de registros con alertas", (68, 74, 65)),
    ("consultas", "Registro y derivación de consultas", (59,)),
    ("aparte", "Planificación y derivación, sin IA obligatoria", (63, 62)),
]

COMPONENTES: list[tuple[str, str, tuple[int, ...]]] = [
    ("Una sola base de normas",
     "Usan la misma base de normas. El Boletín y los proyectos de ley comparten además la lista de seguimiento.",
     (66, 72, 67, 60)),
    ("El circuito de una ley",
     "Un proyecto del Poder Ejecutivo se sanciona como ley y el Boletín publica su promulgación y su reglamentación.",
     (72, 66)),
    ("Un cambio de norma que se propaga",
     "Cuando un decreto modifica una norma, el Boletín registra la relación, expedientes avisa que un antecedente puede "
     "haber quedado desactualizado y dictámenes advierte que el criterio citado puede haber cambiado.",
     (66, 67, 60)),
    ("Clasificar y derivar",
     "Registro único, datos que faltan, propuesta de categoría y derivación que confirma una persona.",
     (68, 59)),
    ("Registros con alertas",
     "Registros que se atrasan, vencen o no coinciden: una regla marca y una persona confirma.",
     (65, 74)),
    ("Subsidios",
     "El registro de subsidios y la capacitación sobre el nuevo esquema comparten el tema y el cuidado por el lenguaje claro.",
     (61, 63)),
]

# Las mismas bases en el sitio del grupo B (salen de su catálogo). No hay componentes compartidos entre sus prototipos.
BASES_GRUPO_B: dict[str, tuple[int, ...]] = {
    "documentos": (81, 84, 85, 90, 92, 99, 100, 101, 105, 112, 113, 116, 119),
    "cruces": (88, 95, 103, 107),
    "tableros": (82, 83, 87, 91, 93, 96, 114),
    "consultas": (94, 98),
    "aparte": (79, 86, 89, 115, 118, 121),
}

AVISO_CONEXIONES = (
    "Los prototipos usan datos ficticios y están en el entorno de pruebas: muestran qué se podría compartir, "
    "no algo que ya se comparta con datos reales."
)


def conexiones(proyectos) -> dict[str, Any]:
    """Bases y componentes compartidos entre los prototipos de los proyectos que la persona puede ver."""
    visibles = {int(p.id): p for p in proyectos if _ubicacion(int(p.id))}

    def caso(pid: int) -> dict[str, Any]:
        titulo = (getattr(visibles[pid], "titulo", None) or "").strip() or "Caso en definición"
        return {"id": pid, "titulo": titulo, "url": de(pid)["url"]}

    bases = [{"clave": clave, "nombre": nombre,
              "casos": [caso(i) for i in (*ids, *BASES_GRUPO_B.get(clave, ())) if i in visibles]}
             for clave, nombre, ids in BASES]
    componentes = [{"nombre": nombre, "texto": texto, "casos": [caso(i) for i in ids if i in visibles]}
                   for nombre, texto, ids in COMPONENTES]
    return {"aviso": AVISO_CONEXIONES, "bases": [b for b in bases if b["casos"]],
            "componentes": [c for c in componentes if len(c["casos"]) >= 2]}
