#!/usr/bin/env python3
import json
import os
import subprocess
import time
from http.server import HTTPServer, BaseHTTPRequestHandler


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/api/system":
            self._json(self._system_info())
        elif self.path == "/api/health":
            self._json({"status": "ok", "hostname": os.uname().nodename})
        else:
            self.send_response(404)
            self.end_headers()

    def _system_info(self):
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            uptime = int(time.time() - psutil.boot_time())
            temp = None
            try:
                r = subprocess.run(["cat", "/sys/class/thermal/thermal_zone0/temp"],
                                   capture_output=True, text=True, timeout=5)
                if r.returncode == 0:
                    temp = round(int(r.stdout.strip()) / 1000, 1)
            except Exception:
                pass
            return {
                "cpu_percent": cpu, "cpu_temp": temp,
                "ram_percent": ram.percent, "ram_used": ram.used, "ram_total": ram.total,
                "disk_percent": disk.percent, "disk_used": disk.used, "disk_total": disk.total,
                "uptime_seconds": uptime, "hostname": os.uname().nodename,
            }
        except Exception as e:
            return {"error": str(e)}

    def _json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())


def main():
    port = int(os.environ.get("AGENT_PORT", 5100))
    print(f"Agent listening on 0.0.0.0:{port}")
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
