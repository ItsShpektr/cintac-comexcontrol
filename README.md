# CINTAC - ComexControl (Prototipo)

# CINTAC ComexControl

Plataforma web para la automatización de cotizaciones de fletes marítimos y gestión de tarifas de comercio exterior (COMEX).

## Arquitectura
* **Backend:** FastAPI (Python 3.11) desplegado en [Render](https://cintac-comexcontrol.onrender.com)
* **Frontend:** React + Vite desplegado en [Vercel](https://cintac-comexcontrol.vercel.app)
* **Base de Datos:** PostgreSQL alojada en Supabase

## Configuración de Entorno (.env)
Se requiere un archivo `.env` en la raíz con la estructura indicada en `.env.example`. 
*Asegúrese de configurar `VITE_API_URL=https://cintac-comexcontrol.onrender.com` en el frontend.*

# Tecnologías Utilizadas

- Frontend: React + Vite

- Backend: FastAPI (Python)

- Procesamiento de Datos: Pandas

# Requisitos Previos

- Node.js (v16 o superior)

- Python (3.8 o superior)

# Instrucciones de Instalación y Ejecución

1. Iniciar el Backend (FastAPI)

Abre una terminal en la carpeta raíz y ejecuta:

cd backend
python -m venv venv
# Activar entorno virtual:
# En Windows: venv\Scripts\activate
# En Mac/Linux: source venv/bin/activate
pip install fastapi uvicorn pandas openpyxl python-multipart
uvicorn main:app --reload


El servidor backend correrá en http://localhost:8000.

# 2. Iniciar el Frontend (React)

Abre una nueva terminal en la carpeta raíz y ejecuta:

cd frontend
npm install
npm run dev


La aplicación web correrá localmente (usualmente en http://localhost:5173).

# Uso del Cotizador

Inicia sesión en la plataforma.

Sube el archivo Excel oficial de tarifas en el módulo de cotización.

El sistema validará automáticamente las columnas y poblará las rutas disponibles.

Selecciona tu puerto de origen, destino, tipo de contenedor y cantidad para obtener la cotización calculada.