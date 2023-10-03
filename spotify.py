import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from config import config


if config.spotifyEnabled:
    SPOTIPY_CLIENT_ID = config.conf['spotify-client-id']
    SPOTIPY_CLIENT_SECRET = config.conf['spotify-client-secret']
    manager = SpotifyClientCredentials(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET)
    sp = spotipy.Spotify(client_credentials_manager=manager)


class Spotify():
    def getTrack(url: str) -> str:
        trackID: str = url.split("?")[0]
        return sp.track(trackID)


if __name__ == "__main__":
    track = Spotify.getTrack('https://open.spotify.com/track/3ERL0lPZqTNGCN6UGOjBsV?si=a111cb5f068546ef')
    print(track['name'], track['artists'][0]['name'])
