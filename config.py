import os
import json

CFGFILE = "config.json"

class Config():
    @classmethod
    def readConfig(self):
        if os.path.isfile(CFGFILE):
            f = open(CFGFILE, 'r')
            self.conf = json.load(f)
            f.close()

            print("Config: Will write and read files at those directories (relative to working dir):")
            
            self.downloadDirectory = "downloads/" # default downloads directory
            if 'download-director' in self.conf:
                self.downloadDirectory = self.conf['download-directory']
            
            print("\tDownloaded files at: " + self.downloadDirectory)

            self.soundDirectory = "sounds/" # default sounds directory
            if 'sound-directory' in self.conf:
                self.soundDirectory = self.conf['sound-directory']
            
            print("\tOther sound files at: " + self.soundDirectory)

            self.spotifyEnabled = False
            if 'spotify-client-id' and 'spotify-client-secret' in self.conf:
                self.spotifyEnabled = True
                print("Config: Spotify research is enabled")
            else:
                print("Config: Spotify research is disabled")
            
            
            self.FoxDotEnabled = False
            if "FoxDot-port" and "FoxDot-address" in self.conf:
                self.FoxDotEnabled = True
                print("Config: FoxDot is enabled")
            else:
                print("Config: FoxDot is disabled")


            self.token = self.conf['discord-token']
        else:
            print("ERR: Config file is missing (%s)" % CFGFILE)
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
