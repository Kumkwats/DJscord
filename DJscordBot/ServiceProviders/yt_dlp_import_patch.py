import sys
import importlib

# replaces yt-dlp import with custom patched file (for litteraly one (1) line that generated an error that prevented the download to proceed to the end)
# "[...]\yt_dlp\extractor\youtube\pot\_provider.py", line 125, in BuiltinIEContentProvider
#     BUG_REPORT_MESSAGE = bug_reports_message(before='')
#                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
# TypeError: <lambda>() got an unexpected keyword argument 'before'
YT_DLP_PROVIDER_UNPATCHED = 'yt_dlp.extractor.youtube.pot._provider'
YT_DLP_PROVIDER_PATCHED = 'DJscordBot.ServiceProviders.yt_dlp_patches.yt_dlp__provider'

if importlib.util.find_spec(YT_DLP_PROVIDER_PATCHED) is not None:
    __import__(YT_DLP_PROVIDER_PATCHED)
    sys.modules[YT_DLP_PROVIDER_UNPATCHED] = sys.modules.pop(YT_DLP_PROVIDER_PATCHED)
    print('Patched yt-dlp provider')