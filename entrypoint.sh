#!/usr/bin/env bash
set -euo pipefail

# entrypoint.sh - translate environment variables into CLI args for chargepoint_mqtt.py

if [ -z "${STATIONS-}" ]; then
  echo "Environment variable STATIONS is required (space or comma separated list of station deviceIds)"
  exit 2
fi

# Normalize STATIONS: convert commas to spaces
STATIONS_CLEAN=${STATIONS//,/ }

ARGS=("/usr/local/bin/python" "/app/chargepoint_mqtt.py")


ARGS+=("--stations")
for s in $STATIONS_CLEAN; do
  ARGS+=("$s")
done

# Optional MQTT host/port/user/pass/prefix
if [ -n "${MQTT_HOST-}" ]; then
  ARGS+=("--mqtt-host" "$MQTT_HOST")
fi
if [ -n "${MQTT_PORT-}" ]; then
  ARGS+=("--mqtt-port" "$MQTT_PORT")
fi
if [ -n "${MQTT_USER-}" ]; then
  ARGS+=("--mqtt-user" "$MQTT_USER")
fi
if [ -n "${MQTT_PASS-}" ]; then
  ARGS+=("--mqtt-pass" "$MQTT_PASS")
fi
if [ -n "${MQTT_PREFIX-}" ]; then
  ARGS+=("--mqtt-prefix" "$MQTT_PREFIX")
fi

# Interval
if [ -n "${INTERVAL-}" ]; then
  ARGS+=("--interval" "$INTERVAL")
fi

# Run once flag: set ONCE to true/1 to run once
if [ "${ONCE-}" = "1" ] || [ "${ONCE-}" = "true" ] || [ "${ONCE-}" = "True" ]; then
  ARGS+=("--once")
fi

echo "Starting chargepoint_mqtt with args: ${ARGS[*]}"
exec "${ARGS[@]}"
