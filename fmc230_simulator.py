import time
import json
import random
import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "sensor/data"

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Static Retail Fridges at Specific Store Locations
RETAIL_FRIDGES = [
    {"imei": "356938035643809", "lat": -33.8688, "lng": 18.6819, "store": "Brackenfell Mall"},
    {"imei": "356938035643810", "lat": -34.0023, "lng": 18.4239, "store": "Constantia Village"},
    {"imei": "356938035643811", "lat": -33.8209, "lng": 18.4721, "store": "Blaauwberg Shopping Centre"},
]

# Ship Fridges (Moving GPS Locations)
SHIP_FRIDGES = [
    {"imei": "356938035643812", "lat": -33.918861, "lng": 18.4233, "speed_kmh": 30},
    {"imei": "356938035643813", "lat": -33.928861, "lng": 18.4333, "speed_kmh": 32},
    {"imei": "356938035643814", "lat": -33.938861, "lng": 18.4433, "speed_kmh": 28},
]

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("✅ Connected to MQTT Broker!")
    else:
        print(f"❌ Connection failed with error code {rc}")

def on_publish(client, userdata, mid):
    print(f"📩 Message {mid} successfully published!")

# Move Ship Fridges Closer to Europe Over Time
def update_ship_positions():
    for ship in SHIP_FRIDGES:
        lat_change = 0.002 * (ship["speed_kmh"] / 30)
        lng_change = 0.004 * (ship["speed_kmh"] / 30)

        ship["lat"] += lat_change
        ship["lng"] += lng_change

        if ship["lat"] >= 45.0:
            ship["speed_kmh"] = 10  # Slow down near Europe

# Generate Complete Sensor Data for Any Fridge
def generate_sensor_data(imei, lat, lng):
    return {
        "state": {
            "reported": {
                "deviceId": imei,
                "ts": int(time.time() * 1000),
                "latlng": f"{lat},{lng}",
                "alt": random.randint(0, 20),
                "ang": random.randint(0, 360),
                "sat": random.randint(3, 15),
                "sp": random.randint(0, 5),
                "evt": random.choice([0, 10828, 10829, 10831]),

                # Sensor Data (Temperature, Humidity, Movement, Battery)
                "10800": round(random.uniform(-5, 5), 1),
                "10801": round(random.uniform(-5, 5), 1),
                "10804": round(random.uniform(30, 80), 1),
                "10805": round(random.uniform(30, 80), 1),
                "10808": random.randint(0, 20),
                "10810": round(random.uniform(3.2, 3.7), 2),
                "10812": random.randint(0, 5),
                "10814": random.randint(0, 100),
                "10816": round(random.uniform(-180, 180), 1),
                "10818": round(random.uniform(-180, 180), 1),
                "10820": random.randint(0, 1),
            }
        }
    }

# MQTT Client Setup
client = mqtt.Client()
client.on_connect = on_connect
client.on_publish = on_publish
client.connect(BROKER, PORT, 60)
client.loop_start()  # Keep MQTT running in the background

while True:
    update_ship_positions()

    # Simulate Retail Fridges (Static)
    for fridge in RETAIL_FRIDGES:
        data = generate_sensor_data(fridge["imei"], fridge["lat"], fridge["lng"])
        payload = json.dumps(data)
        result = client.publish(TOPIC, payload)
        result.wait_for_publish()

    # Simulate Ship Fridges (Moving)
    for ship in SHIP_FRIDGES:
        data = generate_sensor_data(ship["imei"], ship["lat"], ship["lng"])
        payload = json.dumps(data)
        result = client.publish(TOPIC, payload)
        result.wait_for_publish()

    time.sleep(5)  # Simulate real-time updates every 5 sec
