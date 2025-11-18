import logging
import json
import requests
import paho.mqtt.client as mqtt
import argparse

def format_mqtt_autodiscovery(device_data, mqtt_prefix="homeassistant"):
	device_id = str(device_data["deviceId"])
	model = device_data.get("modelNumber", "Unknown")
	sw_version = device_data.get("deviceSoftwareVersion", "Unknown")
	name = " ".join(device_data.get("name", []))
	# Abbreviated device info for Home Assistant
	device = {
		"ids": f"chargepoint_{device_id}",
		"name": name,
		"mf": "ChargePoint",
		"mdl": model,
		"sw": sw_version,
		"sn": device_id,
		"configuration_url": f"https://driver.chargepoint.com/stations/{device_id}"
	}
	# Abbreviated origin info
	origin = {
		"name": "chargepoint_mqtt_http",
		"sw": "1.0",
		"url": f"https://driver.chargepoint.com/stations/{device_id}"
	}
	sensors = []
	# Compose binary sensors under 'cmps' for device discovery
	cmps = {}
	for port in device_data.get("portsInfo", {}).get("ports", []):
		outlet = port["outletNumber"]
		unique_id = f"chargepoint_{device_id}_port{outlet}"
		object_id = unique_id
		state_topic = f"chargepoint/{device_id}/port/{outlet}/state"
		avail_topic = f"chargepoint/{device_id}/port/{outlet}/availability"
		cmps[object_id] = {
			"p": "binary_sensor",
			"name": f"Port {outlet}",
			"device_class": "plug",
			"icon": "mdi:ev-station",
			"stat_t": state_topic,
			"avty_t": avail_topic,
			"uniq_id": unique_id,
			"object_id": object_id
		}
	# Device config topic and payload (for device registry)
	device_config_topic = f"{mqtt_prefix}/device/chargepoint_{device_id}/config"
	device_payload = {
		"dev": device,
		"o": origin,
		"cmps": cmps
	}
	sensors = [{"topic": device_config_topic, "payload": json.dumps(device_payload)}]
	return sensors

def publish_states(client, device_data, mqtt_prefix="homeassistant"):
	device_id = str(device_data["deviceId"])
	for port in device_data.get("portsInfo", {}).get("ports", []):
		outlet = port["outletNumber"]
		state_topic = f"chargepoint/{device_id}/port/{outlet}/state"
		avail_topic = f"chargepoint/{device_id}/port/{outlet}/availability"
		status = port.get("statusV2", port.get("status", "unknown")).lower()
		# Determine state and availability
		if status == "in_use":
			state = "ON"
			availability = "online"
		elif status == "available":
			state = "OFF"
			availability = "online"
		elif status in ["unreachable", "unavailable", "maintenance_required"]:
			state = "OFF"
			availability = "offline"
		else:
			state = "OFF"
			availability = "offline"
		# Publish state
		client.publish(state_topic, state, retain=True)
		# Publish availability
		client.publish(avail_topic, availability, retain=True)


# CLI argument parsing
def parse_args():
	parser = argparse.ArgumentParser(description="ChargePoint MQTT Home Assistant Bridge")
	parser.add_argument('--stations', nargs='+', required=True, help='List of ChargePoint station deviceIds')
	parser.add_argument('--mqtt-host', required=True, help='MQTT broker host')
	parser.add_argument('--mqtt-port', type=int, default=1883, help='MQTT broker port (default: 1883)')
	parser.add_argument('--mqtt-user', default=None, help='MQTT username')
	parser.add_argument('--mqtt-pass', default=None, help='MQTT password')
	parser.add_argument('--mqtt-prefix', default='homeassistant', help='MQTT discovery prefix (default: homeassistant)')
	parser.add_argument('--once', action='store_true', help='Run only once and exit')
	parser.add_argument('--interval', type=int, default=60, help='Polling interval in seconds (default: 60)')
	return parser.parse_args()

USER_AGENT = (
	"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
	"AppleWebKit/537.36 (KHTML, like Gecko) "
	"Chrome/119.0.0.0 Safari/537.36"
)

def fetch_chargepoint_data(device_id):
	url = f"https://mc.chargepoint.com/map-prod/v3/station/info?deviceId={device_id}"
	headers = {"User-Agent": USER_AGENT}
	response = requests.get(url, headers=headers)
	response.raise_for_status()
	return response.json()

if __name__ == "__main__":
	import time
	logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
	args = parse_args()
	client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
	if args.mqtt_user and args.mqtt_pass:
		client.username_pw_set(args.mqtt_user, args.mqtt_pass)
	client.connect(args.mqtt_host, args.mqtt_port, 60)
	client.loop_start()

	def run_once():
		for station_id in args.stations:
			try:
				data = fetch_chargepoint_data(station_id)
				sensors = format_mqtt_autodiscovery(data, args.mqtt_prefix)
				# Log station info and port availability
				station_name = " ".join(data.get("name", []))
				logging.info(f"Station {station_id}: {station_name}")
				for port in data.get("portsInfo", {}).get("ports", []):
					outlet = port["outletNumber"]
					status = port.get("statusV2", port.get("status", "unknown")).lower()
					if status == "in_use":
						availability = "online (in use)"
					elif status == "available":
						availability = "online (available)"
					elif status in ["unreachable", "unavailable", "maintenance_required"]:
						availability = f"offline ({status})"
					else:
						availability = f"offline ({status})"
					logging.info(f"  Port {outlet}: {availability}")
				# Publish binary sensor configs
				for sensor in sensors:
					client.publish(sensor["topic"], sensor["payload"], retain=True)
				publish_states(client, data, args.mqtt_prefix)
			except Exception as e:
				logging.error(f"Error processing station {station_id}: {e}")

	if args.once:
		run_once()
	else:
		try:
			while True:
				run_once()
				time.sleep(args.interval)
		except KeyboardInterrupt:
			logging.info("Exiting...")
	client.loop_stop()
	client.disconnect()
