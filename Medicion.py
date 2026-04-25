import cv2
import numpy as np

class DetectorLimones:
    def __init__(self, distancia_referencia_cm=25):
        """
        Inicializa el detector de limones.
        distancia_referencia_cm: Distancia a la que se tomaron las fotos para definir los tamaños.
        """
        self.distancia_referencia = distancia_referencia_cm
        
        # --- Rangos de color HSV para detectar limones (amarillos y verdes) ---
        # Estos rangos están ampliamente documentados para detectar cítricos [citation:4].
        self.color_bajos = [
            (12, 50, 50),   # Amarillo
            (30, 40, 40),   # Verde claro
            (35, 20, 20)    # Verde oscuro/oliva
        ]
        self.color_altos = [
            (38, 255, 255),  # Amarillo [citation:4]
            (85, 255, 255),  # Verde claro
            (85, 200, 150)   # Verde oscuro
        ]

        # --- Umbrales de área en PÍXELES (a la distancia de referencia) ---
        # Estos valores son el punto de partida. Deberás ajustarlos tras las primeras pruebas.
        print("\n=== CONFIGURACIÓN INICIAL ===")
        print("Los umbrales iniciales son estimados.")
        print("Deberás ajustar 'self.area_pequeno' y 'self.area_mediano'")
        print("según los valores de 'Área medida' que veas en tus pruebas.")
        self.area_pequeno = 1500   # Área máxima para un limón "Pequeño"
        self.area_mediano = 4000   # Área máxima para un limón "Mediano"
        print(f"Umbrales actuales: PEQUEÑO < {self.area_pequeno}px < MEDIANO < {self.area_mediano}px < GRANDE")
        print("=====================================\n")

    def obtener_mascara_limon(self, image_bytes):
        """
        Aplica máscaras de color y morfología para aislar el contorno del limón.
        """
        # Decodificar imagen
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return None

        # Reducir ruido con un desenfoque
        img_blur = cv2.GaussianBlur(img, (7, 7), 0)
        
        # Convertir a espacio de color HSV (mejor para segmentación por color)
        hsv = cv2.cvtColor(img_blur, cv2.COLOR_BGR2HSV)

        # Crear una máscara combinando los diferentes rangos de color
        mascara_total = cv2.inRange(hsv, np.array(self.color_bajos[0]), np.array(self.color_altos[0]))
        for i in range(1, len(self.color_bajos)):
            mascara_parcial = cv2.inRange(hsv, np.array(self.color_bajos[i]), np.array(self.color_altos[i]))
            mascara_total = cv2.bitwise_or(mascara_total, mascara_parcial)

        # --- Limpieza de la máscara (Morfológica) ---
        # Eliminar ruido pequeño y cerrar huecos dentro del limón [citation:4]
        kernel = np.ones((9, 9), np.uint8)
        mascara_limpia = cv2.morphologyEx(mascara_total, cv2.MORPH_CLOSE, kernel)
        mascara_limpia = cv2.morphologyEx(mascara_limpia, cv2.MORPH_OPEN, kernel)
        
        # Rellenar agujeros internos más grandes
        mascara_limpia = cv2.dilate(mascara_limpia, kernel, iterations=2)
        mascara_limpia = cv2.erode(mascara_limpia, kernel, iterations=1)
        mascara_limpia = cv2.morphologyEx(mascara_limpia, cv2.MORPH_CLOSE, kernel)

        return mascara_limpia

    def obtener_contorno_principal(self, mascara):
        """
        Encuentra el contorno más grande en la máscara, asumiendo que es el limón.
        """
        # Encontrar todos los contornos [citation:8]
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        if not contornos:
            return None, 0

        # Encontrar el contorno con el área más grande
        contorno_principal = max(contornos, key=cv2.contourArea)
        area = cv2.contourArea(contorno_principal)
        
        return contorno_principal, area

    def corregir_por_distancia(self, area_px, distancia_actual_cm):
        """
        Corrige el área en píxeles si la distancia de la foto es diferente a la de referencia.
        Aplica la ley cuadrática inversa.
        """
        if distancia_actual_cm <= 0:
            return area_px
        factor = (distancia_actual_cm / self.distancia_referencia) ** 2
        # Si la foto se tomó más lejos, el factor es >1 y el área aumenta
        return area_px * factor

    def clasificar_limon(self, area_px):
        """
        Clasifica el limón como 'PEQUEÑO', 'MEDIANO' o 'GRANDE' según los umbrales.
        """
        if area_px < self.area_pequeno:
            return "PEQUEÑO"
        elif area_px < self.area_mediano:
            return "MEDIANO"
        else:
            return "GRANDE"

    def detectar(self, image_bytes, distancia_actual_cm=25):
        """
        Función principal para detectar y clasificar el limón en una imagen.
        
        Args:
            image_bytes: Bytes de la imagen.
            distancia_actual_cm: Distancia en cm a la que se tomó la foto.
        
        Returns:
            tuple: (clasificacion_texto, area_en_pixeles)
        """
        # 1. Obtener la máscara del limón
        mascara = self.obtener_mascara_limon(image_bytes)
        if mascara is None:
            return "ERROR", 0

        # 2. Encontrar el contorno principal
        _, area_medida_px = self.obtener_contorno_principal(mascara)
        if area_medida_px < 100: # Área mínima para considerar un objeto
            return "NO_DETECTADO", 0

        # 3. Corregir área según la distancia (clave para la robustez) [citation:8]
        area_corregida_px = self.corregir_por_distancia(area_medida_px, distancia_actual_cm)

        # 4. Clasificar el limón
        clasificacion = self.clasificar_limon(area_corregida_px)

        # Mostrar información de depuración
        if distancia_actual_cm != self.distancia_referencia:
            print(f"  -> Área corregida para {distancia_actual_cm}cm: {area_corregida_px:.0f}px (medido: {area_medida_px:.0f}px)")
        else:
            print(f"  -> Área medida: {area_medida_px:.0f}px")

        return clasificacion, int(area_corregida_px)

# --- FUNCIÓN DE FÁCIL USO (para integrar en tu otro código) ---
def detectar_tamano(image_bytes, distancia_cm=25):
    """
    Punto de entrada simple para usar el detector.
    """
    detector = DetectorLimones(distancia_referencia_cm=25)
    return detector.detectar(image_bytes, distancia_cm)

# --- CÓDIGO PARA CALIBRACIÓN (¡IMPORTANTE!) ---
def calibrar_con_tus_imagenes():
    """
    Ejecuta este bloque para ajustar los umbrales a tu configuración.
    No requiere una base de datos, solo pasar una imagen de ejemplo.
    """
    print("\n--- MODO DE CALIBRACIÓN ---")
    print("1. Pega la ruta de una imagen de un limón cuyo tamaño conozcas")
    print("2. Ejecuta este bloque para ver qué área en píxeles detecta")
    print("3. Ajusta los valores 'area_pequeno' y 'area_mediano' en la clase 'DetectorLimones'")
    print("   basándote en las áreas que observes.")
    print("Ejemplo: Si un limón 'Mediano' que has medido da 3000px, ajusta 'area_mediano' a 3000.")
    print("-----------------------------------\n")

    # --- ¡CAMBIA ESTO POR LA RUTA DE TU IMAGEN DE PRUEBA! ---
    RUTA_IMAGEN_PRUEBA = "ruta/a/tu/imagen_de_limon.jpg"
    # --------------------------------------------------------
    
    try:
        with open(RUTA_IMAGEN_PRUEBA, "rb") as f:
            img_bytes = f.read()
        
        # Usar el detector para obtener el área de tu limón de ejemplo
        detector_temp = DetectorLimones(distancia_referencia_cm=25)
        clasificacion, area = detector_temp.detectar(img_bytes, distancia_actual_cm=25)
        
        print(f"\n--- RESULTADO DE LA PRUEBA ---")
        print(f"Área detectada para el limón de ejemplo: {area} píxeles")
        print(f"(Clasificación temporal: {clasificacion})")
        print("\n👉 ¡Usa este valor de área como referencia para ajustar tus umbrales!")
    
    except FileNotFoundError:
        print(f"\n[ERROR] No se encontró la imagen en: {RUTA_IMAGEN_PRUEBA}")
        print("Por favor, cambia 'RUTA_IMAGEN_PRUEBA' por la ruta correcta a una imagen de limón.")

# ---- EJEMPLO DE CÓMO USAR EL DETECTOR ----
if __name__ == "__main__":
    # 1. (OPCIONAL) Ejecuta la calibración una vez para ajustar los parámetros
    # calibrar_con_tus_imagenes() # Descomenta esta línea y edita la ruta de la imagen
    
    # 2. Después de calibrar, creas una instancia del detector
    mi_detector = DetectorLimones(distancia_referencia_cm=25)
    
    # 3. Simulas la llegada de una imagen (cámbialo por los bytes de tu ESP32-CAM)
    print("\n--- SIMULACIÓN DE DETECCIÓN ---")
    # Simula los bytes de una imagen desde tu ESP32-CAM
    # imagen_bytes = ... (aquí pondrías los bytes que recibes de la cámara)
    # resultado, area = mi_detector.detectar(imagen_bytes, distancia_actual_cm=25)
    # print(f"Tamaño detectado: {resultado}, Área: {area} píxeles")
    print("El código está listo. Reemplaza los comentarios con la captura real de tu ESP32-CAM.")