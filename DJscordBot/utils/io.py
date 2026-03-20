from genericpath import isfile
import os
import random
import subprocess
import shutil
import sys
from typing import Any

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


_FFPROBE_PATH = shutil.which("ffprobe")

class AudioFileAttributes:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.is_local = True if os.path.isfile(self.file_path) else False
        self.byte_size = os.path.getsize(self.file_path) if self.is_local else 0
        result: subprocess.CompletedProcess = subprocess.run([_FFPROBE_PATH, "-i", self.file_path, "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1"], capture_output=True, text=True)
        if result.returncode != 0:
            logger.error(f"[AudioFileAttributes] ffprobe error\n{result.stderr}")
            raise ValueError("ffprobe error\n{result.stderr}")
        try:
            _float = float(result.stdout) #Audio file
            self.duration = _float
        except ValueError:
            if result.stdout == "N/A": #Audio stream / Radio
                self.duration = -1
            logger.error("[AudioFileAttributes] unable to get duration from ffprobe result")
            raise ValueError("Unable to get duration from ffprobe result")
