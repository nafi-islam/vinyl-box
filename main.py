import os, json, time, signal, sys
import board, busio
from adafruit_pn532.i2c import PN532_I2C
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

PLACE_DEBOUNCE_S   = 0.20
REMOVAL_DEBOUNCE_S = 0.50
POLL_TIMEOUT_S     = 0.12
CACHE_PATH         = os.path.expanduser("~/.cache/spotipy_cache")
TAGS_JSON          = os.path.expanduser("~/vinyl-box/tags.json")

load_dotenv(os.path.expanduser("~/vinyl-box/.env"))
#DEVICE_NAME = os.getenv("DEVICE_NAME", "VinylBox")
DEVICE_NAME = os.getenv("DEVICE_NAME", "raspotify (raspberrypi)")

sp = Spotify(auth_manager=SpotifyOAuth(
    client_id=os.environ["SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI","http://127.0.0.1:8888/callback"),
    scope="user-read-playback-state user-modify-playback-state",
    cache_path=CACHE_PATH
))


# def list_devices():
#     devs = sp.devices().get("devices", [])
#     print("Visible Spotify devices:")
#     for d in devs:
#         print(f"- name={d.get('name')!r} id={d.get('id')} type={d.get('type')} active={d.get('is_active')}")

# # call once after auth:
# list_devices()


def get_device_id_by_name(name: str):
    for _ in range(4):
        for d in sp.devices().get("devices", []):
            if d.get("name") == name:
                return d["id"]
        time.sleep(0.7)
    return None

def play_uri_on_pi(uri: str):
    dev_id = get_device_id_by_name(DEVICE_NAME)
    print("Using device ID for DEVICE_NAME:", DEVICE_NAME)
    if not dev_id:
        print("Spotify device not found. Is Raspotify running? Name:", DEVICE_NAME)
        return False
    if uri.startswith(("spotify:album:", "spotify:playlist:")):
        sp.start_playback(device_id=dev_id, context_uri=uri)
    elif uri.startswith("spotify:track:"):
        sp.start_playback(device_id=dev_id, uris=[uri])
    else:
        print("Unsupported URI:", uri); return False
    return True

def pause_on_pi():
    try:
        pb = sp.current_playback()
        if pb and pb.get("is_playing"):
            sp.pause_playback()
    except Exception as e:
        print("Pause error:", e)

def same_context(uri: str) -> bool:
    try:
        pb = sp.current_playback()
        if not pb: return False
        ctx = pb.get("context")
        return bool(ctx and ctx.get("uri") == uri)
    except Exception:
        return False

with open(TAGS_JSON) as f:
    TAG_MAP = json.load(f)

i2c = busio.I2C(board.SCL, board.SDA)
pn532 = PN532_I2C(i2c, debug=False); pn532.SAM_configuration()

current_uid = None; placed_at = None; last_seen = 0.0

def shutdown(*_): print("Shutting down."); sys.exit(0)
signal.signal(signal.SIGINT, shutdown); signal.signal(signal.SIGTERM, shutdown)

print("Ready. Tap a card...")
while True:
    uid = pn532.read_passive_target(timeout=POLL_TIMEOUT_S)
    now = time.time()
    if uid:
        uid_hex = "".join(f"{b:02X}" for b in uid); last_seen = now
        if current_uid != uid_hex:
            current_uid = uid_hex; placed_at = now; print("Detected", uid_hex)
        if placed_at and (now - placed_at) >= PLACE_DEBOUNCE_S:
            uri = TAG_MAP.get(current_uid)
            if not uri: print(f"Unknown UID {current_uid}. Add it to tags.json."); placed_at=None; continue
            if same_context(uri): placed_at=None; continue
            print(f"Playing {uri} for UID {current_uid}")
            ok=False
            for _ in range(3):
                try:
                    ok = play_uri_on_pi(uri)
                    if ok: break
                except Exception as e: print("Playback error:", e)
                time.sleep(0.6)
            placed_at=None
    else:
        if current_uid and (now - last_seen) >= REMOVAL_DEBOUNCE_S:
            print("Card removed → pause"); pause_on_pi(); current_uid=None; placed_at=None
    time.sleep(0.02)
