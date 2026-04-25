import cv2
import numpy as np

def detectar_tamano(image_bytes):
    # Convertir bytes a imagen OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return "ERROR", 0

    # Suavizado para reducir ruido
    img = cv2.GaussianBlur(img, (5, 5), 0)

    # Aumentar contraste para mejorar detección de verdes oscuros
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
    l = clahe.apply(l)
    lab = cv2.merge([l, a, b])
    img = cv2.cvtColor(lab, cv2.COLOR_LAB2BGR)

    # Convertir a HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # ================== UMBRALES DE COLOR MUCHO MÁS AMPLIOS ==================
    
    # Rango para AMARILLO (limones maduros)
    lower_yellow = np.array([10, 50, 50])
    upper_yellow = np.array([40, 255, 255])
    
    # Rango para VERDE CLARO (limones verdes / pintones)
    lower_green_light = np.array([25, 35, 35])
    upper_green_light = np.array([95, 255, 255])
    
    # Rango para VERDE OSCURO (limones más verdes) - AMPLIADO
    lower_green_dark = np.array([30, 20, 20])
    upper_green_dark = np.array([95, 255, 150])
    
    # Rango para VERDE MUY OSCURO (casi negro pero aún verde)
    lower_green_very_dark = np.array([35, 15, 15])
    upper_green_very_dark = np.array([90, 200, 100])
    
    # Rango para VERDE OLIVA (tonos verdosos más apagados)
    lower_green_olive = np.array([20, 15, 15])
    upper_green_olive = np.array([45, 120, 120])
    
    # Rango para VERDE-AMARILLO (tonos intermedios)
    lower_green_yellow = np.array([15, 40, 40])
    upper_green_yellow = np.array([55, 255, 255])
    
    # Rango para AMARILLO PÁLIDO/VERDE MUY CLARO
    lower_pale = np.array([8, 25, 90])
    upper_pale = np.array([32, 100, 255])
    
    # Rango para VERDE INTENSO (limones bien verdes)
    lower_intense_green = np.array([35, 50, 35])
    upper_intense_green = np.array([90, 255, 160])
    
    # NUEVO: Rango para VERDE AZULADO (tonos más fríos)
    lower_blue_green = np.array([45, 20, 20])
    upper_blue_green = np.array([95, 200, 140])
    
    # NUEVO: Rango para VERDE AMARILLENTO OSCURO
    lower_dark_yellow_green = np.array([15, 25, 25])
    upper_dark_yellow_green = np.array([35, 200, 130])
    
    # NUEVO: Rango para MARRÓN CLARO / VERDE MARRÓN (limones pasados, manchas)
    lower_brown_green = np.array([8, 15, 15])
    upper_brown_green = np.array([25, 150, 100])
    
    # Rango para MARRÓN (manchas)
    lower_brown = np.array([5, 40, 30])
    upper_brown = np.array([22, 180, 120])
    
    # Crear máscaras individuales
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    mask_green_light = cv2.inRange(hsv, lower_green_light, upper_green_light)
    mask_green_dark = cv2.inRange(hsv, lower_green_dark, upper_green_dark)
    mask_green_very_dark = cv2.inRange(hsv, lower_green_very_dark, upper_green_very_dark)
    mask_green_olive = cv2.inRange(hsv, lower_green_olive, upper_green_olive)
    mask_green_yellow = cv2.inRange(hsv, lower_green_yellow, upper_green_yellow)
    mask_pale = cv2.inRange(hsv, lower_pale, upper_pale)
    mask_intense_green = cv2.inRange(hsv, lower_intense_green, upper_intense_green)
    mask_blue_green = cv2.inRange(hsv, lower_blue_green, upper_blue_green)
    mask_dark_yellow_green = cv2.inRange(hsv, lower_dark_yellow_green, upper_dark_yellow_green)
    mask_brown_green = cv2.inRange(hsv, lower_brown_green, upper_brown_green)
    mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)
    
    # Combinar todas las máscaras
    mask = cv2.bitwise_or(mask_yellow, mask_green_light)
    mask = cv2.bitwise_or(mask, mask_green_dark)
    mask = cv2.bitwise_or(mask, mask_green_very_dark)
    mask = cv2.bitwise_or(mask, mask_green_olive)
    mask = cv2.bitwise_or(mask, mask_green_yellow)
    mask = cv2.bitwise_or(mask, mask_pale)
    mask = cv2.bitwise_or(mask, mask_intense_green)
    mask = cv2.bitwise_or(mask, mask_blue_green)
    mask = cv2.bitwise_or(mask, mask_dark_yellow_green)
    mask = cv2.bitwise_or(mask, mask_brown_green)
    mask = cv2.bitwise_or(mask, mask_brown)
    
    # ================== POST-PROCESAMIENTO MEJORADO ==================
    # Primera pasada: cerrar huecos grandes
    kernel_close = np.ones((12, 12), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)
    
    # Segunda pasada: eliminar ruido pequeño
    kernel_open = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
    
    # Dilatar para conectar áreas cercanas
    kernel_dilate = np.ones((8, 8), np.uint8)
    mask = cv2.dilate(mask, kernel_dilate, iterations=2)
    mask = cv2.erode(mask, kernel_dilate, iterations=1)
    
    # Rellenar agujeros internos
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((18, 18), np.uint8))

    # Encontrar contornos
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return "NO DETECTADO", 0

    # Filtrar contornos por área mínima (ajustado para 25cm)
    min_area = 600  # Mínimo 600 píxeles
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    
    if not filtered_contours:
        return "NO DETECTADO", 0

    # Encontrar el contorno más grande
    largest = max(filtered_contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    
    # Calcular circularidad
    perimeter = cv2.arcLength(largest, True)
    if perimeter > 0:
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        print(f"DEBUG - Circularidad: {circularity:.2f}")
        # Si es muy poco circular y área pequeña, probablemente no es un limón
        if circularity < 0.3 and area < 2000:
            return "NO DETECTADO", 0

    # Calcular el centro
    moments = cv2.moments(largest)
    if moments["m00"] != 0:
        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])
    else:
        cx, cy = 0, 0

    print(f"DEBUG - Área detectada en píxeles: {area}")
    print(f"DEBUG - Centro del objeto: ({cx}, {cy})")
    
    # Mostrar estadísticas de máscaras
    print(f"DEBUG - Total de píxeles detectados: {cv2.countNonZero(mask)}")

    # ================== CLASIFICACIÓN DE TAMAÑO (AJUSTADO PARA 25cm) ==================
    if area < 1200:
        size = "PEQUEÑO"
    elif area < 4500:
        size = "MEDIANO"
    else:
        size = "GRANDE"
    
    print(f"DEBUG - Clasificación: {size}")

    return size, int(area)