import cv2
import numpy as np
from ultralytics import YOLO

# Cargar el modelo YOLO
model = YOLO('yolov8n.pt')

def detectar_tamano(image_bytes):
    # Convertir bytes a imagen OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return "ERROR", 0, 0, 0

    # Usar YOLO para detectar
    results = model(img)

    if not results or len(results[0].boxes) == 0:
        return "NO DETECTADO", 0, 0, 0

    # Tomar la detección con mayor confianza
    boxes = results[0].boxes
    best_box = boxes[0]  # Asumiendo ordenado por confianza

    # Obtener coordenadas
    x1, y1, x2, y2 = best_box.xyxy[0].cpu().numpy()
    width = x2 - x1
    height = y2 - y1
    area = width * height

    # Obtener clase predicha
    class_id = int(best_box.cls[0].cpu().numpy())
    confidence = best_box.conf[0].cpu().numpy()

    # Asumir clases: 0=PEQUEÑO, 1=MEDIANO, 2=GRANDE
    sizes = ["PEQUEÑO", "MEDIANO", "GRANDE"]
    size = sizes[class_id] if class_id < len(sizes) else "DESCONOCIDO"

    print(f"DEBUG - Área: {area:.0f} px, Ancho: {width:.0f} px, Alto: {height:.0f} px, Clase: {size}, Confianza: {confidence:.2f}")

    return size, area