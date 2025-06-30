import cv2
import numpy as np
import time
import datetime
import os
from threading import Thread
from queue import Queue

class DetectionService:
    def __init__(self):
        self.net = None
        self.classes = []
        self.esp32_url = ''
        self.save_folder = ''
        self.last_stream_frame = np.zeros((240, 320, 3), dtype=np.uint8)

    def init_app(self, prototxt_path, caffe_path, classes, esp32_url, save_folder):
        self.net = cv2.dnn.readNetFromCaffe(prototxt_path, caffe_path)
        self.classes = classes
        self.esp32_url = esp32_url
        self.save_folder = save_folder
        os.makedirs(self.save_folder, exist_ok=True)
        print("Detection service initialized.")

    def _capture_frame(self):
        q = Queue()

        def worker(url, queue_instance):
            cap = cv2.VideoCapture(url)
            ret, frame = cap.read()
            cap.release()
            
            if not ret or frame is None:
                queue_instance.put(None)
            else:
                queue_instance.put(frame)

        capture_thread = Thread(target=worker, args=(self.esp32_url, q))
        capture_thread.daemon = True
        capture_thread.start()

        try:
            frame = q.get(timeout=10.0)
            if frame is not None:
                print("[INFO] Frame berhasil ditangkap dari thread.")
                return frame
            else:
                print("[ERROR] Thread penangkap gambar selesai, namun tidak ada frame yang valid.")
                return None
        except Exception:
            print("[ERROR] Gagal menangkap frame dalam 10 detik (Timeout). Kamera mungkin tidak responsif.")
            return None

    def detect_bottle(self):
        print("Memulai proses penangkapan frame...")
        frame = self._capture_frame()
        if frame is None:
            return None, None
        
        print("Frame diterima, memulai deteksi objek...")
        (h, w) = frame.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(frame, (224, 224)), 0.007843, (224, 224), 127.5)
        self.net.setInput(blob)
        detections = self.net.forward()

        detected_bottle = False
        max_confidence = 0.0

        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            idx = int(detections[0, 0, i, 1])
            label = self.classes[idx].upper()

            if confidence > 0.3:
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                color = (0, 255, 0) if confidence > 0.95 else (0, 165, 255)
                cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
                cv2.putText(frame, f"{label}: {confidence*100:.1f}%", (startX, startY-10),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                
                if label == "BOTTLE" and confidence > max_confidence:
                    detected_bottle = True
                    max_confidence = confidence

        self.last_stream_frame = cv2.resize(frame, (320, 240))

        result = {
            "is_bottle": detected_bottle,
            "confidence": float(max_confidence),
            "timestamp": int(time.time()),
        }
        
        print("Deteksi objek selesai.")
        return result, self.last_stream_frame
    
    def save_detected_image(self, frame, confidence):
        dt_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self.save_folder}/bottle_{dt_str}_{int(confidence*100)}.jpg"
        save_img = cv2.resize(frame, (320, 240))
        cv2.imwrite(filename, save_img)
        print(f"[SAVE] Image saved to {filename}")
        return filename

detection_service = DetectionService()