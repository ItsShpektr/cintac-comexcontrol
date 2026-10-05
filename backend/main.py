from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi import HTTPException, Depends
from sqlalchemy.orm import Session
from passlib.context import CryptContext
import jwt
import pandas as pd
from pydantic import BaseModel
from datetime import datetime, timedelta
import models, schemas
import io

app = FastAPI(title="Cintac ComexControl API", version="2.0")

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

db_cache = {"df": None, "filename": None}
REQUIRED_COLUMNS = [
    "Puerto Origen", "Puerto Destino", "Tipo de Ruta",
    "Tarifa 20' Min (US$)", "Tarifa 20' Max (US$)",
    "Tarifa 40' Min (US$)", "Tarifa 40' Max (US$)",
    "Transito Min (dias)", "Transito Max (dias)", "Fuente",
]

@app.get("/")
def home():
    return {"message": "Conexión exitosa con el Backend ComexControl (Modo Dinámico con Excel)"}

@app.get("/api/health")
def health_check():
    return {"status": "OK", "version": app.version}

@app.post("/api/upload-excel")
async def upload_excel(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls")):
        raise HTTPException(status_code=400, detail="El archivo debe ser un Excel válido (.xlsx o .xls)")
    try:
        contents = await file.read()

        # Revisar hasta 30 filas de cada hoja para encontrar la tabla aunque
        # esté más abajo o en una pestaña distinta de la primera.
        excel = pd.ExcelFile(io.BytesIO(contents))
        required_headers = {header.casefold() for header in REQUIRED_COLUMNS}
        header_candidates = []
        scanned_sheets = []
        for sheet_name in excel.sheet_names:
            preview = pd.read_excel(excel, sheet_name=sheet_name, header=None, nrows=30)
            scanned_rows = []
            for row_index, row in preview.iterrows():
                row_values = ["" if pd.isna(value) else str(value).strip() for value in row.tolist()]
                scanned_rows.append(f"Fila {row_index + 1}: {row_values}")
                normalized_values = {value.casefold() for value in row_values if value}
                if "puerto origen" in normalized_values:
                    matched_headers = required_headers.intersection(normalized_values)
                    header_candidates.append((len(matched_headers), sheet_name, row_index, row_values))
            scanned_sheets.append({"hoja": sheet_name, "filas": scanned_rows})

        if not header_candidates:
            diagnostic = "\n".join(
                f"Hoja '{sheet['hoja']}':\n" + "\n".join(sheet["filas"])
                for sheet in scanned_sheets
            )
            raise HTTPException(
                status_code=400,
                detail=(
                    "No se encontró la fila de encabezados ('Puerto Origen') en las primeras 30 filas "
                    "de ninguna hoja. Filas leídas por el sistema:\n" + diagnostic
                ),
            )

        # Priorizar la fila que coincide con más columnas requeridas.
        _, sheet_name, header_index, detected_header = max(
            header_candidates, key=lambda candidate: candidate[0]
        )
        df = pd.read_excel(io.BytesIO(contents), sheet_name=sheet_name, header=header_index)
        df.columns = [str(column).strip() for column in df.columns]
        canonical_headers = {header.casefold(): header for header in REQUIRED_COLUMNS}
        df.rename(
            columns={column: canonical_headers[column.casefold()] for column in df.columns if column.casefold() in canonical_headers},
            inplace=True,
        )
        missing_cols = [col for col in REQUIRED_COLUMNS if col not in df.columns]
        if missing_cols:
            columnas_encontradas = ", ".join(str(column) for column in df.columns)
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Se detectó una posible tabla en la hoja '{sheet_name}', fila {header_index + 1}, "
                    f"pero faltan columnas requeridas: "
                    f"Faltan: {', '.join(missing_cols)}. "
                    f"Encabezados detectados: {columnas_encontradas}. "
                    f"Fila leída: {detected_header}"
                ),
            )
        db_cache.update({"df": df, "filename": file.filename})
        return {
            "message": "Archivo Excel procesado y validado con éxito",
            "filename": file.filename,
            "puertos_origen": df["Puerto Origen"].dropna().astype(str).unique().tolist(),
            "puertos_destino": df["Puerto Destino"].dropna().astype(str).unique().tolist(),
            "diagnostico": {
                "hoja_detectada": sheet_name,
                "fila_encabezados": header_index + 1,
                "encabezados_detectados": df.columns.tolist(),
                "filas_de_tarifas_leidas": len(df),
                "muestra_de_datos": df.head(5).fillna("").astype(str).to_dict(orient="records"),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer el archivo Excel: {str(e)}")

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
def cotizar_flete(request: CotizacionRequest):
    df = db_cache["df"]
    if df is None:
        raise HTTPException(status_code=400, detail="Primero debe subir un archivo Excel de tarifas válido.")

    origen = df["Puerto Origen"].astype(str).str.strip().str.casefold()
    destino = df["Puerto Destino"].astype(str).str.strip().str.casefold()
    matches = df[(origen == request.puerto_origen.strip().casefold()) & (destino == request.puerto_destino.strip().casefold())]
    if matches.empty:
        raise HTTPException(status_code=404, detail="No se encontró tarifa para la ruta seleccionada en el Excel cargado.")
    if request.cantidad <= 0:
        raise HTTPException(status_code=400, detail="La cantidad debe ser mayor que cero.")

    row = matches.iloc[0]
    if request.tipo_contenedor == "20'":
        tarifa_min = float(row["Tarifa 20' Min (US$)"])
        tarifa_max = float(row["Tarifa 20' Max (US$)"])
    elif request.tipo_contenedor == "40'":
        tarifa_min = float(row["Tarifa 40' Min (US$)"])
        tarifa_max = float(row["Tarifa 40' Max (US$)"])
    else:
        raise HTTPException(status_code=400, detail="Tipo de contenedor inválido. Use 20' o 40'")

    return {
        "ruta": str(row["Tipo de Ruta"]) if not pd.isna(row["Tipo de Ruta"]) else "No especificado",
        "transito_min": int(row["Transito Min (dias)"]),
        "transito_max": int(row["Transito Max (dias)"]),
        "tarifa_min": tarifa_min,
        "tarifa_max": tarifa_max,
        "moneda": "USD",
        "fuente": str(row["Fuente"]) if not pd.isna(row["Fuente"]) else "Desconocida",
        "total_min": tarifa_min * request.cantidad,
        "total_max": tarifa_max * request.cantidad,
    }
