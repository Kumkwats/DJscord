import os
import random
import subprocess
import shutil
import sys

from ..config import config

from ..logging.utils import get_logger
logger = get_logger("djscordbot.utils.io")




def pick_sound_file(folder_name: str) -> tuple[bool, str]:
    folder_path = config.soundDirectory + folder_name
    if os.path.isdir(folder_path):
        file_list = os.listdir(folder_path)
        logger.debug(f"[PICK_SOUND] Folder '{folder_name}', file_list : {file_list}")
        if len(file_list) > 0:
            rnd = random.randint(0, len(file_list)-1)
            full_path = os.path.join(folder_path, file_list[rnd])
            if os.path.isdir(full_path):
                return pick_sound_file(full_path)
            return True, full_path
        return True, "" # Folder exist but no file found
    return False, "" # Folder does not exist


def get_file_duration(filepath: str) -> tuple[bool, float, str]:
    """
    Get the duration of an audio file (local or remote) using ffprobe.
    :param filepath: Path to the audio file.

    :returns:
        A tuple with the following elements:

        - bool: False if an error is encountered.

        - float: the duration in seconds.

        - str: Error message if any.
    """
    if not os.path.isfile(filepath):
        logger.error("[GET_DURATION] file not found")
        return (False, -10, "file not found")

    
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path is None:
        logger.critical("[GET_DURATION] ffmpeg/ffprobe is not installed")
        return (False, sys.float_info.min, "ffmpeg/ffprobe is not installed")

    result: subprocess.CompletedProcess = subprocess.run([ffprobe_path, "-i", filepath, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1"], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"[GET_DURATION] ffprobe error\n{result.stderr}")
        return (False, result.returncode, "Unable to get duration from ffprobe result")
    try:
        _float = float(result.stdout)
        return (True, _float, "") #Audio file
    except ValueError:
        if result.stdout == "N/A":
            return (True, -1, "") #Audio stream / Radio
        logger.error("[GET_DURATION] unable to get duration from ffprobe result")
        return (False, -11, "Unable to get duration from ffprobe result")

