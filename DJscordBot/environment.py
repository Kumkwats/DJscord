import os
import signal
from enum import Enum, auto

class OSName(Enum):
    UNIX = auto()
    WINDOWS = auto()
    MACOS = auto()

def __get_os():
    if os.name == "nt":
        return OSName.WINDOWS
    elif platform.platform == "Darwin":
        return OSName.MACOS
    else:
        return OSName.UNIX
    
def __get_supported_interrupt_signals(current_os: OSName):
    signals = [signal.SIGINT]
    if current_os is OSName.WINDOWS:
        signals.append(signal.SIGBREAK)
    else:
        signals.append(signal.SIGTERM)
    return signals


OPERATING_SYSTEM: OSName = __get_os()
SUPPORTED_TERMINATE_SIGNALS = __get_supported_interrupt_signals(OPERATING_SYSTEM)

