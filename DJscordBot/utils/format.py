"""Utiliy functions for the bot
"""

from ..config import config

def time_format(time_in_seconds: int) -> str:
    """Format the time in a more readable manner

    Args:
        time_in_seconds (int): the time to format in seconds

    Returns:
        str: Formatted time.
        
        Formats: (d:hh:mm:ss) or (h:mm:ss) or (m:ss) depending of the highest factor
    """


    time_in_seconds = int(time_in_seconds)
    
    days = time_in_seconds // 86400
    hrs = time_in_seconds // 3600 % 24
    min = time_in_seconds % 3600 // 60
    sec = time_in_seconds % 60
    
    if days > 0:
        return f"{days}:{hrs:0>2}:{min:0>2}:{sec:0>2}"
    
    if hrs > 0:
        return f"{hrs}:{min:0>2}:{sec:0>2}"
    
    return f"{min}:{sec:0>2}"