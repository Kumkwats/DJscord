import os
import time
import asyncio
import traceback

if os.name == "nt":
    from threading import Thread
else:
    from multiprocessing import Process, Pipe
    from multiprocessing.connection import Connection

import yt_dlp
#from youtubesearchpython.__future__ import VideosSearch


from ..config import config

from .common import CommonResponseData

PLAYLIST_SIZE_LIMIT: int = 100
PROVIDER: str = 'youtube'
DEFAULT_ASYNC_UPDATE_FREQ: float = 2


from ..logging.utils import get_logger
logger = get_logger("djscordbot.youtube")


# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda before=';': ''


opts_outtmpl = config.downloadDirectory + '%(extractor)s-%(id)s-%(title)s.%(ext)s'

opts_default = {
    # Video format code. See options.py for more information.
    'format': 'bestaudio[format_note*=original]/bestaudio',
    # Template for output names.
    'outtmpl': opts_outtmpl,
    # Do not allow "&" and spaces in file names
    'restrictfilenames': True, 
    # Download single video instead of a playlist if in doubt.
    'noplaylist': True,
    # Do not verify SSL certificates
    'nocheckcertificate': True,
    # Do not stop on download errors.
    'ignoreerrors': True,
    # A class having a `debug`, `warning` and `error` function where each has a single string parameter, the message to be logged.
    # For compatibility reasons, both debug and info messages are passed to `debug`.
    # A debug message will have a prefix of `[debug] ` to discern it from info messages.
    'logger': get_logger("yt-dlp"),
    # Log messages to stderr instead of stdout.
    'logtostderr': False,       
    # Print additional info to stdout.
    'verbose': False,
    # Do not print messages to stdout.
    'quiet': False,
    # Do not print out anything for warnings.
    'no_warnings': True,
    # Prepend this string if an input url is not valid. 'auto' for elaborate guessing
    'default_search': 'auto',
    # Client-side IP address to bind to.
    # bind to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0',

    ### Options for the downloader

    'noprogress': True,


    'extractor_args': {
        
        'youtube': {
            'skip': ['translated_subs'],
            'player-client': ['mweb'],
            'player-skip': ['webpage'],
            'max-comments': ['0','0','0','0']
        },
        'youtubepot-bgutilhttp': { 
            'base_url': [f'http://{config.bgutil_server_ip}:4416']
        }
    }
}

ydl_downloader_opts = opts_default.copy()
ydl_downloader_opts['extract_flat'] = 'True' #downloader never downloads a playlist directly
ydl_downloader = yt_dlp.YoutubeDL(ydl_downloader_opts)
oldTime = 0



ydl_extractor_opts = opts_default.copy()
ydl_extractor_opts['logger'] = get_logger('yt-dlp_search')
ydl_extractor_opts['extractor_args']['youtube'] = {
    'skip': ['translated_subs'],
    'player-skip': ['js', 'configs']
}
ydl_extractor_opts['skip_download'] = True
ydl_extractor = yt_dlp.YoutubeDL(ydl_extractor_opts)


#region Youtube Objects

class YoutubeBaseObject():
    def __init__(self, request_data):
        self.id = request_data['id']
        self.name = request_data['title']

        self.type = YoutubeAPI.infer_response_object_type(request_data)
        
        self.url = request_data['original_url']
        self.web_url = request_data['webpage_url'] if 'webpage_url' in request_data else None
        self._raw_data = request_data

    def __str__(self):
        return f"YouTube (type: {self.type}) | name: '{self.name}' | id: '{self.id}'"


class   YoutubeVideo(YoutubeBaseObject):
    def __init__(self, request_data):
        super().__init__(request_data)

        self.view_count = request_data['view_count']
        self.like_count = request_data['like_count']

        self.channel = request_data['channel']
        self.channel_url = request_data['channel_url']
        self.channel_follower_count = request_data['channel_follower_count']
        
        if 'album' in request_data:
            self.album = request_data['album']
        self.duration = request_data['duration']
        self.thumbnail = request_data['thumbnail']
        self.is_live: bool = request_data['is_live']

    def get_filename(self) -> str:
        return ydl_downloader.prepare_filename(self._raw_data)[len(config.downloadDirectory):]

    def __str__(self):
        return f"Vidéo youtube | titre: '{self.name}' | id: '{self.id}'"


class YoutubePlaylist(YoutubeBaseObject):
    def __init__(self, request_data):
        super().__init__(request_data)
        self.uploader = request_data['uploader']
        self.uploader_id = request_data['uploader_id']
        self.uploader_url = request_data['uploader_url']
        self.entries: list[YoutubeVideo] = []
        for entry in request_data['entries']:
            self.entries.append(YoutubeVideo(entry))
        
    @property
    def is_empty(self):
        return len(self.entries) <= 0

    def __str__(self):
        return f"Playlist youtube | titre: '{self.name}' | id: '{self.id}' | nombre d'entrées '{len(self.entries)}'"
    
class YoutubeSearch(YoutubeBaseObject):
    def __init__(self, request_data):
        super().__init__(request_data)
        self.entries: list[YoutubeBaseObject] = []

        if 'entries' in request_data:
            data_entres = request_data['entries']

            for i in range(0, min(PLAYLIST_SIZE_LIMIT, len(data_entres))):
                if data_entres[i] is not None:
                    self.entries.append(YoutubeBaseObject(data_entres[i]))

    @property
    def is_empty(self):
        return len(self.entries) <= 0

    def __str__(self):
        return f"Recherche youtube | requête: '{self.name}' | nombre d'entrées: '{len(self.entries)}'"


#endregion





#region API Calls
class YoutubeAPI():
    @classmethod
    def search_sync(cls, query: str) -> YoutubeSearch:
        request_data = ydl_extractor.extract_info(f"ytsearch:{query}", download=False)
        return YoutubeSearch(request_data)

    @classmethod
    def get_data_sync(cls, youtube_url: str) -> CommonResponseData:
        try:
            request_data = ydl_extractor.extract_info(youtube_url, download=False)
        except Exception as ex:
            logger.exception(ex)
            return None
        return CommonResponseData(PROVIDER, request_data['id'], request_data, cls.infer_type_from_request_url(youtube_url))
    


    @classmethod
    async def __extract_info_async(cls, query: str, extractor, user_update_coroutine = None, frequency_update: float = DEFAULT_ASYNC_UPDATE_FREQ, print_in_console: bool = False) -> CommonResponseData:

        start_time: float = time.time()
        last_update_time: float = time.time()
        time_since_last_update: float = frequency_update 

        if os.name == "nt": # 'nt' => Windows; Multiprocessing doesn't work similarly between Windows and Linux and causes problems that I don't want to deal with yet so I'm bringing back the old way for Windows
            response_data: CommonResponseData = CommonResponseData.create_empty()
            extract_thread: Thread = Thread(target=extractor, args=[query, response_data])
        else:
            receiver, sender = Pipe(False)
            extract_thread: Process = Process(target=extractor, args=[query, sender])
        extract_thread.start()

        while extract_thread.is_alive():
            delta_time = time.time() - last_update_time
            last_update_time = time.time()
            time_since_last_update += delta_time

            if os.name != "nt":
                if receiver.poll(0.1):
                    break
            
            if time_since_last_update > frequency_update:
                time_since_last_update -= frequency_update
                if print_in_console:
                    logger.info(f"[YOUTUBE.DATA.GET] awaiting response...\ttime elapsed:{(time.time() - start_time):4.2f}")
                if user_update_coroutine is not None:
                    time_elapsed = time.time() - start_time
                    await user_update_coroutine(time_elapsed)
            await asyncio.sleep(0.15)

        if os.name != "nt":
            response_data: CommonResponseData = receiver.recv()
            receiver.close()

        return response_data

        




    @classmethod
    async def search_async(cls, query: str, user_update_coroutine = None, frequency_update: int = DEFAULT_ASYNC_UPDATE_FREQ, print_in_console: bool = False) -> YoutubeSearch:
        if os.name == "nt":
            def search_extract_coro(query, returned_response_data: CommonResponseData):
                raw_data = ydl_extractor.extract_info(query, download=False)
                if cls.validate_basic_raw_data(raw_data):
                    returned_response_data.apply_values(CommonResponseData(PROVIDER, raw_data['id'], raw_data, 'search'))
                else:
                    returned_response_data = None
        else:
            def search_extract_coro(query: str, pipe_sender: Connection):
                raw_data = ydl_extractor.extract_info(query, download=False)
                if cls.validate_basic_raw_data(raw_data):
                    pipe_sender.send(CommonResponseData(PROVIDER, raw_data['id'], raw_data, 'search'))
                else:
                    pipe_sender.send(None)
                pipe_sender.close()


        request_data = await cls.__extract_info_async(f"ytsearch:{query}", search_extract_coro, user_update_coroutine, frequency_update, print_in_console)
        if request_data is None or request_data.is_empty_or_incomplete:
            return None
        logger.info(f"Retrieved info from search : {request_data}")
        search_result = YoutubeSearch(request_data.data)
        return search_result

    @classmethod
    async def get_data_async(cls, youtube_link: str, user_update_coroutine = None, frequency_update: float = DEFAULT_ASYNC_UPDATE_FREQ, print_in_console: bool = False) -> CommonResponseData:
        #extractor
        if os.name == "nt":
            def data_extract_coro(query, response_data: CommonResponseData):
                raw_data = ydl_extractor.extract_info(query, download=False)
                if cls.validate_basic_raw_data(raw_data):
                    response_data.apply_values(CommonResponseData(PROVIDER, raw_data['id'], raw_data, cls.infer_type_from_request_url(query)))
                else:
                    response_data = None
        else:
            def data_extract_coro(query: str, pipe_sender: Connection):
                raw_data = ydl_extractor.extract_info(query, download=False)
                if cls.validate_basic_raw_data(raw_data):
                    pipe_sender.send(CommonResponseData(PROVIDER, raw_data['id'], raw_data, cls.infer_type_from_request_url(query)))
                else:
                    pipe_sender.send(None)
                pipe_sender.close()


        return await cls.__extract_info_async(youtube_link, data_extract_coro, user_update_coroutine, frequency_update, print_in_console)







    @staticmethod
    def validate_basic_raw_data(raw_data):
        if raw_data is None or 'id' not in raw_data:
            return False
        return True

    @staticmethod
    def infer_type_from_request_url(url) -> str:
        query = url[len("https://"):].split('/')[1]
        first_part = query.split('?')[0]
        if first_part.startswith(("playlist")):
            return 'playlist'
        if first_part.startswith(("@", "channel")):
            return 'channel'
        return 'video'


    @classmethod
    def infer_response_object_type(cls, response_data) -> str | None:
        if '_type' in response_data:
            if 'modified_date' in response_data:
                return 'playlist'
            else:
                return 'search'
        else:
            return 'video'



    @classmethod
    def convert_to_youtube_video(cls, response_data: CommonResponseData) -> YoutubeVideo:
        if not cls.__is_correct_provider(response_data):
            logger.error(f"[YOUTUBE_API.ERR.convert_to_youtube_video] WRONG_PROVIDER : '{response_data.provider}' instead of '{PROVIDER}'")
            return None
        if cls.infer_response_object_type(response_data.data) != "video":
            logger.error(f"[YOUTUBE_API.ERR.convert_to_youtube_video] WRONG_TYPE : '{cls.infer_response_object_type(response_data.data)}' instead of 'video'")
            return None
        return YoutubeVideo(response_data.data)
    
    @classmethod
    def convert_to_youtube_playlist(cls, response_data: CommonResponseData) -> YoutubePlaylist:
        if not cls.__is_correct_provider(response_data):
            logger.error(f"[YOUTUBE_API.ERR.convert_to_youtube_playlist] WRONG_PROVIDER : '{response_data.provider}' instead of '{PROVIDER}'")
            return None
        if cls.infer_response_object_type(response_data.data) != "playlist":
            logger.error(f"[YOUTUBE_API.ERR.convert_to_youtube_playlist] WRONG_TYPE : '{cls.infer_response_object_type(response_data.data)}' instead of 'video'")
            return None
        try:
            yt_playlist: YoutubePlaylist = YoutubePlaylist(response_data.data)
            return yt_playlist
        except Exception as ex:
            number_of_data_keys: int = len(response_data.data)
            match number_of_data_keys:
                case 0:
                    err: str = "Error while creating youtube playlist object. No keys present in data."
                case _:
                    err: str = f"Error while creating youtube playlist object. {len(response_data.data)} key(s) present in data"
                    err += f"[{response_data.data[0]}"
                    if number_of_data_keys > 1:
                        for i in range(1, number_of_data_keys):
                            err += f", {response_data.data[i]}"
                    err +="]"
            logger.exception(f"{err}\n\n{traceback.format_exc()}")
            return None
    
    @classmethod
    def convert_to_youtube_search(cls, response_data: CommonResponseData) -> YoutubePlaylist:
        if not cls.__is_correct_provider(response_data):
            logger.error(f"[YOUTUBE_API.ERR.convert_to_youtube_search] WRONG_PROVIDER : '{response_data.provider}' instead of '{PROVIDER}'")
            return None
        if cls.infer_response_object_type(response_data.data) != "search":
            logger.error(f"[YOUTUBE_API.ERR.convert_to_youtube_search] WRONG_TYPE : '{cls.infer_response_object_type(response_data.data)}' instead of 'search'")
            return None
        return YoutubeSearch(response_data.data)



    #region Download

    async def download(video: YoutubeVideo):
        logger.info(f"[YOUTUBE.DOWNLOAD] Begin download for file {video.get_filename()} !")
        print_in_console = True
        frequency_update: float = 5 #how much time (in seconds) between prints in console

        start_time: float = time.time()
        last_update_time: float = start_time #last time the process has been checked
        time_since_last_update: float = frequency_update #used to calculate when to print

        if os.name == "nt": # 'nt' => Windows; Multiprocessing doesn't work similarly between Windows and Linux and causes problems that I don't want to deal with yet so I'm bringing back the old way for Windows
            download_process: Thread = Thread(target=ydl_downloader.download, args=[video.web_url])
        else:
            download_process: Process = Process(target=ydl_downloader.download, args=[video.web_url])
        download_process.start()

        while download_process.is_alive():
            delta_time = time.time() - last_update_time
            time_since_last_update += delta_time
            
            last_update_time = time.time()

            if time_since_last_update > frequency_update:
                time_since_last_update -= frequency_update
                if print_in_console:
                    logger.info(f"[YOUTUBE.DOWNLOAD.RUN] Downloading video with id '{video.id}'... (Elapsed : {(time.time() - start_time):4.2f} seconds)")
            await asyncio.sleep(0.1)

        # Check if file has been correctly downloaded
        if not os.path.isfile(config.downloadDirectory + video.get_filename()):
            logger.error(f"[YOUTUBE.DOWNLOAD] Download finished but file is not found !")
            return False
        logger.info(f"[YOUTUBE.DOWNLOAD] Download finished for file {video.get_filename()} !")
        return True
    
    

    #endregion



    @staticmethod
    def __is_correct_provider(response_data: CommonResponseData) -> bool:
        return response_data.provider == PROVIDER
    

#endregion






#region OTHER STREAMS

    async def link_download(link: str, raw_data):
        file_name = ydl_downloader.prepare_filename(raw_data)[len(config.downloadDirectory):]
        logger.info(f"[YOUTUBE.DOWNLOAD] Begin download for file {file_name} !")
        print_in_console = True
        frequency_update: float = 5 #how much time (in seconds) between prints in console

        start_time: float = time.time()
        last_update_time: float = start_time #last time the process has been checked
        time_since_last_update: float = frequency_update #used to calculate when to print

        if os.name == "nt": # 'nt' => Windows; Multiprocessing doesn't work similarly between Windows and Linux and causes problems that I don't want to deal with yet so I'm bringing back the old way for Windows
            download_process: Thread = Thread(target=ydl_downloader.download, args=[link])
        else:
            download_process: Process = Process(target=ydl_downloader.download, args=[link])
        download_process.start()

        while download_process.is_alive():
            delta_time = time.time() - last_update_time
            time_since_last_update += delta_time
            
            last_update_time = time.time()

            if time_since_last_update > frequency_update:
                time_since_last_update -= frequency_update
                if print_in_console:
                    logger.info(f"[YOUTUBE.DOWNLOAD.RUN] Downloading video with id '{raw_data['id']}'... (Elapsed : {(time.time() - start_time):4.2f} seconds)")
            await asyncio.sleep(0.1)

        # Check if file has been correctly downloaded
        if not os.path.isfile(config.downloadDirectory + file_name):
            logger.error(f"[YOUTUBE.DOWNLOAD] Download finished but file is not found !")
            return False, ""
        logger.info(f"[YOUTUBE.DOWNLOAD] Download finished for file {file_name} !")
        return True, file_name

#endregion
