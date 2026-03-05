from DJscordBot.ServiceProviders.common import Identifier

from .core import SptBase



class SptSongAlbumInfo(SptBase):
    cover: str
    color_hex: int
    track_number: int

class SptSongArtistInfo(SptBase):
    avatar: str


class SptSong(SptBase):
    duration: int # milliseconds
    playcount: int

    album: SptSongAlbumInfo
    
    first_artist: SptSongArtistInfo
    other_artists: list[SptSongArtistInfo]
