# routes.py -- all HTTP endpoints for the mega-site (adafruit_httpserver).

import time
import os
import binascii

from adafruit_httpserver import GET, POST, JSONResponse, Request

import config
from app import storage, stats, sensors, external, profanity

MAX_SCORES = 10          # top-N kept per game
MAX_CHAT = 200           # keep the most recent N chat messages
MAX_NOTES = 200

BAD_REQUEST = (400, "Bad Request")
UNAUTHORIZED = (401, "Unauthorized")
SERVER_ERROR = (500, "Internal Server Error")

_id_counter = [0]
_tokens = {}             # token -> expiry epoch


def _new_id():
    _id_counter[0] += 1
    return "%d-%d" % (int(time.time()), _id_counter[0])


def _token():
    return binascii.hexlify(os.urandom(16)).decode()


def _body(request):
    try:
        data = request.json()
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _authed(request):
    tok = request.headers.get("X-Admin-Token") or ""
    exp = _tokens.get(tok)
    if not exp:
        return False
    if time.time() > exp:
        _tokens.pop(tok, None)
        return False
    return True


def register(server):

    # ---- system / sensors -------------------------------------------
    @server.route("/api/stats", GET)
    def api_stats(request: Request):
        return JSONResponse(request, stats.get())

    @server.route("/api/sensor", GET)
    def api_sensor(request: Request):
        return JSONResponse(request, sensors.read())

    @server.route("/api/weather", GET)
    def api_weather(request: Request):
        return JSONResponse(request, external.get_weather())

    @server.route("/api/aqi", GET)
    def api_aqi(request: Request):
        return JSONResponse(request, external.get_aqi())

    @server.route("/api/diag", GET)
    def api_diag(request: Request):
        return JSONResponse(request, storage.where())

    # ---- leaderboards -----------------------------------------------
    @server.route("/api/leaderboard/<game>", GET)
    def lb_get(request: Request, game=""):
        boards = storage.load("leaderboards.json", {})
        return JSONResponse(request, boards.get(game, []))

    @server.route("/api/leaderboard/<game>", POST)
    def lb_post(request: Request, game=""):
        data = _body(request)
        name = str(data.get("name", "AAA"))[:3].upper() or "AAA"
        try:
            score = int(data.get("score", 0))
        except Exception:
            score = 0
        boards = storage.load("leaderboards.json", {})
        board = boards.get(game, [])
        board.append({"name": name, "score": score, "ts": int(time.time())})
        board.sort(key=lambda e: e["score"], reverse=True)
        boards[game] = board[:MAX_SCORES]
        try:
            storage.save("leaderboards.json", boards)
        except Exception as e:
            print("routes: leaderboard save failed:", e)
            return JSONResponse(request, {"ok": False, "error": "save failed"},
                                status=SERVER_ERROR)
        rank = None
        for i, e in enumerate(boards[game]):
            if e["name"] == name and e["score"] == score:
                rank = i + 1
                break
        return JSONResponse(request, {"ok": True, "rank": rank,
                                      "board": boards[game]})

    # ---- public chat -------------------------------------------------
    @server.route("/api/chat", GET)
    def chat_get(request: Request):
        msgs = storage.load("chat.json", [])
        visible = [
            {"name": m["name"], "text": m["text"], "ts": m["ts"]}
            for m in msgs if (not m.get("flagged")) or m.get("approved")
        ]
        return JSONResponse(request, visible[-100:])

    @server.route("/api/chat", POST)
    def chat_post(request: Request):
        data = _body(request)
        name = str(data.get("name", "anon"))[:16] or "anon"
        text = str(data.get("text", "")).strip()[:280]
        if not text:
            return JSONResponse(request, {"ok": False, "error": "empty message"},
                                status=BAD_REQUEST)
        flagged, hits = profanity.check(text)
        msgs = storage.load("chat.json", [])
        msgs.append({
            "id": _new_id(), "name": name, "text": text,
            "ts": int(time.time()), "flagged": flagged,
            "approved": not flagged, "hits": hits,
        })
        try:
            storage.save("chat.json", msgs[-MAX_CHAT:])
        except Exception as e:
            print("routes: chat save failed:", e)
            return JSONResponse(request, {"ok": False, "error": "save failed"},
                                status=SERVER_ERROR)
        return JSONResponse(request, {"ok": True, "held": flagged})

    # ---- private notes to the microcontroller -----------------------
    @server.route("/api/notes", POST)
    def notes_post(request: Request):
        data = _body(request)
        name = str(data.get("name", "anon"))[:16] or "anon"
        text = str(data.get("text", "")).strip()[:1000]
        if not text:
            return JSONResponse(request, {"ok": False, "error": "empty note"},
                                status=BAD_REQUEST)
        flagged, hits = profanity.check(text)
        notes = storage.load("notes.json", [])
        notes.append({
            "id": _new_id(), "name": name, "text": text,
            "ts": int(time.time()), "flagged": flagged, "hits": hits,
        })
        storage.save("notes.json", notes[-MAX_NOTES:])
        return JSONResponse(request, {"ok": True})

    # ---- admin / moderation -----------------------------------------
    @server.route("/api/admin/login", POST)
    def admin_login(request: Request):
        data = _body(request)
        if str(data.get("password", "")) != config.ADMIN_PASSWORD:
            return JSONResponse(request, {"ok": False, "error": "bad password"},
                                status=UNAUTHORIZED)
        tok = _token()
        _tokens[tok] = time.time() + 3600  # 1 hour
        return JSONResponse(request, {"ok": True, "token": tok})

    @server.route("/api/admin/queue", GET)
    def admin_queue(request: Request):
        if not _authed(request):
            return JSONResponse(request, {"ok": False, "error": "unauthorized"},
                                status=UNAUTHORIZED)
        chat = storage.load("chat.json", [])
        notes = storage.load("notes.json", [])
        flagged_chat = [m for m in chat if m.get("flagged")
                        and not m.get("approved")]
        return JSONResponse(request, {"ok": True, "flagged_chat": flagged_chat,
                                      "notes": notes})

    @server.route("/api/admin/approve", POST)
    def admin_approve(request: Request):
        if not _authed(request):
            return JSONResponse(request, {"ok": False, "error": "unauthorized"},
                                status=UNAUTHORIZED)
        data = _body(request)
        mid = data.get("id")
        chat = storage.load("chat.json", [])
        for m in chat:
            if m.get("id") == mid:
                m["approved"] = True
                m["flagged"] = False
                break
        storage.save("chat.json", chat)
        return JSONResponse(request, {"ok": True})

    @server.route("/api/admin/delete", POST)
    def admin_delete(request: Request):
        if not _authed(request):
            return JSONResponse(request, {"ok": False, "error": "unauthorized"},
                                status=UNAUTHORIZED)
        data = _body(request)
        mid = data.get("id")
        kind = data.get("kind", "chat")
        fname = "notes.json" if kind == "note" else "chat.json"
        items = storage.load(fname, [])
        items = [m for m in items if m.get("id") != mid]
        storage.save(fname, items)
        return JSONResponse(request, {"ok": True})

    # ---- visitor country map (IP geolocation counts) ----------------
    @server.route("/api/map", GET)
    def map_get(request: Request):
        countries = storage.load("guestmap.json", {})
        # Ignore legacy pin-list format from the old map.
        if not isinstance(countries, dict):
            countries = {}
        total = 0
        for v in countries.values():
            try:
                total += int(v.get("count", 0))
            except Exception:
                pass
        return JSONResponse(request, {
            "countries": countries,
            "total": total,
            "country_count": len(countries),
        })

    @server.route("/api/map", POST)
    def map_post(request: Request):
        # Browser looks up the visitor's public IP via ip-api.com /
        # ipwho.is, then posts the resulting country here.
        data = _body(request)
        code = str(data.get("code", "")).strip().upper()[:2]
        name = str(data.get("name", "")).strip()[:60]
        if len(code) != 2 or not name:
            return JSONResponse(request,
                                {"ok": False, "error": "need code and name"},
                                status=BAD_REQUEST)
        countries = storage.load("guestmap.json", {})
        if not isinstance(countries, dict):
            countries = {}
        entry = countries.get(code) or {"name": name, "count": 0}
        entry["name"] = name
        entry["count"] = int(entry.get("count", 0)) + 1
        countries[code] = entry
        try:
            storage.save("guestmap.json", countries)
        except Exception as e:
            print("routes: map save failed:", e)
            return JSONResponse(request, {"ok": False, "error": "save failed"},
                                status=SERVER_ERROR)
        total = sum(int(v.get("count", 0)) for v in countries.values())
        return JSONResponse(request, {
            "ok": True,
            "code": code,
            "count": entry["count"],
            "total": total,
            "country_count": len(countries),
            "countries": countries,
        })
