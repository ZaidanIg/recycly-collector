import json
import threading
import time
import traceback

from flask import Flask, current_app

from config import Config
from .services.firebase_service import firebase_service
from .services.mqtt_service import mqtt_service
from .services.detection_service import detection_service

trigger_event = threading.Event()

def handle_detection_trigger(app, session_id):
    with app.app_context():
        print(f"[DETECTION] Memproses deteksi untuk sesi {session_id}")
        
        session = firebase_service.get_session(session_id)
        if not session or not session.get("active", False):
            print(f"[DETECTION] Sesi {session_id} tidak aktif atau tidak ditemukan. Proses dibatalkan.")
            return

        detection_result, annotated_frame = detection_service.detect_bottle()
        if not detection_result:
            print("[DETECTION] Gagal melakukan deteksi (kemungkinan timeout atau error kamera).")
            return
        
        if not session or not session.get("active", False):
            print(f"[DETECTION] Sesi {session_id} menjadi tidak aktif saat deteksi berjalan. Hasil tidak akan disimpan.")

        session = firebase_service.get_session(session_id)
        if detection_result["is_bottle"] and detection_result["confidence"] > 0.95:
            filename = detection_service.save_detected_image(annotated_frame, detection_result['confidence'])
            
            session = firebase_service.get_session(session_id)
            if not session: return

            new_bottles = session.get("bottles", 0) + 1
            new_points = session.get("points", 0) + 2
            history = session.get("history", [])
            
            log_entry = {
                "status": "accepted", "label": "bottle", "point": 2,
                "confidence": detection_result["confidence"],
                "timestamp": int(time.time()), "filename": filename
            }
            history.append(log_entry)
            
            firebase_service.update_session(session_id, {
                "bottles": new_bottles, "points": new_points,
                "history": history, "last_update": int(time.time())
            })
            
            mqtt_service.publish(current_app.config['MQTT_RESULT_TOPIC'], json.dumps(log_entry))
        else:
            print(f"Botol tidak terdeteksi atau confidence rendah ({detection_result.get('confidence', 0):.2f})")


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Inisialisasi semua service
    firebase_service.init_app(app.config['FIREBASE_CREDENTIALS_PATH'])
    mqtt_service.init_app(
        app.config['MQTT_BROKER_URL'],
        app.config['MQTT_BROKER_PORT'],
        app.config['MQTT_USERNAME'],
        app.config['MQTT_PASSWORD']
    )
    detection_service.init_app(
        app.config['MODEL_PROTOTXT_PATH'],
        app.config['MODEL_CAFFE_PATH'],
        app.config['DETECTION_CLASSES'],
        app.config['ESP32_STREAM_URL'],
        app.config['SAVE_FOLDER']
    )

    from . import routes
    app.register_blueprint(routes.bp)

    return app