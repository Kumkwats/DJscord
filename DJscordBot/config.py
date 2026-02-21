import os
import dotenv
import json

from .app import *

from .logging.utils import get_logger, GLOBAL_LOG_LEVEL
logger = get_logger(f"{ROOT_LOGGER}.config")

class Config():

    __default_conf = {
        'discord-token' : "<your discord token here>",
        'minutes-before-disconnecting' : 0
    }

    def read_config(self):
        logger.info("Retrieving config information from environment and files...")

        config_dict = {}

    # Loading json files
        if os.path.isfile(CONFIG_FILE):
            f = open(CONFIG_FILE, 'r')
            json_config = json.load(f)
            f.close()
            config_dict.update(json_config)

    # Loading .env
        config_dict.update(dotenv.dotenv_values())
        config_dict.update(os.environ)

        def check_config_value_from_key(key: str) -> bool:
            return key in config_dict and config_dict[key] is not None

    # Get Discord Token
        if check_config_value_from_key('DISCORD_TOKEN'):
            self.token = config_dict['DISCORD_TOKEN'] # .env token
        elif 'discord-token' in config_dict:
            self.token = config_dict['discord-token'] # config.json token
        else:
            logger.critical("No token was provided, please make sure that you have setup your environment properly or that you provided a valid token in your config.json file")
            exit(1)

        logger.debug("[VALUE_SET] Loaded discord token.")

    # Spotify tokens
        self.spotify_id = None
        if check_config_value_from_key('SPOTIFY_CLIENT_ID'):
            self.spotify_id = config_dict['SPOTIFY_CLIENT_ID'] # .env
            logger.debug("[VALUE_SET] Loaded Spotify client ID from environment")
        elif 'spotify-client-id' in config_dict:
            self.spotify_id = config_dict['spotify-client-id'] # config.json
            logger.debug("[VALUE_SET] Loaded Spotify client ID from config.json")

        self.spotify_secret = None
        if check_config_value_from_key('SPOTIFY_CLIENT_SECRET'):
            self.spotify_secret = config_dict['SPOTIFY_CLIENT_SECRET'] # .env
            logger.debug("[VALUE_SET] Loaded Spotify client SECRET from environment")
        elif 'spotify-client-secret' in config_dict:
            self.spotify_secret = config_dict['spotify-client-secret'] # config.json
            logger.debug("[VALUE_SET] Loaded Spotify client SECRET from config.json")

        # Feedback spotify setup
        self.spotifyEnabled = False
        if self.spotify_id is not None and self.spotify_secret is not None:
            logger.info("[OPTION] Spotify search is ENABLED")
            self.spotifyEnabled = True
        else:
            if self.spotify_id is not None or self.spotify_secret is not None: # user error
                logger.warning("[OPTION] Spotify search is DISABLED.\n" \
                "You may have made a mistake while setting up the secrets for Spotify.\n" \
                "Please verify your environment and/or config files")
            else:
                logger.info("[OPTION] Spotify search is DISABLED.")
            


    # YT-DLP Settings
        self.bgutil_server_ip = "0.0.0.0"
        if check_config_value_from_key('YTDLP_BGUTIL_SERVER_IP'):
            self.bgutil_server_ip = config_dict['YTDLP_BGUTIL_SERVER_IP']
            logger.debug("[VALUE_SET] Loaded bgutil_server_ip from environment")
        elif 'bgutil-server-ip' in config_dict:
            self.bgutil_server_ip = config_dict['bgutil-server-ip']
            logger.debug("[VALUE_SET] Loaded bgutil_server_ip from config.json")



    # Audio files locations
        logger.info("[FILES] Will write and read files at those directories (relative to working dir):")
        self.downloadDirectory = DOWNLOAD_FOLDER_PATH # default downloads directory
        logger.info(f"\t\tDownloaded files at: ./{self.downloadDirectory}")
        self.soundDirectory = SOUND_FOLDER_PATH # default sounds directory
        logger.info(f"\t\tOther sound files at: ./{self.soundDirectory}")



    # AFK Options
        self.leave_afk_enabled = True
        self.leave_afk_time = self.__default_conf['minutes-before-disconnecting'] # default timeout afk leave
        if 'minutes-before-disconnecting' in config_dict:
            self.leave_afk_enabled = True if config_dict['minutes-before-disconnecting'] > 0 else False
            self.leave_afk_time = config_dict['minutes-before-disconnecting']

        if self.leave_afk_enabled:
            logger.info(f"[AFK] Will disconnect when inactive for more than {self.leave_afk_time} minutes")
        else:
            logger.info("[AFK] Will not disconnect when inactive")



    # misc. options
        self.allow_startup_filters = False
        if 'allow-startup-filters' in config_dict and config_dict['allow-startup-filters'] == True:
            self.allow_startup_filters = True
            logger.info("[SET] Will sometimes apply filters on startup sounds")



    # Debug
        self.debug = False
        if 'DEBUG' in config_dict:
            self.debug = True
            logger.warning("[DEBUG] Debug flag activated ! This may create quite some additional files at run time")

        self.log_level = GLOBAL_LOG_LEVEL



config = Config()
config.read_config()
