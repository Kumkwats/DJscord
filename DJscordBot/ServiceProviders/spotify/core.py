from dataclasses import dataclass

from ..common import Identifier



PROVIDER: str = "spotify"
DEFAULT_URL: str = "https://open.spotify.com"



@dataclass
class SptBase:
    identifier: Identifier
    name: str

    @property
    def type(self):
        return self.identifier.type

    @property
    def id(self):
        return self.identifier.id
    
    @property
    def weburl(self):
        return f"{DEFAULT_URL}/{self.identifier.type}/{self.identifier.id}"
