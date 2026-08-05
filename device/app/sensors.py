# sensors.py -- DHT11 temperature + humidity (CircuitPython / adafruit_dht).

import time

import config

_sensor = None
_last = {"t": 0.0, "temp": None, "hum": None, "err": None}


def _init():
    global _sensor
    if _sensor is None:
        if not config.DHT_PIN:
            raise Exception("DHT disabled (DHT_PIN is None)")
        import board
        import adafruit_dht
        pin = getattr(board, config.DHT_PIN)
        # use_pulseio=False is more reliable on ESP32-S3.
        try:
            _sensor = adafruit_dht.DHT11(pin, use_pulseio=False)
        except TypeError:
            _sensor = adafruit_dht.DHT11(pin)
    return _sensor


def read():
    now = time.monotonic()
    # DHT11 can only be polled about once every 2 seconds; cache in between.
    if _last["temp"] is None or (now - _last["t"]) > 2.0:
        try:
            s = _init()
            temp_c = s.temperature
            hum = s.humidity
            if temp_c is not None:
                _last["temp"] = temp_c
            if hum is not None:
                _last["hum"] = hum
            _last["err"] = None
        except Exception as e:
            # adafruit_dht raises RuntimeError often; keep last good reading.
            _last["err"] = str(e)
        _last["t"] = now

    temp_c = _last["temp"]
    temp_f = None
    if temp_c is not None:
        temp_f = round(temp_c * 9 / 5 + 32, 1)

    return {
        "temperature_c": temp_c,
        "temperature_f": temp_f,
        "humidity": _last["hum"],
        "error": _last["err"],
    }
