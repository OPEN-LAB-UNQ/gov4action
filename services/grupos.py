"""Grupos de cursada (0.10.62): cada participante ve los proyectos y la votación de su propio grupo.

Una cuenta sin grupo pertenece al grupo por defecto. Desde la 0.10.71 es la comisión 1 del grupo A, la de agosto: la comisión 2
tiene su grupo, «Grupo A · comisión 2» (sql/0171_comision2.sql). Las cuentas nuevas conviene darlas de alta con su
grupo. La cuenta administradora ve todos.

Desde la 0.10.80, los grupos de GRUPOS_SIN_VOTACION (la comisión 2 del grupo A y el grupo B) no usan votación.
"""
from __future__ import annotations

from typing import Optional


def normalizar(valor: Optional[str]) -> Optional[str]:
    """Vacío o sólo espacios es el grupo por defecto (None)."""
    return (valor or "").strip() or None


def de(usuario) -> Optional[str]:
    return normalizar(getattr(usuario, "grupo", None))


def ve_todo(usuario) -> bool:
    """Sin usuario (llamadas internas) o con la cuenta administradora no se filtra por grupo."""
    return usuario is None or getattr(usuario, "rol", None) == "admin"


def filtro(columna, grupo: Optional[str]):
    """Condición SQL «del mismo grupo»: sin grupo coincide con NULL, no con todos."""
    grupo = normalizar(grupo)
    return columna.is_(None) if grupo is None else columna == grupo


def sin_votacion() -> set[str]:
    """Grupos de cursada que no usan votación (0.10.80): no ven la actividad y el servidor no acepta sus votos."""
    from config import settings

    return {g.strip() for g in (settings.grupos_sin_votacion or "").split(",") if g.strip()}


def con_votacion(usuario) -> bool:
    """La cuenta administradora y las llamadas internas, siempre; un participante, si su grupo usa votación."""
    return ve_todo(usuario) or de(usuario) not in sin_votacion()
