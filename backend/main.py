from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt
import pandas as pd
from pydantic import BaseModel
from fastapi import HTTPException
from datetime import datetime, timedelta
import models, schemas

app = FastAPI(title="CINTAC ComexControl API")

# --- CONFIGURACIÓN DE SEGURIDAD ---
SECRET_KEY = "clave_secreta_comexcontrol_muy_segura" # En producción, esto va en el .env
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def get_password_hash(password):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# Configura CORS para permitir peticiones desde REACT
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class CotizacionRequest(BaseModel):
    puerto_origen: str
    puerto_destino: str
    tipo_contenedor: str  # Esperamos que sea "20'" o "40'"
    cantidad: int

@app.get("/")
def home():
    return {"message": "API ComexControl Activa y Respondiendo"}

@app.get("/api/health")
def health_check():
    return {"status": "OK", "version":"1.0.0"}

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# bloque de Prueba de conexion a la base de datos Supabase PostgreSQL

from database import SessionLocal
from sqlalchemy import text

@app.get("/api/test-db")
def test_db():
    try:
        db = SessionLocal()
        # Hacemos una consulta simple para probar
        db.execute(text("SELECT 1"))
        return {"status": "Conexión exitosa a Supabase PostgreSQL"}
    except Exception as e:
        return {"status": "Error de conexión", "detalles": str(e)}

# Fin del bloque de prueba de conexion a la base de datos Supabase PostgreSQL

@app.post("/api/register", response_model=schemas.Token)
def register_user(user: schemas.UsuarioCreate, db: Session = Depends(get_db)):
    # Verificar si el correo ya existe
    db_user = db.query(models.Usuario).filter(models.Usuario.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    # Encriptar contraseña y guardar usuario
    hashed_password = get_password_hash(user.password)
    nuevo_usuario = models.Usuario(
        nombre=user.nombre,
        email=user.email,
        password_hash=hashed_password,
        rol=user.rol
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    
    # Generar token para que entre directamente
    access_token = create_access_token(data={"sub": nuevo_usuario.email, "rol": nuevo_usuario.rol})
    return {"access_token": access_token, "token_type": "bearer", "rol": nuevo_usuario.rol}

@app.post("/api/login", response_model=schemas.Token)
def login(user: schemas.UsuarioLogin, db: Session = Depends(get_db)):
    # Buscar usuario en la base de datos
    db_user = db.query(models.Usuario).filter(models.Usuario.email == user.email).first()
    
    # Validar que exista el correo y la contraseña coincida con el hash
    if not db_user or not verify_password(user.password, db_user.password_hash):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    
    # Generar token de sesión
    access_token = create_access_token(data={"sub": db_user.email, "rol": db_user.rol})
    return {"access_token": access_token, "token_type": "bearer", "rol": db_user.rol}

@app.post("/api/cotizar")
async def cotizar_flete(request: CotizacionRequest):
    try:
        # 1. Leer la hoja exacta del archivo Excel
        df = pd.read_excel("Cotizador - Calculadora.xlsx", sheet_name="Tarifas Referencia")
        
        # 2. Filtrar buscando el origen y destino (usamos .lower() para evitar errores por mayúsculas/minúsculas)
        filtro = (df['Puerto Origen'].str.lower() == request.puerto_origen.lower()) & \
                 (df['Puerto Destino'].str.lower() == request.puerto_destino.lower())
        
        df_ruta = df[filtro]
        
        # Si no encontramos la ruta, avisamos al frontend
        if df_ruta.empty:
            raise HTTPException(status_code=404, detail="Ruta no encontrada en la base de tarifas")
        
        # 3. Tomamos la primera coincidencia encontrada
        ruta = df_ruta.iloc[0]
        
        # 4. Asignamos las tarifas según el tipo de contenedor
        if request.tipo_contenedor == "20'":
            tarifa_min = float(ruta["Tarifa 20' Min (US$)"])
            tarifa_max = float(ruta["Tarifa 20' Max (US$)"])
        elif request.tipo_contenedor == "40'":
            tarifa_min = float(ruta["Tarifa 40' Min (US$)"])
            tarifa_max = float(ruta["Tarifa 40' Max (US$)"])
        else:
            raise HTTPException(status_code=400, detail="Tipo de contenedor inválido. Use 20' o 40'")
            
        # 5. Calculamos el total
        total_min = tarifa_min * request.cantidad
        total_max = tarifa_max * request.cantidad
        
        # Manejamos posibles celdas vacías (NaN) en la base de datos por los datos sucios
        fuente = str(ruta["Fuente"]) if not pd.isna(ruta["Fuente"]) else "Desconocida"
        tipo_ruta = str(ruta["Tipo de Ruta"]) if not pd.isna(ruta["Tipo de Ruta"]) else "No especificado"
        
        # 6. Devolvemos el resultado al frontend
        return {
            "ruta": tipo_ruta,
            "tarifa_min": tarifa_min,
            "tarifa_max": tarifa_max,
            "transito_min": int(ruta["Transito Min (dias)"]),
            "transito_max": int(ruta["Transito Max (dias)"]),
            "total_min": total_min,
            "total_max": total_max,
            "fuente": fuente,
            "moneda": "US$"
        }
        
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Archivo Excel no encontrado en el servidor")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error interno al procesar la cotización: {str(e)}")