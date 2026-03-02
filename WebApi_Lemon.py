from fastapi import FastAPI, WebSocket
import Medicion
from datetime import datetime
import base64
from pydantic import BaseModel

app = FastAPI()


class ImageRequest(BaseModel):
    image: str


@app.post("/clasificar")
async def clasificar(data: ImageRequest):
    image_bytes = base64.b64decode(data.image)

    size, area = Medicion.detectar_tamano(image_bytes)

    return {
        "id": f"LIM-{int(datetime.utcnow().timestamp())}",
        "tamano": size,
        "area": area,
        "fecha": datetime.utcnow().isoformat()
    }