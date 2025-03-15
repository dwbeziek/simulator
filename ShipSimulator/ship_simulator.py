import time
import json
import random
import paho.mqtt.client as mqtt
from math import sin, cos, radians, sqrt, atan2
import logging
import threading
import searoute as sr

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# MQTT Setup
BROKER = "localhost"
PORT = 1883
TOPIC = "teltonika/{}/from"
KNOTS_TO_KMH = 1.852
EARTH_RADIUS = 6371  # km

# OceanPulse Logistics Ships
SHIPS = [
    {
        "imei": "356938035643815",
        "name": "OceanPulse Cape-NZ-AUS",
        "token": "FMC230_356938035643815",
        "main_port": "Cape Town",
        "ports": [
            (-33.9249, 18.4241),  # Cape Town, ZA
            (-36.8485, 174.7633), # Auckland, NZ
            (-33.8688, 151.2093)  # Sydney, AU
        ],
        "speed_knots": 15,
        "progress": 0,
        "route_idx": 0,
        "docking": False,
        "docking_time": 0
    },
    {
        "imei": "356938035643816",
        "name": "OceanPulse Cape-Asia",
        "token": "FMC230_356938035643816",
        "main_port": "Cape Town",
        "ports": [
            (-33.9249, 18.4241),  # Cape Town, ZA
            (-6.2088, 106.8456),  # Jakarta, ID
            (1.3521, 103.8198),   # Singapore, SG
            (3.1390, 101.6869),   # Kuala Lumpur, MY
            (31.2304, 121.4737),  # Shanghai, CN
            (25.0329, 121.5654),  # Taipei, TW
            (35.6762, 139.6503)   # Tokyo, JP
        ],
        "speed_knots": 14,
        "progress": 0,
        "route_idx": 0,
        "docking": False,
        "docking_time": 0
    },
    {
        "imei": "356938035643817",
        "name": "OceanPulse SA-Coast",
        "token": "FMC230_356938035643817",
        "main_port": "Cape Town",
        "ports": [
            (-33.9249, 18.4241),  # Cape Town
            (-33.9180, 25.6062),  # Gqeberha
            (-29.8587, 31.0218),  # Durban
            (-28.7700, 32.0567),  # Richards Bay
            (-32.9890, 17.8850)   # Saldanha
        ],
        "speed_knots": 12,
        "progress": 0,
        "route_idx": 0,
        "docking": False,
        "docking_time": 0
    },
    {
        "imei": "356938035643818",
        "name": "OceanPulse Cape-Europe",
        "token": "FMC230_356938035643818",
        "main_port": "Cape Town",
        "ports": [
            (-33.9249, 18.4241),  # Cape Town, ZA
            (41.9028, 12.4964),   # Rome, IT (port: Civitavecchia)
            (40.4168, -3.7038),   # Madrid, ES (port: Valencia)
            (37.9838, 23.7275),   # Athens, GR (port: Piraeus)
            (48.8566, 2.3522),    # Paris, FR (port: Le Havre)
            (43.2141, 15.5460)    # Split, HR
        ],
        "speed_knots": 16,
        "progress": 0,
        "route_idx": 0,
        "docking": False,
        "docking_time": 0
    },
    {
        "imei": "356938035643819",
        "name": "OceanPulse North-Europe",
        "token": "FMC230_356938035643819",
        "main_port": "London",
        "ports": [
            (51.5074, -0.1278),   # London, UK (port: Tilbury)
            (53.3498, -6.2603),   # Dublin, IE
            (59.9139, 10.7522),   # Oslo, NO
            (59.3293, 18.0686),   # Stockholm, SE
            (55.6761, 12.5683),   # Copenhagen, DK
            (60.1699, 24.9384),   # Helsinki, FI
            (64.1466, -21.9426)   # Reykjavik, IS
        ],
        "speed_knots": 15,
        "progress": 0,
        "route_idx": 0,
        "docking": False,
        "docking_time": 0
    },
    {
        "imei": "356938035643820",
        "name": "OceanPulse Cape-Americas",
        "token": "FMC230_356938035643820",
        "main_port": "Cape Town",
        "ports": [
            (-33.9249, 18.4241),  # Cape Town, ZA
            (40.7128, -74.0060),  # New York, US
            (19.4326, -99.1332),  # Mexico City, MX (port: Veracruz)
            (23.1136, -82.3666),  # Havana, CU
            (-23.5505, -46.6333), # São Paulo, BR (port: Santos)
            (-34.6037, -58.3816)  # Buenos Aires, AR
        ],
        "speed_knots": 14,
        "progress": 0,
        "route_idx": 0,
        "docking": False,
        "docking_time": 0
    }
]

# Generate Realistic Routes
for ship in SHIPS:
    routes = []
    for i in range(len(ship["ports"])):
        start = ship["ports"][i]
        end = ship["ports"][(i + 1) % len(ship["ports"])]
        route = sr.searoute([start[1], start[0]], [end[1], end[0]])
        coords = [(coord[1], coord[0]) for coord in route.geometry["coordinates"]]  # Flip lat,lng
        routes.extend(coords)
    ship["route"] = routes

# MQTT Callbacks
def on_connect(client, userdata, flags, rc, properties=None):
    if rc == 0:
        logger.info(f"Connected {userdata['imei']} to MQTT Broker")
        client.subscribe(TOPIC.format(userdata["imei"]))
    else:
        logger.error(f"Connection failed for {userdata['imei']}: {rc}")

def on_disconnect(client, userdata, rc):
    logger.warning(f"Disconnected {userdata['imei']}. Reconnecting...")
    while True:
        try:
            client.reconnect()
            break
        except Exception as e:
            logger.error(f"Reconnect failed for {userdata['imei']}: {e}")
            time.sleep(5)

def on_publish(client, userdata, mid):
    logger.debug(f"Message {mid} published for {userdata['imei']}")

# Helper Functions
def haversine(lat1, lon1, lat2, lon2):
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    return EARTH_RADIUS * c

def interpolate_position(start_lat, start_lng, end_lat, end_lng, progress):
    lat = start_lat + (end_lat - start_lat) * progress
    lng = start_lng + (end_lng - start_lng) * progress
    return lat, lng

def simulate_ship(ship, client):
    while True:
        try:
            route = ship["route"]
            idx = int(ship["progress"] * (len(route) - 1)) % (len(route) - 1)
            start = route[idx]
            end = route[idx + 1]
            distance = haversine(start[0], start[1], end[0], end[1])

            # Docking Logic
            near_port = any(haversine(start[0], start[1], p[0], p[1]) < 5 for p in ship["ports"])
            if near_port and not ship["docking"] and random.random() < 0.2:  # 20% chance to dock
                ship["docking"] = True
                ship["docking_time"] = random.randint(360, 720)  # 1-2 hours in seconds
            if ship["docking"]:
                ship["docking_time"] -= 10
                if ship["docking_time"] <= 0:
                    ship["docking"] = False
                speed = 0
            else:
                speed = ship["speed_knots"] * KNOTS_TO_KMH
                if near_port:  # Slow near ports
                    speed *= 0.3
                if random.random() < 0.05:  # 5% chance of detour
                    detour_idx = min(idx + random.randint(5, 20), len(route) - 2)
                    end = route[detour_idx]
                    distance = haversine(start[0], start[1], end[0], end[1])
                step = (speed / 3600) / distance if distance > 0 else 0
                ship["progress"] += step * 10 / len(route)  # Normalize progress

            lat, lng = interpolate_position(start[0], start[1], end[0], end[1], ship["progress"] % 1)

            # Payload (matches original)
            ts = int(time.time() * 1000)
            door_opens = random.randint(0, 2) if ship["docking"] else 0
            temp = -20 + door_opens * 0.1
            humidity = random.randint(0, 95)
            packet = {
                "state": {
                    "reported": {
                        "ts": ts,
                        "pr": 1 if door_opens > 0 else 0,
                        "latlng": f"{lat},{lng}",
                        "alt": 5,
                        "ang": random.randint(0, 360),
                        "sat": random.randint(3, 15),
                        "sp": speed,
                        "evt": 0,
                        "imei": ship["imei"],
                        "17": random.randint(-369, 460),
                        "18": random.randint(-156, 635),
                        "19": random.randint(-1052, 962),
                        "239": random.randint(0, 1),
                        "240": 1 if speed > 0 else 0,
                        "80": random.randint(0, 4),
                        "21": random.randint(0, 5),
                        "200": random.randint(0, 2),
                        "69": random.randint(0, 3),
                        "113": random.randint(0, 100),
                        "181": random.randint(0, 500),
                        "182": random.randint(0, 500),
                        "66": random.uniform(4534, 12470),
                        "206": 21014,
                        "67": random.uniform(3472, 4116),
                        "68": random.randint(0, 138),
                        "25": 32767,
                        "26": 32767,
                        "27": 32767,
                        "28": 32767,
                        "86": 65535,
                        "104": 65535,
                        "106": 65535,
                        "108": 65535,
                        "241": 65501,
                        "199": random.randint(0, 1000),
                        "16": random.randint(2949, 30131),
                        "636": int(random.uniform(238008613, 238008587)),
                        "11": 893980000000,
                        "14": 17048176,
                        "387": f"{lat:.4f}+{lng:.4f}+5.000/",
                        "10804": int(humidity),
                        "10808": 1 if door_opens > 0 else 0,
                        "10812": 1 if speed > 0 or door_opens > 0 else 0,
                        "10816": random.randint(-90, 90),
                        "10820": 0,
                        "10800": int(temp * 100),
                        "10824": random.randint(2800, 3200),
                        "10832": random.randint(-180, 180),
                        "10836": door_opens,
                        "10840": door_opens,
                        "252": random.randint(0, 1)
                    }
                }
            }
            client.publish(TOPIC.format(ship["imei"]), json.dumps(packet))
            time.sleep(10)
        except Exception as e:
            logger.error(f"Error in {ship['imei']}: {e}")
            time.sleep(10)  # Keep thread alive

# Setup Clients
clients = {}
for ship in SHIPS:
    client = mqtt.Client(client_id=f"fmc230_{ship['imei']}")
    client.user_data_set({"imei": ship["imei"]})
    client.on_connect = on_connect
    client.on_disconnect = on_disconnect
    client.on_publish = on_publish
    client.username_pw_set(username=ship["token"])
    while True:
        try:
            client.connect(BROKER, PORT, 60)
            client.loop_start()
            break
        except Exception as e:
            logger.error(f"Initial connect failed for {ship['imei']}: {e}")
            time.sleep(5)
    clients[ship["imei"]] = client
    threading.Thread(target=simulate_ship, args=(ship, client), daemon=True).start()

# Keep Main Thread Alive
while True:
    time.sleep(60)