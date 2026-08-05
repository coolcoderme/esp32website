# external.py -- outdoor weather (NWS) + air quality (Open-Meteo).
# CircuitPython version using adafruit_requests. Results are cached in RAM
# with a TTL and mirrored to storage so the last-known value survives.

import time

import config
from app import storage

WEATHER_TTL = 600   # 10 minutes
AQI_TTL = 600

_cache = {}
_session = None


def _get_session():
    global _session
    if _session is None:
        import ssl
        import socketpool
        import wifi
        import adafruit_requests
        pool = socketpool.SocketPool(wifi.radio)
        _session = adafruit_requests.Session(pool, ssl.create_default_context())
    return _session


def _get_json(url, headers=None):
    r = _get_session().get(url, headers=headers)
    try:
        if r.status_code != 200:
            raise Exception("HTTP %d" % r.status_code)
        return r.json()
    finally:
        r.close()


def _cached(key, ttl, fetch, cache_file):
    now = time.monotonic()
    entry = _cache.get(key)
    if entry and (now - entry[0]) < ttl:
        return entry[1]
    try:
        data = fetch()
        _cache[key] = (now, data)
        try:
            storage.save(cache_file, data)
        except Exception:
            pass
        return data
    except Exception as e:
        if entry:
            return entry[1]
        disk = storage.load(cache_file, None)
        if disk:
            _cache[key] = (now, disk)
            return disk
        return {"error": str(e)}


def _fetch_weather():
    hdr = {"User-Agent": config.NWS_USER_AGENT,
           "Accept": "application/geo+json"}
    pts = _get_json("https://api.weather.gov/points/%s,%s"
                    % (config.LAT, config.LON), hdr)
    props = pts["properties"]
    forecast_url = props["forecast"]

    city = state = ""
    try:
        rel = props["relativeLocation"]["properties"]
        city = rel.get("city", "")
        state = rel.get("state", "")
    except Exception:
        pass

    fc = _get_json(forecast_url, hdr)
    periods = fc["properties"]["periods"][:6]
    slim = []
    for p in periods:
        slim.append({
            "name": p.get("name"),
            "temperature": p.get("temperature"),
            "unit": p.get("temperatureUnit"),
            "short": p.get("shortForecast"),
            "wind": p.get("windSpeed"),
            "windDir": p.get("windDirection"),
            "isDay": p.get("isDaytime"),
        })
    return {
        "location": ("%s, %s" % (city, state)).strip(", "),
        "periods": slim,
    }


def _fetch_aqi():
    url = ("https://air-quality-api.open-meteo.com/v1/air-quality"
           "?latitude=%s&longitude=%s"
           "&current=us_aqi,pm2_5,pm10,ozone,nitrogen_dioxide,"
           "sulphur_dioxide,carbon_monoxide" % (config.LAT, config.LON))
    data = _get_json(url)
    cur = data.get("current", {})
    return {
        "us_aqi": cur.get("us_aqi"),
        "pm2_5": cur.get("pm2_5"),
        "pm10": cur.get("pm10"),
        "ozone": cur.get("ozone"),
        "no2": cur.get("nitrogen_dioxide"),
        "so2": cur.get("sulphur_dioxide"),
        "co": cur.get("carbon_monoxide"),
        "time": cur.get("time"),
    }


def get_weather():
    return _cached("weather", WEATHER_TTL, _fetch_weather, "weather_cache.json")


def get_aqi():
    return _cached("aqi", AQI_TTL, _fetch_aqi, "aqi_cache.json")
