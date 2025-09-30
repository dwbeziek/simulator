import time
import json
import random
import ssl
import paho.mqtt.client as mqtt

# MQTT Setup
BROKER = "app.cryolytix.com"
PORT = 8883

# Certificate paths
ca_cert_path = "../rootCA.pem"
client_cert_path = "certs/400000000000002_chain.pem"
client_key_path = "certs/400000000000002.key"


# Fridge Definitions
FRIDGES = [
    {"imei": "400000000000002", "lat": -33.8673337, "lng": 18.6344686, "name": "Engen Durban Road Convenience Centre"}
]



# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"Connected {userdata['imei']} to Cryolytix via MQTT and X.509 Auth!")
    else:
        print(f"Connection failed for {userdata['imei']}: {rc}")

def on_publish(client, userdata, mid):
    print(f"Message {mid} published for {userdata['imei']}!")




def generate_packet(fridge):
    lat, lng = fridge["lat"], fridge["lng"]
    ts = int(time.time() * 1000)
    door_opens = random.randint(1, 5)
    temp = -18 + door_opens * 0.5  # Simplified since all are static
    humidity = random.randint(0, 95)
    sensor_battery = random.uniform(2800, 3200)  # EYE Beacon battery

    packet = {
        "state": {
            "reported": {
                "ts": ts,
                "pr": 0,
                "latlng": f"{lat},{lng}",
                "alt": 69,
                "ang": 80,
                "sat": 14,
                "sp": 0,
                "evt": 0,
                "21": random.randint(0, 5),  # GSM Signal
                "113": random.randint(0, 100),  # Battery Level
                "182": random.randint(0, 500),  # GNSS HDOP
                "66": random.uniform(4534, 12470),  # External Voltage
                "67": random.uniform(3472, 4116),  # Device Battery Voltage (mV)
                "10804": int(humidity),  # EYE Humidity 1 (%)
                "10800": int(temp * 100),  # EYE Inside Temperature 1 (m°C)
                "10824": int(sensor_battery),  # EYE Battery Voltage 1 (mV)
                "10801": int(temp * 100)  # EYE Compressor Temperature 1 (m°C)
            }
        }
    }
    return packet

# Create clients per device
clients = {}
for fridge in FRIDGES:
    # ✅ Fixed client_id syntax
    client = mqtt.Client(client_id=fridge['imei'])
    # ✅ Added user data for callbacks
    client.user_data_set({"imei": fridge["imei"]})
    client.on_connect = on_connect
    client.on_publish = on_publish

    # Configure TLS/SSL
    client.tls_set(
        ca_certs=ca_cert_path,
        certfile=client_cert_path,
        keyfile=client_key_path,
        tls_version=ssl.PROTOCOL_TLSv1_2
    )

    client.connect(BROKER, PORT, 60)
    client.loop_start()
    clients[fridge["imei"]] = client

# Main Loop
try:
    while True:
        for fridge in FRIDGES:
            client = clients[fridge["imei"]]
            topic = "v1/devices/me/telemetry"
            packet = generate_packet(fridge)
            payload = json.dumps(packet)
            result = client.publish(topic, payload)
            result.wait_for_publish()
            print(f"Published to {topic}: {payload[:100]}...")
        time.sleep(30)
except KeyboardInterrupt:
    print("Simulator stopped by user")
    for client in clients.values():
        client.loop_stop()
        client.disconnect()