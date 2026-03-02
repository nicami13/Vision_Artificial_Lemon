from fastapi import FastAPI
from pydantic import BaseModel
from datetime import datetime
import base64
import Medicion

app = FastAPI()


# Modelo para recibir la imagen en Base64
class ImageRequest(BaseModel):
    image: str


@app.post("/clasificar")
async def clasificar(data: ImageRequest):
    # Decodificar imagen Base64 a bytes
    image_bytes = base64.b64decode(data.image)

    # Procesar imagen
    size, area = Medicion.detectar_tamano(image_bytes)

    # Respuesta JSON
    return {
        "id": f"LIM-{int(datetime.utcnow().timestamp())}",
        "tamano": size,
        "area": area,
        "fecha": datetime.utcnow().isoformat()
    }