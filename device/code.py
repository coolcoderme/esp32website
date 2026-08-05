# code.py -- CircuitPython entry point for the ESP32-S3 mega-site.
# Runs automatically on boot. Connects WiFi, mounts the SD card, syncs the
# clock, then serves the website with adafruit_httpserver.

import time
import gc

import wifi
import socketpool

import config
from app import storage, routes

gc.collect()


def connect_wifi():
    print("code: connecting to WiFi '%s' ..." % config.WIFI_SSID)
    for attempt in range(3):
        try:
            wifi.radio.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
            ip = str(wifi.radio.ipv4_address)
            print("code: WiFi connected. Open http://%s in your browser." % ip)
            return ip
        except Exception as e:
            print("code: WiFi attempt %d failed: %s" % (attempt + 1, e))
            time.sleep(2)
    print("code: WiFi FAILED -- check SSID/password in config.py")
    return None


def sync_time(pool):
    try:
        import adafruit_ntp
        import rtc
        ntp = adafruit_ntp.NTP(pool, tz_offset=0)
        rtc.RTC().datetime = ntp.datetime
        print("code: clock synced via NTP")
    except Exception as e:
        print("code: NTP sync failed (non-fatal):", e)


gc.collect()

# Mount SD first (before WiFi), same as Adafruit demos -- keeps SPI free of
# radio init side effects and matches the example that works on your board.
storage.init()

ip = connect_wifi()
pool = socketpool.SocketPool(wifi.radio)

sync_time(pool)
gc.collect()

from adafruit_httpserver import Server, FileResponse, Request

server = Server(pool, "/www", debug=False)
server.headers = {"Access-Control-Allow-Origin": "*"}


@server.route("/")
def index(request: Request):
    return FileResponse(request, "index.html", "/www")


routes.register(server)

print("code: starting HTTP server on port %d" % config.HTTP_PORT)
server.serve_forever(ip or "0.0.0.0", config.HTTP_PORT)
