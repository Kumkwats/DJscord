import os
import random
import subprocess
import shutil

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


def get_file_duration(filepath: str) -> float:
    if not os.path.isfile(filepath):
        logger.error("get_file_duration: file not found")
        return -1
    
    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path is None:
        logger.critical("ffmpeg/ffprobe is not installed")
        return -999

    result: subprocess.CompletedProcess = subprocess.run([ffprobe_path, "-i", filepath, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1"], capture_output=True, text=True)
    if result.returncode != 0:
        logger.error(f"get_file_duration: ffprobe error\n{result.stderr}")
        return -1
    try:
        _float = float(result.stdout)
        return _float
    except ValueError:
        logger.error("get_file_duration: unable to get duration from ffprobe result")
        return -1

