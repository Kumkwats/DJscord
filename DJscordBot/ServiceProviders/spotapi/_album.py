from dataclasses import dataclass
from enum import StrEnum, auto
from typing import Any

from ._core import SptIdentifier, _spt_logger, SptBase, SptCoverArt
from ._track import SptSongBase
from ._artist import SptArtistBase, parse_artists_info


_ALBUM_KEYS = ['__typename', 'uri', 'name', 'label', 'tracksV2', 'type', 'discs', 'artists', 'date', 'coverArt', 'copyright', 'isPreRelease']



class SptAlbumType(StrEnum):
    ALBUM = auto()
    EP = auto()
    SINGLE = auto()
    COMPILATION = auto()


    @classmethod
    def _missing_(cls, value: str):
        value = value.lower()
        for member in cls:
            if member.value == value:
                return member
        return None


    def to_desc(self):
        match self.value:
            case SptAlbumType.EP:
                return "EP"
            case _:
                return self.value.capitalize()



@dataclass
class SptAlbumTrackData(SptSongBase):
    disc_number: int
    track_number: int
    artists: list[SptArtistBase]

@dataclass
class SptAlbumDisc():
    tracks: list[SptAlbumTrackData]

    @property
    def number_of_tracks(self) -> int:
        return len(self.tracks)

@dataclass
class SptAlbum(SptBase):
    type: str
    label: str
    discs: list[SptAlbumDisc]
    artists: list[SptArtistBase]
    visual_art: SptCoverArt
    
    @property
    def tracks(self) -> list[SptAlbumTrackData]:
        """Get all the tracks of the album."""
        ret_tracks: list[SptAlbumTrackData] = []
        for disc in self.discs:
            for track in disc.tracks:
                ret_tracks.append(track)
        return ret_tracks

    @property
    def total_duration(self) -> int:
        """The total duration of the album"""
        return sum(track.duration for track in self.tracks)

    @property
    def number_of_tracks(self) -> int:
        return sum(len(disc.tracks) for disc in self.discs)



#region Parse data
def process_album_data(raw_data: dict[str, Any]) -> SptAlbum | None:
    sanitised_data = _sanitise_album_data(raw_data=raw_data)
    try:
        uri = SptIdentifier.parse_str(sanitised_data['uri'])
    except ValueError as ex:
        _spt_logger.error(f"Failed to parse media identifier: {ex}")
        return None
    
    name = sanitised_data['name']
    label = sanitised_data['label']
    track_mapping = _tracksV2_track_mapping(sanitised_data['tracksV2'])
    discs: list[SptAlbumDisc] = []
    for disc_number in range(1, sanitised_data['discs']['totalCount'] + 1): # spotify numbering starts at 1
        #get all tracks in their respective disc
        disc_tracks: list[SptAlbumTrackData] = []
        for track in sorted(filter(lambda track: track.disc_number == disc_number, track_mapping), key= lambda track: track.track_number):
            disc_tracks.append(track)
        discs.append(SptAlbumDisc(disc_tracks))

    artists: list[SptArtistBase] = parse_artists_info(sanitised_data['artists']['items'])

    visual_art = SptCoverArt(
        cover_art=max(sanitised_data['coverArt']['sources'], key=lambda cover_art_source: cover_art_source['width'])['url'],
        color_hex=sanitised_data['coverArt']['extractedColors']['colorRaw']['hex']
        )
    
    albumtype = SptAlbumType(sanitised_data['type'].lower())

    if albumtype is None:
        _spt_logger.warning(f"Unknown album type : {sanitised_data['type']}")
        albumtype = SptAlbumType('album')

    return SptAlbum(
        identifier=uri,
        name=name,
        type=albumtype.to_desc(),
        label=label,
        discs=discs,
        artists=artists,
        visual_art=visual_art
    )


def _tracksV2_track_mapping(tracksV2_data: dict[str, Any]) -> list[SptAlbumTrackData]:
    return [
        SptAlbumTrackData(
        identifier=SptIdentifier.parse_str(track['track']['uri']),
        name=track['track']['name'],
        disc_number=track['track']['discNumber'],
        track_number=track['track']['trackNumber'],
        duration=track['track']['duration']["totalMilliseconds"],
        playcount=track['track']['playcount'],
        artists=parse_artists_info(track['track']['artists']['items'])
        )
        for track in tracksV2_data['items']]


def _sanitise_album_data(raw_data: dict[str, Any]) -> dict[str, Any]:
    """
    Returns a dict with only the relevant data.
    """
    temp_dict = raw_data
    if 'data' in temp_dict:
        temp_dict = temp_dict['data']

    if not 'albumUnion' in temp_dict:
        raise ValueError("Raw data is not from an album query. Can't find 'albumUnion' entry.")
    temp_dict = temp_dict['albumUnion']

    if temp_dict['__typename'].lower() != 'Album'.lower():
        raise ValueError("__typename is not 'Album'")
    
    #only keeping relevant keys
    sanitised_dict: dict[str, Any] = {}
    for key in _ALBUM_KEYS:
        if key not in temp_dict:
            sanitised_dict[key] = None
            continue
        sanitised_dict[key] = temp_dict[key]
    return sanitised_dict


#endregion
