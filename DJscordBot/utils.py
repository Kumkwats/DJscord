"""Utiliy functions for the bot
"""

import os
import random
from DJscordBot.config import config

def time_format(seconds: int) -> str:
    """Format the time in a more readable manner

    Args:
        seconds (int): 

    Returns:
        str: formatted time (h:mm:ss) or (m:ss)
    """


    seconds = int(seconds)
    h = seconds // 3600 % 24
    m = seconds % 3600 // 60
    s = seconds % 60

    if h > 0:
        return f"{h}:{m:0>2}:{s:0>2}"
    else:
        return f"{m}:{s:0>2}"


def pick_sound_file(folder_name: str) -> tuple[bool, str]:
    file_path = config.soundDirectory + folder_name
    if os.path.isdir(file_path):
        if len(os.listdir(file_path)) > 0:
            rnd = random.randint(0, len(os.listdir(file_path))-1)
            return True, f"{file_path}/{os.listdir(file_path)[rnd]}"
        return True, "" # Folder exist but no file found
    return False, "" # Folder does not exist