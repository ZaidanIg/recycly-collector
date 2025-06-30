
import json
import paho.mqtt.client as mqtt

class MQTTService:
    def __init__(self):
        self.client = mqtt.Client(client_id="flask_recycly_collector_modular")
        self.on_message_callback = None

    def init_app(self, broker, port, username, password):
        self.client.username_pw_set(username, password)
        self.client.on_message = self._on_message_internal
        self.client.connect(broker, port, 60)
        self.client.loop_start()
        print("MQTT service initialized and connected.")

    def _on_message_internal(self, client, userdata, msg):
        if self.on_message_callback:
            self.on_message_callback(msg.topic, msg.payload)

    def subscribe(self, topic):
        print(f"Subscribing to MQTT topic: {topic}")
        self.client.subscribe(topic)

    def publish(self, topic, payload):
        self.client.publish(topic, payload)
        print(f"[MQTT] Published to {topic}: {payload}")

    def set_on_message_callback(self, callback):
        self.on_message_callback = callback

mqtt_service = MQTTService()