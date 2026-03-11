from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
from zoneinfo import ZoneInfo
import base64
import Medicion

app = FastAPI()

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

    # Si viene con encabezado base64 lo quitamos
    if "," in data.image:
        image_base64 = data.image.split(",")[1]
    else:
        image_base64 = data.image

    image_bytes = base64.b64decode(image_base64)

    size, area = Medicion.detectar_tamano(image_bytes)

    ahora = datetime.now(zona_colombia)

    registro = {
        "id": f"LIM-{int(ahora.timestamp())}",
        "tamano": size,
        "area": area,

        # fecha y hora Colombia
        "fecha": ahora.strftime("%Y-%m-%d"),
        "hora": ahora.strftime("%H:%M:%S"),
        "timestamp": ahora.isoformat(),

        # 👉 guardamos la imagen
        "imagen_base64": image_base64
    }

    registros.append(registro)

    return registro


# =========================
# GET - Listar todos
# =========================
@app.get("/listar")
def listar():
    return registros


# =========================
# GET - Buscar por ID
# =========================
@app.get("/listar/{limon_id}")
def buscar_por_id(limon_id: str):

    for r in registros:
        if r["id"] == limon_id:
            return r

    raise HTTPException(status_code=404, detail="Registro no encontrado")