import sys

# Allows to fake import modules, to prevent ModuleNotFoundError.

# This should NOT be necessary but whenever you try to import a part of spotapi, everything single module in spotapi is imported.
# Including other module imports like pymongo or redis, which are not installed by default when spotapi is installed but they supposedly should have been.
# Because they are not used anywhere near the bot's use-case and won't be in a foreseeable future, I will just dummy import to bypass the Error.


DUMMY_MODULE_PATH = 'DJscordBot.utils._dummy_module'

def patch_dummy_import(module_name):
    __import__(DUMMY_MODULE_PATH)
    sys.modules[module_name] = sys.modules.pop(DUMMY_MODULE_PATH)


patch_dummy_import('pymongo')
patch_dummy_import('redis')
