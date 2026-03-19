from dataclasses import dataclass
from typing import Any

from ._core import SptBase, SptIdentifier


@dataclass
class SptArtistBase(SptBase):
    avatar_url: str


def _get_best_avatar_image(artist: dict[str, Any]):
    if not 'visuals' in artist:
        return ""
    if artist['visuals']['avatarImage'] is None:
        return ""
    return max(artist['visuals']['avatarImage']['sources'], key=lambda cover_art_source: cover_art_source['width'])['url']


def parse_artists_info(artist_items: dict[str, Any]) -> list[SptArtistBase]:
    return [SptArtistBase(
        identifier=SptIdentifier.parse_str(artist['uri']),
        name=artist['profile']['name'],
        avatar_url=_get_best_avatar_image(artist)
    ) for artist in artist_items]
