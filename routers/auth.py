"Login/logout y administracion basica de usuarios."
from __future__ import annotations

import re

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

import models
import schemas
from core.auth import (
    COOKIE_MAX_AGE,
    COOKIE_NAME,
    DESTINOS_INGRESO,
    VER_COMO_COOKIE,
    VER_COMO_MAX_AGE,
    authenticate_user,
    destino_ingreso,
    get_current_user,
    hash_password,
    limpiar_login_fallidos,
    login_bloqueado,
    login_html,
    make_token,
    make_ver_como,
    registrar_login_fallido,
    require_admin,
    revocar_sesiones,
    sesion_vigente,
    token_info,
    ver_como_info,
    ver_como_vence_en,
    verify_password,
)
from database import get_db
from services import actividad as actividad_svc
from services import grupos

router = APIRouter()
API_ROLES = {"admin", "analista", "lector"}

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def limpiar_email_notificaciones(valor: str | None) -> str | None:
    email = str(valor or "").strip().lower()
    if not email:
        return None
    if not EMAIL_RE.match(email):
        raise HTTPException(422, "correo de notificaciones inválido")
    return email


@router.get("/login", response_class=HTMLResponse)
def login_form(ir: str | None = None):
    return HTMLResponse(login_html(ir=ir), headers={"Cache-Control": "no-store"})


@router.post("/login")
async def login(request: Request, db: Session = Depends(get_db)):
    ip = request.client.host if request.client else "desconocida"
    try:
        form = await request.form()
    except Exception:
        # Formularios malformados (escáneres automáticos): no es un error del servidor.
        return HTMLResponse(login_html("No se pudo leer el formulario."), status_code=400, headers={"Cache-Control": "no-store"})
    email = str(form.get("email") or "").strip().lower()
    password = str(form.get("password") or "")
    ir = destino_ingreso(form.get("ir"))  # 0.10.73: pantalla a la que se vuelve (lista cerrada)
    # Freno por origen y también por cuenta: muchos orígenes distintos probando la misma
    # cuenta ya no esquivan el límite. Bloquea la cuenta 5 minutos, no la desactiva.
    cuenta = f"cuenta:{email}"
    if login_bloqueado(ip) or (email and login_bloqueado(cuenta)):
        return HTMLResponse(
            login_html("Demasiados intentos fallidos. Esperá unos minutos antes de volver a probar.", ir=ir),
            status_code=429,
            headers={"Cache-Control": "no-store"},
        )
    user = authenticate_user(db, email, password)
    if not user:
        registrar_login_fallido(ip)
        if email:
            registrar_login_fallido(cuenta)
        return HTMLResponse(login_html("Usuario o contraseña incorrectos", ir=ir), status_code=401, headers={"Cache-Control": "no-store"})
    limpiar_login_fallidos(ip)
    limpiar_login_fallidos(cuenta)
    resp = RedirectResponse(DESTINOS_INGRESO[ir] if ir else "/#/inicio", status_code=303)
    resp.delete_cookie(VER_COMO_COOKIE)  # 0.10.74: entrar de nuevo nunca retoma una vista «ver como» vieja
    resp.set_cookie(COOKIE_NAME, make_token(user.id), max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax", secure=True)
    return resp


@router.get("/logout")
def logout(request: Request, db: Session = Depends(get_db)):
    # Salir invalida el token (no solo borra la cookie): una copia robada deja de valer.
    # Como el corte es por fecha de emisión, también cierra las otras sesiones de la cuenta.
    info = token_info(request.cookies.get(COOKIE_NAME))
    if info:
        user = db.get(models.Usuario, info[0])
        if user and sesion_vigente(user, info[1]):
            revocar_sesiones(user)
            db.commit()
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie(COOKIE_NAME)
    resp.delete_cookie(VER_COMO_COOKIE)
    return resp


# 0.10.74: «ver como». La cuenta administradora abre Gov4Action como la ve un participante, en sólo lectura.
class VerComoIn(BaseModel):
    usuario_id: int


def _usuario_visto(u: models.Usuario) -> dict:
    return {"id": u.id, "nombre": u.nombre, "email": u.email, "grupo": grupos.de(u)}


@router.post("/api/admin/ver-como")
def ver_como_iniciar(datos: VerComoIn, admin: models.Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    visto = db.get(models.Usuario, datos.usuario_id)
    if visto is None:
        raise HTTPException(404, "no existe esa cuenta")
    if visto.rol == "admin":
        raise HTTPException(400, "la vista «ver como» es para cuentas de participantes")
    # Queda registrado quién miró como quién: es lo único que se guarda de la vista.
    actividad_svc.registrar(db, usuario=admin, modulo="administracion", accion="ver_como_inicio",
                            resumen=f"Vista de sólo lectura como la cuenta {visto.id}")
    db.commit()
    resp = JSONResponse({"ok": True, "usuario": _usuario_visto(visto)})
    resp.set_cookie(VER_COMO_COOKIE, make_ver_como(admin.id, visto.id), max_age=VER_COMO_MAX_AGE, httponly=True,
                    samesite="lax", secure=True)
    return resp


@router.get("/api/admin/ver-como/cuentas")
def ver_como_cuentas(_admin: models.Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    """0.10.75: todos los participantes, con su grupo y su proyecto si lo tiene, para elegir a quién mirar desde la
    barra de arriba. Incluye a quienes todavía no abrieron su proyecto: también se puede ver qué ven ellos."""
    filas = db.query(models.ProyectoIA.id, models.ProyectoIA.usuario_id, models.ProyectoIA.titulo,
                     models.ProyectoIA.estado).all()
    por_id = {f.id: f for f in filas}
    propio = {f.usuario_id: f for f in filas}
    # Quien se sumó a un proyecto en equipo ve ese proyecto en «Mi proyecto» (equipos.proyecto_ajeno): va primero.
    en_equipo = {i.usuario_id: por_id.get(i.proyecto_id)
                 for i in db.query(models.IntegranteProyectoIA.usuario_id, models.IntegranteProyectoIA.proyecto_id)}
    cuentas = []
    for u in db.query(models.Usuario).filter(models.Usuario.rol != "admin").order_by(models.Usuario.id).all():
        p = en_equipo.get(u.id) or propio.get(u.id)
        cuentas.append({**_usuario_visto(u), "activo": bool(u.activo),
                        "proyecto": {"id": p.id, "titulo": p.titulo, "estado": p.estado,
                                     "en_equipo": u.id in en_equipo} if p else None})
    return cuentas


@router.get("/api/admin/ver-como")
def ver_como_estado(request: Request, db: Session = Depends(get_db)):
    """Si hay una vista activa, a quién se está mirando (para el aviso fijo y el botón de salir)."""
    vista = ver_como_info(request)
    if not vista:
        return {"activo": False}
    visto = db.get(models.Usuario, vista[1])
    # Si la cuenta mirada ya no existe o pasó a administradora, la pantalla muestra la propia cuenta (sin poder
    # escribir): el aviso lo dice y ofrece salir, en lugar de nombrar a alguien que no se está viendo.
    valida = visto is not None and visto.rol != "admin"
    return {"activo": True, "valida": valida, "usuario": _usuario_visto(visto) if valida else None,
            "vence_en": ver_como_vence_en(request)}


@router.post("/api/admin/ver-como/salir")
def ver_como_salir():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(VER_COMO_COOKIE)
    return resp


@router.get("/api/me", response_model=schemas.UsuarioOut)
def me(user: models.Usuario = Depends(get_current_user)):
    return user


@router.patch("/api/me/notificaciones", response_model=schemas.UsuarioOut)
def actualizar_notificaciones(payload: schemas.UsuarioNotificacionesUpdate, user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    user.email_notificaciones = limpiar_email_notificaciones(payload.email_notificaciones)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/api/usuarios", response_model=list[schemas.UsuarioOut])
def listar_usuarios(_admin: models.Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(models.Usuario).order_by(models.Usuario.email.asc()).all()


@router.post("/api/usuarios", response_model=schemas.UsuarioOut)
def crear_usuario(payload: schemas.UsuarioCreate, _admin: models.Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if not email or "@" not in email:
        raise HTTPException(422, "email inválido")
    if payload.rol not in API_ROLES:
        raise HTTPException(422, "rol inválido")
    if len(payload.password) < 8:
        raise HTTPException(422, "la contraseña debe tener al menos 8 caracteres")
    if db.query(models.Usuario).filter(models.Usuario.email == email).first():
        raise HTTPException(409, "ya existe un usuario con ese email")
    user = models.Usuario(email=email, nombre=payload.nombre.strip() or email, password_hash=hash_password(payload.password), rol=payload.rol, activo=True,
                          grupo=grupos.normalizar(payload.grupo))
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _registrar(db: Session, admin: models.Usuario, accion: str, resumen: str, usuario_id: int) -> None:
    from services import actividad as actividad_svc

    actividad_svc.registrar(db, usuario=admin, modulo="usuarios", accion=accion, resumen=resumen,
                            metadata={"usuario_afectado_id": usuario_id})


@router.patch("/api/usuarios/{usuario_id}", response_model=schemas.UsuarioOut)
def cambiar_estado_usuario(usuario_id: int, payload: schemas.UsuarioEstadoUpdate,
                           admin: models.Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    """Activa o desactiva un usuario. Desactivarlo cierra además todas sus sesiones."""
    user = db.get(models.Usuario, usuario_id)
    if not user:
        raise HTTPException(404, "usuario no encontrado")
    if user.id == admin.id and not payload.activo:
        raise HTTPException(409, "no podés desactivar tu propio usuario")
    user.activo = payload.activo
    if not payload.activo:
        revocar_sesiones(user)
    _registrar(db, admin, "usuario_activado" if payload.activo else "usuario_desactivado",
               "Usuario activado" if payload.activo else "Usuario desactivado y sus sesiones cerradas", user.id)
    db.commit()
    db.refresh(user)
    return user


@router.post("/api/usuarios/{usuario_id}/cerrar-sesiones", response_model=schemas.UsuarioOut)
def cerrar_sesiones_usuario(usuario_id: int, admin: models.Usuario = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(models.Usuario, usuario_id)
    if not user:
        raise HTTPException(404, "usuario no encontrado")
    revocar_sesiones(user)
    _registrar(db, admin, "sesiones_cerradas", "Sesiones del usuario cerradas por administración", user.id)
    db.commit()
    db.refresh(user)
    return user


@router.post("/api/me/cerrar-sesiones")
def cerrar_mis_sesiones(user: models.Usuario = Depends(get_current_user), db: Session = Depends(get_db)):
    """Cierra la sesión en todos los dispositivos, incluido este."""
    revocar_sesiones(user)
    db.commit()
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE_NAME)
    return resp


@router.post("/api/me/password")
def cambiar_password(payload: schemas.CambioPassword, user: models.Usuario = Depends(get_current_user),
                     db: Session = Depends(get_db)):
    """Cambia la contraseña y cierra las demás sesiones; esta sigue abierta con un token nuevo."""
    # Mismo freno que el login: con una cookie robada no se puede probar la contraseña sin límite.
    clave = f"cambio-password:{user.id}"
    if login_bloqueado(clave):
        raise HTTPException(429, "Demasiados intentos. Esperá unos minutos y volvé a probar.")
    if not verify_password(payload.actual, user.password_hash):
        registrar_login_fallido(clave)
        raise HTTPException(403, "la contraseña actual no es correcta")
    if len(payload.nueva) < 8:
        raise HTTPException(422, "la contraseña nueva debe tener al menos 8 caracteres")
    user.password_hash = hash_password(payload.nueva)
    revocar_sesiones(user)
    db.commit()
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE_NAME, make_token(user.id), max_age=COOKIE_MAX_AGE, httponly=True, samesite="lax", secure=True)
    return resp
