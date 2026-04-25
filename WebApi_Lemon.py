from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from zoneinfo import ZoneInfo
import base64

# Importa tu módulo de detección
import Medicion

app = FastAPI(title="API Detección de Limones")

registros = []

# Zona horaria Colombia
zona_colombia = ZoneInfo("America/Bogota")


class ImageRequest(BaseModel):
    image: str


# =========================
# POST - Clasificar limón
# =========================
@app.post("/clasificar")
async def clasificar(data: ImageRequest):
    # Quitar encabezado base64 si viene (data:image/jpeg;base64,...)
    if "," in data.image:
        image_base64 = data.image.split(",")[1]
    else:
        image_base64 = data.image

    image_bytes = base64.b64decode(image_base64)

    size, area, width, height = Medicion.detectar_tamano(image_bytes)

    ahora = datetime.now(zona_colombia)

    registro = {
        "id": f"LIM-{int(ahora.timestamp())}",
        "tamano": size,
        "area": area,
        "ancho": width,
        "alto": height,
        "fecha": ahora.strftime("%Y-%m-%d"),
        "hora": ahora.strftime("%H:%M:%S"),
        "timestamp": ahora.isoformat(),
        "imagen_base64": image_base64   # solo se guarda aquí
    }

    registros.append(registro)

    return registro


# =========================
# GET - Listar TODO (con imagen) - Para navegador / debugging
# =========================
@app.get("/listar")
def listar_todo():
    return registros


# =========================
# NUEVO ENDPOINT - LIGERO para el ESP32
# =========================
@app.get("/listar_lite")
def listar_lite():
    """Endpoint optimizado para ESP32 - NO devuelve la imagen base64"""
    if not registros:
        # Si no hay registros aún, devolvemos un valor por defecto claro
        return {
            "id": None,
            "tamano": "NO DETECTADO",
            "area": 0,
            "ancho": 0,
            "alto": 0,
            "fecha": None,
            "hora": None,
            "timestamp": None
        }

    # Devolvemos solo el registro más reciente (el último)
    ultimo = registros[-1].copy()          # copiamos para no modificar el original
    ultimo.pop("imagen_base64", None)      # eliminamos la imagen grande

    return ultimo


# =========================
# GET - Buscar por ID (opcional)
# =========================
@app.get("/listar/{limon_id}")
def buscar_por_id(limon_id: str):
    for r in registros:
        if r["id"] == limon_id:
            return r
    raise HTTPException(status_code=404, detail="Registro no encontrado")