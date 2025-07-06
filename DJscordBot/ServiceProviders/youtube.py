import time

import asyncio
from threading import Thread


import yt_dlp
#from youtubesearchpython.__future__ import VideosSearch


from DJscordBot.config import config
from DJscordBot.ServiceProviders.common import CommonResponseData

PLAYLIST_SIZE_LIMIT: int = 100
PROVIDER: str = 'youtube'
DEFAULT_ASYNC_UPDATE_FREQ: float = 2



# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda: ''

ydl_opts = {
    'format': 'bestaudio[format_note*=original]/bestaudio',
    'outtmpl': config.downloadDirectory + '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False,
    'verbose': False,
    'quiet': True,
    'no_warnings': True,
    'noprogress': True,
    'default_search': 'auto',
    # bind to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0'
}

ydl = yt_dlp.YoutubeDL(ydl_opts)
oldTime = 0







#region Youtube Objects

class YoutubeBaseObject():
    def __init__(self, request_data):
        self.id = request_data['id']
        self.name = request_data['title']

        self.type = YoutubeAPI.infer_response_object_type(request_data)
        
        self.url = request_data['original_url']
        self.web_url = request_data['webpage_url']
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
        return ydl.prepare_filename(self._raw_data)[len(config.downloadDirectory):]

    def __str__(self):
        return f"Vidéo youtube | titre: '{self.name}' | id: '{self.id}'"


class YoutubePlaylist(YoutubeBaseObject):
    def __init__(self, request_data):
        super().__init__(request_data)
        self.web_url = request_data['webpage_url']
        self.uploader = request_data['uploader']
        self.uploader_id = request_data['uploader_id']
        self.uploader_url = request_data['uploader_url']
        self.entries: list[YoutubeVideo] = []
        for entry in request_data['entries']:
            self.entries.append(YoutubeVideo(entry))
        


    def __str__(self):
        return f"Playlist youtube | titre: '{self.name}' | id: '{self.id}' | nombre d'entrées '{len(self.entries)}'"
    
class YoutubeSearch(YoutubeBaseObject):
    def __init__(self, request_data):
        super().__init__(request_data)
        self.entries: list[YoutubeBaseObject] = []

        data_entres = request_data['entries']
        print(f"entries length : {len(request_data['entries'])}")
        for i in range(0, min(PLAYLIST_SIZE_LIMIT, len(data_entres))):
            self.entries.append(YoutubeBaseObject(data_entres[i]))



    def __str__(self):
        return f"Recherche youtube | requête: '{self.name}' | nombre d'entrées: '{len(self.entries)}'"


#endregion





#region API Calls
class YoutubeAPI():
    @classmethod
    def search_sync(cls, query: str) -> YoutubeSearch:
        request_data = ydl.extract_info(f"ytsearch:{query}", download=False)
        return YoutubeSearch(request_data)

    @classmethod
    def get_data_sync(cls, youtube_url: str) -> CommonResponseData:
        request_data = ydl.extract_info(youtube_url, download=False)
        return CommonResponseData(PROVIDER, request_data['id'], request_data, cls.infer_type_from_request_url(youtube_url))
    


    @classmethod
    async def __extract_info_async(cls, query: str, extractor, user_update_coroutine = None, frequency_update: float = DEFAULT_ASYNC_UPDATE_FREQ, print_in_console: bool = False) -> CommonResponseData:
        response_data: CommonResponseData = CommonResponseData.get_empty()

        start_time: float = time.time()
        last_update_time: float = time.time()
        time_since_last_update: float = frequency_update 

        extract_thread: Thread = Thread(target=extractor, args=[query, response_data])
        extract_thread.start()

        while extract_thread.is_alive():
            delta_time = time.time() - last_update_time
            last_update_time = time.time()
            time_since_last_update += delta_time
            if time_since_last_update > frequency_update:
                time_since_last_update -= frequency_update
                if print_in_console:
                    print(f"[YOUTUBE.DATA.GET] awaiting response...\ttime elapsed:{(time.time() - start_time):4.2f}")
                if user_update_coroutine is not None:
                    time_elapsed = time.time() - start_time
                    await user_update_coroutine(time_elapsed)
            await asyncio.sleep(0.1)

        return response_data


    @classmethod
    async def search_async(cls, query: str, user_update_coroutine = None, frequency_update: int = DEFAULT_ASYNC_UPDATE_FREQ, print_in_console: bool = False) -> YoutubeSearch:
        def search_extract_coro(query, response_data: CommonResponseData):
            raw_data = ydl.extract_info(query, download=False)
            response_data.apply_values(CommonResponseData(PROVIDER, raw_data['id'], raw_data, 'search'))

        request_data = await cls.__extract_info_async(f"ytsearch:{query}", search_extract_coro, user_update_coroutine, frequency_update, print_in_console)
        search_result = YoutubeSearch(request_data.data)
        return search_result

    @classmethod
    async def get_data_async(cls, youtube_link: str, user_update_coroutine = None, frequency_update: float = DEFAULT_ASYNC_UPDATE_FREQ, print_in_console: bool = False) -> CommonResponseData:
        def data_extract_coro(query, response_data: CommonResponseData):
            raw_data = ydl.extract_info(query, download=False)
            response_data.apply_values(CommonResponseData(PROVIDER, raw_data['id'], raw_data, cls.infer_type_from_request_url(query)))
        
        return await cls.__extract_info_async(youtube_link, data_extract_coro, user_update_coroutine, frequency_update, print_in_console)


    

    


    


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
            print(f"[YOUTUBE_API.ERR.convert_to_youtube_video] WRONG_PROVIDER : '{response_data.provider}' instead of '{PROVIDER}'")
            return None
        if cls.infer_response_object_type(response_data.data) != "video":
            print(f"[YOUTUBE_API.ERR.convert_to_youtube_video] WRONG_TYPE : '{cls.infer_response_object_type(response_data.data)}' instead of 'video'")
            return None
        return YoutubeVideo(response_data.data)
    
    @classmethod
    def convert_to_youtube_playlist(cls, response_data: CommonResponseData) -> YoutubePlaylist:
        if not cls.__is_correct_provider(response_data):
            print(f"[YOUTUBE_API.ERR.convert_to_youtube_playlist] WRONG_PROVIDER : '{response_data.provider}' instead of '{PROVIDER}'")
            return None
        if cls.infer_response_object_type(response_data.data) != "playlist":
            print(f"[YOUTUBE_API.ERR.convert_to_youtube_playlist] WRONG_TYPE : '{cls.infer_response_object_type(response_data.data)}' instead of 'video'")
            return None
        return YoutubePlaylist(response_data.data)
    
    @classmethod
    def convert_to_youtube_search(cls, response_data: CommonResponseData) -> YoutubePlaylist:
        if not cls.__is_correct_provider(response_data):
            print(f"[YOUTUBE_API.ERR.convert_to_youtube_search] WRONG_PROVIDER : '{response_data.provider}' instead of '{PROVIDER}'")
            return None
        if cls.infer_response_object_type(response_data.data) != "search":
            print(f"[YOUTUBE_API.ERR.convert_to_youtube_search] WRONG_TYPE : '{cls.infer_response_object_type(response_data.data)}' instead of 'search'")
            return None
        return YoutubeSearch(response_data.data)



    #region Download
    #old method
    @classmethod #TODO try update hook
    async def __downloadAudio(cls, url, message, text: str, loop: asyncio.AbstractEventLoop):
        #ydl.add_progress_hook(lambda d: cls.downloadProgress(d, message, text, loop))
        await ydl.download(url)


    async def download(video: YoutubeVideo):
        # # if progress_hook is not None:
        # #     text = f"Téléchargement de **{video.name}**"
        # #     ydl.add_progress_hook(lambda download_data: progress_hook(download_data, loop, text))
        # ydl.download(video.web_url)


        # Added Thread to prevent locking the bot from responding to other commands
        frequency_update = 5
        print_in_console = True

        last_update_time: float = time.time()
        time_since_last_update: float = frequency_update 

        download_thread: Thread = Thread(target=ydl.download, args=[video.web_url])
        download_thread.start()

        while download_thread.is_alive():
            delta_time = time.time() - last_update_time
            last_update_time = time.time()
            time_since_last_update += delta_time
            if time_since_last_update > frequency_update:
                time_since_last_update -= frequency_update
                if print_in_console:
                    print(f"[YOUTUBE.DOWNLOAD.RUN] Downloading video with id '{video.id}'...")
                # if user_update_coroutine is not None:
                #     time_elapsed = time.time() - start_time
                #     await user_update_coroutine(time_elapsed)
            await asyncio.sleep(0.1)

        return

        
    

    # async def download_bulk(videos: list[YoutubeVideo], loop: asyncio.AbstractEventLoop, progress_hook, max_simultaneous_downloads = 4):
    #     pass

    #endregion



    @staticmethod
    def __is_correct_provider(response_data: CommonResponseData) -> bool:
        return response_data.provider == PROVIDER
    

#end region