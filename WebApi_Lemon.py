from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from zoneinfo import ZoneInfo
import base64
import json
import os
import uuid

# Tu módulo de detección
import Medicion

app = FastAPI(title="API Detección de Limones")

# =========================
# CONFIG
# =========================
ARCHIVO_DATOS = "datos.json"
zona_colombia = ZoneInfo("America/Bogota")

# =========================
# MEMORIA
# =========================
registros = []

# =========================
# CARGAR DATOS AL INICIAR
# =========================
if os.path.exists(ARCHIVO_DATOS):
    try:
        with open(ARCHIVO_DATOS, "r") as f:
            registros = json.load(f)
        print(f"📂 Datos cargados: {len(registros)} registros")
    except:
        print("⚠️ Error cargando datos, iniciando vacío")
        registros = []

# =========================
# GUARDAR DATOS
# =========================
def guardar_datos():
    try:
        with open(ARCHIVO_DATOS, "w") as f:
            json.dump(registros, f)
    except Exception as e:
        print("❌ Error guardando:", e)

# =========================
# MODELO
# =========================
class ImageRequest(BaseModel):
    image: str

# =========================
# POST - Clasificar limón
# =========================
@app.post("/clasificar")
async def clasificar(data: ImageRequest):

    try:
        # Quitar encabezado base64
        if "," in data.image:
            image_base64 = data.image.split(",")[1]
        else:
            image_base64 = data.image

        image_bytes = base64.b64decode(image_base64)

        # 🔥 DETECCIÓN
        size, area = Medicion.detectar_tamano(image_bytes)

        ahora = datetime.now(zona_colombia)

        registro = {
            # 🔥 ID único REAL (evita duplicados)
            "id": f"LIM-{uuid.uuid4().hex[:8]}",

            "tamano": size,
            "area": area,
            "fecha": ahora.strftime("%Y-%m-%d"),
            "hora": ahora.strftime("%H:%M:%S"),
            "timestamp": ahora.isoformat(),

            # 🔥 solo se guarda internamente
            "imagen_base64": image_base64
        }

        registros.append(registro)

        # 💾 Guardar en archivo
        guardar_datos()

        # DEBUG
        print("🍋 Nuevo limón:", registro["tamano"], "| Área:", registro["area"])

        return registro

    except Exception as e:
        print("❌ Error en clasificación:", e)
        raise HTTPException(status_code=500, detail="Error procesando imagen")

# =========================
# GET - TODO (debug)
# =========================
@app.get("/listar")
def listar_todo():
    return registros

# =========================
# GET - SOLO EL ÚLTIMO (ESP32)
# =========================
@app.get("/listar_lite")
def listar_lite():

    if not registros:
        return {
            "id": None,
            "tamano": "NO DETECTADO",
            "area": 0,
            "fecha": None,
            "hora": None,
            "timestamp": None
        }

    ultimo = registros[-1].copy()
    ultimo.pop("imagen_base64", None)

    return ultimo

# =========================
# GET - ÚLTIMO (COMPLETO)
# =========================
@app.get("/ultimo")
def ultimo_completo():
    if not registros:
        raise HTTPException(status_code=404, detail="Sin registros")

    return registros[-1]

# =========================
# GET - POR ID
# =========================
@app.get("/listar/{limon_id}")
def buscar_por_id(limon_id: str):
    for r in registros:
        if r["id"] == limon_id:
            return r
    raise HTTPException(status_code=404, detail="Registro no encontrado")