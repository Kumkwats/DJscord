import sys
import importlib

# replaces yt-dlp import with custom patched file (for litteraly one (1) line that generated an error that prevented the download to proceed to the end)
# "[...]\yt_dlp\extractor\youtube\pot\_provider.py", line 125, in BuiltinIEContentProvider
#     BUG_REPORT_MESSAGE = bug_reports_message(before='')
#                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# TypeError: <lambda>() got an unexpected keyword argument 'before'

def patch(source, patch, name):
    if importlib.util.find_spec(patch) is not None:
        __import__(patch)
        sys.modules[source] = sys.modules.pop(patch)
        print(f'Patched yt-dlp {name}')

patch('yt_dlp.extractor.youtube.pot._provider',
      'DJscordBot.ServiceProviders.yt_dlp_patches.yt_dlp__provider',
      "pot._provider")
patch('yt_dlp.extractor.youtube._provider',
      'DJscordBot.ServiceProviders.yt_dlp_patches.yt_dlp__video',
      "_video")