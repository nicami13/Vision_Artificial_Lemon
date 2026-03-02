from fastapi import FastAPI, WebSocket
import Medicion
from datetime import datetime
import base64

app = FastAPI()

@app.websocket("/ws/clasificar")
async def websocket_clasificar(websocket: WebSocket):
    await websocket.accept()

    while True:
        # Recibir JSON desde cliente
        data = await websocket.receive_json()

        # Obtener Base64
        base64_img = data["image"]

        # Decodificar a bytes
        image_bytes = base64.b64decode(base64_img)

        # Procesar con OpenCV
        size, area = Medicion.detectar_tamano(image_bytes)

        # Crear respuesta
        response = {
            "id": f"LIM-{int(datetime.utcnow().timestamp())}",
            "tamano": size,
            "area": area,
            "fecha": datetime.utcnow().isoformat()
        }

        # Enviar resultado al cliente
        await websocket.send_json(response)