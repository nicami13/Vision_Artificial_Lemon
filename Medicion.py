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

    # Rango verde limón
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([80, 255, 255])
    mask_green = cv2.inRange(hsv, lower_green, upper_green)

    # Rango amarillo
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([35, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # Combinar máscaras
    mask = cv2.bitwise_or(mask_green, mask_yellow)

    # Limpieza de ruido
    kernel = np.ones((5, 5), np.uint8)

    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

    mask = cv2.erode(mask, kernel, iterations=1)
    mask = cv2.dilate(mask, kernel, iterations=1)

    # Encontrar contornos
    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    # Si no hay contornos
    if not contours:
        return "NO DETECTADO", 0

    # Obtener contorno más grande
    largest = max(contours, key=cv2.contourArea)

    # Calcular área
    area = cv2.contourArea(largest)

    print(f"DEBUG - Área detectada en píxeles: {area}")

    # Si el área es menor a 740
    if area < 740:
        return "NO DETECTADO", area

    # Clasificación por tamaño
    if area < 9000:
        size = "PEQUEÑO"
    elif area < 14000:
        size = "MEDIANO"
    else:
        size = "GRANDE"

    return size, area