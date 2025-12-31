import os
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv(os.path.expanduser("~/vinyl-box/.env"))

scope = "user-read-playback-state user-modify-playback-state"

Spotify(auth_manager=SpotifyOAuth(
    client_id=os.environ["SPOTIFY_CLIENT_ID"],
    client_secret=os.environ["SPOTIFY_CLIENT_SECRET"],
    redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI","http://127.0.0.1:8888/callback"),
    scope=scope,
    cache_path=os.path.expanduser("~/.cache/spotipy_cache"),
))

print("Auth complete! Token cached at ~/.cache/spotipy_cache")
