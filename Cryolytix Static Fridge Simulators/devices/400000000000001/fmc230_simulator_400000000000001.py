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
client_cert_path = "certs/400000000000001_chain.pem"
client_key_path = "certs/400000000000001.key"

# Fridge Definitions
FRIDGES = [
    {"imei": "400000000000001", "lat": -33.841723, "lng": 18.6822246, "name": "Engen Winelands 1 Stop North"}
]

# Enhanced Freezer Simulator Class
class IceCreamFreezerSimulator:
    def __init__(self):
        # Temperature parameters (ice cream freezers: -18°C to -23°C)
        self.target_temp = -20.0  # °C - ideal for ice cream storage
        self.current_temp = -20.0
        self.min_temp = -23.0    # °C - compressor turns off
        self.max_temp = -17.0    # °C - compressor turns on
        self.compressor_on = False

        # Humidity parameters (typical freezer humidity: 40-60% RH)
        self.current_humidity = 50.0  # % RH
        self.min_humidity = 40.0
        self.max_humidity = 60.0
        self.humidity_variation = 2.0

        # Compressor temperature parameters
        self.compressor_temp = 25.0  # °C - ambient when off
        self.compressor_min_temp = 20.0  # °C when running normally
        self.compressor_max_temp = 65.0  # °C under load
        self.compressor_heat_rate = 8.0  # °C per 30s when running
        self.compressor_cool_rate = 3.0  # °C per 30s when off

        # Power consumption parameters (typical commercial freezer)
        self.power_consumption = 0.0  # Watts
        self.idle_power = 50.0       # Watts - control systems, lights
        self.running_power = 350.0   # Watts - compressor running
        self.peak_power = 450.0      # Watts - startup surge

        # Temperature change rates
        self.cooling_rate = 0.15     # °C per 30s when compressor running
        self.warming_rate = 0.08     # °C per 30s when compressor off
        self.temp_variation = 0.1    # Small random variations

        # State tracking
        self.compressor_start_time = 0
        self.is_startup_surge = False

    def simulate_humidity(self):
        """Simulate humidity changes based on temperature and door openings"""
        # Humidity increases when temperature rises (condensation)
        if not self.compressor_on:
            humidity_change = random.uniform(0.5, 1.5)
        else:
            humidity_change = random.uniform(-1.0, 0.5)

        # Random door opening simulation (5% chance every cycle)
        if random.random() < 0.05:
            # Door opening causes humidity spike
            humidity_change += random.uniform(5.0, 15.0)
            print(f"{time.strftime('%H:%M:%S')} - Door opened! Humidity spike")

        self.current_humidity += humidity_change

        # Keep humidity within realistic bounds
        self.current_humidity = max(self.min_humidity,
                                    min(self.max_humidity, self.current_humidity))

        return self.current_humidity

    def simulate_compressor_temperature(self):
        """Simulate compressor temperature changes"""
        if self.compressor_on:
            # Compressor running - temperature increases
            if self.is_startup_surge:
                # Rapid heating during startup
                temp_increase = self.compressor_heat_rate * 2
                # End startup surge after 2 minutes
                if time.time() - self.compressor_start_time > 120:
                    self.is_startup_surge = False
            else:
                temp_increase = self.compressor_heat_rate

            self.compressor_temp += temp_increase

            # Compressor can't exceed max safe temperature
            if self.compressor_temp > self.compressor_max_temp:
                self.compressor_temp = self.compressor_max_temp

        else:
            # Compressor off - gradual cooling to ambient
            self.compressor_temp -= self.compressor_cool_rate
            if self.compressor_temp < self.compressor_min_temp:
                self.compressor_temp = self.compressor_min_temp

        return self.compressor_temp

    def simulate_power_consumption(self):
        """Simulate realistic power consumption"""
        if not self.compressor_on:
            self.power_consumption = self.idle_power
        else:
            if self.is_startup_surge:
                # Startup surge lasts for first 2 minutes
                self.power_consumption = self.peak_power
            else:
                # Normal running power with small variations
                self.power_consumption = self.running_power + random.uniform(-20, 20)

        return self.power_consumption

    def simulate_temperature_cycle(self):
        """Simulate one 30-second temperature cycle"""
        # Add small random variation
        random_variation = random.uniform(-self.temp_variation, self.temp_variation)

        if self.compressor_on:
            # Compressor is cooling - temperature decreases
            self.current_temp -= self.cooling_rate + random_variation

            # Check if we've reached minimum temperature
            if self.current_temp <= self.min_temp:
                self.current_temp = self.min_temp
                self.compressor_on = False
                print(f"{time.strftime('%H:%M:%S')} - Compressor OFF (reached min: {self.current_temp:.1f}°C)")

        else:
            # Compressor is off - temperature increases
            self.current_temp += self.warming_rate + random_variation

            # Check if we've reached maximum temperature
            if self.current_temp >= self.max_temp:
                self.current_temp = self.max_temp
                self.compressor_on = True
                self.compressor_start_time = time.time()
                self.is_startup_surge = True
                print(f"{time.strftime('%H:%M:%S')} - Compressor ON (reached max: {self.current_temp:.1f}°C)")

        return self.current_temp

    def generate_sensor_readings(self):
        """Generate complete sensor readings package"""
        # Update all sensor values
        temperature = self.simulate_temperature_cycle()
        humidity = self.simulate_humidity()
        compressor_temp = self.simulate_compressor_temperature()
        power_usage = self.simulate_power_consumption()

        return {
            "chamber_temperature": round(temperature, 1),
            "chamber_humidity": round(humidity, 1),
            "compressor_temperature": round(compressor_temp, 1),
            "power_consumption": round(power_usage, 1),
            "compressor_status": "ON" if self.compressor_on else "OFF",
            "compressor_runtime": round((time.time() - self.compressor_start_time) / 60, 1) if self.compressor_on else 0
        }

# Initialize freezer simulators for each fridge
freezer_simulators = {}
for fridge in FRIDGES:
    freezer_simulators[fridge["imei"]] = IceCreamFreezerSimulator()

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

    # Get enhanced sensor readings from the simulator
    simulator = freezer_simulators[fridge["imei"]]
    sensor_data = simulator.generate_sensor_readings()

    # Convert temperatures to m°C (milli-degrees Celsius) for EYE protocol
    chamber_temp_mc = int(sensor_data["chamber_temperature"] * 100)
    compressor_temp_mc = int(sensor_data["compressor_temperature"] * 100)

    # Convert power to appropriate scale (assuming 0.1W resolution)
    power_consumption_scale = int(sensor_data["power_consumption"] * 10)

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
                "113": random.randint(75, 100),  # Battery Level
                "182": random.randint(0, 500),  # GNSS HDOP
                "66": random.uniform(4534, 12470),  # External Voltage
                "67": random.uniform(3472, 4116),  # Device Battery Voltage (mV)

                # Enhanced sensor readings
                "10804": int(sensor_data["chamber_humidity"]),  # EYE Humidity 1 (%)
                "10800": chamber_temp_mc,  # EYE Inside Temperature 1 (m°C)
                "10824": random.uniform(2800, 3200),  # EYE Battery Voltage 1 (mV)
                "10801": compressor_temp_mc,  # EYE Compressor Temperature 1 (m°C)

                # # New power consumption field (you can define the appropriate code)
                # "10810": power_consumption_scale,  # Power Consumption (0.1W resolution)
                #
                # # Additional status fields
                # "10811": 1 if sensor_data["compressor_status"] == "ON" else 0,  # Compressor Status
                # "10812": int(sensor_data["compressor_runtime"] * 10),  # Compressor Runtime (0.1 min resolution)
                #
                # # System efficiency indicator
                # "10813": random.randint(1, 4)  # Efficiency Rating (1=POOR, 2=FAIR, 3=GOOD, 4=EXCELLENT)
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
    print("Starting enhanced freezer simulator with realistic temperature cycles...")
    print("Monitoring: Chamber Temp, Humidity, Compressor Temp, Power Usage")
    print("-" * 80)

    while True:
        for fridge in FRIDGES:
            client = clients[fridge["imei"]]
            topic = "v1/devices/me/telemetry"
            packet = generate_packet(fridge)
            payload = json.dumps(packet)
            result = client.publish(topic, payload)
            result.wait_for_publish()

            # Enhanced status display
            simulator = freezer_simulators[fridge["imei"]]
            sensor_data = simulator.generate_sensor_readings()

            status = (
                f"{time.strftime('%H:%M:%S')} | "
                f"Chamber: {sensor_data['chamber_temperature']:5.1f}°C | "
                f"Humidity: {sensor_data['chamber_humidity']:5.1f}% | "
                f"Compressor: {sensor_data['compressor_temperature']:5.1f}°C | "
                f"Power: {sensor_data['power_consumption']:5.1f}W | "
                f"Status: {sensor_data['compressor_status']}"
            )
            print(status)

        time.sleep(30)

except KeyboardInterrupt:
    print("Simulator stopped by user")
    for client in clients.values():
        client.loop_stop()
        client.disconnect()