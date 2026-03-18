"""
Wrapper for the public access of Spotify web pages using spotapi.
Provides a higher-level interface for getting song, album, playlist, and artist information.
"""
from typing import Any


from DJscordBot.Types.entry import Entry, EntryPlaylist

from ..common import MediaProcessInteraction

from ._core import _spt_logger, SptIdentifier, SptType
from ._track import *
from ._album import *


from spotapi import client_pool, TLSClient, Public, PublicAlbum, PublicPlaylist


def get_data(url: str, interaction: MediaProcessInteraction) -> list[MediaEntry]:
    _spt_logger.debug("get_data(): Begin retrieving data")

    _spt_logger.debug("get_data(): Converting url to identifier")
    identifier: SptIdentifier = SptIdentifier.parse_url(url)
    if identifier is None:
        _spt_logger.debug("get_data(): Identifier is None")
        return None
    if identifier.type == SptType.ARTIST:
        _spt_logger.debug("get_data(): Identifier is of an artist, which isn't handled")
        return None
    
    raw_data = get_raw_data(identifier)

    return process_data(identifier, interaction, raw_data=raw_data)


def get_raw_data(identifier: SptIdentifier) -> dict[str, Any]:
    client: TLSClient = client_pool.get()
    raw_data: dict[str, Any] = None
    try:
        match identifier.type:
            case SptType.TRACK:
                _spt_logger.debug("get_raw_data(): retrieving public song_info...")
                raw_data = Public.song_info(identifier.id)
            case SptType.ALBUM:
                _spt_logger.debug("get_raw_data(): retrieving public album_info...")
                album = PublicAlbum(identifier.id, client=client)
                raw_data = album.get_album_info()

            case SptType.PLAYLIST:
                _spt_logger.debug("get_raw_data(): retrieving public album_info...")
                playlist = PublicPlaylist(identifier.id, client=client)
                raw_data = playlist.get_playlist_info()

            case _:
                _spt_logger.debug("get_raw_data(): Unhandled type, aborting")
                return None
    except:
        _spt_logger.debug("get_raw_data(): Something went wrong")
        return None
    finally:
        client_pool.put(client)
    
    return raw_data



def process_data(identifier: SptIdentifier, interaction: MediaProcessInteraction, raw_data: dict[str, Any]) -> list[Entry]:
    _spt_logger.debug("process_data(): begin processing")
    interaction.add_title("Traitement des données")

    #TODO: interaction
    match identifier.type:
        case SptType.TRACK:
            _spt_logger.debug("process_data(): processing track data")
            song: SptSongFull = process_track_data(raw_data)
            if song is None:
                _spt_logger.debug("process_data(): unable to process data")
                return []
            _spt_logger.debug("process_data(): creating entry")
            song_entry: Entry = Entry(f"{song.first_artists[0].name} - {song.name}", interaction.wrapper.author, song.identifier.to_web_url())
            song_entry.add_image(song.album_art.cover_art)
            description = f"{song.album.name}]({song.album.identifier.to_web_url()})\n" # Album
            description += f"Artiste : [{song.first_artists[0].name}]({song.first_artists[0].identifier.to_web_url()})\n" # Artiste
            description += f"-# source: Spotify"
            song_entry.add_description(description)
            song_entry.duration = float(song.duration/1000)

            _spt_logger.debug("process_data(): processing ended")
            return [song_entry]
        
        case SptType.ALBUM:
            ret_entry_list: list[Entry] = []

            _spt_logger.debug("process_data(): processing album data")
            album: SptAlbum = process_album_data(raw_data)
            if album is None:
                _spt_logger.debug("process_data(): unable to process data")
                return ret_entry_list

            #TODO: When interaction with button is figured out and when multiple discs in album, prompt user which disc(s) to play.
            album_tracks = album.tracks

            _spt_logger.debug(f"album data: {len(album.discs)} discs, {len(album_tracks)} tracks")

            entry_playlist: EntryPlaylist = EntryPlaylist(album.identifier.id, album.name, interaction.wrapper.author, "album", album.identifier.to_web_url())

            _spt_logger.debug(f"process_data(): creating entries")
            for track in album.tracks:
                _spt_logger.debug(f"process_data(): creating entry for {track.name}...")
                track_url: str = track.identifier.to_web_url()
                track_entry: Entry = Entry(f"{track.artists[0].name} - {track.name}", interaction.wrapper.author, track_url)
                track_entry.set_playlist(entry_playlist)
                track_entry.add_image(album.visual_art.cover_art)
                description = f"{album.name}]({track_url})\n" # Album
                description += f"Artiste : [{album.artists[0].name}]({album.artists[0].identifier.to_web_url()})\n" # Artiste
                description += f"-# source: Spotify"
                track_entry.add_description(description)
                track_entry.duration = int(track.duration/1000)
                
                ret_entry_list.append(track_entry)
            _spt_logger.debug("process_data(): processing ended")
            return ret_entry_list
        
        case _:
            _spt_logger.warning("process_data(): unhandled type")
            return None
