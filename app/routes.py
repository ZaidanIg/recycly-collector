import json
import time
import datetime
import io
import base64
import qrcode
import cv2
import traceback
import os

from flask import Blueprint, jsonify, request, send_file, Response, render_template, current_app, send_from_directory
from .services.firebase_service import firebase_service
from .services.mqtt_service import mqtt_service
from .services.detection_service import detection_service

bp = Blueprint('main', __name__)

# ... (fungsi handle_error, index, start_scan, scan_state, stop_scan tetap sama) ...
def handle_error(e, context="API"):
    print(f"ERROR in {context}: {e}\n{traceback.format_exc()}")
    return jsonify({"error": "An internal server error occurred."}), 500

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/start_scan', methods=['POST'])
def start_scan():
    try:
        req = request.get_json(force=True, silent=True) or {}
        session_id = req.get("session_id", f"qr_{int(time.time())}")
        data = { "active": True, "bottles": 0, "points": 0, "history": [], "started_at": int(time.time()), "last_update": int(time.time()), "session_id": session_id }
        if not firebase_service.set_session(session_id, data): return jsonify({"error": "Failed to communicate with database."}), 500
        payload = json.dumps({"session_id": session_id})
        mqtt_service.publish(current_app.config['MQTT_SESSION_TOPIC'], payload)
        return jsonify({"status": "started", "session_id": session_id})
    except Exception as e: return handle_error(e, "start_scan")

@bp.route('/scan_state', methods=['GET'])
def scan_state():
    try:
        session_id = request.args.get("session_id")
        if not session_id: return jsonify({"error": "session_id required"}), 400
        session = firebase_service.get_session(session_id)
        if session is None:
            if not firebase_service.db: return jsonify({"error": "Database connection error"}), 500
            return jsonify({"error": "session not found"}), 404
        return jsonify(session)
    except Exception as e: return handle_error(e, "scan_state")

@bp.route('/stop_scan', methods=['POST'])
def stop_scan():
    try:
        req = request.get_json(force=True, silent=True) or {}
        session_id = req.get("session_id")
        if not session_id: return jsonify({"error": "session_id required"}), 400
        session = firebase_service.get_session(session_id)
        if not session or not session.get("active"): return jsonify({"status": "not_active", "message": "Session not found or already inactive."})
        if not firebase_service.update_session(session_id, {"active": False}): return jsonify({"error": "Failed to update session in database."}), 500
        payload = json.dumps({"session_id": session_id})
        mqtt_service.publish(current_app.config['MQTT_STOP_SESSION_TOPIC'], payload)
        return jsonify({"status": "stopped"})
    except Exception as e: return handle_error(e, "stop_scan")

@bp.route('/generate_qr', methods=['POST'])
def generate_qr():
    try:
        req = request.get_json(force=True, silent=True) or {}
        session_id = req.get("session_id")
        if not session_id: return jsonify({"error": "session_id required"}), 400
        session = firebase_service.get_session(session_id)
        if not session: return jsonify({"error": "Session not found"}), 404
        if session.get("active"): return jsonify({"error": "Cannot generate QR for an active session"}), 400
        if session.get("bottles", 0) == 0: return jsonify({"error": "No data to generate QR"}), 400
            
        expires_at_dt = datetime.datetime.now() + datetime.timedelta(days=1)
        expires_at_iso = expires_at_dt.isoformat() + 'Z'
        
        qr_payload = {
            "id": session_id,
            "bottles": session.get("bottles", 0),
            "points": session.get("points", 0),
            "expiresAt": expires_at_iso,
            "filename": f"{session_id}.png"
        }
        if not firebase_service.save_qr_code_data(session_id, qr_payload):
            return jsonify({"error": "Failed to save QR data to database."}), 500
        
        qr_content = json.dumps(qr_payload)
        img = qrcode.make(qr_content)
        
        save_folder = os.path.join(current_app.root_path, '..', current_app.config['SAVE_FOLDER'])
        os.makedirs(save_folder, exist_ok=True)
        
        img_path = os.path.join(save_folder, qr_payload["filename"])
        img.save(img_path)
        
        mqtt_service.publish(current_app.config['MQTT_QR_TOPIC'], qr_content)
        return jsonify(qr_payload)
    except Exception as e: return handle_error(e, "generate_qr")

# ... (fungsi gen_frames dan /stream tetap sama) ...
def gen_frames():
    while True:
        try:
            frame = detection_service.last_stream_frame
            if frame is None or frame.size == 0:
                frame = np.zeros((240, 320, 3), dtype=np.uint8)
                cv2.putText(frame, "No Signal", (100, 120), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            ret, jpeg = cv2.imencode('.jpg', frame)
            if ret:
                yield (b'--frame\r\n' b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        except Exception as e: print(f"Error in gen_frames: {e}")
        time.sleep(0.05) 

@bp.route('/stream')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@bp.route('/display_qr/<filename>')
def display_qr(filename):
    try:
        return send_from_directory(
            directory=os.path.join(current_app.root_path, '..', current_app.config['SAVE_FOLDER']), 
            path=filename
        )
    except FileNotFoundError:
        return jsonify({"error": "File not found."}), 404

@bp.route('/download_qr/<filename>')
def download_qr(filename):
    """Menyajikan file QR untuk diunduh (memaksa download)."""
    try:
        return send_from_directory(
            directory=os.path.join(current_app.root_path, '..', current_app.config['SAVE_FOLDER']), 
            path=filename,
            as_attachment=True
        )
    except FileNotFoundError:
        return jsonify({"error": "File not found."}), 404

@bp.route('/monitor')
def monitor():
    return render_template('monitor.html')