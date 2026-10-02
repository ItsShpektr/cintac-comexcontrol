from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="CINTAC ComexControl API")

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
