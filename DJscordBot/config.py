import os
import json

from .logging.utils import get_logger
logger = get_logger("djscordbot.config")

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
                logger.critical("No discord token provided in config file. The bot can't work without a discord token")
                exit()
            elif self.conf["discord-token"].startswith('<') or self.conf["discord-token"].endswith('>'):
                logger.critical("Please provide a valid token. The bot can't work without a valid token")
                exit()

            write_info = "[FILES] Will write and read files at those directories (relative to working dir):"
            
            self.downloadDirectory = "resources/downloads/" # default downloads directory
            # if 'download-directory' in self.conf:
            #     self.downloadDirectory = self.conf['download-directory']
            #     if self.downloadDirectory[0:2] == "./": # when ./ is added it mess up with the filename for some reason
            #         self.downloadDirectory = self.downloadDirectory[2:]
            #     if self.downloadDirectory[-1] != "/":
            #         self.downloadDirectory += "/"

            write_info += "\tDownloaded files at: " + self.downloadDirectory


            self.soundDirectory = "resources/sounds/" # default sounds directory
            # if 'sound-directory' in self.conf:
            #     self.soundDirectory = self.conf['sound-directory']
            #     if self.soundDirectory[0:2] == "./":
            #         self.soundDirectory = self.downloadDirectory[2:]
            #     if self.soundDirectory[-1] != "/":
            #         self.soundDirectory += "/"
            
            write_info += "\tOther sound files at: " + self.soundDirectory
            logger.info(write_info)

            self.afkLeaveActive = True
            self.afkLeaveTime = 15 # default timeout afk leave
            if 'minutes-before-disconnecting' in self.conf:
                self.afkLeaveActive = True if self.conf['minutes-before-disconnecting'] > 0 else False
                self.afkLeaveTime = self.conf['minutes-before-disconnecting']

            if self.afkLeaveActive:
                logger.info(f"[AFK] Will disconnect when inactive for more than {self.afkLeaveTime} minutes")
            else:
                logger.info("[AFK] Will not disconnect when inactive")

            self.spotifyEnabled = False
            if 'spotify-client-id' and 'spotify-client-secret' in self.conf:
                self.spotifyEnabled = True

            if self.spotifyEnabled:
                logger.info(f"[SPOTIFY] research is ENABLED")
            else:
                logger.info(f"[SPOTIFY] research is DISABLED")

            if 'bgutil-server-ip' in self.conf:
                self.bgutil_server_ip = self.conf['bgutil-server-ip']
            else:
                self.bgutil_server_ip = "127.0.0.1"
            logger.info(f"[POT] Will attempt to get a PO Token at this IP : {self.bgutil_server_ip}")

            self.debug: bool = False
            if 'debug' in self.conf:
                self.debug = self.conf['debug']

            if self.debug is True:
                logger.warning("[DEBUG] Debug flag activated ! This may create quite some additional files at run time")
            
            self.token = self.conf['discord-token']
        else:
            logger.critical("[NO_FILE] No config file found")
            self.conf = {
                "discord-token" : self._defaults["discord-token"]
            }
            f = open(CFGFILE, 'w')
            json.dump(self.conf, f)
            f.close()
            logger.critical(f"[NO_FILE] Created template at {CFGFILE}\nNow please fill the necessary fields for the bot to work")
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
