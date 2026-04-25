import cv2
import numpy as np

# Variables globales para calibración
areas_detectadas = {
    "PEQUEÑO": [],
    "MEDIANO": [],
    "GRANDE": []
}
modo_calibracion = True  # Cambia a False cuando termines de calibrar
cantidad_muestras = 3    # Número de muestras por tamaño

def detectar_tamano(image_bytes, modo_calibracion=True, tamanio_real=None):
    global areas_detectadas
    
    # Convertir bytes a imagen OpenCV
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

    if img is None:
        return "ERROR", 0

    # Suavizado
    img = cv2.GaussianBlur(img, (5, 5), 0)

    # Convertir a HSV
    hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

    # ================== RANGOS DE VERDES EXTREMADAMENTE AMPLIOS ==================
    mask_main = cv2.inRange(hsv, np.array([10, 15, 15]), np.array([95, 255, 255]))
    mask_dark = cv2.inRange(hsv, np.array([30, 10, 10]), np.array([90, 150, 80]))
    mask_olive = cv2.inRange(hsv, np.array([8, 10, 10]), np.array([35, 120, 100]))
    
    mask = cv2.bitwise_or(mask_main, mask_dark)
    mask = cv2.bitwise_or(mask, mask_olive)
    
    # Post-procesamiento
    kernel = np.ones((10, 10), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.dilate(mask, kernel, iterations=2)

    # Encontrar contornos
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return "NO DETECTADO", 0

    # Filtrar por área mínima
    filtered_contours = [cnt for cnt in contours if cv2.contourArea(cnt) > 500]
    
    if not filtered_contours:
        return "NO DETECTADO", 0

    largest = max(filtered_contours, key=cv2.contourArea)
    area = cv2.contourArea(largest)

    print(f"DEBUG - Área detectada: {area} píxeles")
    
    # ================== MODO CALIBRACIÓN ==================
    if modo_calibracion and tamanio_real:
        print(f"📝 Calibrando: {tamanio_real} con área {area}")
        areas_detectadas[tamanio_real].append(area)
        
        # Mostrar progreso de calibración
        for tamaño in ["PEQUEÑO", "MEDIANO", "GRANDE"]:
            if len(areas_detectadas[tamaño]) > 0:
                promedio = sum(areas_detectadas[tamaño]) / len(areas_detectadas[tamaño])
                print(f"  {tamaño}: {len(areas_detectadas[tamaño])}/{cantidad_muestras} muestras (promedio: {promedio:.0f})")
        
        # Verificar si ya tenemos suficientes muestras
        todos_completos = all(len(areas_detectadas[t]) >= cantidad_muestras for t in ["PEQUEÑO", "MEDIANO", "GRANDE"])
        if todos_completos:
            print("\n✅ ¡CALIBRACIÓN COMPLETADA!")
            print("=" * 50)
            print("ÁREAS PROMEDIO:")
            for tamaño in ["PEQUEÑO", "MEDIANO", "GRANDE"]:
                promedio = sum(areas_detectadas[tamaño]) / len(areas_detectadas[tamaño])
                print(f"  {tamaño}: {promedio:.0f} píxeles")
            print("=" * 50)
            print("Actualiza tu código con estos umbrales:")
            
            # Calcular umbrales óptimos
            umbral_mediano = (sum(areas_detectadas["PEQUEÑO"])/len(areas_detectadas["PEQUEÑO"]) + 
                             sum(areas_detectadas["MEDIANO"])/len(areas_detectadas["MEDIANO"])) / 2
            umbral_grande = (sum(areas_detectadas["MEDIANO"])/len(areas_detectadas["MEDIANO"]) + 
                            sum(areas_detectadas["GRANDE"])/len(areas_detectadas["GRANDE"])) / 2
            
            print(f"\nif area < {umbral_mediano:.0f}:")
            print(f"    size = \"PEQUEÑO\"")
            print(f"elif area < {umbral_grande:.0f}:")
            print(f"    size = \"MEDIANO\"")
            print(f"else:")
            print(f"    size = \"GRANDE\"")
            
            return "CALIBRADO", int(area)
        
        return "CALIBRANDO", int(area)
    
    # ================== MODO NORMAL (usando áreas calibradas) ==================
    # Si hay datos de calibración, usarlos
    if any(len(areas_detectadas[t]) > 0 for t in ["PEQUEÑO", "MEDIANO", "GRANDE"]):
        # Usar área máxima conocida o promedio
        areas_promedio = {}
        for tamaño in ["PEQUEÑO", "MEDIANO", "GRANDE"]:
            if len(areas_detectadas[tamaño]) > 0:
                areas_promedio[tamaño] = sum(areas_detectadas[tamaño]) / len(areas_detectadas[tamaño])
        
        if areas_promedio:
            # Ordenar por área
            if "GRANDE" in areas_promedio and area > areas_promedio["GRANDE"] * 0.7:
                size = "GRANDE"
            elif "MEDIANO" in areas_promedio and area > areas_promedio["MEDIANO"] * 0.7:
                size = "MEDIANO"
            else:
                size = "PEQUEÑO"
        else:
            # Umbrales por defecto (ajústalos según tu calibración)
            if area < 1500:
                size = "PEQUEÑO"
            elif area < 4000:
                size = "MEDIANO"
            else:
                size = "GRANDE"
    else:
        # Umbrales por defecto
        if area < 1500:
            size = "PEQUEÑO"
        elif area < 4000:
            size = "MEDIANO"
        else:
            size = "GRANDE"

    print(f"DEBUG - Clasificación: {size}")
    return size, int(area)