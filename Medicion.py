import cv2
import numpy as np

def detectar_tamano(image_bytes):

    # Convertir bytes a imagen OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # Rango color limón (ajústalo luego)
    lower = np.array([20, 100, 100])
    upper = np.array([40, 255, 255])

    mask = cv2.inRange(hsv, lower, upper)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return "NO DETECTADO", 0

    largest = max(contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    if area < 1000:
        size = "PEQUEÑO"
    elif area < 3000:
        size = "MEDIANO"
    else:
        size = "GRANDE"

    return size, area