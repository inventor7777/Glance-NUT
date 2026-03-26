import json
import os
import subprocess
from http.server import BaseHTTPRequestHandler, HTTPServer


HOST = os.environ.get("UPSBRIDGE_HOST", "0.0.0.0")
PORT = int(os.environ.get("UPSBRIDGE_PORT", "3494"))
UPS_NAME = os.environ["NUT_UPS_NAME"]


def parse_upsc_output(output):
    values = {}

    for line in output.splitlines():
        if ": " not in line:
            continue
        key, value = line.split(": ", 1)
        values[key.strip()] = value.strip()

    return values


def to_int(values, key):
    raw = values.get(key, "")
    if raw == "":
        return None

    try:
        return int(float(raw))
    except ValueError:
        return None


def to_float(values, key):
    raw = values.get(key, "")
    if raw == "":
        return None

    try:
        return float(raw)
    except ValueError:
        return None


def calculate_power_watts(load_percent, nominal_watts):
    if load_percent is None or nominal_watts is None:
        return None

    return round((load_percent / 100) * nominal_watts)


def read_ups():
    result = subprocess.run(
        ["upsc", UPS_NAME],
        capture_output=True,
        text=True,
        check=True,
    )
    values = parse_upsc_output(result.stdout)
    name = values.get("device.model") or UPS_NAME.split("@", 1)[0]
    load = to_int(values, "ups.load")
    nominal_watts = to_int(values, "ups.realpower.nominal")

    return {
        "name": name,
        "battery": {
            "charge": to_int(values, "battery.charge"),
            "runtime": to_int(values, "battery.runtime"),
            "voltage": to_float(values, "battery.voltage"),
        },
        "ups": {
            "status": values.get("ups.status", ""),
            "load": load,
            "realpower_nominal": nominal_watts,
            "power": calculate_power_watts(load, nominal_watts),
        },
        "input": {
            "voltage": to_float(values, "input.voltage"),
        },
    }


class Handler(BaseHTTPRequestHandler):
    def _send_json(self, payload, status=200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/healthz":
            self._send_json({"status": "ok"})
            return

        if self.path != "/ups":
            self._send_json({"error": "not found"}, status=404)
            return

        try:
            self._send_json(read_ups())
        except subprocess.CalledProcessError as exc:
            message = exc.stderr.strip() or exc.stdout.strip() or "upsc failed"
            self._send_json({"error": message}, status=502)
        except Exception as exc:
            self._send_json({"error": str(exc)}, status=500)

    def log_message(self, format, *args):
        return


if __name__ == "__main__":
    server = HTTPServer((HOST, PORT), Handler)
    server.serve_forever()
