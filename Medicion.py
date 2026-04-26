import cv2
import numpy as np

def detectar_tamano(image_bytes):
    # Convertir bytes a imagen OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return "ERROR", 0

    # Convertir a HSV para mejor detección de color
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Rangos para limones verdes con toques amarillos (distancia 19cm)
    # Rango verde: H 35-80, S 50-255, V 50-255
    lower_green = np.array([35, 50, 50])
    upper_green = np.array([80, 255, 255])
    mask_green = cv2.inRange(hsv, lower_green, upper_green)

    # Rango amarillo para toques: H 20-35, S 100-255, V 100-255
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([35, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # Combinar máscaras
    mask = cv2.bitwise_or(mask_green, mask_yellow)

    # Mejorar limpieza de ruido para fondo blanco/beige
    kernel = np.ones((7, 7), np.uint8)  # Kernel más grande para mejor filtrado
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.erode(mask, kernel, iterations=1)  # Erosionar para eliminar ruido fino
    mask = cv2.dilate(mask, kernel, iterations=1)  # Dilatar para restaurar forma

    # Encontrar contornos
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return "NO DETECTADO", 0

    # Filtrar contornos por área mínima para ignorar ruido
    valid_contours = [c for c in contours if cv2.contourArea(c) > 200]  # Área mínima 200 px
    if not valid_contours:
        return "NO DETECTADO", 0

    largest = max(valid_contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    print(f"DEBUG - Área detectada en píxeles: {area}")

    # Clasificación ajustada para distancia de 19cm
    if area < 7000:
        size = "PEQUEÑO"
    elif area < 10000:
        size = "MEDIANO"
    else:
        size = "GRANDE"

    return size, area