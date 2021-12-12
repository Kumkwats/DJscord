import os
import json

CFGFILE = "config.json"
DLDIR = "downloads/"
SNDDIR = "../Sound/" #TODO Move to the config.json


class Config():
    @classmethod
    def readConfig(self):
        if os.path.isfile(CFGFILE):
            f = open(CFGFILE, 'r')
            self.conf = json.load(f)
            f.close()

            self.spotifyEnabled = False
            if 'spotify-client-id' and 'spotify-client-secret' in self.conf:
                self.spotifyEnabled = True

            self.FoxDotEnabled = False
            if "FoxDot-port" and "FoxDot-address" in self.conf:
                self.FoxDotEnabled = True

            self.token = self.conf['discord-token']
        else:
            print("Fichier config non trouvé ou non valide:", CFGFILE)
            exit()

    @classmethod
    def getPrefix(self):
        return self.conf['prefix']

    @classmethod
    def setPrefix(self, prefix):
        self.conf['prefix'] = prefix
        f = open(CFGFILE, 'w')
        json.dump(self.conf, f)
        f.close()

config = Config()
config.readConfig()
