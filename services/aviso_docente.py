"""Aviso por correo al docente cuando un participante escribe en el espacio docente de la Incubadora y, desde la
0.10.81, al participante cuando el docente le escribe a él.

Corre después de responder la carga (BackgroundTasks) con su propia sesión: si el SMTP falla o tarda, la
consulta ya quedó guardada. Cada aviso deja un evento en la bitácora con el id del mensaje; si ya hay uno
«enviada» para ese mensaje no se vuelve a mandar (una consulta = un aviso).
"""
from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from sqlalchemy.orm import Session

import models
from config import settings
from services import actividad as actividad_svc
from services import equipos, notificaciones

log = logging.getLogger(__name__)

ACCION_AVISO = "aviso_docente_consulta"
ACCION_AVISO_PARTICIPANTE = "aviso_participante_mensaje_docente"  # 0.10.81
REMITENTE_CONSULTA = "consulta_docente"
REMITENTE_DOCENTE = "docente"
ACCION_SIN_RESPUESTA = "consulta_docente_no_requiere_respuesta"


def atendidas_sin_respuesta(db: Session, proyecto_ids: list[int] | None = None) -> dict[int, int]:
    """Por proyecto, el id de la última consulta que el docente marcó como «no requiere respuesta» (0.10.69).

    La marca es un evento de la bitácora: no borra ni cambia la consulta, y una consulta posterior (id mayor)
    vuelve a quedar pendiente."""
    consulta = db.query(models.ActivityEvent).filter(models.ActivityEvent.accion == ACCION_SIN_RESPUESTA)
    if proyecto_ids is not None:
        consulta = consulta.filter(models.ActivityEvent.proyecto_id.in_(proyecto_ids))
    marcas: dict[int, int] = {}
    for evento in consulta.all():
        hasta = (evento.metadata_evento or {}).get("hasta_mensaje_id")
        if evento.proyecto_id and isinstance(hasta, int):
            marcas[evento.proyecto_id] = max(marcas.get(evento.proyecto_id, 0), hasta)
    return marcas


def _aviso_ya_enviado(db: Session, proyecto_id: int, mensaje_id: int, accion: str = ACCION_AVISO) -> bool:
    eventos = db.query(models.ActivityEvent).filter(
        models.ActivityEvent.proyecto_id == proyecto_id,
        models.ActivityEvent.accion == accion,
    ).all()
    return any((e.metadata_evento or {}).get("mensaje_id") == mensaje_id
               and (e.metadata_evento or {}).get("estado") == "enviada" for e in eventos)


def avisar_consulta_docente(bind: Any, mensaje_id: int) -> str:
    """Tarea en segundo plano. Nunca levanta: devuelve el estado y lo deja registrado."""
    try:
        with Session(bind=bind) as db:
            mensaje = db.get(models.MensajeProyectoIA, mensaje_id)
            if not mensaje or mensaje.remitente != REMITENTE_CONSULTA:
                return "omitida"
            proyecto = db.get(models.ProyectoIA, mensaje.proyecto_id)
            if _aviso_ya_enviado(db, mensaje.proyecto_id, mensaje_id):
                return "duplicado"
            estado, error = notificaciones.enviar_aviso_consulta_docente(
                notificaciones.destinatarios_docente(), mensaje.proyecto_id,
                proyecto.titulo if proyecto else None, mensaje.creado_en,
            )
            if estado != "enviada":
                log.warning("aviso al docente por la consulta %s: %s (%s)", mensaje_id, estado, error)
            actividad_svc.registrar(
                db, usuario=None, modulo="incubadora", accion=ACCION_AVISO,
                resumen="Aviso por correo al docente de una consulta nueva",
                proyecto_id=mensaje.proyecto_id,
                metadata={"mensaje_id": mensaje_id, "estado": estado, "error": (error or "")[:200] or None},
            )
            db.commit()
            return estado
    except Exception:  # noqa: BLE001 — el aviso nunca debe afectar la consulta ya guardada.
        log.exception("no se pudo procesar el aviso al docente de la consulta %s", mensaje_id)
        return "error"


def destinatarios_participantes(proyecto) -> list[str]:
    """Quienes integran el proyecto (quien lo abrió y su equipo), con cuenta activa; nunca la administración ni las
    cuentas de prueba excluidas de las métricas."""
    excluidos = {c.strip().lower() for c in (settings.usuarios_excluidos_metricas or "").split(",") if c.strip()}
    salida: list[str] = []
    for persona in equipos.personas(proyecto):
        correo = (getattr(persona, "email", "") or "").strip()
        if (not correo or "@" not in correo or any(c.isspace() for c in correo) or not getattr(persona, "activo", True)
                or getattr(persona, "rol", None) == "admin" or correo.lower() in excluidos or correo in salida):
            continue
        salida.append(correo)
    return salida


def avisar_mensaje_docente(bind: Any, mensaje_id: int) -> str:
    """0.10.81: tarea en segundo plano. Avisa por correo, sin el texto, que el docente escribió en el proyecto.
    Nunca levanta: devuelve el estado y lo deja en la bitácora (sin direcciones). Un mensaje = un aviso."""
    try:
        with Session(bind=bind) as db:
            mensaje = db.get(models.MensajeProyectoIA, mensaje_id)
            if not mensaje or mensaje.remitente != REMITENTE_DOCENTE:
                return "omitida"
            proyecto = db.get(models.ProyectoIA, mensaje.proyecto_id)
            if proyecto is None:
                return "omitida"
            if _aviso_ya_enviado(db, proyecto.id, mensaje_id, ACCION_AVISO_PARTICIPANTE):
                return "duplicado"
            destinatarios = destinatarios_participantes(proyecto)
            estado, error = notificaciones.enviar_aviso_mensaje_docente(destinatarios, proyecto.id, proyecto.titulo)
            if estado != "enviada":
                log.warning("aviso al participante por el mensaje docente %s: %s (%s)", mensaje_id, estado, error)
            actividad_svc.registrar(
                db, usuario=None, modulo="incubadora", accion=ACCION_AVISO_PARTICIPANTE,
                resumen="Aviso por correo al participante de un mensaje docente",
                proyecto_id=proyecto.id,
                metadata={"mensaje_id": mensaje_id, "estado": estado, "destinatarios": len(destinatarios),
                          "error": (error or "")[:200] or None},
            )
            db.commit()
            return estado
    except Exception:  # noqa: BLE001 — el aviso nunca debe afectar el mensaje ya guardado.
        log.exception("no se pudo procesar el aviso al participante del mensaje docente %s", mensaje_id)
        return "error"


def consultas_sin_respuesta(db: Session, ahora: dt.datetime | None = None, mas_de_dias: int = -1) -> list[dict]:
    """Consultas posteriores a la última respuesta docente de cada proyecto (misma regla que
    `_consulta_docente_pendiente`), con más de `mas_de_dias` días de antigüedad. Sin texto ni datos personales."""
    ahora = ahora or models.now()
    marcas = atendidas_sin_respuesta(db)
    salida = []
    for proyecto in db.query(models.ProyectoIA).all():
        canal = sorted(
            (m for m in (proyecto.mensajes or []) if m.remitente in {REMITENTE_CONSULTA, REMITENTE_DOCENTE}),
            key=lambda m: (m.creado_en or dt.datetime.min, m.id or 0),
        )
        ultima_respuesta = max((i for i, m in enumerate(canal) if m.remitente == REMITENTE_DOCENTE), default=-1)
        for m in canal[ultima_respuesta + 1:]:
            if (m.id or 0) <= marcas.get(proyecto.id, 0):
                continue  # el docente marcó que no requiere respuesta
            dias = (ahora - m.creado_en).days if m.creado_en else 0
            if dias > mas_de_dias:
                salida.append({"mensaje_id": m.id, "proyecto_id": proyecto.id, "titulo": proyecto.titulo,
                               "creado_en": m.creado_en, "dias": dias})
    return sorted(salida, key=lambda p: (p["creado_en"] or dt.datetime.min, p["mensaje_id"]))
