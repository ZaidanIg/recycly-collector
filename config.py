# config.py
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SAVE_FOLDER = "waste-collection"

    FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS_PATH', 'recycly-collector-firebase-adminsdk-fbsvc-40b4a103a0.json')

    MQTT_BROKER_URL = os.environ.get('MQTT_BROKER_URL', 'broker.emqx.io')
    MQTT_BROKER_PORT = int(os.environ.get('MQTT_BROKER_PORT', 1883))
    MQTT_USERNAME = os.environ.get('MQTT_USERNAME', 'recycly-collectorv2')
    MQTT_PASSWORD = os.environ.get('MQTT_PASSWORD', '')
    MQTT_TRIGGER_TOPIC = 'waste/trigger'
    MQTT_RESULT_TOPIC = 'waste/accepted'
    MQTT_QR_TOPIC = "waste/qr"
    MQTT_SESSION_TOPIC = "waste/session"
    MQTT_STOP_SESSION_TOPIC = "waste/stop_session"

    MODEL_PROTOTXT_PATH = './model/MobileNetSSD_deploy.prototxt'
    MODEL_CAFFE_PATH = './model/MobileNetSSD_deploy.caffemodel'
    DETECTION_CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat", "bottle", "bus", "car", "cat", "chair", "cow",
                         "diningtable", "dog", "horse", "motorbike", "person", "pottedplant", "sheep", "sofa", "train", "tvmonitor"]
    
    ESP32_STREAM_URL = os.environ.get('ESP32_STREAM_URL', 'http://172.20.10.2:81/stream')