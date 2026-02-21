import os
import sqlite3

from dataclasses import dataclass

from DJscordBot.app import DATABASE_ROOT_PATH, ROOT_LOGGER
from ...logging.utils import get_logger
logger = get_logger(f"{ROOT_LOGGER}.linker.spotify")
__DATABASE_NAME = DATABASE_ROOT_PATH + "linker.spotify.db"

# class SpotifyItemType(StrEnum):
#     TRACK = 'track'
#     ALBUM = 'album'
#     ARTIST = 'artist'
#     PLAYLIST = 'playlist'
#     UNKNWON = auto()



@dataclass
class SpotifyLinker:
    spt_id: str
    yt_related_id: str
    is_valid: bool

    @property
    def yt_link(self):
        return f"https://youtu.be/{self.yt_related_id}"



def __create_db():
    # create folder if it doesn't exists
    if not os.path.exists(DATABASE_ROOT_PATH):
        os.mkdir(DATABASE_ROOT_PATH)
    con = sqlite3.connect(__DATABASE_NAME)
    con.execute("""
                    CREATE TABLE IF NOT EXISTS Linker (
                        spt_id TEXT NOT NULL,
                        yt_id TEXT NOT NULL,
                        is_valid INT NOT NULL,
                        PRIMARY KEY (spt_id, yt_id)
                    )
                    """
                    )
    con.close()



def __get_linkers_in_db(spt_id: str) -> list[SpotifyLinker]:
    con = sqlite3.connect(__DATABASE_NAME)
    cur: sqlite3.Cursor = con.execute("SELECT yt_id, is_valid FROM Linker WHERE spt_id=?", [spt_id])
    results: list[tuple] = cur.fetchall()
    con.close()

    linkers: list[SpotifyLinker] = []
    
    if results is None or len(results) < 1:
        return linkers

    for result in results:
        (yt_id, is_valid) = result
        if yt_id == "": # skip potential errors
            logger.warning("get_linkers(): ignoring linker with empty yt id !")
            continue
        linkers.append(SpotifyLinker(spt_id, yt_id, is_valid != 0))

    return linkers


def __get_specific_linker_in_db(spt_id: str, yt_id: str) -> SpotifyLinker | None:
    con = sqlite3.connect(__DATABASE_NAME)
    cur: sqlite3.Cursor = con.execute("SELECT is_valid FROM Linker WHERE spt_id=? AND yt_id=?", [spt_id, yt_id])
    result = cur.fetchone()
    con.close()
    if result is None:
        return None
    return SpotifyLinker(spt_id, yt_id, result[0] != 0)



def __set_new_linker_in_db(spt_id: str, yt_id: str):
    con = sqlite3.connect(__DATABASE_NAME)
    con.execute("INSERT INTO Linker VALUES (?, ?, ?)", [spt_id, yt_id, 1])
    con.commit()
    con.close()



def __set_invalidity(spt_id: str, yt_id: str, is_valid: bool):
    con = sqlite3.connect(__DATABASE_NAME)
    con.execute("""
                UPDATE Linker
                SET is_valid = ?
                WHERE spt_id=? AND yt_id=?
                """, 
                [1 if is_valid else 0, spt_id, yt_id])
    con.commit()
    con.close()



# very basic db check
if not os.path.isfile(__DATABASE_NAME):
    __create_db()



class LinkerAPI:
    @staticmethod
    def create_new_link(spt_id: str, yt_id: str):
        __set_new_linker_in_db(spt_id, yt_id)

    @staticmethod
    def get_linker(spt_id: str, yt_id: str) -> SpotifyLinker | None:
        return __get_specific_linker_in_db(spt_id, yt_id)
    

    @staticmethod
    def get_first_available_linker(spt_id: str) -> SpotifyLinker | None:
        linkers: list[SpotifyLinker] = __get_linkers_in_db(spt_id)
        return next((link for link in linkers if link.is_valid), None)

    @staticmethod
    def invalidate_linker(linker: SpotifyLinker):
        __set_invalidity(linker.spt_id, linker.yt_related_id)
        pass
