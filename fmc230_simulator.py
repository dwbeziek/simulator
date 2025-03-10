import time
import json
import random
import paho.mqtt.client as mqtt
from math import sin, cos, radians, sqrt, atan2, degrees

# MQTT Setup
BROKER = "mqtt://localhost" # use localhost if you want to run manually
PORT = 1883
client = mqtt.Client()

# Constants
EARTH_RADIUS = 6371  # km
KNOTS_TO_KMH = 1.852

# Fridge Definitions
FRIDGES = [
    {"imei": "356938035643809", "lat": -33.8688, "lng": 18.6819, "name": "Brackenfell Shop", "type": "static", "token": "FMC230_356938035643809"},
    {"imei": "356938035643810", "lat": -34.0023, "lng": 18.4239, "name": "Constantia Shop", "type": "static", "token": "FMC230_356938035643810"},
    {"imei": "356938035643811", "lat": -33.9249, "lng": 18.4241, "name": "Cruise Pantry", "type": "boat", "speed_knots": 15, "route": [(-29.8587, 31.0218), (-33.9249, 18.4241)], "progress": 0, "direction": 1, "token": "FMC230_356938035643811"},
    {"imei": "356938035643812", "lat": -33.9249, "lng": 18.4241, "name": "Cargo Container", "type": "boat", "speed_knots": 12, "route": [(-33.9249, 18.4241), (38.7223, -9.1393)], "progress": 0, "direction": 1, "signal": True, "token": "FMC230_356938035643812"},
    {"imei": "356938035643813", "lat": -33.9249, "lng": 18.4241, "name": "Cape Town Truck", "type": "truck", "speed_kmh": 60, "route": [(-33.9249, 18.4241), (-33.6167, 19.0111), (-33.9321, 18.8602)], "progress": 0, "direction": 1, "stops": 0, "token": "FMC230_356938035643813"},
    {"imei": "356938035643814", "lat": -33.9249, "lng": 18.4241, "name": "Springbok Truck", "type": "truck", "speed_kmh": 70, "route": [(-33.9249, 18.4241), (-29.6641, 17.8866)], "progress": 0, "direction": 1, "stops": 0, "token": "FMC230_356938035643814"},
]



# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    print(f"Connected {userdata['imei']} to MQTT Broker!" if rc == 0 else f"Connection failed for {userdata['imei']}: {rc}")

def on_publish(client, userdata, mid):
    print(f"Message {mid} published for {userdata['imei']}!")

# Helper Functions
def haversine(lat1, lon1, lat2, lon2):
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return EARTH_RADIUS * c

def interpolate_position(start_lat, start_lng, end_lat, end_lng, progress):
    lat = start_lat + (end_lat - start_lat) * progress
    lng = start_lng + (end_lng - end_lng) * progress
    return lat, lng

def update_position(fridge):
    if fridge["type"] == "static":
        return fridge["lat"], fridge["lng"]

    route = fridge["route"]
    start_idx = int(fridge["progress"] * (len(route) - 1))
    if start_idx >= len(route) - 1:
        fridge["direction"] *= -1
        start_idx = len(route) - 2

    start = route[start_idx]
    end = route[start_idx + 1]
    distance = haversine(start[0], start[1], end[0], end[1])
    speed = fridge["speed_kmh"] if "speed_kmh" in fridge else fridge["speed_knots"] * KNOTS_TO_KMH
    step = (speed / 3600) / distance
    fridge["progress"] += step * fridge["direction"] * 10
    if fridge["progress"] >= 1:
        fridge["progress"] = 1
    elif fridge["progress"] <= 0:
        fridge["progress"] = 0
    return interpolate_position(start[0], start[1], end[0], end[1], fridge["progress"] % 1)

def generate_packet(fridge):
    lat, lng = update_position(fridge)
    ts = int(time.time() * 1000)
    door_opens = random.randint(1, 5) if fridge["type"] == "static" else (random.randint(5, 10) if fridge["name"] == "Cruise Pantry" else random.randint(0, 2))
    temp = (-18 + door_opens * 0.5) if fridge["type"] == "static" else (-5 + door_opens * 0.2 if fridge["name"] == "Cruise Pantry" else -20 + door_opens * 0.1)
    humidity = random.randint(0, 95)
    battery = random.uniform(3472, 4116)  # Device battery (DB range)
    sensor_battery = random.uniform(2800, 3200)  # EYE Beacon battery
    speed = 0 if fridge["type"] == "static" else (fridge["speed_knots"] * KNOTS_TO_KMH if "speed_knots" in fridge else fridge["speed_kmh"] + random.uniform(-5, 5))

    packet = {
        "state": {
            "reported": {
                "ts": ts,
                "pr": 1 if door_opens > 0 else 0,
                "latlng": f"{lat},{lng}",
                "alt": random.randint(0, 20) if fridge["type"] != "boat" else 5,
                "ang": random.randint(0, 360),
                "sat": random.randint(3, 15) if fridge["type"] != "boat" or fridge.get("signal", True) else 0,
                "sp": speed,
                "evt": 0,
                "17": random.randint(-369, 460),  # Axis X
                "18": random.randint(-156, 635),  # Axis Y
                "19": random.randint(-1052, 962),  # Axis Z
                "239": random.randint(0, 1),  # Ignition
                "240": 1 if speed > 0 else 0,  # Movement
                "80": random.randint(0, 4),  # Data Mode
                "21": random.randint(0, 5),  # GSM Signal
                "200": random.randint(0, 2),  # Sleep Mode
                "69": random.randint(0, 3),  # GNSS Status
                "113": random.randint(0, 100),  # Battery Level
                "181": random.randint(0, 500),  # GNSS PDOP
                "182": random.randint(0, 500),  # GNSS HDOP
                "66": random.uniform(4534, 12470),  # External Voltage
                "206": 21014,  # GSM Area Code
                "67": random.uniform(3472, 4116),  # Device Battery Voltage (mV)
                "68": random.randint(0, 138),  # Battery Current
                "25": 32767,  # BLE Temp #1 - not found
                "26": 32767,  # BLE Temp #2 - not found
                "27": 32767,  # BLE Temp #3 - not found
                "28": 32767,  # BLE Temp #4 - not found
                "86": 65535,  # BLE Humidity #1 - not found
                "104": 65535, # BLE Humidity #2 - not found
                "106": 65535, # BLE Humidity #3 - not found
                "108": 65535, # BLE Humidity #4 - not found
                "241": 65501, # Active GSM Operator
                "199": random.randint(0, 1000),  # Trip Odometer
                "16": random.randint(2949, 30131),  # Total Odometer
                "636": int(random.uniform(238008613, 238008587)),  # UMTS/LTE Cell ID
                "11": 893980000000,  # ICCID1
                "14": 17048176,  # ICCID2
                "387": f"{lat:.4f}+{lng:.4f}+{random.randint(0, 20) if fridge['type'] != 'boat' else 5:.3f}/",  # ISO6709
                "10804": int(humidity),  # EYE Humidity 1 (%)
                "10808": 1 if door_opens > 0 else 0,  # EYE Magnet 1 (0/1)
                "10812": 1 if speed > 0 or door_opens > 0 else 0,  # EYE Movement 1 (0/1)
                "10816": random.randint(-90, 90),  # EYE Pitch 1 (degrees)
                "10820": 0 if sensor_battery > 3000 else 1,  # EYE Low Battery 1 (0/1)
                "10800": int(temp * 100),  # EYE Temperature 1 (m°C)
                "10824": int(sensor_battery),  # EYE Battery Voltage 1 (mV)
                "10832": random.randint(-180, 180),  # EYE Roll 1 (degrees)
                "10836": door_opens,  # EYE Movement Count 1
                "10840": door_opens,  # EYE Magnet Count 1 (subset of opens)
                "252": random.randint(0, 1)  # Unplug
            }
        }
    }
    if fridge["type"] == "truck" and random.random() < 0.1:
        packet["state"]["reported"]["sp"] = 0
        fridge["stops"] += 1
    if fridge["name"] == "Cargo Container" and random.random() < 0.05:
        fridge["signal"] = not fridge["signal"]
    return packet

# Create clients per device
clients = {}
for fridge in FRIDGES:
    if fridge["token"]:
        client = mqtt.Client(client_id=f"fmc230_{fridge['imei']}")  # Unique client_id per IMEI
        client.user_data_set({"imei": fridge["imei"]})  # Pass IMEI to callbacks
        client.on_connect = on_connect
        client.on_publish = on_publish
        client.username_pw_set(username=fridge["token"])  # Token as username, no password
        client.connect(BROKER, PORT, 60)
        client.loop_start()
        clients[fridge["imei"]] = client

# Main Loop
while True:
    for fridge in FRIDGES:
        if fridge["token"]:  # Only if token exists
            client = clients[fridge["imei"]]
            topic = f"teltonika/{fridge['imei']}/from"
            packet = generate_packet(fridge)
            payload = json.dumps(packet)
            result = client.publish(topic, payload)
            result.wait_for_publish()
            print(f"Published to {topic}: {payload[:100]}...")
    time.sleep(10)