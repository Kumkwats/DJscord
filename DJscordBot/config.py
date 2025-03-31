import os
import json

CFGFILE: str = "resources/config.json"

class Config():

    _defaults = {
        'discord-token' : "<your discord token here>",
        'minutes-before-disconnecting' : 15
    }

    def ReadConfig(self):
        if os.path.isfile(CFGFILE):
            #print("Reading Config...")
            f = open(CFGFILE, 'r')
            self.conf = json.load(f)
            f.close()
            
            if 'discord-token' not in self.conf:
                print("[CONFIG.ERROR] No discord token provided in config file. The bot can't work without a discord token")
                exit()
            elif self.conf["discord-token"].startswith('<') or self.conf["discord-token"].endswith('>'):
                print("[CONFIG.ERROR] Please provide a valid token. The bot can't work without a valid token")
                exit()

            print("[FILE_DIRECTORIES] Will write and read files at those directories (relative to working dir):")
            
            self.downloadDirectory = "resources/downloads/" # default downloads directory
            # if 'download-directory' in self.conf:
            #     self.downloadDirectory = self.conf['download-directory']
            #     if self.downloadDirectory[0:2] == "./": # when ./ is added it mess up with the filename for some reason
            #         self.downloadDirectory = self.downloadDirectory[2:]
            #     if self.downloadDirectory[-1] != "/":
            #         self.downloadDirectory += "/"

            print("\tDownloaded files at: " + self.downloadDirectory)


            self.soundDirectory = "resources/sounds/" # default sounds directory
            # if 'sound-directory' in self.conf:
            #     self.soundDirectory = self.conf['sound-directory']
            #     if self.soundDirectory[0:2] == "./":
            #         self.soundDirectory = self.downloadDirectory[2:]
            #     if self.soundDirectory[-1] != "/":
            #         self.soundDirectory += "/"
            
            print("\tOther sound files at: " + self.soundDirectory)


            self.afkLeaveActive = True
            self.afkLeaveTime = 15 # default timeout afk leave
            if 'minutes-before-disconnecting' in self.conf:
                self.afkLeaveActive = True if self.conf['minutes-before-disconnecting'] > 0 else False
                self.afkLeaveTime = self.conf['minutes-before-disconnecting']

            if self.afkLeaveActive:
                print("[CONFIG.AFK] Will disconnect when inactive for more than %d minutes" % (self.afkLeaveTime))
            else:
                print("[CONFIG.AFK] Will not disconnect when inactive")

            self.spotifyEnabled = False
            if 'spotify-client-id' and 'spotify-client-secret' in self.conf:
                self.spotifyEnabled = True
            print("[CONFIG.SPOTIFY] research is %s" % ("enabled" if self.spotifyEnabled else "disabled"))

            self.debug: bool = False
            if 'debug' in self.conf:
                self.debug = self.conf['debug']

            print('----------------')
            if self.debug is True:
                print("[CONFIG.DEBUG] Debug flag activated !")
                print('----------------')
            
            self.token = self.conf['discord-token']
        else:
            print(f"[CONFIG.NO_FILE] No config file found")
            self.conf = {
                "discord-token" : self._defaults["discord-token"]
            }
            f = open(CFGFILE, 'w')
            json.dump(self.conf, f)
            f.close()
            print(f"[CONFIG.NO_FILE] Created template at {CFGFILE}")
            exit()

    @classmethod
    def GetPrefix(self):
        return "\u00b5"
        # return self.conf['prefix']

    @classmethod
    def SetPrefix(self, prefix):
        self.conf['prefix'] = prefix
        f = open(CFGFILE, 'w')
        json.dump(self.conf, f)
        f.close()

config = Config()
config.ReadConfig()
