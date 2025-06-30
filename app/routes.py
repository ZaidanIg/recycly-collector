import json
import time
import datetime
import io
import base64
import qrcode
import cv2

from flask import Blueprint, jsonify, request, send_file, Response, render_template, current_app
from .services.firebase_service import firebase_service
from .services.mqtt_service import mqtt_service
from .services.detection_service import detection_service

bp = Blueprint('main', __name__)

@bp.route('/')
def index():
    return render_template('index.html')

@bp.route('/start_scan', methods=['POST'])
def start_scan():
    req = request.get_json(force=True, silent=True) or {}
    session_id = req.get("session_id", f"qr_{int(time.time())}")
    
    data = {
        "active": True, "bottles": 0, "points": 0, "history": [],
        "started_at": int(time.time()), "last_update": int(time.time()),
        "session_id": session_id
    }
    firebase_service.set_session(session_id, data)
    
    payload = json.dumps({"session_id": session_id})
    mqtt_service.publish(current_app.config['MQTT_SESSION_TOPIC'], payload)
    
    return jsonify({"status": "started", "session_id": session_id})

@bp.route('/scan_state', methods=['GET'])
def scan_state():
    session_id = request.args.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400
    
    session = firebase_service.get_session(session_id)
    if not session:
        return jsonify({"error": "session not found"}), 404
        
    return jsonify(session)

@bp.route('/stop_scan', methods=['POST'])
def stop_scan():
    req = request.get_json(force=True, silent=True) or {}
    session_id = req.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400
        
    session = firebase_service.get_session(session_id)
    if not session or not session.get("active"):
        return jsonify({"status": "not_active", "message": "Session not found or already inactive."})
        
    firebase_service.update_session(session_id, {"active": False})
    
    payload = json.dumps({"session_id": session_id})
    mqtt_service.publish(current_app.config['MQTT_STOP_SESSION_TOPIC'], payload)
    
    return jsonify({"status": "stopped"})

@bp.route('/generate_qr', methods=['POST'])
def generate_qr():
    req = request.get_json(force=True, silent=True) or {}
    session_id = req.get("session_id")
    if not session_id:
        return jsonify({"error": "session_id required"}), 400
        
    session = firebase_service.get_session(session_id)
    if not session:
        return jsonify({"error": "Session not found"}), 404
    if session.get("active"):
        return jsonify({"error": "Cannot generate QR for an active session"}), 400
    if session.get("bottles", 0) == 0:
        return jsonify({"error": "No data to generate QR"}), 400
        
    expires_at_ts = int(time.time()) + 600  # Expire in 10 minutes
    expires_at_iso = datetime.datetime.utcfromtimestamp(expires_at_ts).isoformat() + 'Z'
    
    qr_payload = {
        "id": session_id,
        "bottles": session.get("bottles", 0),
        "points": session.get("points", 0),
        "expiresAt": expires_at_iso
    }
    firebase_service.save_qr_code_data(session_id, qr_payload)
    
    qr_content = json.dumps(qr_payload)
    img = qrcode.make(qr_content)
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    qr_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    
    mqtt_service.publish(current_app.config['MQTT_QR_TOPIC'], qr_content)
    
    return jsonify({**qr_payload, "qr_base64": qr_base64})

@bp.route('/qr_image/<session_id>', methods=['GET'])
def qr_image(session_id):
    qr_payload = firebase_service.get_qr_code_data(session_id)
    if not qr_payload:
        return jsonify({"error": "Not found"}), 404
        
    qr_data = json.dumps(qr_payload)
    qr_img = qrcode.make(qr_data)
    buf = io.BytesIO()
    qr_img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')

def gen_frames():
    while True:
        frame = detection_service.last_stream_frame.copy()
        ret, jpeg = cv2.imencode('.jpg', frame)
        if ret:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
        time.sleep(0.05) 
@bp.route('/stream')
def video_feed():
    return Response(gen_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

@bp.route('/monitor')
def monitor():
    return render_template('monitor.html')