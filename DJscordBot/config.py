import os
import json

CFGFILE: str = "resources/config.json"

class Config():

    @classmethod
    def readConfig(self):
        if os.path.isfile(CFGFILE):
            print("Reading Config...")
            f = open(CFGFILE, 'r')
            self.conf = json.load(f)
            f.close()
            
            if 'discord-token' not in self.conf:
                print("[CONFIG.ERROR] No discord token provided. The bot can't work without a discord token")
                return

            print("[CONFIG.FILES] Will write and read files at those directories (relative to working dir):")
            
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
                
            
            # self.FoxDotEnabled = False
            # if "FoxDot-port" and "FoxDot-address" in self.conf:
            #     self.FoxDotEnabled = True
            #     print("Config: FoxDot is enabled")
            # else:
            #     print("Config: FoxDot is disabled")

            print('----------------')
            if self.debug is True:
                print("[CONFIG.DEBUG] Debug flag activated !")
                print('----------------')
            
            self.token = self.conf['discord-token']
        else:
            print(f"[CONFIG.ERROR] Config file is missing {CFGFILE}")
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
