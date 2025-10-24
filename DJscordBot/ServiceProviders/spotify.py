import spotipy
from spotipy.oauth2 import SpotifyClientCredentials

from ..config import config
from .common import CommonResponseData


PLAYLIST_SIZE_LIMIT = 100
PROVIDER = 'spotify'


if config.spotifyEnabled:
    SPOTIPY_CLIENT_ID = config.conf['spotify-client-id']
    SPOTIPY_CLIENT_SECRET = config.conf['spotify-client-secret']
    manager: SpotifyClientCredentials = SpotifyClientCredentials(SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET)
    sp: spotipy.Spotify = spotipy.Spotify(client_credentials_manager=manager)







#region Spotify Objects

class SpotifyBaseObject:
    def __init__(self, request_data):
        self.id = request_data['id']
        self.name = request_data['name']
        self.type = request_data['type']
        self.uri = request_data['uri']
        self.api_url = request_data['href']
        self.web_url = request_data['external_urls']['spotify']

    def __str__(self):
        return f"SpotifyObject | name:{self.name} | id:{self.id} | type:{self.type}"


class SpotifyTrack(SpotifyBaseObject):
    def __init__(self, track_request_data):
        super().__init__(track_request_data)
        self.album: SpotifyAlbum = None
        if 'album' in track_request_data:
            self.album: SpotifyAlbum = SpotifyAlbum(track_request_data['album'], False)

        self.artists: list[SpotifyArtist] = []
        if 'artists' in track_request_data:
            for artist in track_request_data['artists']:
                self.artists.append(SpotifyArtist(artist))

        self.track_number = track_request_data['track_number']
        self.disc_number = track_request_data['disc_number']
        self.is_explicit = track_request_data['explicit']
        if 'popularity' in track_request_data:
            self.popularity = track_request_data['popularity']
        else:
            self.popularity = None

    def get_title_response(self):
        return f"{self.name} \u2014 {self.artists[0].name}"
    
    def get_yt_search_query(self):
        return f"{self.name} \u2014 {self.artists[0].name}"

    def __str__(self):
        return f"SpotifyTrack | {self.name} by {self.artists[0].name} on {self.album.name} | id:{self.id}"


class SpotifyArtist(SpotifyBaseObject):
    def __init__(self, artist_request_data):
        super().__init__(artist_request_data)

    def __str__(self):
        return f"SpotifyArtist | name : {self.name} | id:{self.id}"



class SpotifyAlbum(SpotifyBaseObject):
    def __init__(self, album_request_data, resolve_track_data = True):
        super().__init__(album_request_data)
        self.album_type: str = album_request_data['album_type']
        self.release_date = album_request_data['release_date']
        self.release_date_precision = album_request_data['release_date_precision']
        self.image: str = album_request_data['images'][0]['url']

        self.total_tracks: int = album_request_data['total_tracks']
        self.tracks: list[SpotifyTrack] = []
        self.has_track_data: bool = resolve_track_data
        if self.has_track_data:
            for ii in range(0, min(len(album_request_data['tracks']['items']), PLAYLIST_SIZE_LIMIT)):
                self.tracks.append(SpotifyTrack(album_request_data['tracks']['items'][ii]))



    def __str__(self):
        return f"SpotifyAlbum | name : {self.name} | id:{self.id} | album_type:{self.album_type}"


class SpotifyPlaylist(SpotifyBaseObject):
    def __init__(self, playlist_request_data):
        super().__init__(playlist_request_data)
        self.description = playlist_request_data['description']
        self.image = playlist_request_data['images'][0]['url']
        self.followers = playlist_request_data['followers']
        self.owner = playlist_request_data['owner']['display_name']
        self.tracks: list[SpotifyTrack] = []
        self.total_tracks = playlist_request_data['tracks']['total']
        for ii in range(0, min(len(playlist_request_data['tracks']['items']), PLAYLIST_SIZE_LIMIT)):
            self.tracks.append(SpotifyTrack(playlist_request_data['tracks']['items'][ii]['track']))

        #self.primary_color = playlist_request_data['primary_color'] #/!\ retourne None

    def __str__(self):
        return f"SpotifyPlaylist | name : {self.name} | id:{self.id} | actual_size:{len(self.tracks)}"
    
#endregion






#region API Calls
class SpotifyAPI():
    @classmethod
    def sanitise_link_and_get_data(cls, spotify_url: str) -> CommonResponseData:
        return cls.get_item(cls.sanitise_link(spotify_url))

        

    @classmethod
    def sanitise_link(cls, spotify_url: str) -> str:
         # Sanitize URL into Spotify API format thing (spotify:type:id)
        api_str = spotify_url
        if spotify_url.startswith("https://open.spotify.com/"):
            splitedQuery = spotify_url[len("https://open.spotify.com/"):].replace('/', ':').split(':')
            if(len(splitedQuery) == 2):
                [_type, _id_dirty] = splitedQuery
            else:
                [_market, _type, _id_dirty] = splitedQuery
            return f"spotify:{_type}:{_id_dirty.split('?')[0]}"
        
        return spotify_url

    @classmethod
    def get_item(cls, spt_id: str) -> CommonResponseData:
        [_spotify, _type, _id] = spt_id.split(':')

        match _type:
            case 'track':
                track_data = sp.track(_id)
                return CommonResponseData(PROVIDER, _id, track_data, 'track')
            case 'artist':
                artist_data = sp.artist(_id)
                return CommonResponseData(PROVIDER, _id, artist_data, 'artist')
            case 'album':
                album_data = sp.album(_id)
                return CommonResponseData(PROVIDER, _id, album_data, 'album')
            case 'playlist':
                playlist_data = sp.playlist(_id)
                return CommonResponseData(PROVIDER, _id, playlist_data, 'playlist')
            case _:
                return None

    @classmethod
    def infer_type_from_request_url(cls, url) -> str:
        sane_url = cls.sanitise_link(url)
        [_spotify, _type, _id] = sane_url.split(':')
        return _type
    

    @classmethod
    def convert_to_track(cls, primitiveData: CommonResponseData) -> SpotifyTrack | None:
        if not cls.__is_correct_provider(primitiveData):
            return None
        if primitiveData.data['type'] != 'track':
            return None
        return SpotifyTrack(primitiveData.data)
    
    @classmethod
    def convert_to_artist(cls, primitiveData: CommonResponseData) -> SpotifyArtist | None:
        if not cls.__is_correct_provider(primitiveData):
            return None
        if primitiveData.data['type'] != 'artist':
            return None
        return SpotifyArtist(primitiveData.data)
    
    @classmethod
    def convert_to_album(cls, primitiveData: CommonResponseData) -> SpotifyAlbum | None:
        if not cls.__is_correct_provider(primitiveData):
            return None
        if primitiveData.data['type'] != 'album':
            return None
        return SpotifyAlbum(primitiveData.data)
    
    @classmethod
    def convert_to_playlist(cls, primitiveData: CommonResponseData) -> SpotifyPlaylist | None:
        if not cls.__is_correct_provider(primitiveData):
            return None
        if primitiveData.data['type'] != 'playlist':
            return None
        return SpotifyPlaylist(primitiveData.data)
    


    @staticmethod
    def __is_correct_provider(primitiveData: CommonResponseData):
        return primitiveData.provider == PROVIDER



#endregion