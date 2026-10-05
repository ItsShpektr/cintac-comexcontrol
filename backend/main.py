from __future__ import annotations

from contextlib import asynccontextmanager
from math import ceil
from pathlib import Path
from threading import Lock
from time import monotonic

from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, text
from sqlalchemy.orm import Session

import models
import schemas
from config import get_settings
from database import Base, SessionLocal, engine, get_db
from security import (
    create_access_token,
    get_current_user,
    hash_password,
    password_needs_rehash,
    require_roles,
    verify_password,
)
from tariff_service import activate_version, create_tariff_version, seed_initial_tariffs


settings = get_settings()

LOGIN_WINDOW_SECONDS = 600
LOGIN_MAX_ATTEMPTS = 8
_login_attempts: dict[str, list[float]] = {}
_login_lock = Lock()


def enforce_login_rate_limit(identifier: str):
    now = monotonic()
    with _login_lock:
        recent = [ts for ts in _login_attempts.get(identifier, []) if now - ts < LOGIN_WINDOW_SECONDS]
        _login_attempts[identifier] = recent
        if len(recent) >= LOGIN_MAX_ATTEMPTS:
            raise HTTPException(status_code=429, detail="Demasiados intentos de acceso. Intente nuevamente más tarde")


def record_failed_login(identifier: str):
    with _login_lock:
        _login_attempts.setdefault(identifier, []).append(monotonic())


def clear_login_attempts(identifier: str):
    with _login_lock:
        _login_attempts.pop(identifier, None)



def bootstrap_admin(db: Session):
    if not settings.bootstrap_admin_email or not settings.bootstrap_admin_password:
        return
    if len(settings.bootstrap_admin_password) < 10:
        raise RuntimeError("BOOTSTRAP_ADMIN_PASSWORD debe tener al menos 10 caracteres")
    existing = db.query(models.Usuario).filter(func.lower(models.Usuario.email) == settings.bootstrap_admin_email.lower()).first()
    if existing:
        return
    user = models.Usuario(
        nombre=settings.bootstrap_admin_name or "Administrador ComexControl",
        email=settings.bootstrap_admin_email.lower(),
        password_hash=hash_password(settings.bootstrap_admin_password),
        rol="Administrador",
    )
    db.add(user)
    db.commit()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        bootstrap_admin(db)
        excel_path = Path(__file__).resolve().parent / "Cotizador - Calculadora.xlsx"
        seed_initial_tariffs(db, excel_path)
    finally:
        db.close()
    yield


app = FastAPI(
    title=settings.app_name,
    version="2.0.0",
    docs_url="/docs" if settings.environment.lower() != "production" else None,
    redoc_url=None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Authorization", "Content-Type"],
)


@app.middleware("http")
async def security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if settings.environment.lower() == "production":
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    return response


def audit(db: Session, user_id: int | None, action: str, resource: str, resource_id=None, detail: str | None = None):
    db.add(models.Auditoria(
        usuario_id=user_id,
        accion=action,
        recurso=resource,
        recurso_id=str(resource_id) if resource_id is not None else None,
        detalle=detail,
    ))



@app.get("/")
def home():
    return {"message": "API ComexControl activa"}


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "OK", "version": "2.0.0", "database": "OK"}
    except Exception:
        raise HTTPException(status_code=503, detail="Servicio temporalmente no disponible")


@app.post("/api/login", response_model=schemas.Token)
def login(user: schemas.UsuarioLogin, request: Request, db: Session = Depends(get_db)):
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{client_ip}:{user.email.lower()}"
    enforce_login_rate_limit(identifier)
    db_user = db.query(models.Usuario).filter(func.lower(models.Usuario.email) == user.email.lower()).first()
    if not db_user or not verify_password(user.password, db_user.password_hash):
        record_failed_login(identifier)
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")

    clear_login_attempts(identifier)
    if password_needs_rehash(db_user.password_hash):
        db_user.password_hash = hash_password(user.password)
        db.commit()

    audit(db, db_user.id, "LOGIN", "sesion", detail="Inicio de sesión exitoso")
    db.commit()
    return {
        "access_token": create_access_token(db_user),
        "token_type": "bearer",
        "rol": db_user.rol,
        "nombre": db_user.nombre,
    }


@app.get("/api/me", response_model=schemas.UsuarioPublico)
def me(current_user: models.Usuario = Depends(get_current_user)):
    return current_user


@app.get("/api/routes")
def routes(
    _: models.Usuario = Depends(require_roles("Analista COMEX")),
    db: Session = Depends(get_db),
):
    active = db.query(models.VersionTarifa).filter(models.VersionTarifa.estado == "ACTIVA").first()
    if not active:
        return {"version_id": None, "origenes": [], "destinos": [], "rutas": []}
    rows = db.query(models.Tarifa).filter(models.Tarifa.version_id == active.id).all()
    route_pairs = sorted({(row.puerto_origen, row.puerto_destino) for row in rows})
    return {
        "version_id": active.id,
        "origenes": sorted({row.puerto_origen for row in rows}),
        "destinos": sorted({row.puerto_destino for row in rows}),
        "rutas": [{"origen": origin, "destino": destination} for origin, destination in route_pairs],
    }


@app.post("/api/cotizar")
def cotizar_flete(
    request: schemas.CotizacionRequest,
    current_user: models.Usuario = Depends(require_roles("Analista COMEX")),
    db: Session = Depends(get_db),
):
    active = db.query(models.VersionTarifa).filter(models.VersionTarifa.estado == "ACTIVA").first()
    if not active:
        raise HTTPException(status_code=409, detail="No existe una versión activa de tarifas")

    routes = db.query(models.Tarifa).filter(
        models.Tarifa.version_id == active.id,
        func.lower(models.Tarifa.puerto_origen) == request.puerto_origen.lower(),
        func.lower(models.Tarifa.puerto_destino) == request.puerto_destino.lower(),
    ).all()
    if not routes:
        raise HTTPException(status_code=404, detail="Ruta no encontrada en la versión activa de tarifas")

    # RN-02 del informe: máximo 25 toneladas por contenedor.
    cantidad = max(1, ceil(request.peso_toneladas / 25))
    alternatives = []
    for route in routes:
        if request.tipo_contenedor == "20'":
            unit_min, unit_max = route.tarifa_20_min, route.tarifa_20_max
        else:
            unit_min, unit_max = route.tarifa_40_min, route.tarifa_40_max

        total_min = round(unit_min * cantidad, 2)
        total_max = round(unit_max * cantidad, 2)
        item = {
            "tarifa_id": route.id,
            "tipo_ruta": route.tipo_ruta,
            "tarifa_min_usd": unit_min,
            "tarifa_max_usd": unit_max,
            "total_min_usd": total_min,
            "total_max_usd": total_max,
            "transito_min_dias": route.transito_min + request.contingencia_dias,
            "transito_max_dias": route.transito_max + request.contingencia_dias,
            "transito_base_min_dias": route.transito_min,
            "transito_base_max_dias": route.transito_max,
            "fuente": route.fuente or "Sin fuente indicada",
        }
        if request.tipo_cambio_clp_usd:
            item["total_min_clp"] = round(total_min * request.tipo_cambio_clp_usd)
            item["total_max_clp"] = round(total_max * request.tipo_cambio_clp_usd)
        alternatives.append(item)

    response = {
        "version_id": active.id,
        "version_archivo": active.nombre_archivo,
        "puerto_origen": request.puerto_origen,
        "puerto_destino": request.puerto_destino,
        "tipo_contenedor": request.tipo_contenedor,
        "peso_toneladas": request.peso_toneladas,
        "cantidad_contenedores": cantidad,
        "contingencia_dias": request.contingencia_dias,
        "tipo_cambio_clp_usd": request.tipo_cambio_clp_usd,
        "alternativas": alternatives,
    }

    quote = models.Cotizacion(
        usuario_id=current_user.id,
        version_id=active.id,
        puerto_origen=request.puerto_origen,
        puerto_destino=request.puerto_destino,
        tipo_contenedor=request.tipo_contenedor,
        peso_toneladas=request.peso_toneladas,
        cantidad_contenedores=cantidad,
        contingencia_dias=request.contingencia_dias,
        tipo_cambio_clp_usd=request.tipo_cambio_clp_usd,
        resultado_json=response,
    )
    db.add(quote)
    db.flush()
    audit(db, current_user.id, "COTIZAR", "cotizacion", quote.id, f"{request.puerto_origen} → {request.puerto_destino}")
    db.commit()
    response["cotizacion_id"] = quote.id
    return response


@app.get("/api/history")
def history(
    current_user: models.Usuario = Depends(require_roles("Analista COMEX", "Jefatura COMEX", "Administrador")),
    db: Session = Depends(get_db),
):
    query = db.query(models.Cotizacion)
    if current_user.rol == "Analista COMEX":
        query = query.filter(models.Cotizacion.usuario_id == current_user.id)
    rows = query.order_by(models.Cotizacion.created_at.desc()).limit(50).all()
    return [{
        "id": row.id,
        "usuario": row.usuario.nombre if row.usuario else "Desconocido",
        "ruta": f"{row.puerto_origen} → {row.puerto_destino}",
        "contenedor": row.tipo_contenedor,
        "cantidad": row.cantidad_contenedores,
        "peso_toneladas": row.peso_toneladas,
        "version_id": row.version_id,
        "created_at": row.created_at,
    } for row in rows]


@app.get("/api/admin/users", response_model=list[schemas.UsuarioPublico])
def list_users(
    _: models.Usuario = Depends(require_roles("Administrador")),
    db: Session = Depends(get_db),
):
    return db.query(models.Usuario).order_by(models.Usuario.nombre).all()


@app.post("/api/admin/users", response_model=schemas.UsuarioPublico, status_code=201)
def create_user(
    user: schemas.UsuarioAdminCreate,
    current_user: models.Usuario = Depends(require_roles("Administrador")),
    db: Session = Depends(get_db),
):
    if db.query(models.Usuario).filter(func.lower(models.Usuario.email) == user.email.lower()).first():
        raise HTTPException(status_code=409, detail="El correo ya está registrado")
    new_user = models.Usuario(
        nombre=user.nombre,
        email=user.email.lower(),
        password_hash=hash_password(user.password),
        rol=user.rol,
    )
    db.add(new_user)
    db.flush()
    audit(db, current_user.id, "CREAR_USUARIO", "usuario", new_user.id, f"Rol: {new_user.rol}")
    db.commit()
    db.refresh(new_user)
    return new_user


@app.get("/api/admin/audit")
def audit_log(
    _: models.Usuario = Depends(require_roles("Administrador")),
    db: Session = Depends(get_db),
):
    rows = db.query(models.Auditoria).order_by(models.Auditoria.created_at.desc()).limit(100).all()
    return [{
        "id": row.id,
        "usuario": row.usuario.nombre if row.usuario else "Sistema",
        "accion": row.accion,
        "recurso": row.recurso,
        "recurso_id": row.recurso_id,
        "detalle": row.detalle,
        "created_at": row.created_at,
    } for row in rows]


@app.get("/api/admin/tariff-versions")
def tariff_versions(
    _: models.Usuario = Depends(require_roles("Administrador")),
    db: Session = Depends(get_db),
):
    versions = db.query(models.VersionTarifa).order_by(models.VersionTarifa.created_at.desc()).all()
    return [{
        "id": v.id,
        "archivo": v.nombre_archivo,
        "estado": v.estado,
        "total_filas": v.total_filas,
        "filas_validas": v.filas_validas,
        "filas_invalidas": v.filas_invalidas,
        "created_at": v.created_at,
        "activated_at": v.activated_at,
    } for v in versions]


@app.post("/api/admin/tariff-versions", status_code=201)
async def upload_tariff_version(
    file: UploadFile = File(...),
    current_user: models.Usuario = Depends(require_roles("Administrador")),
    db: Session = Depends(get_db),
):
    filename = Path(file.filename or "").name
    if not filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=400, detail="Solo se permiten archivos .xlsx")
    content = await file.read(settings.max_upload_mb * 1024 * 1024 + 1)
    if len(content) > settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(status_code=413, detail=f"El archivo supera {settings.max_upload_mb} MB")
    if not content:
        raise HTTPException(status_code=400, detail="El archivo está vacío")

    try:
        version = create_tariff_version(
            db,
            filename=filename,
            content=content,
            created_by_id=current_user.id,
            allow_partial=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    audit(db, current_user.id, "CARGAR_TARIFAS", "version_tarifa", version.id, filename)
    db.commit()
    return {
        "id": version.id,
        "estado": version.estado,
        "filas_validas": version.filas_validas,
        "filas_invalidas": version.filas_invalidas,
        "mensaje": "Archivo validado. Debe activarse explícitamente antes de usarse en el cotizador.",
    }


@app.post("/api/admin/tariff-versions/{version_id}/activate")
def activate_tariff_version(
    version_id: int,
    current_user: models.Usuario = Depends(require_roles("Administrador")),
    db: Session = Depends(get_db),
):
    try:
        version = activate_version(db, version_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    audit(db, current_user.id, "ACTIVAR_TARIFAS", "version_tarifa", version.id, version.nombre_archivo)
    db.commit()
    return {"id": version.id, "estado": version.estado, "mensaje": "Versión activada correctamente"}
