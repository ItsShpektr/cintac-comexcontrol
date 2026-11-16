from io import BytesIO
from pathlib import Path
import sys

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from database import Base, get_db
from main import _login_attempts, app
import models
from security import hash_password
from tariff_service import SHEET_NAME


TEST_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=TEST_ENGINE)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_test_db():
    _login_attempts.clear()
    Base.metadata.drop_all(bind=TEST_ENGINE)
    Base.metadata.create_all(bind=TEST_ENGINE)
    app.dependency_overrides[get_db] = override_get_db

    db = TestingSessionLocal()
    admin = models.Usuario(
        nombre="Admin Test",
        email="admin@cintac.cl",
        password_hash=hash_password("AdminPass123!"),
        rol="Administrador",
    )
    jefatura = models.Usuario(
        nombre="Jefatura Test",
        email="jefatura@cintac.cl",
        password_hash=hash_password("JefaturaPass123!"),
        rol="Jefatura COMEX",
    )
    analista1 = models.Usuario(
        nombre="Analista Uno",
        email="analista1@cintac.cl",
        password_hash=hash_password("AnalistaPass123!"),
        rol="Analista COMEX",
    )
    analista2 = models.Usuario(
        nombre="Analista Dos",
        email="analista2@cintac.cl",
        password_hash=hash_password("AnalistaPass123!"),
        rol="Analista COMEX",
    )
    db.add_all([admin, jefatura, analista1, analista2])
    db.flush()

    version = models.VersionTarifa(
        nombre_archivo="Tarifas_Base.xlsx",
        hash_archivo="hash_inicial_test",
        estado="ACTIVA",
        total_filas=2,
        filas_validas=2,
        filas_invalidas=0,
        resumen_validacion={"errores": []},
        creada_por_id=admin.id,
    )
    db.add(version)
    db.flush()

    db.add_all([
        models.Tarifa(
            version_id=version.id,
            puerto_origen="Qingdao",
            pais_origen="China",
            puerto_destino="San Antonio",
            tipo_ruta="Directo",
            tarifa_20_min=4100.0,
            tarifa_20_max=4300.0,
            tarifa_40_min=5500.0,
            tarifa_40_max=5700.0,
            transito_min=35,
            transito_max=45,
            fuente="Interna",
        ),
        models.Tarifa(
            version_id=version.id,
            puerto_origen="San Antonio",
            pais_origen="Chile",
            puerto_destino="Callao (Peru)",
            tipo_ruta="Directo",
            tarifa_20_min=900.0,
            tarifa_20_max=900.0,
            tarifa_40_min=970.0,
            tarifa_40_max=970.0,
            transito_min=3,
            transito_max=5,
            fuente="Interna",
        ),
    ])
    db.commit()
    db.close()

    yield

    app.dependency_overrides.clear()
    _login_attempts.clear()


client = TestClient(app)


def login_token(email: str, password: str) -> str:
    res = client.post("/api/login", json={"email": email, "password": password})
    assert res.status_code == 200
    return res.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_excel_upload(rows: list[dict]) -> bytes:
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        pd.DataFrame(rows).to_excel(writer, sheet_name=SHEET_NAME, index=False)
    return buf.getvalue()


# IT-01
def test_login_valido_entrega_jwt():
    res = client.post("/api/login", json={"email": "analista1@cintac.cl", "password": "AnalistaPass123!"})
    assert res.status_code == 200
    body = res.json()
    assert "access_token" in body and len(body["access_token"]) > 20
    assert body["rol"] == "Analista COMEX"


# IT-02
def test_login_incorrecto():
    res = client.post("/api/login", json={"email": "analista1@cintac.cl", "password": "ClaveIncorrecta999"})
    assert res.status_code == 401


# IT-03
def test_rate_limit_tras_8_intentos_fallidos():
    for _ in range(8):
        r = client.post("/api/login", json={"email": "analista1@cintac.cl", "password": "ClaveIncorrecta999"})
        assert r.status_code == 401
    ninth = client.post("/api/login", json={"email": "analista1@cintac.cl", "password": "ClaveIncorrecta999"})
    assert ninth.status_code == 429


# IT-04
def test_endpoint_protegido_sin_token():
    assert client.get("/api/me").status_code == 401
    assert client.get("/api/history").status_code == 401


def test_token_manipulado():
    token = login_token("analista1@cintac.cl", "AnalistaPass123!")
    tampered = token[:-4] + "XXXX"
    assert client.get("/api/me", headers=auth_headers(tampered)).status_code == 401


# IT-05
def test_analista_no_accede_a_administracion():
    headers = auth_headers(login_token("analista1@cintac.cl", "AnalistaPass123!"))
    assert client.get("/api/admin/users", headers=headers).status_code == 403
    assert client.get("/api/admin/audit", headers=headers).status_code == 403
    assert client.get("/api/admin/tariff-versions", headers=headers).status_code == 403


# IT-06
def test_jefatura_actualiza_tarifas_pero_no_gestiona_usuarios():
    headers = auth_headers(login_token("jefatura@cintac.cl", "JefaturaPass123!"))
    excel_bytes = make_excel_upload([{
        "Clave": "Valparaiso|Callao (Peru)",
        "Puerto Origen": "Valparaiso",
        "Pais Origen": "Chile",
        "Puerto Destino": "Callao (Peru)",
        "Tipo de Ruta": "Directo",
        "Tarifa 20' Min (US$)": 900,
        "Tarifa 20' Max (US$)": 900,
        "Tarifa 40' Min (US$)": 970,
        "Tarifa 40' Max (US$)": 970,
        "Transito Min (dias)": 3,
        "Transito Max (dias)": 5,
        "Fuente": "Tarifario Validado",
    }])
    up = client.post(
        "/api/admin/tariff-versions",
        headers=headers,
        files={"file": ("tarifas_jefatura.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert up.status_code == 201

    forbidden = client.post(
        "/api/admin/users",
        headers=headers,
        json={"nombre": "Nuevo", "email": "nuevo@cintac.cl", "password": "ClaveSegura123!", "rol": "Analista COMEX"},
    )
    assert forbidden.status_code == 403


# IT-07
def test_admin_crea_usuario_y_rechaza_duplicado():
    headers = auth_headers(login_token("admin@cintac.cl", "AdminPass123!"))
    payload = {"nombre": "Usuario Nuevo", "email": "nuevo@cintac.cl", "password": "ClaveSegura123!", "rol": "Analista COMEX"}
    created = client.post("/api/admin/users", headers=headers, json=payload)
    assert created.status_code == 201

    duplicated = client.post("/api/admin/users", headers=headers, json=payload)
    assert duplicated.status_code == 409


# IT-08
def test_crear_usuario_con_clave_corta_o_rol_invalido():
    headers = auth_headers(login_token("admin@cintac.cl", "AdminPass123!"))
    short_pw = client.post(
        "/api/admin/users",
        headers=headers,
        json={"nombre": "Test", "email": "short@cintac.cl", "password": "12345", "rol": "Analista COMEX"},
    )
    assert short_pw.status_code == 422

    bad_role = client.post(
        "/api/admin/users",
        headers=headers,
        json={"nombre": "Test", "email": "role@cintac.cl", "password": "ClaveSegura123!", "rol": "Gerente General"},
    )
    assert bad_role.status_code == 422


# IT-09
def test_carga_rechaza_extension_invalida():
    headers = auth_headers(login_token("jefatura@cintac.cl", "JefaturaPass123!"))
    res = client.post(
        "/api/admin/tariff-versions",
        headers=headers,
        files={"file": ("tarifas.txt", b"hola mundo", "text/plain")},
    )
    assert res.status_code == 400


def test_carga_rechaza_filas_invalidas():
    headers = auth_headers(login_token("jefatura@cintac.cl", "JefaturaPass123!"))
    bad_excel = make_excel_upload([{
        "Clave": "Clave|Incorrecta",
        "Puerto Origen": "Valparaiso",
        "Pais Origen": "Chile",
        "Puerto Destino": "Callao (Peru)",
        "Tipo de Ruta": "Directo",
        "Tarifa 20' Min (US$)": 1200,
        "Tarifa 20' Max (US$)": 900,
        "Tarifa 40' Min (US$)": 970,
        "Tarifa 40' Max (US$)": 970,
        "Transito Min (dias)": 5,
        "Transito Max (dias)": 3,
        "Fuente": "Test",
    }])
    res = client.post(
        "/api/admin/tariff-versions",
        headers=headers,
        files={"file": ("invalidas.xlsx", bad_excel, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )
    assert res.status_code == 422
    assert len(res.json()["detail"]) > 10


# IT-10
def test_cotizar_calcula_contenedores_y_totales():
    headers = auth_headers(login_token("analista1@cintac.cl", "AnalistaPass123!"))
    res = client.post(
        "/api/cotizar",
        headers=headers,
        json={
            "puerto_origen": "Qingdao",
            "puerto_destino": "San Antonio",
            "tipo_contenedor": "40'",
            "peso_toneladas": 34,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["cantidad_contenedores"] == 2
    alt = body["alternativas"][0]
    assert alt["flete_min_usd"] == 11000.0
    assert alt["flete_max_usd"] == 11400.0
    assert alt["total_min_usd"] == 11000.0
    assert alt["total_max_usd"] == 11400.0


def test_cotizar_con_contingencia_y_tipo_de_cambio():
    headers = auth_headers(login_token("analista1@cintac.cl", "AnalistaPass123!"))
    res = client.post(
        "/api/cotizar",
        headers=headers,
        json={
            "puerto_origen": "San Antonio",
            "puerto_destino": "Callao (Peru)",
            "tipo_contenedor": "40'",
            "peso_toneladas": 26,
            "contingencia_dias": 5,
            "tipo_cambio_clp_usd": 950,
            "valor_carga_usd": 5000,
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["cantidad_contenedores"] == 2
    alt = body["alternativas"][0]
    assert alt["total_min_usd"] == 6940.0
    assert alt["total_min_clp"] == round(6940.0 * 950)
    assert alt["transito_min_dias"] == 8
    assert alt["transito_max_dias"] == 10


# IT-11
def test_cotizar_ruta_inexistente():
    headers = auth_headers(login_token("analista1@cintac.cl", "AnalistaPass123!"))
    res = client.post(
        "/api/cotizar",
        headers=headers,
        json={
            "puerto_origen": "Puerto Inexistente",
            "puerto_destino": "San Antonio",
            "tipo_contenedor": "20'",
            "peso_toneladas": 10,
        },
    )
    assert res.status_code == 404


def test_cotizar_peso_invalido():
    headers = auth_headers(login_token("analista1@cintac.cl", "AnalistaPass123!"))
    res = client.post(
        "/api/cotizar",
        headers=headers,
        json={
            "puerto_origen": "Qingdao",
            "puerto_destino": "San Antonio",
            "tipo_contenedor": "20'",
            "peso_toneladas": 0,
        },
    )
    assert res.status_code == 422


# IT-12
def test_solo_el_analista_puede_cotizar():
    payload = {
        "puerto_origen": "Qingdao",
        "puerto_destino": "San Antonio",
        "tipo_contenedor": "40'",
        "peso_toneladas": 10,
    }
    jef_headers = auth_headers(login_token("jefatura@cintac.cl", "JefaturaPass123!"))
    adm_headers = auth_headers(login_token("admin@cintac.cl", "AdminPass123!"))
    assert client.post("/api/cotizar", headers=jef_headers, json=payload).status_code == 403
    assert client.post("/api/cotizar", headers=adm_headers, json=payload).status_code == 403


# IT-13
def test_historial_del_analista_solo_muestra_sus_cotizaciones():
    h1 = auth_headers(login_token("analista1@cintac.cl", "AnalistaPass123!"))
    h2 = auth_headers(login_token("analista2@cintac.cl", "AnalistaPass123!"))

    client.post(
        "/api/cotizar",
        headers=h1,
        json={"puerto_origen": "Qingdao", "puerto_destino": "San Antonio", "tipo_contenedor": "40'", "peso_toneladas": 10},
    )
    client.post(
        "/api/cotizar",
        headers=h2,
        json={"puerto_origen": "San Antonio", "puerto_destino": "Callao (Peru)", "tipo_contenedor": "20'", "peso_toneladas": 12},
    )

    hist1 = client.get("/api/history", headers=h1).json()
    hist2 = client.get("/api/history", headers=h2).json()
    assert len(hist1) == 1 and hist1[0]["usuario"] == "Analista Uno"
    assert len(hist2) == 1 and hist2[0]["usuario"] == "Analista Dos"


# IT-14
def test_auditoria_registra_acciones():
    adm_headers = auth_headers(login_token("admin@cintac.cl", "AdminPass123!"))
    client.post(
        "/api/admin/users",
        headers=adm_headers,
        json={"nombre": "Auditado", "email": "auditado@cintac.cl", "password": "ClaveSegura123!", "rol": "Analista COMEX"},
    )
    excel_bytes = make_excel_upload([{
        "Clave": "Qingdao|San Antonio",
        "Puerto Origen": "Qingdao",
        "Pais Origen": "China",
        "Puerto Destino": "San Antonio",
        "Tipo de Ruta": "Directo",
        "Tarifa 20' Min (US$)": 4100,
        "Tarifa 20' Max (US$)": 4300,
        "Tarifa 40' Min (US$)": 5500,
        "Tarifa 40' Max (US$)": 5700,
        "Transito Min (dias)": 35,
        "Transito Max (dias)": 45,
        "Fuente": "Audit Test",
    }])
    client.post(
        "/api/admin/tariff-versions",
        headers=adm_headers,
        files={"file": ("audit_tarifas.xlsx", excel_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
    )

    logs = client.get("/api/admin/audit", headers=adm_headers).json()
    acciones = {row["accion"] for row in logs}
    assert {"LOGIN", "CREAR_USUARIO", "CARGAR_TARIFAS"}.issubset(acciones)
    assert all(row["usuario"] and row["created_at"] for row in logs)


# CP-20
def test_admin_elimina_usuario():
    adm_headers = auth_headers(login_token("admin@cintac.cl", "AdminPass123!"))
    users = client.get("/api/admin/users", headers=adm_headers).json()
    target = next(u for u in users if u["email"] == "analista2@cintac.cl")

    deleted = client.delete(f"/api/admin/users/{target['id']}", headers=adm_headers)
    assert deleted.status_code == 204

    login_after = client.post("/api/login", json={"email": "analista2@cintac.cl", "password": "AnalistaPass123!"})
    assert login_after.status_code == 401


# CP-21
def test_eliminar_usuario_sin_permisos_o_autoeliminacion():
    adm_headers = auth_headers(login_token("admin@cintac.cl", "AdminPass123!"))
    ana_headers = auth_headers(login_token("analista1@cintac.cl", "AnalistaPass123!"))
    users = client.get("/api/admin/users", headers=adm_headers).json()
    admin_user = next(u for u in users if u["email"] == "admin@cintac.cl")
    other_user = next(u for u in users if u["email"] == "analista2@cintac.cl")

    forbidden = client.delete(f"/api/admin/users/{other_user['id']}", headers=ana_headers)
    assert forbidden.status_code == 403

    self_delete = client.delete(f"/api/admin/users/{admin_user['id']}", headers=adm_headers)
    assert self_delete.status_code in (400, 403, 422)

