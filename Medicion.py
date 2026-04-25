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

    # ================== MEJORA DE UMBRALES DE COLOR ==================
    # Rango para AMARILLO (limones maduros)
    lower_yellow = np.array([15, 80, 80])
    upper_yellow = np.array([35, 255, 255])
    
    # Rango para VERDE CLARO (limones verdes / pintones)
    lower_green_light = np.array([35, 50, 50])
    upper_green_light = np.array([85, 255, 255])
    
    # Rango para VERDE OSCURO (limones más verdes)
    lower_green_dark = np.array([40, 30, 30])
    upper_green_dark = np.array([85, 255, 150])
    
    # Rango para VERDE-AMARILLO (tonos intermedios)
    lower_green_yellow = np.array([25, 60, 60])
    upper_green_yellow = np.array([45, 255, 255])
    
    # Crear máscaras individuales
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)
    mask_green_light = cv2.inRange(hsv, lower_green_light, upper_green_light)
    mask_green_dark = cv2.inRange(hsv, lower_green_dark, upper_green_dark)
    mask_green_yellow = cv2.inRange(hsv, lower_green_yellow, upper_green_yellow)
    
    # Combinar todas las máscaras (UNIÓN de todos los colores)
    mask = cv2.bitwise_or(mask_yellow, mask_green_light)
    mask = cv2.bitwise_or(mask, mask_green_dark)
    mask = cv2.bitwise_or(mask, mask_green_yellow)
    
    # Limpiar ruido (MEJORADO)
    kernel_close = np.ones((7, 7), np.uint8)  # Kernel más grande para cerrar huecos
    kernel_open = np.ones((3, 3), np.uint8)   # Kernel pequeño para eliminar ruido
    
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel_close)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel_open)
    
    # Opcional: Dilatar para conectar áreas cercanas
    kernel_dilate = np.ones((5, 5), np.uint8)
    mask = cv2.dilate(mask, kernel_dilate, iterations=1)
    mask = cv2.erode(mask, kernel_dilate, iterations=1)

    # Encontrar contornos
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return "NO DETECTADO", 0

    # Filtrar contornos por área mínima (eliminar ruido muy pequeño)
    min_area = 500  # Mínimo 500 píxeles para considerar un limón
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > min_area]
    
    if not filtered_contours:
        return "NO DETECTADO", 0

    largest = max(filtered_contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    # Calcular el centro y el radio aproximado
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
    print(f"DEBUG - Píxeles detectados - Amarillo: {yellow_pixels}, Verde claro: {green_light_pixels}, Verde oscuro: {green_yellow_pixels}, Verde-amarillo: {green_yellow_pixels}")

    # ================== CLASIFICACIÓN DE TAMAÑO ==================
    # Ajusta estos umbrales según tus mediciones reales
    if area < 1000:
        size = "PEQUEÑO"
    elif area < 4000:
        size = "MEDIANO"
    else:
        size = "GRANDE"

    return size, int(area)