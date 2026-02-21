import os
import platform

from .app import *
from .logging.utils import get_logger
__logger = get_logger(f"{ROOT_LOGGER}.init")

def __os_warnings():
    if os.name == "nt":
        __logger.warning("[WINDOWS] You are running python on Windows.") 
        __logger.warning("There are some discrepancies in the inner working of some python modules between the Windows and Linux implementation that may impact how the bot works.")
        __logger.warning("The bot was developped primarly for Linux. There is no guarranties that everything will work as intended on Windows.")
    else:
        if platform.platform == "Darwin":
            __logger.warning("[MACOS] The bot is currently running on MacOS.")
            __logger.warning("The platform hasn't been tested at all.")
            __logger.warning("Be aware that you may need to install additional packages and/or things may break.")


def __create_folders():
    folders = [RESOURCES_FOLDER_PATH, DOWNLOAD_FOLDER_PATH, SOUND_FOLDER_PATH, DATABASE_ROOT_PATH]
    for folder in folders:
        if not os.path.isdir(folder):
            __logger.debug(f"CREATED FOLDER: \'{folder}\'")
            os.makedirs(folder)

def __download_folder_cleanup():
    dl_files = os.listdir(DOWNLOAD_FOLDER_PATH)
    if len(dl_files) > 0:
        for file in dl_files:
            full_path_file = DOWNLOAD_FOLDER_PATH + file
            os.remove(full_path_file)
            __logger.debug(f"DOWNLOAD CLEANUP: removed file \'{file}\'")


def init_environment():
    __os_warnings()
    __create_folders()
    __download_folder_cleanup()
