# storage.py -- JSON persistence for CircuitPython.
#
# Primary location is the SD card (/sd/data) using the Metro ESP32-S3's
# onboard SD reader -- same pattern as Adafruit's SD Card demo.
# If the card is missing or not writable, we fall back to an in-RAM store
# so the site keeps working (data is lost on reboot).

import os
import json

SD_DIR = "/sd/data"
DATA_DIR = SD_DIR
USING_FALLBACK = False
_MOUNTED = False

# MUST stay alive for the life of the program. CircuitPython will break the
# SD mount if these get garbage-collected (that was why our mount "failed"
# while the Adafruit example worked -- locals went out of scope).
_sd_cs = None
_sd_card = None
_sd_vfs = None

# In-RAM fallback store: name -> python object.
_ram = {}

DEFAULTS = {
    "leaderboards.json": {},
    "chat.json": [],
    "notes.json": [],
    "guestmap.json": {},
}


def _path(name):
    return DATA_DIR + "/" + name


def _exists(path):
    try:
        os.stat(path)
        return True
    except Exception:
        return False


def _mkdir(path):
    try:
        os.mkdir(path)
        return True
    except Exception as e:
        # Already exists is fine.
        if _exists(path):
            return True
        print("storage: mkdir %s failed: %s" % (path, e))
        return False


def mount_sd():
    """Mount the onboard SD card at /sd. Same wiring as the Adafruit demo."""
    global _MOUNTED, _sd_cs, _sd_card, _sd_vfs

    # If we already mounted successfully this boot, don't remount.
    if _MOUNTED and _sd_card is not None:
        return True

    try:
        import board
        import digitalio
        import storage
        import adafruit_sdcard

        # Exact same sequence as the working Adafruit example.
        _sd_cs = digitalio.DigitalInOut(board.SD_CS)
        _sd_card = adafruit_sdcard.SDCard(board.SPI(), _sd_cs)
        _sd_vfs = storage.VfsFat(_sd_card)
        storage.mount(_sd_vfs, "/sd")

        _MOUNTED = True
        print("storage: SD card mounted at /sd")
        try:
            print("storage: /sd contains:", os.listdir("/sd"))
        except Exception as e:
            print("storage: listdir /sd failed:", e)
        return True
    except Exception as e:
        print("storage: SD mount failed:", e)
        _MOUNTED = False
        _sd_cs = None
        _sd_card = None
        _sd_vfs = None
        return False


def _writable(directory):
    """Return True if we can create + write + delete a file in `directory`.
    Filename must NOT start with a dot (FAT often rejects that)."""
    if not _mkdir(directory):
        return False
    test = directory + "/wtest.tmp"
    try:
        with open(test, "w") as f:
            f.write("ok")
        with open(test) as f:
            data = f.read()
        try:
            os.remove(test)
        except Exception:
            pass
        return data == "ok"
    except Exception as e:
        print("storage: write test failed in %s: %s" % (directory, e))
        return False


def init():
    """Mount the SD card, pick a writable data dir (SD preferred, RAM
    fallback), and seed any missing data files. Never overwrites files."""
    global DATA_DIR, USING_FALLBACK

    mount_sd()

    if _MOUNTED and _writable(SD_DIR):
        DATA_DIR = SD_DIR
        USING_FALLBACK = False
        print("storage: using SD card at %s" % SD_DIR)
    else:
        USING_FALLBACK = True
        print("storage: SD unavailable -- using in-RAM store (data will NOT persist)")

    for name, default in DEFAULTS.items():
        if USING_FALLBACK:
            if name not in _ram:
                _ram[name] = default
        else:
            _create_if_missing(name, default)


def _create_if_missing(name, default):
    path = _path(name)
    if _exists(path):
        return
    try:
        with open(path, "w") as f:
            json.dump(default, f)
        print("storage: created %s" % path)
    except Exception as e:
        print("storage: could not create %s: %s" % (name, e))


def load(name, default):
    if USING_FALLBACK:
        return _ram.get(name, default)
    try:
        with open(_path(name)) as f:
            return json.load(f)
    except Exception:
        return default


def save(name, data):
    if USING_FALLBACK:
        _ram[name] = data
        return
    tmp = _path(name) + ".tmp"
    with open(tmp, "w") as f:
        json.dump(data, f)
    try:
        os.remove(_path(name))
    except Exception:
        pass
    try:
        os.rename(tmp, _path(name))
    except Exception:
        with open(_path(name), "w") as f:
            json.dump(data, f)
        try:
            os.remove(tmp)
        except Exception:
            pass


def where():
    """Diagnostics: report the active storage location and its status."""
    info = {
        "data_dir": DATA_DIR if not USING_FALLBACK else "RAM",
        "using_ram_fallback": USING_FALLBACK,
        "sd_mounted": _MOUNTED,
        "files": {},
    }
    for name in DEFAULTS:
        if USING_FALLBACK:
            info["files"][name] = "ram" if name in _ram else None
        else:
            try:
                info["files"][name] = os.stat(_path(name))[6]
            except Exception:
                info["files"][name] = None
    return info
