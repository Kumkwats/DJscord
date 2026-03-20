from dataclasses import dataclass
from typing import Any


from ..common import MediaBaseIdentifier, MediaEntry

from ._core import SptAlbumType, SptIdentifier, _spt_logger, SptBase, SptAlbumBase, SptCoverArt
from ._artist import SptArtistBase, parse_artists_info


_SONG_KEYS = ['__typename', 'mediaType', 'uri', 'name', 'duration', 'playcount', 'albumOfTrack', 'firstArtist', 'otherArtists']


@dataclass
class SptSongBase(SptBase):
    duration: int # milliseconds
    playcount: int

@dataclass
class SptSongFull(SptSongBase):
    album: SptAlbumBase       # we just need its name, its type
    album_art: SptCoverArt    # and its cover
    
    first_artists: list[SptArtistBase]
    other_artists: list[SptArtistBase]



#region Parse data
def process_track_data(raw_data: dict[str, Any]) -> SptSongFull | None:
    sanitised_data = _sanitise_track_data(raw_data=raw_data)
    try:
        uri = SptIdentifier.parse_str(sanitised_data['uri'])
    except ValueError as ex:
        _spt_logger.error(f"Failed to parse media identifier: {ex}")
        return None
    name = sanitised_data['name']
    album = SptAlbumBase(
        identifier=SptIdentifier.parse_str(sanitised_data['albumOfTrack']['uri']),
        name=sanitised_data['albumOfTrack']['name'],
        a_type=SptAlbumType(sanitised_data['albumOfTrack']['type'].lower()))

    duration: int = sanitised_data['duration']['totalMilliseconds']
    playcount:int = int(sanitised_data['playcount'])

    first_artist: list[SptArtistBase] = parse_artists_info(sanitised_data['firstArtist']['items'])
    other_artists: list[SptArtistBase] = parse_artists_info(sanitised_data['otherArtists']['items'])
    visual_art = SptCoverArt(
        cover_art=max(sanitised_data['albumOfTrack']['coverArt']['sources'], key=lambda cover_art_source: cover_art_source['width'])['url'],
        color_hex=sanitised_data['albumOfTrack']['coverArt']['extractedColors']['colorRaw']['hex']
        )

    return SptSongFull(
        identifier=uri,
        name=name,
        duration=duration,
        playcount=playcount,
        album=album,
        first_artists=first_artist,
        other_artists=other_artists,
        album_art=visual_art
    )


def _sanitise_track_data(raw_data: dict[str, Any]) -> dict[str, Any]:
    """
    Returns a dict with only the relevant data.
    """
    temp_dict = raw_data
    if 'data' in temp_dict:
        temp_dict = temp_dict['data']

    if not 'trackUnion' in temp_dict:
        raise ValueError("Raw data is not from an album query. Can't find 'albumUnion' entry.")
    temp_dict = temp_dict['trackUnion']

    if temp_dict['__typename'].lower() != 'track'.lower():
        raise ValueError("__typename is not 'Track'")
    
    #only keeping relevant keys
    sanitised_dict: dict[str, Any] = {}
    for key in _SONG_KEYS:
        if key not in temp_dict:
            sanitised_dict[key] = None
            continue
        sanitised_dict[key] = temp_dict[key]
    return sanitised_dict


#endregion
