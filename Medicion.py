import argparse
import time
from pathlib import Path
import cv2 as cv
import numpy as np
from ultralytics import YOLO

def parse_args():
    p = argparse.ArgumentParser(description="YOLOv8 sobre stream MJPEG de ESP32-CAM - solo dimensiones")
    
    p.add_argument("--url", required=True, 
                   help="URL del stream (p.ej. http://10.187.134.56:81/stream)")
    
    p.add_argument("--model", default="yolov8n.pt", 
                   help="nombre del modelo YOLO (yolov8n.pt, yolov8s.pt, etc)")
    
    p.add_argument("--conf", type=float, default=0.35, 
                   help="Umbral de confianza")
    
    p.add_argument("--save", action="store_true", 
                   help="Guardar video con anotaciones (output.mp4)")
    
    p.add_argument("--show", action="store_true", 
                   help="Mostrar ventana con vídeo procesado")
    
    p.add_argument("--max-w", type=int, default=640, 
                   help="Redimensionar ancho máximo (0 = no escalar)")
    
    p.add_argument("--reconnect", type=int, default=3, 
                   help="Intentos de reconexión si el stream cae")
    
    return p.parse_args()


def open_capture(url: str):
    cap = cv.VideoCapture(url, cv.CAP_FFMPEG)
    cap.set(cv.CAP_PROP_BUFFERSIZE, 1)
    return cap


def main():
    args = parse_args()
    
    print(f"Cargando modelo: {args.model}")
    model = YOLO(args.model)
    
    cap = open_capture(args.url)
    
    if not cap.isOpened():
        print(f"[ERROR] No se puede abrir el stream: {args.url}")
        return
    
    writer = None
    fourcc = None
    
    if args.save:
        fourcc = cv.VideoWriter_fourcc(*"mp4v")
    
    prev_time = time.time()
    fps = 0.0
    reconnects_left = args.reconnect
    
    while True:
        ok, frame = cap.read()
        
        if not ok or frame is None:
            print("[WARN] Frame nulo. Intentando reconectar...")
            time.sleep(0.7)
            cap.release()
            cap = open_capture(args.url)
            
            if not cap.isOpened():
                reconnects_left -= 1
                if reconnects_left < 1:
                    print("[ERROR] Sin stream y sin reconexiones restantes. Saliendo.")
                    break
            continue
        
        reconnects_left = args.reconnect
        
        # Redimensionar si es necesario
        if args.max_w > 0 and frame.shape[1] > args.max_w:
            h = int(frame.shape[0] * (args.max_w / frame.shape[1]))
            frame = cv.resize(frame, (args.max_w, h), interpolation=cv.INTER_AREA)
        
        # Inferencia
        results = model.predict(source=frame, conf=args.conf, verbose=False)
        
        annotated = frame.copy()
        
        # Dibujar solo bounding box + dimensiones
        for r in results:
            if r.boxes is None:
                continue
                
            for box in r.boxes:
                conf = float(box.conf)
                if conf < args.conf:  # por si acaso
                    continue
                    
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                x1, y1, x2, y2 = xyxy.tolist()
                
                # Calcular ancho y alto en píxeles
                width = x2 - x1
                height = y2 - y1
                
                # Etiqueta solo con dimensiones
                label = f"{width}x{height}"
                
                # Rectángulo
                cv.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
                
                # Fondo para el texto
                tw, th = cv.getTextSize(label, cv.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                cv.rectangle(annotated, (x1, y1 - th - 6), (x1 + tw + 6, y1), (0, 255, 0), -1)
                
                # Texto
                cv.putText(annotated, label, (x1 + 3, y1 - 4),
                          cv.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
        
        # FPS
        now = time.time()
        fps = fps * 0.9 + (1.0 / max(1e-6, now - prev_time)) * 0.1
        prev_time = now
        
        cv.putText(annotated, f"FPS: {fps:.1f}", (8, 20),
                  cv.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        
        # Inicializar writer con el tamaño real (solo primera vez)
        if writer is None and args.save and annotated is not None:
            h, w = annotated.shape[:2]
            writer = cv.VideoWriter("output.mp4", fourcc, 20.0, (w, h))
            print(f"Guardando vídeo en output.mp4 – {w}x{h} @ 20fps")
        
        if writer is not None:
            writer.write(annotated)
        
        if args.show:
            cv.imshow("ESP32-CAM + YOLOv8 (dimensiones)", annotated)
            
            key = cv.waitKey(1) & 0xFF
            if key == 27 or key == ord('q'):
                break
    
    if writer is not None:
        writer.release()
    
    cap.release()
    cv.destroyAllWindows()


if __name__ == "__main__":
    main()