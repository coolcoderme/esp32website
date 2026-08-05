# stats.py -- live RAM / flash / SD usage (CircuitPython).

import gc
import os

from app import storage


def _fs(path):
    s = os.statvfs(path)
    frsize = s[1]
    blocks = s[2]
    bfree = s[3]
    total = frsize * blocks
    free = frsize * bfree
    used = total - free
    return total, used, free


def _ram():
    gc.collect()
    free = gc.mem_free()
    try:
        used = gc.mem_alloc()
    except AttributeError:
        used = 0
    return free + used, used, free


def get():
    ram_total, ram_used, ram_free = _ram()

    try:
        flash_total, flash_used, flash_free = _fs("/")
    except Exception:
        flash_total = flash_used = flash_free = 0

    mounted = getattr(storage, "_MOUNTED", False)
    if mounted:
        try:
            sd_total, sd_used, sd_free = _fs("/sd")
        except Exception:
            sd_total = sd_used = sd_free = 0
            mounted = False
    else:
        sd_total = sd_used = sd_free = 0

    return {
        "ram": {"total": ram_total, "used": ram_used, "free": ram_free},
        "flash": {"total": flash_total, "used": flash_used, "free": flash_free},
        "sd": {"total": sd_total, "used": sd_used, "free": sd_free,
               "mounted": mounted},
    }
