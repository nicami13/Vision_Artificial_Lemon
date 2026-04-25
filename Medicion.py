import cv2
import numpy as np


def detectar_tamano(image_bytes):
    # Convertir bytes a imagen OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return "ERROR", 0

    # Convertir a HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Rango color limón (amarillo)
    lower = np.array([20, 80, 80])
    upper = np.array([40, 255, 255])

    mask = cv2.inRange(hsv, lower, upper)

    # Limpiar ruido
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    # Encontrar contornos
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return "NO DETECTADO", 0

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    print(f"DEBUG - Área detectada en píxeles: {area}")

    # 🔴 AJUSTA ESTOS VALORES según tus mediciones reales
    # Con la cámara a 18cm:
    # - Limón pequeño: ~80-200 píxeles
    # - Limón mediano: ~200-500 píxeles  
    # - Limón grande: >500 píxeles
    
    if area < 400:
        size = "PEQUEÑO"
    elif area < 2100:
        size = "MEDIANO"
    else:
        size = "GRANDE"

    return size, int(area)