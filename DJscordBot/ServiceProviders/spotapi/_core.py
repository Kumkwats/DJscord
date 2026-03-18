from dataclasses import dataclass
from enum import StrEnum
from typing import Self

from ...logging.utils import get_logger
_spt_logger = get_logger("djscordbot.media_provider.spotify.spotapi")


from ..common import MediaBaseIdentifier

_PROVIDER_ID: str = "spotify"
_DEFAULT_URL: str = "https://open.spotify.com/"


#region Identifier
class SptType(StrEnum):
    TRACK = "track"
    ALBUM = "album"
    PLAYLIST = "playlist"
    ARTIST = "artist"

    @classmethod
    def _missing_(cls, value: str):
        value = value.lower()
        for member in cls:
            if member.value == value:
                return member
        return None


@dataclass
class SptCoverArt:
    cover_art: str
    color_hex: int


@dataclass(frozen=True)
class SptIdentifier:
    type: SptType
    id: str

    def to_base_identifier(self) -> MediaBaseIdentifier:
        return MediaBaseIdentifier(_PROVIDER_ID, [self.type, self.id])

    def to_web_url(self) -> str:
        return f"{_DEFAULT_URL}{self.type}/{self.id}"

    def __repr__(self):
        return f"{_PROVIDER_ID}:{self.type}:{self.id}" # MediaIdentifier compatible format

    @staticmethod
    def _convert(identifier: MediaBaseIdentifier) -> Self:
        if identifier.provider != _PROVIDER_ID:
            raise ValueError(f"Invalid provider for identifier {{{identifier}}}")
        if len(identifier.provider_identifiers) < 2:
            raise ValueError(f"Invalid identifier format {{{identifier}}}")
        type = SptType(identifier.provider_identifiers[0])
        if type is None:
            raise ValueError(f"Invalid type, {{{identifier}}}")
        return SptIdentifier(type, identifier.provider_identifiers[1])
    
    @staticmethod
    def parse_str(identifier: str) -> Self:
        try:
            return SptIdentifier._convert(MediaBaseIdentifier.parse(identifier))
        except ValueError as ex:
            _spt_logger.error(f"Failed to parse identifier {{{identifier}}}\n{ex}")
            return None
    
    @staticmethod
    def parse_url(url: str) -> Self:
        if url.startswith(_DEFAULT_URL):
            splitedQuery = url[len(_DEFAULT_URL):].replace('/', ':').split(':')
            if(len(splitedQuery) == 2):
                [_type, _id_dirty] = splitedQuery
            else:
                [_market, _type, _id_dirty] = splitedQuery
            return SptIdentifier(_type, _id_dirty.split('?')[0])
        else:
            _spt_logger.info(f"Provided url `{url}` is not in the correct format for provider")
            return None


#endregion



@dataclass
class SptBase:
    identifier: SptIdentifier
    name: str

    @property
    def type(self):
        return self.identifier.type

    @property
    def id(self):
        return self.identifier.id
    
    @property
    def weburl(self):
        return f"{_DEFAULT_URL}/{self.identifier.type}/{self.identifier.id}"
