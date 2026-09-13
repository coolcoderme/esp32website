# ESP32-S3 Mega-Site (CircuitPython)

A full-featured website hosted directly on an **Adafruit Metro ESP32-S3 (N16R8)** running **CircuitPython**. The whole site (games, tools, pages) lives on the board's internal flash (`CIRCUITPY` drive) and is served from there. Visitor-generated data (leaderboards, chat, notes, guest-map pins) is written to a **microSD card in the Metro's onboard SD reader**.

> Ported from the original MicroPython/ESP32-CAM version because that board's SD reader was faulty. The Metro ESP32-S3's onboard SD slot is used instead.

## What it includes

- **Live system dashboard** - real-time RAM, internal flash, and SD-card usage.
- **DHT11 sensor** - live indoor temperature (C/F) and humidity.
- **Outdoor weather** - forecast from the National Weather Service (`api.weather.gov`).
- **Air quality** - US AQI + pollutants from Open-Meteo (free, no API key).
- **10 arcade games** with shared 3-letter-initials leaderboards: Snake, Tetris, Breakout, 2048, Pong, Minesweeper, Memory Match, Tic-Tac-Toe (vs AI), Space Invaders, Color Memory Game.
- **4 offline tools**: Scientific Calculator, GPA Calculator, Pomodoro Study Timer, Unit Converter.
- **Open chat** with automatic profanity flagging.
- **Notes to the microcontroller** - private notes only the owner can read.
- **Admin panel** (`/admin.html`) - password-protected moderation queue.
- **Visitor map** - interactive world map of visitor countries (auto IP geolocation via ip-api.com, then ipwho.is).

## Feature vs. network requirement

| Works offline (LAN only) | Needs the board to have internet | Needs internet on the visitor's device |
|---|---|---|
| All games, all tools, dashboard, DHT11 | Weather (NWS), Air quality (Open-Meteo) | Visitor map (IP geolocation + choropleth) |

## Hardware

- Adafruit Metro ESP32-S3 (N16R8): 16 MB flash, 8 MB PSRAM, **onboard microSD slot** (SPI, chip-select on `board.SD_CS`).
- A microSD card (FAT32).
- A DHT11 temperature/humidity sensor.

### DHT11 wiring

```
DHT11            Metro ESP32-S3
-----            --------------
VCC  ----------- 3V3
DATA ----------- D5      (add a 10k pull-up between DATA and 3V3)
GND  ----------- GND
```

Change the pin by editing `DHT_PIN` in `config.py` (use the `board` pin name as a string, e.g. `"D5"`, `"A1"`). Set it to `None` to disable the sensor.

## Required CircuitPython libraries

Install the **latest stable CircuitPython** for the Metro ESP32-S3 (currently **10.x** — download from [circuitpython.org](https://circuitpython.org/board/adafruit_metro_esp32s3/)), then copy these from the **matching** [Adafruit CircuitPython Bundle](https://circuitpython.org/libraries) into the `CIRCUITPY/lib/` folder (10.x firmware → 10.x bundle):

- `adafruit_httpserver`
- `adafruit_requests`
- `adafruit_sdcard`
- `adafruit_dht`
- `adafruit_ntp`
- `adafruit_connection_manager` (dependency of requests/httpserver)

`wifi`, `socketpool`, `ssl`, `storage`, `board`, `busio`, `digitalio`, `os`, `gc`, `json`, `rtc`, and `time` are built into the ESP32-S3 CircuitPython firmware.

## Repository layout

```
espwebsite/
  device/                 -> copy ALL of this to the CIRCUITPY drive root
    code.py               -> entry point: WiFi, SD mount, NTP, HTTP server
    config.py             -> EDIT: WiFi, coordinates, admin password, DHT pin
    www/                  -> the whole website: HTML/CSS/JS, games, tools
    app/
      __init__.py
      routes.py           -> all HTTP endpoints (adafruit_httpserver)
      storage.py          -> JSON persistence (SD card, RAM fallback)
      stats.py            -> RAM/flash/SD usage
      sensors.py          -> DHT11 reader (adafruit_dht)
      external.py         -> NWS + Open-Meteo (adafruit_requests, cached)
      profanity.py        -> auto-flag word list
    lib/                  -> put the Adafruit libraries here (see above)
```

The SD card needs no files copied to it. On first boot the code creates `/sd/data` and seeds the JSON stores automatically (`storage.init()`). If no card is present or it isn't writable, the site falls back to an in-RAM store so it keeps working (data won't persist across reboots).

## Setup

1. **Install CircuitPython** on the Metro ESP32-S3 (download the latest stable .UF2 from [circuitpython.org](https://circuitpython.org/board/adafruit_metro_esp32s3/) and drag it onto the bootloader drive).
2. **Add the libraries** listed above to `CIRCUITPY/lib/` — use the Adafruit library bundle that matches your CircuitPython major version.
3. **Copy the contents of `device/`** to the root of the `CIRCUITPY` drive (so you have `CIRCUITPY/code.py`, `CIRCUITPY/config.py`, `CIRCUITPY/www/`, `CIRCUITPY/app/`).
4. **Edit `config.py`**: `WIFI_SSID`, `WIFI_PASSWORD`, `LAT`/`LON` (US only for NWS), `NWS_USER_AGENT` (real contact email), `ADMIN_PASSWORD`, and `DHT_PIN`.
5. **Insert a FAT32 microSD card** into the Metro's onboard slot.
6. **Reset** the board and open the serial console (Mu, `screen`, or Thonny). You should see:

```
code: WiFi connected. Open http://192.168.1.42 in your browser.
storage: SD card mounted at /sd
storage: using SD card at /sd/data
code: starting HTTP server on port 80
```

Open that IP on any device on the same network.

## API reference

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/stats` | RAM / flash / SD usage |
| GET | `/api/sensor` | DHT11 temperature + humidity |
| GET | `/api/weather` | NWS forecast (cached 10 min) |
| GET | `/api/aqi` | Open-Meteo air quality (cached 10 min) |
| GET | `/api/diag` | Storage location + SD status (debugging) |
| GET/POST | `/api/leaderboard/<game>` | Get / submit scores (top 10) |
| GET/POST | `/api/chat` | Public chat (auto-flags profanity) |
| POST | `/api/notes` | Private note to the owner |
| POST | `/api/admin/login` | Get an admin token |
| GET | `/api/admin/queue` | Flagged chat + all notes (token) |
| POST | `/api/admin/approve` | Approve a held chat message (token) |
| POST | `/api/admin/delete` | Delete a chat message / note (token) |
| GET/POST | `/api/map` | Country visitor counts / record a visit |

Static files (the site itself) are served automatically from the `www/` root.

## Notes and design choices

- **Web framework.** Uses `adafruit_httpserver` (`server.serve_forever()`), which serves the static site from `root_path="/www"` and dispatches the `/api/...` routes. This replaces the custom async server from the MicroPython version.
- **Air quality source.** NWS provides weather but not air quality, so AQI comes from Open-Meteo's free, no-key API. Coordinates come from `config.py`.
- **Visitor map.** The browser looks up the visitor's **public** IP with **ip-api.com first**, then **ipwho.is** if that fails or is rate-limited, and posts the country to the board. Counts are stored per country on the SD card. The dark interactive choropleth (hover for visitor counts) uses jsVectorMap from a CDN, so the visitor's device needs internet for the map UI + geo lookup. Each browser session is counted once.
- **Moderation** is manual: the profanity list only *flags* messages; you approve or delete them in the admin panel.

## Troubleshooting

- **`ImportError: no module named 'adafruit_httpserver'`** (or similar) - a library is missing from `CIRCUITPY/lib/`. Re-copy it from the bundle that matches your CircuitPython version.
- **SD not mounted / dashboard shows "using flash fallback"** - check the card is FAT32 and seated. Visit `/api/diag` to see `sd_mounted` and the active data dir.
- **Weather says error** - confirm `LAT`/`LON` are in the US and `NWS_USER_AGENT` has a real contact; the last good value is cached and reused if the API hiccups.
- **DHT11 reads null** - DHT11 is finicky; the reader keeps the last good value and retries. Confirm the pull-up resistor and the `DHT_PIN` name.
