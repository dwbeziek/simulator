
import time
import json
import random
import paho.mqtt.client as mqtt
from threading import Thread

BROKER = "localhost"
PORT = 1883
PUBLISH_INTERVAL = 10  # seconds

# Define ships with dummy but logical routes
SHIPS = [
    {
        "name": "Cape Explorer",
        "imei": "356938035643821",
        "route": [(-33.918861, 18.4233), (-36.8485, 174.7633), (-33.8688, 151.2093)],  # Cape Town → Auckland → Sydney
    },
    {
        "name": "Eastern Trader",
        "imei": "356938035643822",
        "route": [(-33.918861, 18.4233), (-6.2088, 106.8456), (1.3521, 103.8198), (3.139, 101.6869), (31.2304, 121.4737), (25.033, 121.5654), (35.6762, 139.6503)],
    },
    {
        "name": "Coastal Carrier",
        "imei": "356938035643823",
        "route": [(-33.918861, 18.4233), (-29.8587, 31.0218), (-33.9608, 25.6022), (-28.783, 32.0377), (-32.998, 17.9482)],
    },
    {
        "name": "Euro Runner",
        "imei": "356938035643824",
        "route": [(-33.918861, 18.4233), (40.8518, 14.2681), (41.3851, 2.1734), (37.9838, 23.7275), (43.2965, 5.3698), (42.6507, 18.0944)],
    },
    {
        "name": "Nordic Freighter",
        "imei": "356938035643825",
        "route": [(51.5074, -0.1278), (53.3498, -6.2603), (59.9139, 10.7522), (59.3293, 18.0686), (55.6761, 12.5683), (60.1695, 24.9354), (64.1355, -21.8954)],
    },
    {
        "name": "Atlantic Voyager",
        "imei": "356938035643826",
        "route": [(-33.918861, 18.4233), (40.7128, -74.006), (19.4326, -99.1332), (23.1136, -82.3666), (-22.9068, -43.1729), (-34.6037, -58.3816)],
    }
]

def haversine(lat1, lon1, lat2, lon2):
    from math import radians, sin, cos, sqrt, atan2
    R = 6371  # km
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def interpolate(start, end, progress):
    lat = start[0] + (end[0] - start[0]) * progress
    lon = start[1] + (end[1] - start[1]) * progress
    return lat, lon

def ship_thread(ship):
    client = mqtt.Client(client_id=ship["imei"])
    client.username_pw_set(username=f"FMC230_{ship['imei']}")

    def on_connect(c, userdata, flags, rc):
        print(f"{ship['name']} connected to MQTT broker." if rc == 0 else f"{ship['name']} failed to connect.")

    client.on_connect = on_connect

    connected = False
    while not connected:
        try:
            client.connect(BROKER, PORT, 60)
            client.loop_start()
            connected = True
        except Exception as e:
            print(f"{ship['name']} MQTT connection failed. Retrying in 5s...")
            time.sleep(5)

    progress = 0.0
    segment = 0
    direction = 1

    while True:
        route = ship["route"]
        if segment >= len(route) - 1:
            segment = 0
            progress = 0.0

        start = route[segment]
        end = route[segment + 1]
        distance = haversine(*start, *end)
        speed_kmh = random.uniform(20, 35)  # Ship speed
        step = (speed_kmh / 3600) / distance  # per second
        progress += step * PUBLISH_INTERVAL

        if progress >= 1.0:
            segment += 1
            progress = 0.0

        lat, lon = interpolate(start, end, progress)
        temp = random.uniform(-2, 5)
        humidity = random.randint(60, 90)

        ts = int(time.time() * 1000)
        payload = {
            "state": {
                "reported": {
                    "ts": ts,           
                    "pr":  0,
                    "latlng":  f"{lat:.5f},{lon:.5f}",
                    "alt": 5,
                    "ang": random.randint(0, 360),
                    "sp": speed_kmh,
                    "sat": random.randint(3, 15),
                    "evt": 0,
                    "17": random.randint(-369, 460),
                    "18": random.randint(-156, 635),
                    "19": random.randint(-1052, 962),
                    "239": random.randint(0, 1),
                    "240": 1 if speed_kmh > 0 else 0,
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
                    "387": f"{lat:.4f},{lon:.4f}+5.000/",
                    "10804": humidity,
                    "10808": 0,
                    "10812": 0,
                    "10816": random.randint(-90, 90),
                    "10820": 0,
                    "10800": int(temp * 100),
                    "10824": random.randint(2800, 3200),
                    "10832": random.randint(-180, 180),
                    "10836": 0,
                    "10840": 0,
                    "252": random.randint(0, 1)
                }
            }
        }

        topic = f"teltonika/{ship['imei']}/from"
        client.publish(topic, json.dumps(payload))
        print(f"[{ship['name']}] Published to {topic}: {payload}")
        time.sleep(PUBLISH_INTERVAL)

# Start ship threads
for ship in SHIPS:
    t = Thread(target=ship_thread, args=(ship,))
    t.daemon = True
    t.start()

# Keep main thread alive
while True:
    time.sleep(60)