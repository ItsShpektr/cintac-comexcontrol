from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt
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