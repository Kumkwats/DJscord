from dataclasses import dataclass
from typing import Any

from ._core import SptBase, SptIdentifier


@dataclass
class SptArtistBase(SptBase):
    avatar_url: str


def parse_artists_info(artist_items: dict[str, Any]) -> list[SptArtistBase]:
    return [SptArtistBase(
        identifier=SptIdentifier.parse_str(artist['uri']),
        name=artist['profile']['name'],
        avatar_url=max(artist['visuals']['avatarImage']['sources'], key=lambda cover_art_source: cover_art_source['width'])['url']
    ) for artist in artist_items]


def parse_album_track_artists_info(artist_items: dict[str, Any]) -> list[SptArtistBase]:
    return [SptArtistBase(
        identifier=SptIdentifier.parse_str(artist['uri']),
        name=artist['profile']['name'],
        avatar_url=""
    ) for artist in artist_items]
