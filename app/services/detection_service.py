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
        try:
            self.net = cv2.dnn.readNetFromCaffe(prototxt_path, caffe_path)
            self.classes = classes
            self.esp32_url = esp32_url
            self.save_folder = save_folder
            os.makedirs(self.save_folder, exist_ok=True)
            print("Detection service initialized.")
        except cv2.error as e:
            print(f"ERROR: Gagal memuat model Caffe. Pastikan path file benar: {e}")
            raise  # Re-throw exception to stop the app
        except Exception as e:
            print(f"ERROR: Terjadi kesalahan saat inisialisasi DetectionService: {e}")
            raise

    def _capture_frame(self):
        q = Queue()

        def worker(url, queue_instance):
            try:
                cap = cv2.VideoCapture(url)
                if not cap.isOpened():
                    print(f"[ERROR] Tidak bisa membuka stream dari URL: {url}")
                    queue_instance.put(None)
                    return
                
                ret, frame = cap.read()
                cap.release()
                
                if not ret or frame is None:
                    queue_instance.put(None)
                else:
                    queue_instance.put(frame)
            except Exception as e:
                print(f"[ERROR] Exception di dalam thread penangkap gambar: {e}")
                queue_instance.put(None)

        capture_thread = Thread(target=worker, args=(self.esp32_url, q))
        capture_thread.start()
        
        try:
            # Menunggu hasil dari thread dengan timeout
            frame = q.get(timeout=10.0)
            if frame is not None:
                print("[INFO] Frame berhasil ditangkap dari thread.")
                return frame
            else:
                print("[ERROR] Thread selesai, namun tidak ada frame yang valid.")
                return None
        except Exception:
            print("[ERROR] Gagal menangkap frame dalam 10 detik (Timeout). Kamera mungkin tidak responsif.")
            return None

    def detect_bottle(self):
        print("Memulai proses penangkapan frame...")
        frame = self._capture_frame()
        if frame is None:
            return None, self.last_stream_frame
        
        print("Frame diterima, memulai deteksi objek...")
        (h, w) = frame.shape[:2]
        
        try:
            blob = cv2.dnn.blobFromImage(cv2.resize(frame, (224, 224)), 0.007843, (224, 224), 127.5)
            self.net.setInput(blob)
            detections = self.net.forward()
        except cv2.error as e:
            print(f"ERROR: Terjadi kesalahan saat proses deteksi DNN: {e}")
            return None, frame # Return original frame on error

        max_confidence = 0.0
        best_detection_idx = -1
        
        # Cari deteksi dengan confidence tertinggi
        for i in range(detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > max_confidence:
                max_confidence = confidence
                best_detection_idx = i

        is_bottle = False
        detected_label = "unknown"

        # Proses deteksi terbaik
        if best_detection_idx != -1:
            confidence = detections[0, 0, best_detection_idx, 2]
            idx = int(detections[0, 0, best_detection_idx, 1])
            label = self.classes[idx].upper()

            box = detections[0, 0, best_detection_idx, 3:7] * np.array([w, h, w, h])
            (startX, startY, endX, endY) = box.astype("int")
            
            is_bottle_detected = (label == "BOTTLE")
            color = (0, 255, 0) if is_bottle_detected and confidence > 0.95 else (0, 0, 255)
            
            cv2.rectangle(frame, (startX, startY), (endX, endY), color, 2)
            text = f"{label}: {confidence*100:.1f}%"
            cv2.putText(frame, text, (startX, startY - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
            
            if is_bottle_detected:
                is_bottle = True
            
            detected_label = label

        self.last_stream_frame = cv2.resize(frame, (320, 240))

        result = {
            "is_bottle": is_bottle,
            "confidence": float(max_confidence),
            "label": detected_label,
            "timestamp": int(time.time()),
        }
        
        print(f"Deteksi objek selesai. Hasil: {result}")
        return result, self.last_stream_frame
    
    def save_detected_image(self, frame, confidence, is_rejected=False):
        try:
            dt_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            status = "rejected" if is_rejected else "accepted"
            filename = f"{self.save_folder}/{status}_{dt_str}_{int(confidence*100)}.jpg"
            save_img = cv2.resize(frame, (320, 240))
            cv2.imwrite(filename, save_img)
            print(f"[SAVE] Image saved to {filename}")
            return filename
        except Exception as e:
            print(f"ERROR: Gagal menyimpan gambar: {e}")
            return None

detection_service = DetectionService()