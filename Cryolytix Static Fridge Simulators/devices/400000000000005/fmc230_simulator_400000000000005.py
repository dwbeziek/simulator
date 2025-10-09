import time
import json
import random
import ssl
import argparse
import sys
import paho.mqtt.client as mqtt
from enum import Enum

# MQTT Setup
BROKER = "demo.cryolytix.com"
PORT = 8883

# Certificate paths
ca_cert_path = "../rootCA.pem"

# Failure Scenarios Enum
class FailureScenario(Enum):
    NORMAL = "normal"
    COMPRESSOR_OVERHEATING = "compressor_overheating"
    REFRIGERANT_LEAK = "refrigerant_leak"
    DOOR_SEAL_FAILURE = "door_seal_failure"
    EVAPORATOR_FAN_FAILURE = "evaporator_fan_failure"
    THERMOSTAT_DRIFT = "thermostat_drift"
    POWER_SUPPLY_ISSUES = "power_supply_issues"
    COMPRESSOR_MOTOR_FAILURE = "compressor_motor_failure"
    CONDENSER_BLOCKED = "condenser_blocked"
    DEFROST_SYSTEM_FAILURE = "defrost_system_failure"

# Popular South African Locations with different scenarios
LOCATION_PROFILES = {
    # Western Cape
    "cape_town_victoria_wharf": {
        "imei": "400000000000001",
        "lat": -33.9046, "lng": 18.4181,
        "name": "Victoria & Alfred Waterfront - Normal",
        "scenario": FailureScenario.NORMAL,
        "city": "Cape Town",
        "province": "Western Cape"
    },
    "stellenbosch_spar": {
        "imei": "400000000000002",
        "lat": -33.9348, "lng": 18.8606,
        "name": "Stellenbosch Spar - Overheating Compressor",
        "scenario": FailureScenario.COMPRESSOR_OVERHEATING,
        "city": "Stellenbosch",
        "province": "Western Cape"
    },

    # Gauteng
    "sandton_city": {
        "imei": "400000000000003",
        "lat": -26.1076, "lng": 28.0539,
        "name": "Sandton City Mall - Refrigerant Leak",
        "scenario": FailureScenario.REFRIGERANT_LEAK,
        "city": "Johannesburg",
        "province": "Gauteng"
    },
    "pretoria_menlyn": {
        "imei": "400000000000004",
        "lat": -25.7832, "lng": 28.2754,
        "name": "Menlyn Maine - Door Seal Failure",
        "scenario": FailureScenario.DOOR_SEAL_FAILURE,
        "city": "Pretoria",
        "province": "Gauteng"
    },

    # KwaZulu-Natal
    "durban_gateway": {
        "imei": "400000000000005",
        "lat": -29.8587, "lng": 31.0218,
        "name": "Durban Gateway - Fan Failure",
        "scenario": FailureScenario.EVAPORATOR_FAN_FAILURE,
        "city": "Durban",
        "province": "KwaZulu-Natal"
    },
    "umhlanga_ridge": {
        "imei": "400000000000006",
        "lat": -29.7361, "lng": 31.0887,
        "name": "Umhlanga Ridge - Power Issues",
        "scenario": FailureScenario.POWER_SUPPLY_ISSUES,
        "city": "Umhlanga",
        "province": "KwaZulu-Natal"
    },

    # Eastern Cape
    "pe_boards": {
        "imei": "400000000000007",
        "lat": -33.9608, "lng": 25.6021,
        "name": "PE Boardwalk - Compressor Motor",
        "scenario": FailureScenario.COMPRESSOR_MOTOR_FAILURE,
        "city": "Gqeberha",
        "province": "Eastern Cape"
    },

    # Free State
    "bloemfontein_loch": {
        "imei": "400000000000008",
        "lat": -29.0852, "lng": 26.1596,
        "name": "Bloemfontein Loch Logan - Condenser Blocked",
        "scenario": FailureScenario.CONDENSER_BLOCKED,
        "city": "Bloemfontein",
        "province": "Free State"
    },

    # Mpumalanga
    "nelspruit_ridge": {
        "imei": "400000000000009",
        "lat": -25.4747, "lng": 30.9644,
        "name": "Nelspruit Crossings - Defrost Failure",
        "scenario": FailureScenario.DEFROST_SYSTEM_FAILURE,
        "city": "Nelspruit",
        "province": "Mpumalanga"
    },

    # Limpopo
    "polokwane_mall": {
        "imei": "400000000000010",
        "lat": -23.8964, "lng": 29.4486,
        "name": "Polokwane Mall - Thermostat Drift",
        "scenario": FailureScenario.THERMOSTAT_DRIFT,
        "city": "Polokwane",
        "province": "Limpopo"
    }
}

class IceCreamFreezerSimulator:
    def __init__(self, scenario=FailureScenario.NORMAL):
        self.scenario = scenario
        self.normal_operation = NormalOperation()
        self.failure_mode = self._create_failure_mode(scenario)
        self.cycles_since_start = 0

    def _create_failure_mode(self, scenario):
        failure_modes = {
            FailureScenario.NORMAL: NormalOperation(),
            FailureScenario.COMPRESSOR_OVERHEATING: CompressorOverheatingFailure(),
            FailureScenario.REFRIGERANT_LEAK: RefrigerantLeakFailure(),
            FailureScenario.DOOR_SEAL_FAILURE: DoorSealFailure(),
            FailureScenario.EVAPORATOR_FAN_FAILURE: EvaporatorFanFailure(),
            FailureScenario.THERMOSTAT_DRIFT: ThermostatDriftFailure(),
            FailureScenario.POWER_SUPPLY_ISSUES: PowerSupplyFailure(),
            FailureScenario.COMPRESSOR_MOTOR_FAILURE: CompressorMotorFailure(),
            FailureScenario.CONDENSER_BLOCKED: CondenserBlockedFailure(),
            FailureScenario.DEFROST_SYSTEM_FAILURE: DefrostSystemFailure()
        }
        return failure_modes.get(scenario, NormalOperation())

    def generate_sensor_readings(self):
        self.cycles_since_start += 1
        base_readings = self.normal_operation.generate_readings()
        failure_readings = self.failure_mode.apply_failure(base_readings, self.cycles_since_start)
        return failure_readings

class NormalOperation:
    def __init__(self):
        self.current_temp = -20.0
        self.compressor_on = False
        self.compressor_temp = 25.0
        self.humidity = 50.0

    def generate_readings(self):
        # Normal temperature cycling
        if self.compressor_on:
            self.current_temp -= 0.15 + random.uniform(-0.05, 0.05)
            if self.current_temp <= -23.0:
                self.current_temp = -23.0
                self.compressor_on = False
            self.compressor_temp += 5.0 + random.uniform(-1, 1)
        else:
            self.current_temp += 0.08 + random.uniform(-0.03, 0.03)
            if self.current_temp >= -17.0:
                self.current_temp = -17.0
                self.compressor_on = True
            self.compressor_temp -= 2.0 + random.uniform(-0.5, 0.5)

        # Normal humidity variations
        self.humidity += random.uniform(-2, 2)
        self.humidity = max(40, min(60, self.humidity))

        # Door openings (5% chance)
        if random.random() < 0.05:
            self.humidity += random.uniform(5, 15)
            self.current_temp += random.uniform(1, 3)

        # Power calculation
        if self.compressor_on:
            power = 350 + random.uniform(-20, 20)
        else:
            power = 50 + random.uniform(-5, 5)

        return {
            "chamber_temperature": round(self.current_temp, 1),
            "chamber_humidity": round(self.humidity, 1),
            "compressor_temperature": round(self.compressor_temp, 1),
            "power_consumption": round(power, 1),
            "compressor_status": "ON" if self.compressor_on else "OFF",
            "efficiency": random.choice(["EXCELLENT", "GOOD", "GOOD", "FAIR"])
        }

# Failure Mode Classes (same as before, adding two new ones)
class CompressorOverheatingFailure:
    def apply_failure(self, readings, cycle):
        overheating_factor = min(1.0, cycle / 100)
        readings["compressor_temperature"] += 30 * overheating_factor + random.uniform(0, 5)
        if readings["compressor_status"] == "ON":
            readings["chamber_temperature"] += 0.5 * overheating_factor
        if readings["compressor_temperature"] > 70:
            readings["efficiency"] = "POOR"
        elif readings["compressor_temperature"] > 60:
            readings["efficiency"] = "FAIR"
        return readings

class RefrigerantLeakFailure:
    def apply_failure(self, readings, cycle):
        leak_progress = min(1.0, cycle / 200)
        temperature_increase = 8 * leak_progress
        readings["chamber_temperature"] += temperature_increase
        if readings["compressor_status"] == "ON":
            readings["power_consumption"] += 50 * leak_progress
        if temperature_increase > 5:
            readings["efficiency"] = "POOR"
        elif temperature_increase > 2:
            readings["efficiency"] = "FAIR"
        return readings

class DoorSealFailure:
    def apply_failure(self, readings, cycle):
        readings["chamber_humidity"] = 65 + random.uniform(-5, 5)
        if random.random() < 0.3:
            readings["chamber_temperature"] += random.uniform(2, 6)
            readings["chamber_humidity"] += random.uniform(5, 15)
        if random.random() < 0.4:
            readings["compressor_status"] = "ON" if readings["compressor_status"] == "OFF" else "OFF"
        readings["efficiency"] = "FAIR"
        return readings

class EvaporatorFanFailure:
    def apply_failure(self, readings, cycle):
        temp_variation = random.uniform(2, 6)
        readings["chamber_temperature"] += temp_variation
        readings["chamber_humidity"] = 70 + random.uniform(-5, 10)
        if readings["compressor_status"] == "ON":
            readings["power_consumption"] += 30
            readings["compressor_temperature"] += 10
        readings["efficiency"] = "POOR"
        return readings

class ThermostatDriftFailure:
    def apply_failure(self, readings, cycle):
        # Gradual temperature sensor drift
        drift = (cycle / 300) * 10  # Drift up to 10°C over 300 cycles
        readings["chamber_temperature"] += drift
        # Compressor cycles incorrectly due to wrong readings
        if random.random() < 0.2:
            readings["compressor_status"] = "ON" if random.random() > 0.5 else "OFF"
        if drift > 5:
            readings["efficiency"] = "POOR"
        elif drift > 2:
            readings["efficiency"] = "FAIR"
        return readings

class PowerSupplyFailure:
    def apply_failure(self, readings, cycle):
        if cycle % 20 < 5:
            if readings["compressor_status"] == "ON":
                readings["power_consumption"] = 200 + random.uniform(-50, 50)
                readings["chamber_temperature"] += random.uniform(1, 3)
            else:
                readings["power_consumption"] = 30
        if random.random() < 0.1:
            readings["compressor_status"] = "OFF"
            readings["power_consumption"] = 30
            readings["chamber_temperature"] += random.uniform(2, 4)
        readings["efficiency"] = "FAIR"
        return readings

class CompressorMotorFailure:
    def apply_failure(self, readings, cycle):
        motor_degradation = min(1.0, cycle / 150)
        if readings["compressor_status"] == "ON":
            readings["chamber_temperature"] += 6 * motor_degradation
            readings["power_consumption"] = 280 + random.uniform(-50, 50)
            readings["compressor_temperature"] -= 15 * motor_degradation
        if random.random() < 0.3 * motor_degradation:
            readings["compressor_status"] = "ON" if readings["compressor_status"] == "OFF" else "OFF"
        if motor_degradation > 0.5:
            readings["efficiency"] = "POOR"
        else:
            readings["efficiency"] = "FAIR"
        return readings

class CondenserBlockedFailure:
    def apply_failure(self, readings, cycle):
        # Reduced heat dissipation
        blockage = min(1.0, cycle / 120)
        readings["compressor_temperature"] += 25 * blockage
        if readings["compressor_status"] == "ON":
            readings["chamber_temperature"] += 3 * blockage
            readings["power_consumption"] += 40 * blockage
        if blockage > 0.6:
            readings["efficiency"] = "POOR"
        elif blockage > 0.3:
            readings["efficiency"] = "FAIR"
        return readings

class DefrostSystemFailure:
    def apply_failure(self, readings, cycle):
        # Frost buildup reduces efficiency
        frost_buildup = min(1.0, cycle / 180)
        readings["chamber_temperature"] += 4 * frost_buildup
        readings["chamber_humidity"] += 20 * frost_buildup
        if readings["compressor_status"] == "ON":
            readings["power_consumption"] += 60 * frost_buildup
        if frost_buildup > 0.5:
            readings["efficiency"] = "POOR"
        elif frost_buildup > 0.2:
            readings["efficiency"] = "FAIR"
        return readings

def generate_packet(fridge_config, sensor_data):
    lat, lng = fridge_config["lat"], fridge_config["lng"]
    ts = int(time.time() * 1000)

    chamber_temp_mc = int(sensor_data["chamber_temperature"] * 100)
    compressor_temp_mc = int(sensor_data["compressor_temperature"] * 100)
    power_consumption_scale = int(sensor_data["power_consumption"] * 10)

    efficiency_map = {"EXCELLENT": 4, "GOOD": 3, "FAIR": 2, "POOR": 1}

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
                "21": random.randint(2, 5),
                "113": random.randint(80, 100),
                "182": random.randint(0, 100),
                "66": random.uniform(12000, 12470),
                "67": random.uniform(3800, 4116),
                "10804": int(sensor_data["chamber_humidity"]),
                "10800": chamber_temp_mc,
                "10824": random.uniform(3000, 3200),
                "10801": compressor_temp_mc,
                "10810": power_consumption_scale,
                "10811": 1 if sensor_data["compressor_status"] == "ON" else 0,
                "10813": efficiency_map.get(sensor_data["efficiency"], 2),
                "10814": int(sensor_data["chamber_temperature"] * 10),
                "10815": int(sensor_data["compressor_temperature"] * 10),
            }
        }
    }
    return packet

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print(f"✅ Connected to {userdata['name']}")
        print(f"   📍 Location: {userdata['city']}, {userdata['province']}")
        print(f"   🔧 Scenario: {userdata['scenario'].value}")
        print(f"   📡 IMEI: {userdata['imei']}")
    else:
        print(f"❌ Connection failed: {rc}")

def on_publish(client, userdata, mid):
    pass

def run_simulator(fridge_config):
    print(f"\n🚀 Starting Individual Simulator")
    print("=" * 60)

    # Create simulator
    simulator = IceCreamFreezerSimulator(fridge_config["scenario"])

    # Create MQTT client
    client = mqtt.Client(client_id=fridge_config['imei'])
    client.user_data_set(fridge_config)
    client.on_connect = on_connect
    client.on_publish = on_publish

    # Configure TLS/SSL
    client_cert_path = f"certs/{fridge_config['imei']}_chain.pem"
    client_key_path = f"certs/{fridge_config['imei']}.key"

    try:
        client.tls_set(
            ca_certs=ca_cert_path,
            certfile=client_cert_path,
            keyfile=client_key_path,
            tls_version=ssl.PROTOCOL_TLSv1_2
        )
        client.connect(BROKER, PORT, 60)
        client.loop_start()
    except Exception as e:
        print(f"❌ SSL/TLS Error: {e}")
        print(f"   Make sure certificates exist in ./certs/ directory:")
        print(f"   - {client_cert_path}")
        print(f"   - {client_key_path}")
        return

    # Main loop
    try:
        cycle_count = 0
        while True:
            cycle_count += 1
            sensor_data = simulator.generate_sensor_readings()
            packet = generate_packet(fridge_config, sensor_data)
            payload = json.dumps(packet)

            topic = "v1/devices/me/telemetry"
            result = client.publish(topic, payload)
            result.wait_for_publish()

            status_emoji = "✅" if sensor_data["efficiency"] in ["EXCELLENT", "GOOD"] else "⚠️" if sensor_data["efficiency"] == "FAIR" else "🚨"

            status = (
                f"{status_emoji} Cycle {cycle_count} | "
                f"Temp: {sensor_data['chamber_temperature']:5.1f}°C | "
                f"Hum: {sensor_data['chamber_humidity']:3.0f}% | "
                f"Comp: {sensor_data['compressor_temperature']:4.0f}°C | "
                f"Power: {sensor_data['power_consumption']:4.0f}W | "
                f"Status: {sensor_data['compressor_status']:>3} | "
                f"Eff: {sensor_data['efficiency']:>8}"
            )
            print(status)

            time.sleep(30)

    except KeyboardInterrupt:
        print(f"\n🛑 Stopping {fridge_config['name']}")
        client.loop_stop()
        client.disconnect()

def list_profiles():
    print("\n📋 Available Location Profiles:")
    print("=" * 60)
    for key, profile in LOCATION_PROFILES.items():
        print(f"  {key:25} | {profile['name']:45} | {profile['scenario'].value}")
    print(f"\nUsage: python simulator.py --profile PROFILE_NAME")
    print("Example: python simulator.py --profile cape_town_victoria_wharf")

def main():
    parser = argparse.ArgumentParser(description='Ice Cream Freezer Simulator')
    parser.add_argument('--profile', type=str, help='Location profile name')
    parser.add_argument('--list', action='store_true', help='List all available profiles')

    args = parser.parse_args()

    if args.list:
        list_profiles()
        return

    if args.profile:
        if args.profile in LOCATION_PROFILES:
            fridge_config = LOCATION_PROFILES[args.profile]
            run_simulator(fridge_config)
        else:
            print(f"❌ Profile '{args.profile}' not found.")
            print("   Use --list to see available profiles.")
    else:
        # Interactive mode
        print("🎛️  Ice Cream Freezer Simulator - Interactive Mode")
        print("=" * 50)
        list_profiles()

        try:
            profile_name = input("\nEnter profile name: ").strip()
            if profile_name in LOCATION_PROFILES:
                fridge_config = LOCATION_PROFILES[profile_name]
                run_simulator(fridge_config)
            else:
                print(f"❌ Profile '{profile_name}' not found.")
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")

if __name__ == "__main__":
    main()