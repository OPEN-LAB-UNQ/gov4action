"""Gov4Action Monitoreo: seguimiento de la implementacion real de un proyecto de Incubadora.

Multilente lee datos ya producidos e Incubadora acompana el diseno de una
implementacion; Monitoreo cubre el tramo siguiente, cuando el proyecto ya
opera: registra avances, riesgos, decisiones humanas, indicadores y
aprendizajes sobre la operacion real, con la misma disciplina de estado
explicito y trazabilidad que ya rige en routers/aprendizajes_incubadora.py.
Desde la 0.10.72, los proyectos de los grupos de MONITOREO_GRUPOS_PRUEBA (la comisión 2; desde la 0.10.80, también Grupo B) usan Monitoreo en modo
prueba, con su prototipo y datos ficticios: cada registro guarda su etapa en metadata_evento y la prueba no se
mezcla con el piloto real. Los demás proyectos siguen en cartera, como antes.
No mide desempeno de personas ni compara proyectos entre si.
"""
from __future__ import annotations

import datetime as dt
import re
from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException
from sqlalchemy.orm import Session

import models
from config import settings
from core.auth import get_current_user
from database import get_db
from routers.aprendizajes import _redactar_aprendizaje
from services import actividad as actividad_svc
from services import equipos, grupos, plural, prototipos_incubadora

router = APIRouter(prefix="/api/monitoreo", tags=["monitoreo"])

TIPOS_REGISTRO = {
    "avance": "Avance",
    "riesgo": "Riesgo",
    "decision": "Decision",
    "indicador": "Indicador",
    "aprendizaje": "Aprendizaje",
}

ESTADOS_REGISTRO = {"abierto", "en_curso", "resuelto", "descartado"}

ALCANCE = {
    "piloto": "Piloto habilitado: seguimiento de la implementación real del proyecto ganador.",
    "prueba": ("Modo prueba: registrá lo que aprendés al probar el proyecto (y su prototipo, si tiene uno), con datos "
               "ficticios. No es una implementación "
               "real: pasar a datos o procesos reales exige un piloto chico, reversible y autorizado. Los registros de "
               "otra etapa quedan como historial de solo lectura."),
    "propio": ("Seguimiento propio de una herramienta de Gov4Action: registra avances, riesgos, decisiones humanas e "
               "indicadores de la herramienta mientras se usa, cada uno con su fuente. No es el piloto ni un proyecto "
               "ganador, y no mide a las personas."),
    "cartera": "En cartera; Monitoreo no habilitado en esta etapa. Los registros anteriores se conservan como historial de solo lectura.",
}


def _texto_seguro(valor: object, max_chars: int) -> str:
    texto = _redactar_aprendizaje(str(valor or "").strip())
    return texto[:max_chars].strip()


def _proyecto_o_404(db: Session, proyecto_id: int) -> models.ProyectoIA:
    proyecto = db.get(models.ProyectoIA, proyecto_id)
    if not proyecto:
        raise HTTPException(404, "proyecto no encontrado")
    return proyecto


def _exigir_acceso(proyecto: models.ProyectoIA, usuario: models.Usuario) -> None:
    if usuario.rol != "admin" and not equipos.es_integrante(proyecto, usuario):  # quien lo abrió o integra el equipo
        raise HTTPException(403, "no tenes acceso a este proyecto")


def proyectos_propios() -> set[int]:
    """0.10.85: proyectos de seguimiento propio de las herramientas (MONITOREO_PROYECTOS_PROPIOS, ids por coma)."""
    ids: set[int] = set()
    for valor in (settings.monitoreo_proyectos_propios or "").split(","):
        if valor.strip().isdigit():
            ids.add(int(valor.strip()))
    return ids


def _propio(proyecto: models.ProyectoIA) -> bool:
    return proyecto.id in proyectos_propios()


def _habilitado(proyecto: models.ProyectoIA) -> bool:
    if settings.monitoreo_proyecto_id is not None and proyecto.id == settings.monitoreo_proyecto_id:
        return True
    return _propio(proyecto)


def grupos_prueba() -> set[str]:
    """Grupos de cursada con Monitoreo en modo prueba (0.10.72)."""
    return {g.strip() for g in (settings.monitoreo_grupos_prueba or "").split(",") if g.strip()}


def modo_de(proyecto: models.ProyectoIA) -> str:
    """«piloto» para el proyecto habilitado expresamente; «prueba» para los proyectos de los grupos con modo prueba
    (registran lo que aprenden con su prototipo y sus datos ficticios, sin que cuente como implementación real);
    «cartera» para los demás, como antes de la 0.10.72."""
    if _habilitado(proyecto):
        return "piloto"
    if grupos.de(getattr(proyecto, "usuario", None)) in grupos_prueba():
        return "prueba"
    return "cartera"


_modo = modo_de


def _etapa(registro: models.RegistroMonitoreo) -> str:
    """Etapa en la que se creó el registro. Los anteriores a la 0.10.72 no la guardaban: quedan como «anterior», un
    historial de sólo lectura (no se sabe si fueron del piloto: antes de la 0.8.1 cualquier proyecto podía registrar)."""
    return (registro.metadata_evento or {}).get("etapa") or "anterior"


def _puede_registrar(proyecto: models.ProyectoIA, usuario: models.Usuario) -> bool:
    """En el piloto registran su equipo y la cuenta administradora, como antes. En modo prueba registra sólo el equipo
    del proyecto: es el aprendizaje de quien prueba su prototipo; el equipo docente lo lee."""
    if _modo(proyecto) == "piloto":
        return usuario.rol == "admin" or equipos.es_integrante(proyecto, usuario)
    if _modo(proyecto) == "prueba":
        return equipos.es_integrante(proyecto, usuario)
    return False


def _exigir_registro(proyecto: models.ProyectoIA, usuario: models.Usuario) -> None:
    if _puede_registrar(proyecto, usuario):
        return
    if _modo(proyecto) == "cartera":
        raise HTTPException(403, "Monitoreo está habilitado únicamente para el proyecto ganador del piloto. Este proyecto "
                                 "permanece en cartera; su historial es de solo lectura.")
    raise HTTPException(403, "En modo prueba registra el equipo del proyecto; el equipo docente lo lee.")


def _registro_out(registro: models.RegistroMonitoreo) -> dict[str, Any]:
    return {
        "id": registro.id,
        "proyecto_id": registro.proyecto_id,
        "usuario_id": registro.usuario_id,
        "tipo": registro.tipo,
        "titulo": registro.titulo,
        "contenido": _redactar_aprendizaje(registro.contenido),
        "estado": registro.estado,
        "etapa": _etapa(registro),
        "valor_indicador": registro.valor_indicador,
        "metadata": registro.metadata_evento or {},
        "creado_en": registro.creado_en.isoformat() if registro.creado_en else None,
    }


def _metricas_registros(registros: list[models.RegistroMonitoreo]) -> dict[str, Any]:
    por_tipo: dict[str, int] = {}
    por_estado: dict[str, int] = {}
    for registro in registros:
        por_tipo[registro.tipo] = por_tipo.get(registro.tipo, 0) + 1
        por_estado[registro.estado] = por_estado.get(registro.estado, 0) + 1
    abiertos = por_estado.get("abierto", 0) + por_estado.get("en_curso", 0)
    cerrados = por_estado.get("resuelto", 0) + por_estado.get("descartado", 0)
    if not registros:
        lectura = "Todavía no hay seguimiento registrado. Agregá el primer avance, riesgo, indicador o decisión cuando el proyecto empiece a operar."
    elif abiertos:
        lectura = (f"Hay {plural.contar(abiertos, 'registro')} que todavía "
                   f"{'requiere' if abiertos == 1 else 'requieren'} seguimiento. "
                   "Los cambios de estado quedan asociados a la persona que los realiza.")
    else:
        lectura = "Todos los registros tienen cierre explícito. El seguimiento está al día y puede retomarse cuando aparezca un nuevo avance o riesgo."
    return {"total_registros": len(registros), "por_tipo": por_tipo, "por_estado": por_estado,
            "abiertos": abiertos, "cerrados": cerrados, "lectura": lectura}


def _indicadores_registrados(registros: list[models.RegistroMonitoreo]) -> list[dict[str, Any]]:
    """0.10.76: cada indicador registrado (por título) con su último valor, el anterior y cuántas veces se midió.
    Sólo cuentan los registros con valor: uno sin valor no es una medición ni cambia la fecha."""
    por_titulo: dict[str, dict[str, Any]] = {}
    orden = sorted((r for r in registros if r.tipo == "indicador" and r.valor_indicador is not None),
                   key=lambda r: (r.creado_en.isoformat() if r.creado_en else "", r.id or 0))
    for r in orden:
        clave = " ".join((r.titulo or "").lower().split())
        d = por_titulo.setdefault(clave, {"titulo": r.titulo, "mediciones": 0, "valor": None, "anterior": None,
                                         "fecha": None})
        d["titulo"] = r.titulo
        d["mediciones"] += 1
        d["anterior"], d["valor"] = d["valor"], r.valor_indicador
        d["fecha"] = r.creado_en.isoformat() if r.creado_en else d["fecha"]
    return sorted(por_titulo.values(), key=lambda d: d["fecha"] or "", reverse=True)


# Palabras enteras que dicen «así se mide»: «antes» dentro de «participantes» o «plazo» dentro de «reemplazo» no cuentan.
_CLAVES_INDICADOR = re.compile(
    r"\b(indicador(es)?|medir|medirá|mediremos|medimos|medición|mediciones|medicion|porcentaje|tasa|"
    r"línea de base|linea de base|antes y después|antes y despues|kpi|metas?)\b", re.IGNORECASE)


def _indicador_propuesto(proyecto: models.ProyectoIA) -> str | None:
    """0.10.76: la primera frase de la propuesta (entrega y situación) que dice cómo medir el resultado, si la hay."""
    for texto in (proyecto.entrega_final, proyecto.situacion):
        for frase in re.split(r"(?<=[.!?])\s+|\n+", texto or ""):
            frase = " ".join(frase.split())
            if frase and _CLAVES_INDICADOR.search(frase):
                return frase if len(frase) <= 240 else frase[:239].rstrip() + "…"
    return None


@router.get("/proyecto/{proyecto_id}")
def listar_monitoreo(
    proyecto_id: int,
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    proyecto = _proyecto_o_404(db, proyecto_id)
    _exigir_acceso(proyecto, usuario)
    registros = (
        db.query(models.RegistroMonitoreo)
        .filter(models.RegistroMonitoreo.proyecto_id == proyecto_id)
        .order_by(models.RegistroMonitoreo.creado_en.desc(), models.RegistroMonitoreo.id.desc())
        .all()
    )
    modo = _modo(proyecto)
    # 0.10.76: lo propio del proyecto (su prototipo en acción y sus indicadores), sólo de la etapa vigente: la prueba
    # con datos ficticios no se mezcla con el piloto real. En cartera Monitoreo no está habilitado y no se calcula.
    etapa = [r for r in registros if _etapa(r) == modo] if modo != "cartera" else []
    por_tipo_etapa: dict[str, int] = {}
    for r in etapa:
        por_tipo_etapa[r.tipo] = por_tipo_etapa.get(r.tipo, 0) + 1
    return {
        "proyecto_id": proyecto_id,
        "proyecto_titulo": proyecto.titulo or "Proyecto",
        "habilitado": _habilitado(proyecto),
        "modo": modo,
        "puede_registrar": _puede_registrar(proyecto, usuario),
        "alcance": ALCANCE["propio"] if _propio(proyecto) else ALCANCE[modo],
        "propio": _propio(proyecto),
        "registros": [_registro_out(r) for r in registros],
        "metricas": _metricas_registros(registros),
        "en_accion": prototipos_incubadora.en_accion(proyecto.id) if modo != "cartera" else None,
        "indicador_propuesto": _indicador_propuesto(proyecto) if modo != "cartera" else None,
        "indicadores_registrados": _indicadores_registrados(etapa),
        "por_tipo_etapa": por_tipo_etapa,
    }


@router.get("/mio")
def mi_monitoreo(
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    """0.10.77: la pantalla propia de Monitoreo. Devuelve el Monitoreo del proyecto de quien entra: el del equipo al que
    se sumó o, si no, el suyo, como la Incubadora. Sólo lee: si todavía no tiene proyecto no lo crea (eso lo hace la
    Incubadora) y responde con «proyecto_id» vacío y el modo de su grupo."""
    proyecto = equipos.proyecto_ajeno(db, usuario) or (
        db.query(models.ProyectoIA).filter(models.ProyectoIA.usuario_id == usuario.id).order_by(models.ProyectoIA.id).first()
    )
    if proyecto is None:
        modo = "prueba" if grupos.de(usuario) in grupos_prueba() else "cartera"
        return {"proyecto_id": None, "modo": modo, "alcance": ALCANCE[modo], "puede_registrar": False}
    return listar_monitoreo(proyecto.id, db, usuario)


@router.post("/proyecto/{proyecto_id}")
def registrar_monitoreo(
    proyecto_id: int,
    payload: dict = Body(default_factory=dict),
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    proyecto = _proyecto_o_404(db, proyecto_id)
    _exigir_acceso(proyecto, usuario)
    _exigir_registro(proyecto, usuario)

    tipo = str(payload.get("tipo") or "").strip()
    if tipo not in TIPOS_REGISTRO:
        raise HTTPException(422, "tipo de registro invalido")

    estado = str(payload.get("estado") or "abierto").strip()
    if estado not in ESTADOS_REGISTRO:
        raise HTTPException(422, "estado de registro invalido")

    titulo = _texto_seguro(payload.get("titulo"), 160)
    contenido = _texto_seguro(payload.get("contenido"), 1800)
    if not titulo or not contenido:
        raise HTTPException(422, "titulo y contenido son obligatorios")

    valor_indicador = None
    if tipo == "indicador" and payload.get("valor_indicador") is not None:
        try:
            valor_indicador = float(payload["valor_indicador"])
        except (TypeError, ValueError):
            raise HTTPException(422, "valor_indicador invalido")

    registro = models.RegistroMonitoreo(
        proyecto_id=proyecto_id,
        usuario_id=usuario.id,
        tipo=tipo,
        titulo=titulo,
        contenido=contenido,
        estado=estado,
        valor_indicador=valor_indicador,
        metadata_evento={"tipo_label": TIPOS_REGISTRO[tipo], "etapa": _modo(proyecto)},
    )
    db.add(registro)
    actividad_svc.registrar(
        db,
        usuario=usuario,
        modulo="monitoreo",
        accion="registro_monitoreo_creado",
        resumen=f"Registro de monitoreo ({tipo}) creado",
        proyecto_id=proyecto_id,
        metadata={"tipo": tipo, "estado": estado, "etapa": _modo(proyecto)},
    )
    db.commit()
    return listar_monitoreo(proyecto_id, db, usuario)


@router.patch("/registros/{registro_id}")
def actualizar_estado_monitoreo(
    registro_id: int,
    payload: dict = Body(default_factory=dict),
    db: Session = Depends(get_db),
    usuario: models.Usuario = Depends(get_current_user),
):
    estado = str(payload.get("estado") or "").strip()
    if estado not in ESTADOS_REGISTRO:
        raise HTTPException(422, "estado de registro invalido")
    registro = db.get(models.RegistroMonitoreo, registro_id)
    if not registro:
        raise HTTPException(404, "registro no encontrado")
    proyecto = _proyecto_o_404(db, registro.proyecto_id)
    _exigir_acceso(proyecto, usuario)
    _exigir_registro(proyecto, usuario)
    if _etapa(registro) != _modo(proyecto):
        raise HTTPException(403, "Este registro es de otra etapa y queda como historial de solo lectura.")
    anterior = registro.estado
    registro.estado = estado
    metadata = dict(registro.metadata_evento or {})
    cambios = list(metadata.get("cambios_estado") or [])
    cambios.append({
        "de": anterior,
        "a": estado,
        "usuario_id": usuario.id,
        "fecha": dt.datetime.now(dt.timezone.utc).isoformat(),
    })
    metadata["cambios_estado"] = cambios
    registro.metadata_evento = metadata
    db.add(registro)
    actividad_svc.registrar(
        db,
        usuario=usuario,
        modulo="monitoreo",
        accion="estado_monitoreo_actualizado",
        resumen="Estado de seguimiento actualizado por una persona autorizada",
        proyecto_id=registro.proyecto_id,
        metadata={"registro_id": registro.id, "de": anterior, "a": estado, "etapa": _etapa(registro)},
    )
    db.commit()
    db.refresh(registro)
    return _registro_out(registro)
