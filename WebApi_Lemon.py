from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from datetime import datetime
import base64
import Medicion

app = FastAPI()

# 👉 "Base de datos" temporal en memoria
registros = []


# Modelo para recibir la imagen en Base64
class ImageRequest(BaseModel):
    image: str


# =========================
# POST - Clasificar limón
# =========================
@app.post("/clasificar")
async def clasificar(data: ImageRequest):

    # Decodificar imagen Base64 a bytes
    image_bytes = base64.b64decode(data.image)

    # Procesar imagen
    size, area = Medicion.detectar_tamano(image_bytes)

    # Crear registro
    registro = {
        "id": f"LIM-{int(datetime.utcnow().timestamp())}",
        "tamano": size,
        "area": area,
        "fecha": datetime.utcnow().isoformat()
    }

    # Guardar en memoria
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