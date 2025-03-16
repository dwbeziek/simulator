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
HARBOR_SPEED_KNOTS = 5  # Safe harbor speed
MIN_STEP = 0.1  # Minimum progress step to prevent lockup

# Ships with Sizes and Speeds
SHIPS = [
    {"imei": "356938035643815", "name": "OceanPulse Cape-NZ-AUS", "token": "FMC230_356938035643815", "main_port": "Cape Town", "type": "Container",
     "ports": [(-33.9249, 18.4241), (-36.8436, 174.7657), (-33.8572, 151.2100)], "speed_knots": 11, "position": 0, "at_port": False, "port_idx": 0, "docking": False, "docking_time": 0, "first_start": True},
    {"imei": "356938035643816", "name": "OceanPulse Cape-Asia", "token": "FMC230_356938035643816", "main_port": "Cape Town", "type": "Bulk Carrier",
     "ports": [(-33.9249, 18.4241), (-6.1214, 106.7741), (1.2903, 103.8519), (3.1478, 101.6990), (31.2497, 121.5007), (25.0330, 121.5645), (35.5291, 139.7000)], "speed_knots": 13, "position": 0, "at_port": False, "port_idx": 0, "docking": False, "docking_time": 0, "first_start": True},
    {"imei": "356938035643817", "name": "OceanPulse SA-Coast", "token": "FMC230_356938035643817", "main_port": "Cape Town", "type": "Feeder",
     "ports": [(-33.9249, 18.4241), (-33.9600, 25.6022), (-29.8579, 31.0292), (-28.7864, 32.0377), (-32.9890, 17.8850)], "speed_knots": 15, "position": 0, "at_port": False, "port_idx": 0, "docking": False, "docking_time": 0, "first_start": True},
    {"imei": "356938035643818", "name": "OceanPulse Cape-Europe", "token": "FMC230_356938035643818", "main_port": "Cape Town", "type": "Container",
     "ports": [(-33.9249, 18.4241), (41.6331, 12.0839), (39.4699, -0.3750), (37.9420, 23.6469), (49.6328, 0.1307), (43.2965, 16.4392)], "speed_knots": 10, "position": 0, "at_port": False, "port_idx": 0, "docking": False, "docking_time": 0, "first_start": True},
    {"imei": "356938035643819", "name": "OceanPulse North-Europe", "token": "FMC230_356938035643819", "main_port": "London", "type": "Bulk Carrier",
     "ports": [(51.5080, 0.6400), (53.3331, -6.2489), (59.9494, 10.7564), (59.2753, 18.0076), (55.6867, 12.5701), (60.1559, 24.9503), (64.1355, -21.8954)], "speed_knots": 12, "position": 0, "at_port": False, "port_idx": 0, "docking": False, "docking_time": 0, "first_start": True},
    {"imei": "356938035643820", "name": "OceanPulse Cape-Americas", "token": "FMC230_356938035643820", "main_port": "Cape Town", "type": "Tanker",
     "ports": [(-33.9249, 18.4241), (40.6331, -74.0200), (19.1738, -96.1342), (23.1330, -82.3830), (-23.9608, -46.3331), (-34.9011, -56.1645)], "speed_knots": 14, "position": 0, "at_port": False, "port_idx": 0, "docking": False, "docking_time": 0, "first_start": True}
]

# Generate Routes
for ship in SHIPS:
    routes = []
    port_routes = []
    for i in range(len(ship["ports"])):
        start = ship["ports"][i]
        end = ship["ports"][(i + 1) % len(ship["ports"])]
        route = sr.searoute([start[1], start[0]], [end[1], end[0]])
        coords = [(coord[1], coord[0]) for coord in route.geometry["coordinates"]]
        # Thin points dynamically based on speed, cap at 100 points max
        step = max(5, int(15 / (ship["speed_knots"] / 15)))  # Scale with speed
        thinned = [coords[j] for j in range(0, min(len(coords), 100), step)]
        port_routes.append(thinned)
        routes.extend(thinned[:-1])
    routes.append(routes[0])  # Loop back
    ship["route"] = routes
    ship["port_routes"] = port_routes
    ship["position"] = 0
    ship["current_segment"] = 0
    logger.info(f"Generated route for {ship['name']} with {len(routes)} points")

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

def interpolate_position(start_lat, start_lng, end_lat, end_lng, fraction):
    lat = start_lat + (end_lat - start_lat) * fraction
    lng = start_lng + (end_lng - start_lng) * fraction
    return lat, lng

def simulate_ship(ship, client):
    route = ship["route"]
    total_points = len(route) - 1
    while True:
        try:
            pos = int(ship["position"])
            if pos >= total_points:
                ship["position"] = 0
                pos = 0
                ship["current_segment"] = 0
                ship["port_idx"] = 0
                ship["first_start"] = False  # Reset for new cycle

            # Determine current segment and route
            current_route = ship["port_routes"][ship["current_segment"]]
            segment_pos = pos % len(current_route)
            start = current_route[segment_pos]
            end = current_route[segment_pos + 1] if segment_pos + 1 < len(current_route) else current_route[-1]
            distance = haversine(start[0], start[1], end[0], end[1])

            # Check if at port
            target_port = ship["ports"][(ship["port_idx"] + 1) % len(ship["ports"])]
            at_port = abs(start[0] - target_port[0]) < 0.01 and abs(start[1] - target_port[1]) < 0.01
            ship["at_port"] = at_port

            if at_port:
                if ship["first_start"]:
                    ship["first_start"] = False
                    speed = ship["speed_knots"] * KNOTS_TO_KMH
                else:
                    if not ship["docking"]:
                        ship["docking"] = True
                        ship["docking_time"] = random.randint(3600, 10800)  # 1-3 hours
                    speed = HARBOR_SPEED_KNOTS * KNOTS_TO_KMH
                    if ship["docking"]:
                        ship["docking_time"] -= 10
                        if ship["docking_time"] <= 0:
                            ship["docking"] = False
                            ship["port_idx"] = (ship["port_idx"] + 1) % len(ship["ports"])
                            ship["current_segment"] = (ship["current_segment"] + 1) % len(ship["ports"])
                            ship["position"] = (pos // len(current_route)) * len(current_route) + len(current_route)
                            if ship["position"] >= total_points:
                                ship["position"] = 0
                            continue
            else:
                speed = ship["speed_knots"] * KNOTS_TO_KMH
                if random.random() < 0.05:  # Detour
                    detour_pos = min(segment_pos + random.randint(5, 20), len(current_route) - 1)
                    end = current_route[detour_pos]
                    distance = haversine(start[0], start[1], end[0], end[1])

            # Move with minimum step to prevent lockup
            distance_per_step = (speed / 3600) * 10
            fraction = min(max(distance_per_step / distance if distance > 0 else 1, MIN_STEP), 1)
            lat, lng = interpolate_position(start[0], start[1], end[0], end[1], fraction)
            ship["position"] += fraction if fraction < 1 else 1

            # Force progress if stuck
            if abs(ship["position"] - pos) < 0.01 and not at_port:
                ship["position"] += 1

            # Payload
            ts = int(time.time() * 1000)
            door_opens = random.randint(0, 2) if ship["docking"] else 0
            temp = -20 + door_opens * 0.1
            humidity = random.randint(0, 95)
            sensor_battery = random.uniform(2800, 3200)
            packet = {
                "state": {
                    "reported": {
                        "ts": ts,
                        "pr": 1 if door_opens > 0 else 0,
                        "latlng": f"{lat},{lng}",
                        "alt": 5,
                        "ang": random.randint(0, 360),
                        "sp": speed,
                        "sat": random.randint(3, 15),
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
                        "10820": 0 if sensor_battery > 3000 else 1,
                        "10800": int(temp * 100),
                        "10824":int(sensor_battery),
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
            time.sleep(10)

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

while True:
    time.sleep(60)