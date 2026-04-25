import cv2
import numpy as np

# Configuración
DISTANCIA_REFERENCIA = 25  # cm
UMBRALES = {
    'PEQUEÑO': 1200,   # < 1200 píxeles
    'MEDIANO': 3500,   # 1200-3500 píxeles
    'GRANDE': 3500     # > 3500 píxeles
}

def detectar_tamano(image_bytes, distancia_cm=25):
    """Detecta tamaño del limón en píxeles con corrección por distancia"""
    
    # Convertir a imagen
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    if img is None:
        return "ERROR", 0
    
    # Mejorar iluminación
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)
    
    # Suavizar
    img = cv2.GaussianBlur(img, (7, 7), 0)
    
    # Convertir a HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
    
    # Máscara ultra amplia
    mask = cv2.inRange(hsv, np.array([8, 10, 10]), np.array([95, 255, 255]))
    
    # Post-procesamiento
    kernel = np.ones((15, 15), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.dilate(mask, kernel, iterations=2)
    
    # Encontrar contornos
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return "NO_DETECTADO", 0
    
    # Filtrar por área
    valid_contours = [c for c in contours if cv2.contourArea(c) > 300]
    
    if not valid_contours:
        return "NO_DETECTADO", 0
    
    # Mayor contorno
    largest = max(valid_contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    
    # Corregir por distancia (ley cuadrática inversa)
    factor = (distancia_cm / DISTANCIA_REFERENCIA) ** 2
    area_corregida = area / factor
    
    print(f"📊 Área: {area:.0f}px | Corregida: {area_corregida:.0f}px | Dist: {distancia_cm}cm")
    
    # Clasificar
    if area_corregida < 1200:
        size = "PEQUEÑO"
    elif area_corregida < 3500:
        size = "MEDIANO"
    else:
        size = "GRANDE"
    
    return size, int(area_corregida)