from fastapi.testclient import TestClient
from main import app
from database import Base, engine

Base.metadata.create_all(bind=engine)

client = TestClient(app)

def test_health_check():
    """Verifica que el servicio esté activo."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "OK"

def test_login_credenciales_invalidas():
    """Verifica que el login rechace contraseñas incorrectas."""
    response = client.post(
        "/api/login",
        json={"email": "superadmin@cintac.cl", "password": "ClaveIncorrecta123"}
    )
    assert response.status_code == 401

def test_cotizar_sin_token():
    """Verifica que no se pueda cotizar sin autenticación (401)."""
    response = client.post(
        "/api/cotizar",
        json={
            "puerto_origen": "San Antonio",
            "puerto_destino": "Callao (Perú)",
            "tipo_contenedor": "20'",
            "peso_toneladas": 10.0
        }
    )
    assert response.status_code == 401