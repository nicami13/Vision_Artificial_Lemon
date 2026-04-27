from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from zoneinfo import ZoneInfo
import base64
import asyncio

import Medicion

app = FastAPI(title="API Detección de Limones")

registros = []
lock = asyncio.Lock()  # 🔥 PROTECCIÓN

zona_colombia = ZoneInfo("America/Bogota")


class ImageRequest(BaseModel):
    image: str


# =========================
# POST - Clasificar limón
# =========================
@app.post("/clasificar")
async def clasificar(data: ImageRequest):

    if "," in data.image:
        image_base64 = data.image.split(",")[1]
    else:
        image_base64 = data.image

    image_bytes = base64.b64decode(image_base64)

    print("🧠 Procesando imagen...")
    size, area = Medicion.detectar_tamano(image_bytes)
    print("✅ Resultado:", size)

    ahora = datetime.now(zona_colombia)

    # 🔥 ID MEJORADO (milisegundos)
    unique_id = f"LIM-{int(ahora.timestamp() * 1000)}"

    registro = {
        "id": unique_id,
        "tamano": size,
        "area": area,
        "fecha": ahora.strftime("%Y-%m-%d"),
        "hora": ahora.strftime("%H:%M:%S"),
        "timestamp": ahora.isoformat(),
        "imagen_base64": image_base64
    }

    # 🔥 PROTEGER ESCRITURA
    async with lock:
        registros.append(registro)

    return registro


# =========================
# GET - Listar TODO
# =========================
@app.get("/listar")
async def listar_todo():
    async with lock:
        return registros


# =========================
# GET - LISTAR LITE (CLAVE)
# =========================
@app.get("/listar_lite")
async def listar_lite():

    async with lock:

        if not registros:
            return {
                "id": None,
                "tamano": "NO DETECTADO",
                "area": 0,
                "fecha": None,
                "hora": None,
                "timestamp": None
            }

        # 🔥 ORDENAR POR TIMESTAMP REAL
        ultimo = sorted(registros, key=lambda x: x["timestamp"])[-1].copy()

        ultimo.pop("imagen_base64", None)

        return ultimo


# =========================
# GET - Buscar por ID
# =========================
@app.get("/listar/{limon_id}")
async def buscar_por_id(limon_id: str):

    async with lock:
        for r in registros:
            if r["id"] == limon_id:
                return r

    raise HTTPException(status_code=404, detail="Registro no encontrado")