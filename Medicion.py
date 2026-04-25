import cv2
import numpy as np

class DetectorLimones:
    def __init__(self, distancia_referencia_cm=25):
        self.distancia_ref = distancia_referencia_cm

        # Rangos HSV más amplios posibles para limones (amarillos y verdes)
        # Basados en documentación: el limón puede ir desde amarillo intenso hasta verde oscuro
        self.rangos_verde_amarillo = [
            # Amarillos (maduros)
            (np.array([10, 30, 40]), np.array([40, 255, 255])),
            # Verdes claros (pintones)
            (np.array([30, 30, 30]), np.array([85, 255, 255])),
            # Verdes oscuros / oliva
            (np.array([35, 15, 15]), np.array([90, 200, 150])),
            # Tonos intermedios (amarillo-verdoso)
            (np.array([20, 40, 40]), np.array([55, 255, 255]))
        ]

        # --- Parámetros a ajustar según pruebas ---
        # Mide el área (píxeles) de un limón que consideres PEQUEÑO (a 25cm)
        self.area_pequeno = 1500   # Cambia este valor tras probar
        # Mide el área de un limón MEDIANO (a 25cm)
        self.area_mediano = 4000   # Cambia este valor tras probar
        # -------------------------------------------------

        # Área mínima confiable para ignorar ruido
        self.area_minima = 300

        # Parámetros de forma para limón (opcional, ayuda a filtrar objetos no deseados)
        self.circularidad_min = 0.18
        self.aspect_ratio_min = 0.3
        self.aspect_ratio_max = 3

    def obtener_mascara(self, img_bgr):
        """Genera una máscara combinando múltiples rangos HSV."""
        hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
        mascara = np.zeros(hsv.shape[:2], dtype=np.uint8)
        for lower, upper in self.rangos_verde_amarillo:
            mascara = cv2.bitwise_or(mascara, cv2.inRange(hsv, lower, upper))

        # Limpieza morfológica para cerrar huecos y eliminar ruido
        kernel = np.ones((7,7), np.uint8)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_CLOSE, kernel)
        mascara = cv2.morphologyEx(mascara, cv2.MORPH_OPEN, kernel)
        mascara = cv2.dilate(mascara, kernel, iterations=2)
        mascara = cv2.erode(mascara, kernel, iterations=1)
        return mascara

    def extraer_limon(self, mascara):
        """Encuentra el contorno más grande que cumpla con condiciones de forma."""
        contornos, _ = cv2.findContours(mascara, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if not contornos:
            return None, 0

        mejores = []
        for cnt in contornos:
            area = cv2.contourArea(cnt)
            if area < self.area_minima:
                continue

            # Circularidad (opcional pero útil)
            perimetro = cv2.arcLength(cnt, True)
            if perimetro == 0:
                continue
            circularidad = 4 * np.pi * area / (perimetro * perimetro)

            # Relación de aspecto del rectángulo envolvente
            x, y, w, h = cv2.boundingRect(cnt)
            aspect = max(w, h) / min(w, h) if min(w, h) > 0 else 0

            if (circularidad >= self.circularidad_min and
                self.aspect_ratio_min <= aspect <= self.aspect_ratio_max):
                mejores.append((cnt, area))

        if not mejores:
            # Fallback: el contorno más grande
            cnt_max = max(contornos, key=cv2.contourArea)
            area_max = cv2.contourArea(cnt_max)
            if area_max >= self.area_minima:
                return cnt_max, area_max
            else:
                return None, 0

        # Entre los que pasan el filtro, elegimos el de mayor área
        mejor_contorno = max(mejores, key=lambda x: x[1])[0]
        mejor_area = cv2.contourArea(mejor_contorno)
        return mejor_contorno, mejor_area

    def corregir_por_distancia(self, area_px, distancia_actual_cm):
        """Normaliza el área a la distancia de referencia (ley cuadrática inversa)."""
        if distancia_actual_cm <= 0:
            return area_px
        factor = (distancia_actual_cm / self.distancia_ref) ** 2
        return area_px / factor   # Área que tendría si estuviera a distancia_ref

    def clasificar(self, area_px_normalizada):
        if area_px_normalizada < self.area_pequeno:
            return "PEQUEÑO"
        elif area_px_normalizada < self.area_mediano:
            return "MEDIANO"
        else:
            return "GRANDE"

    def detectar(self, image_bytes, distancia_cm=25):
        """
        Parámetros:
            image_bytes: bytes de la imagen (como lo recibes del ESP32-CAM)
            distancia_cm: distancia real a la que se tomó la foto (por defecto 25)
        Retorna: (tamaño, área_corregida)
        """
        # Convertir bytes a imagen OpenCV
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            return "ERROR", 0

        # 1. Obtener máscara por color
        mascara = self.obtener_mascara(img)

        # 2. Extraer contorno principal del limón
        contorno, area_medida = self.extraer_limon(mascara)
        if contorno is None:
            return "NO_DETECTADO", 0

        # 3. Corregir área por distancia
        area_corregida = self.corregir_por_distancia(area_medida, distancia_cm)

        # 4. Clasificar
        tamano = self.clasificar(area_corregida)

        # Depuración en consola
        print(f"Área medida: {area_medida:.0f} px | Corregida (a {self.distancia_ref}cm): {area_corregida:.0f} px | Clasificación: {tamano}")

        return tamano, int(area_corregida)


# ---------- FUNCIÓN DE FÁCIL USO (para llamar desde tu otro código) ----------
def detectar_tamano(image_bytes, distancia_cm=25):
    """
    Punto de entrada único.
    Uso: tamaño, area_pixeles = detectar_tamano(imagen_bytes, distancia_cm=25)
    """
    detector = DetectorLimones(distancia_referencia_cm=25)
    return detector.detectar(image_bytes, distancia_cm)


# Ejemplo de cómo calibrar los umbrales de área (sin usar imágenes externas):
if __name__ == "__main__":
    print("=== CÓDIGO DE DETECCIÓN DE LIMONES ===")
    print("1. Coloca un limón del tamaño que conozcas (ej. mediano) a 25 cm de la cámara.")
    print("2. Ejecuta la detección (llamando a detectar_tamano) y anota el área corregida que aparece en consola.")
    print("3. Repite con un limón pequeño y uno grande.")
    print("4. Edita los valores de 'area_pequeno' y 'area_mediano' en la clase DetectorLimones según lo observado.\n")
    print("Ejemplo: si el limón mediano dió 3200 px, ajusta area_mediano = 3200.")
    print("         si el pequeño dió 1200 px, ajusta area_pequeno = 1200.\n")
    print("El código ya está listo para usarse; solo necesitas integrar la recepción de la imagen.")