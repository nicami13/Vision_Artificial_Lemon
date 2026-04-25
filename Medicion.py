import cv2
import numpy as np

def detectar_tamano(image_bytes):
    # Convertir bytes a imagen OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return "ERROR", 0

    # Redimensionar para procesamiento más rápido (opcional)
    # img = cv2.resize(img, (0,0), fx=0.5, fy=0.5)

    # Suavizado para reducir ruido
    img = cv2.GaussianBlur(img, (5, 5), 0)

    # Convertir a HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # ================== UMBRALES DE COLOR MUCHO MÁS AMPLIOS ==================
    
    # Rango para AMARILLO (limones maduros) - AMPLIADO
    lower_yellow = np.array([12, 60, 60])
    upper_yellow = np.array([38, 255, 255])
    
    # Rango para VERDE CLARO (limones verdes / pintones)
    lower_green_light = np.array([30, 40, 40])
    upper_green_light = np.array([90, 255, 255])
    
    # Rango para VERDE OSCURO (limones más verdes)
    lower_green_dark = np.array([35, 25, 25])
    upper_green_dark = np.array([90, 255, 180])
    
    # Rango para VERDE-AMARILLO (tonos intermedios)
    lower_green_yellow = np.array([20, 50, 50])
    upper_green_yellow = np.array([50, 255, 255])
    
    # NUEVO: Rango para AMARILLO PÁLIDO/VERDE MUY CLARO
    lower_pale = np.array([10, 30, 100])
    upper_pale = np.array([30, 100, 255])
    
    # NUEVO: Rango para VERDE INTENSO (limones bien verdes)
    lower_intense_green = np.array([40, 60, 40])
    upper_intense_green = np.array([85, 255, 180])
    
    # NUEVO: Rango para MARRÓN CLARO (limones pasados o manchas)
    lower_brown = np.array([5, 50, 40])
    upper_brown = np.array([20, 150, 120])
    
    # Crear máscaras individuales
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    mask_green_light = cv2.inRange(hsv, lower_green_light, upper_green_light)
    mask_green_dark = cv2.inRange(hsv, lower_green_dark, upper_green_dark)
    mask_green_yellow = cv2.inRange(hsv, lower_green_yellow, upper_green_yellow)
    mask_pale = cv2.inRange(hsv, lower_pale, upper_pale)
    mask_intense_green = cv2.inRange(hsv, lower_intense_green, upper_intense_green)
    mask_brown = cv2.inRange(hsv, lower_brown, upper_brown)
    
    # Combinar todas las máscaras (UNIÓN de todos los colores)
    mask = cv2.bitwise_or(mask_yellow, mask_green_light)
    mask = cv2.bitwise_or(mask, mask_green_dark)
    mask = cv2.bitwise_or(mask, mask_green_yellow)
    mask = cv2.bitwise_or(mask, mask_pale)
    mask = cv2.bitwise_or(mask, mask_intense_green)
    mask = cv2.bitwise_or(mask, mask_brown)
    
    # ================== POST-PROCESAMIENTO MEJORADO ==================
    # Primera pasada: cerrar huecos grandes
    kernel_close = np.ones((10, 10), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)
    
    # Segunda pasada: eliminar ruido pequeño
    kernel_open = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
    
    # Dilatar para conectar áreas cercanas
    kernel_dilate = np.ones((7, 7), np.uint8)
    mask = cv2.dilate(mask, kernel_dilate, iterations=2)
    mask = cv2.erode(mask, kernel_dilate, iterations=1)
    
    # Rellenar agujeros internos (opcional)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((15, 15), np.uint8))

    # Encontrar contornos
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return "NO DETECTADO", 0

    # Filtrar contornos por área mínima (ajustado para 25cm)
    min_area = 800  # Mínimo 800 píxeles para considerar un limón a 25cm
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    
    if not filtered_contours:
        return "NO DETECTADO", 0

    # Encontrar el contorno más grande
    largest = max(filtered_contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)
    
    # Calcular circularidad (opcional, ayuda a filtrar)
    perimeter = cv2.arcLength(largest, True)
    if perimeter > 0:
        circularity = 4 * np.pi * area / (perimeter * perimeter)
        print(f"DEBUG - Circularidad: {circularity:.2f}")
    else:
        circularity = 0

    # Calcular el centro
    moments = cv2.moments(largest)
    if moments["m00"] != 0:
        cx = int(moments["m10"] / moments["m00"])
        cy = int(moments["m01"] / moments["m00"])
    else:
        cx, cy = 0, 0

    print(f"DEBUG - Área detectada en píxeles: {area}")
    print(f"DEBUG - Centro del objeto: ({cx}, {cy})")
    
    # Mostrar estadísticas de máscaras para depuración
    yellow_pixels = cv2.countNonZero(mask_yellow)
    green_light_pixels = cv2.countNonZero(mask_green_light)
    green_dark_pixels = cv2.countNonZero(mask_green_dark)
    green_yellow_pixels = cv2.countNonZero(mask_green_yellow)
    pale_pixels = cv2.countNonZero(mask_pale)
    intense_pixels = cv2.countNonZero(mask_intense_green)
    
    print(f"DEBUG - Píxeles detectados:")
    print(f"  - Amarillo: {yellow_pixels}")
    print(f"  - Verde claro: {green_light_pixels}")
    print(f"  - Verde oscuro: {green_dark_pixels}")
    print(f"  - Verde-amarillo: {green_yellow_pixels}")
    print(f"  - Pálido: {pale_pixels}")
    print(f"  - Verde intenso: {intense_pixels}")
    print(f"  - Total: {cv2.countNonZero(mask)}")

    # ================== CLASIFICACIÓN DE TAMAÑO (AJUSTADO PARA 25cm) ==================
    # Basado en pruebas a 25cm de distancia:
    # - Limón pequeño: < 1500 píxeles
    # - Limón mediano: 1500 - 5000 píxeles
    # - Limón grande: > 5000 píxeles
    
    if area < 1500:
        size = "PEQUEÑO"
    elif area < 5000:
        size = "MEDIANO"
    else:
        size = "GRANDE"
    
    print(f"DEBUG - Clasificación: {size}")

    return size, int(area)