import os
import random
import subprocess


from ..config import config


def pick_sound_file(folder_name: str) -> tuple[bool, str]:
    folder_path = config.soundDirectory + folder_name
    if os.path.isdir(folder_path):
        file_list = os.listdir(folder_path)
        print(f"[DEBUG] file_list : {file_list}")
        if len(file_list) > 0:
            rnd = random.randint(0, len(file_list)-1)
            full_path = os.path.join(folder_path, file_list[rnd])
            if os.path.isdir(full_path):
                return pick_sound_file(full_path)
            return True, full_path
        return True, "" # Folder exist but no file found
    return False, "" # Folder does not exist


def get_file_duration(filepath: str) -> float:
    if " " in filepath:
        filepath = f'"{filepath}"'
    if not os.path.isfile(filepath):
        return -1
    result: subprocess.CompletedProcess = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", f'"{filepath}"'], stdout=subprocess.PIPE)
    try:
        _float = float(result.stdout)
        return _float
    except ValueError:
        return -1

