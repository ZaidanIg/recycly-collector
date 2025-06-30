import threading
import json
import time
import traceback


from app import create_app, trigger_event, handle_detection_trigger
from app.services.mqtt_service import mqtt_service


app = create_app()


def on_mqtt_message(topic, payload):
    """Callback ini hanya bertugas menyalakan sinyal."""
    print(f"[MQTT] Trigger diterima: {payload}")
    try:
        data = json.loads(payload)
        session_id = data.get("session_id")
        if session_id:
            trigger_event.session_id = session_id
            trigger_event.set()
    except Exception as e:
        print(f"[MQTT ERROR] Gagal memproses pesan: {e}")

def trigger_watcher():
    """Satu thread tunggal yang menunggu sinyal dan melakukan pekerjaan berat."""
    while True:
        print("Watcher: Menunggu trigger...")
        trigger_event.wait()
        
        session_id = getattr(trigger_event, 'session_id', None)
        trigger_event.clear()
        
        print(f"Watcher: Sinyal diterima untuk sesi {session_id}")
        if session_id:
            try:
                
                handle_detection_trigger(app, session_id)
            except Exception:
                print(f"!!! ERROR DI DALAM WATCHER THREAD UNTUK SESI {session_id} !!!")
                traceback.print_exc()
        
        time.sleep(1) 

if __name__ == '__main__':
    mqtt_service.set_on_message_callback(on_mqtt_message)

    with app.app_context():
        mqtt_service.subscribe(app.config['MQTT_TRIGGER_TOPIC'])

    watcher_thread = threading.Thread(target=trigger_watcher, daemon=True)
    watcher_thread.start()
    print("Thread Trigger Watcher telah dimulai.")

    app.run(host='0.0.0.0', port=5001, debug=False)