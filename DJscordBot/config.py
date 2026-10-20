import os

from dataclasses import dataclass
from inspect import get_annotations
from typing import Any

import dotenv
import json



from .logging.utils import get_logger
logger = get_logger("djscordbot.config")


CONFIG_FOLDER_PATH = "resources/"

@dataclass(slots=True)
class GuildSettings:
    # server_language: str # unused until localised feedback is implemented
    audio_player_update_in_channel_id: int = None # Where the bot should write their update messages
    # afk_leave_timeout: int = 15 # <= 0 or null for no AFK timeout

    @classmethod
    def _from_json(cls, json_dict: dict[str, Any]):
        extractable_values: dict[str,Any] = {k:v for k,v in json_dict.items() if k in GuildSettings.__slots__}

        if not len(extractable_values):
            return None

        annotations = {k:v for k,v in get_annotations(cls) if k in extractable_values.keys()} # get the default type of the class variables
        
        guild_settings = GuildSettings()
        for key in extractable_values.keys():
            try:
                setattr(guild_settings, key, GuildSettings.__parse_values(key, extractable_values[key], annotations[key]))
            except:
                logger.error(f"[GUILD.JSON] Unable to parse value for key {key}. Raw value is {extractable_values[key]}")


    def _to_dict(self):
        ret_dict = {}
        for k in self.__slots__:
            ret_dict[k] = getattr(self, k)
        return ret_dict

    def __parse_values(key: str, value: Any, target_type: type):
        if value is None: # handling null values
            return None
        if target_type == str and isinstance(value, target_type):
            return value
        simple_types = [int, float, bool]
        if target_type in simple_types:
            if isinstance(value, target_type):
                return value
            try:
                return target_type(value)
            except ValueError:
                raise ValueError("Unable to parse to targeted number or bool")
        complex_types = [list, dict]
        if target_type in complex_types:
            if isinstance(value, target_type):
                return value
            raise ValueError("Unable to parse to targeted collection")
        




class GuildConfig:
    config_file_path = CONFIG_FOLDER_PATH + "config_guilds.json"
    _cached_configs: dict[int, GuildSettings] = None

    @classmethod
    def _load_config(cls) -> int: # returns the number of configs
        logger.info("[GUILDS.LOAD] Loading guild configs from disk...")
        
        cls._cached_configs = {}

        if os.path.isfile(cls.config_file_path):
            f = open(cls.config_file_path, 'r')
            loaded_configs: dict[str, Any] = json.load(f)
            f.close()

            for key in loaded_configs.keys():
                try:
                    guild_id = int(key)
                except ValueError:
                    logger.warning(f"[GUILDS.LOAD] key '({key})' is not a parseable id")
                cls._cached_configs[guild_id] = GuildSettings._from_json(loaded_configs[guild_id])
        logger.info("[GUILDS.LOAD] Loading guild configs from disk completed")
        return len(cls._cached_configs)


    @classmethod
    def _save_config(cls):
        logger.info("[GUILDS.SAVE] Saving guild configs to disk...")
        json_dict = {}
        for guild_id in cls._cached_configs:
            json_dict[str(guild_id)] = cls._cached_configs[guild_id]._to_dict() # everything that isn't an id will not be preserved
        f = open(cls.config_file_path, 'w')
        json.dump(json_dict, f)
        f.close()
        logger.info("[GUILDS.SAVE] Saving guild configs to disk completed")
    
    @classmethod
    def get_settings(cls, guild_id: int) -> GuildSettings:
        if cls._cached_configs is None:
            cls._load_config()
        if guild_id not in cls._cached_configs:
            logger.info(f"[GUILDS.GET] Creating default settings for guild [{guild_id}]")
            cls._cached_configs[guild_id] = GuildSettings()
        return cls._cached_configs[guild_id]




CFGFILE: str = "resources/config.json"

class Config():

    __default_conf = {
        'discord-token' : "<your discord token here>",
        'minutes-before-disconnecting' : 0
    }

    def read_config(self):
        logger.info("Retrieving config information from environment and files...")

        config_dict = {}

    # Loading json files
        if os.path.isfile(CFGFILE):
            f = open(CFGFILE, 'r')
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
        self.downloadDirectory = "resources/downloads/" # default downloads directory
        logger.info(f"\t\tDownloaded files at: ./{self.downloadDirectory}")
        self.soundDirectory = "resources/sounds/" # default sounds directory
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

    # Test
        self.test_guild: int = None
        if 'TEST_GUILD' in config_dict:
            try:
                self.test_guild = int(config_dict['TEST_GUILD'])
            except ValueError:
                logger.error("[TEST] Invalid testing guild id")
                self.test_guild = None

    @classmethod
    def get_prefix(self):
        return "\u00b5"
        # return self.conf['prefix']

    @classmethod
    def set_prefix(cls, prefix):
        cls.json_confing['prefix'] = prefix
        f = open(CFGFILE, 'w')
        json.dump(cls.json_confing, f)
        f.close()



config = Config()
config.read_config()
