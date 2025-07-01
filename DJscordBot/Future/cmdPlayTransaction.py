import os
import asyncio
import time

import traceback
import requests

from threading import Lock
from typing_extensions import Self


import discord

from DJscordBot.Managers.queueManager import QueueManager
from DJscordBot.ServiceProviders import youtube, spotify
from DJscordBot.Types.queue import Queue
from DJscordBot.config import config
from DJscordBot.Types.enums import PlayQueryType
from DJscordBot.Types.entry import Entry, EntryPlaylist
from DJscordBot.discord.utils import InteractionWrapper





BYPASS_SONG_LINK = False
PLAYLIST_LIMIT_ENTRIES = 30



class MusicPlayCommandTransaction():
    text_update_interval = 1
    playlist_lock: Lock = Lock()
    playlist_in_process: bool = False
    transaction_locking: Self = None

    def __init__(self, ctx: discord.ApplicationContext, bot: discord.Bot):
        self.ctx: discord.ApplicationContext = ctx
        self.response_wrapper: InteractionWrapper = InteractionWrapper(ctx)
        self.bot: discord.Bot = bot
        self.new_entries: list[Entry] = []
        self.start_transaction_time: float = time.time()
        self.finished = False
        pass

    
    def get_time_elapsed(self) -> float:
        return time.time() - self.start_transaction_time

    def get_time_elapsed_as_str(self) -> str:
        return f"{self.get_time_elapsed():00}"



    #region Playlist Lock


    @classmethod
    def __try_locking(cls, transaction: Self) -> bool:
        if cls.playlist_in_process == True:
            if cls.transaction_locking.finished: # prevent errors that didn't unlocked the playlist download
                print("WARN - [PLAYLIST.LOCK] completed transaction hasn't unlocked the playlist lock")
                cls.__unlock_playlist_download()
            else:
                return False
        if cls.playlist_in_process == False:
            with cls.playlist_lock:
                cls.playlist_in_process = True
                cls.transaction_locking = transaction
            return True
        else:
            return False
        
    @classmethod
    def __unlock_playlist_download(cls):
        with cls.playlist_lock:
            cls.playlist_in_process = False
            cls.transaction_locking = None


    async def __playlist_lock_mutex(self) -> tuple[bool, str]:
        pl_lock_result = self.__try_locking(self)

        # if MusicPlayCommandTransaction.playlist_lock.locked() or MusicPlayCommandTransaction.playlist_in_process:
        #     print(f"[YOUTUBE.PLAYLIST.DOWNLOAD] A playlist is already being processed (GID:{self.response_wrapper.guild_ID})")
        #     return (False, f":warning: Une Playlist est en cours de téléchargement, veuillez réessayer après la fin de celle en cours")

        # with self.playlist_lock:
        #     MusicPlayCommandTransaction.playlist_in_process = True
        if pl_lock_result:
            await self.response_wrapper.send_message_in_author_channel(f"L'ajout d'une playlist vient d'être initié par {self.ctx.author.nick} !\n"
                                                                       + "-# Pour en ajouter une autre, vous devrez attendre la fin de celle-ci")
            return (True, "")
        else:
            return (False, f":warning: Une Playlist est en cours de téléchargement, veuillez réessayer après la fin de celle en cours")

    #endregion



    #region Main Process
    async def process_query(self, query: str):
        await self.__init_process(query)
        self.finished = True


    async def __init_process(self, query: str):
        # pre sanitisation
        if query.startswith("www."):
            query = "https://" + query

        query_type: PlayQueryType = self.__get_query_type(query)

        match query_type:
            case PlayQueryType.LINK_SPOTIFY:
                if not config.spotifyEnabled:
                    print(f"[SPOTIFY.DISABLED] Spotify research is disabled (GID:{self.ctx.guild.id})")
                    self.finished = True
                    return await self.response_wrapper.whisper_to_author(":warning: La recherche Spotify n'est pas activée")
                return await self.__spt_process_link(query)
                


            case PlayQueryType.LINK_YOUTUBE:
                print(f"[QUERY.PROCESS.YOUTUBE.LINK] begin process of youtube link \"{query}\" (GID:{self.response_wrapper.guild_id})")

                link_type: str = youtube.YoutubeAPI.infer_type_from_request_url(query)
                # Personalize message
                match link_type:
                    case 'channel':
                        return await self.response_wrapper.whisper_to_author(f":warning: Le lien trouvé correspond à une chaine, ce qui n'est pas pris en charge")
                    
                    case 'playlist':
                        if self.playlist_lock.locked() or self.playlist_in_process:
                            return await self.response_wrapper.whisper_to_author(f":warning: Une Playlist est en cours de téléchargement, veuillez réessayer après la fin de celle en cours")
                        await self.response_wrapper.whisper_to_author(f"- Investigation sur la playlist : `{query}`\n-# (L'opération peut prendre du temps... (40+ secondes))")
                    
                    case _:
                        await self.response_wrapper.whisper_to_author(f"- Investigation sur la vidéo : `{query}`")

                result: youtube.CommonResponseData = await youtube.YoutubeAPI.get_data_async(query, self.__retrieve_data_feedback)

                if result is None:
                    print(f"[YOUTUBE.ERROR] link check failed\n\n{traceback.format_exc()} | (GID:{self.response_wrapper.guild_id})")
                    return await self.response_wrapper.whisper_to_author(":warning: Une erreur est survenue lors de la vérification du lien")
                
                print(f"[YOUTUBE.SUCCESS] found link \"{(result.data['webpage_url'])}\" | (GID:{self.response_wrapper.guild_id})")
                return await self.__yt_process_response_data(result)



            case PlayQueryType.SEARCH_QUERY:
                print(f"[QUERY.PROCESS.SEARCH] begin youtube search with query: \"{query}\" (GID:{self.response_wrapper.guild_id})")
        
                await self.response_wrapper.append_to_last_whisper(f"- Recherche de `{query}`", True)
                
                search_results: youtube.YoutubeSearch = await youtube.YoutubeAPI.search_async(query, self.__retrieve_data_feedback)
                if search_results is None:
                    return await self.response_wrapper.whisper_to_author(":warning: La recherche a echoué")
                
                yt_video: youtube.YoutubeVideo = None
                for search_entry in search_results.entries:
                    if search_entry.type == 'video':
                        yt_video = youtube.YoutubeVideo(search_entry._raw_data)
                        if yt_video is not None:
                            break

                if yt_video is None:
                    return await self.response_wrapper.whisper_to_author(f":warning: La recherche n'a pas permis de trouver une vidéo `{query}`")
                
                await self.response_wrapper.append_to_last_whisper(f"- Informations reçues sur la video **{yt_video.name}**\n- Téléchargement...", True)

                entry: Entry = self.__yt_prepare_video_entry(yt_video)
                (download_success, download_result_message) = await self.__yt_download_video_final(entry, yt_video)
                
                if download_success:
                    print(f"[PLAY.TRANSACTION.SUCCESS] '{yt_video.id}' has been added to queue")
                    return await self.response_wrapper.whisper_to_author(f"{download_result_message}\n{self.__get_processing_time()}")
                else:
                    return await self.response_wrapper.whisper_to_author(f"{download_result_message}")
            


            case PlayQueryType.OTHER_STREAM:
                return await self.response_wrapper.whisper_to_author(":warning: Cette fonctionnalité n'est pas encore ré-implémentée")


    #endregion


    







    #region Helpers
    def __get_query_type(self, query: str) -> PlayQueryType:
        if query.startswith(("spotify:", "https://open.spotify.com/")):
            return PlayQueryType.LINK_SPOTIFY
        if query.startswith(("https://youtu.be", "https://www.youtube.com", "https://youtube.com")):
            return PlayQueryType.LINK_YOUTUBE
        if query.startswith(("http://", "https://", "udp://")):
            return PlayQueryType.OTHER_STREAM
        return PlayQueryType.SEARCH_QUERY
    
    def __get_queue_from_ctx(self) -> Queue | None:
        return QueueManager.get_queue(self.ctx.guild.id)
    
    def __get_processing_time(self) -> str:
        return f"-# Durée du traitement de la requète : {time.time() - self.start_transaction_time:4.2f} s"
    
    async def __retrieve_data_feedback(self, time_elapsed):
        await self.response_wrapper.append_to_last_whisper(f"-# En attente de la réponse de youtube...  {int(time_elapsed)} secondes", new_line=True, save_edit=False)
    
    #end region






    #TODO Handle live feeds

    #region Youtube related        
    
    async def __yt_process_response_data(self, response_data: youtube.CommonResponseData):
        type = youtube.YoutubeAPI.infer_response_object_type(response_data.data)

        match type:
            case 'video':
                yt_video: youtube.YoutubeVideo = youtube.YoutubeAPI.convert_to_youtube_video(response_data)
                if yt_video is None:
                    print(f"[YOUTUBE.VIDEO.CONVERSION_ERROR] Converstion has returned None")
                    return await self.response_wrapper.whisper_to_author(f":warning: Une erreur interne est survenue lors de l'analyse de la vidéo youtube")
                
                await self.response_wrapper.append_to_last_whisper(f"- Informations reçues sur la video **{yt_video.name}**\n- Téléchargement...", True)

                entry: Entry = self.__yt_prepare_video_entry(yt_video)
                (download_success, download_result_message) = await self.__yt_download_video_final(entry, yt_video)
                
                if download_success:
                    print(f"[PLAY.TRANSACTION.SUCCESS] '{yt_video.id}' has been added to queue")
                    return await self.response_wrapper.whisper_to_author(f"{download_result_message}\n{self.__get_processing_time()}")
                else:
                    return await self.response_wrapper.whisper_to_author(f"{download_result_message}")


            case 'playlist':
                yt_playlist: youtube.YoutubePlaylist = youtube.YoutubeAPI.convert_to_youtube_playlist(response_data)

                if yt_playlist is None:
                    print(f"[YOUTUBE.PLAYLIST.CONVERSION_ERROR] Converstion has returned None ({response_data})")
                    return await self.response_wrapper.whisper_to_author(f":warning: Une erreur interne est survenue lors de l'analyse de la playlist youtube")
                
                entries: list[Entry] = self.__yt_prepare_playlist_entries(yt_playlist)
                if len(entries) != len(yt_playlist.entries):
                    return await self.response_wrapper.whisper_to_author(f":warning: Une erreur interne est survenue lors de l'analyse de la playlist youtube")

                await self.response_wrapper.append_to_last_whisper(f"- Informations reçues sur la playlist **{yt_playlist.name}**", True)

                    
                if MusicPlayCommandTransaction.playlist_lock.locked():
                    return await self.response_wrapper.whisper_to_author(f":warning: Une Playlist est en cours de téléchargement, veuillez réessayer après la fin de celle en cours")
                else:
                    with MusicPlayCommandTransaction.playlist_lock:

                        await self.response_wrapper.send_message_in_author_channel(f"L'ajout d'une playlist vient d'être initié par {self.ctx.author.nick} !\n-# Pour en ajouter une autre, vous devrez attendre la fin de celle-ci")


                        # actual download
                        await self.response_wrapper.append_to_last_whisper(f"- Téléchargement de la playlist (nombre d'entrées : {len(entries)}): \n-# (Le téléchargement est limité à {PLAYLIST_LIMIT_ENTRIES} entrées réussies)", True)
                        
                        (download_success, result_dict) = await self.__yt_download_playlist_final(entries, yt_playlist)
                        
                        if download_success:
                            # await self.response_wrapper.whisper_to_author(f"Téléchargement effectué !\n{self.__get_processing_time()}")
                            
                            if result_dict['success'] <= 0:
                                await self.response_wrapper.whisper_to_author(f"Je n'ai pas réussi à télécharger une seule musique de la playlist :(\n{self.__get_processing_time()}")
                            if result_dict['failed'] > 0:
                                await self.response_wrapper.whisper_to_author(f"Playlist téléchargée avec quelques échecs...\n{self.__get_processing_time()}")
                            else:
                                await self.response_wrapper.whisper_to_author(f"Playlist téléchargée avec succès !\n{self.__get_processing_time()}")

                            await self.response_wrapper.send_message_in_author_channel("Téléchargement de la playlist complété\n-# Vous pouvez démarrer le téléchargement d'une playlist")
                        else:
                            await self.response_wrapper.whisper_to_author(f":warning: Téléchargement annulé !")
                            await self.response_wrapper.send_message_in_author_channel(f"Téléchargement annulé\n-# Vous pouvez démarrer le téléchargement d'une playlist")
                    return





                # (init_success, init_error_message) = await self.__playlist_lock_mutex()
                # if init_success:
                #     # actual download
                #     await self.response_wrapper.append_to_last_whisper(f"- Téléchargement de la playlist (nombre d'entrées : {len(entries)}): \n-# (Le téléchargement est limité à {PLAYLIST_LIMIT_ENTRIES} entrées réussies)", True)
                    
                #     (download_success, result_dict) = await self.__yt_download_playlist_final(entries, yt_playlist)
                    
                #     if download_success:
                #         # await self.response_wrapper.whisper_to_author(f"Téléchargement effectué !\n{self.__get_processing_time()}")
                #         if result_dict['success'] <= 0:
                #             await self.response_wrapper.whisper_to_author(f"Je n'ai pas réussi à télécharger une seule musique de la playlist :(\n{self.__get_processing_time()}")
                #         if result_dict['failed'] > 0:
                #             await self.response_wrapper.whisper_to_author(f"Playlist téléchargée avec quelques échecs...\n{self.__get_processing_time()}")
                #         await self.response_wrapper.whisper_to_author(f"Playlist téléchargée avec succès !\n{self.__get_processing_time()}")
                #         self.__unlock_playlist_download()
                #         return await self.response_wrapper.send_message_in_author_channel("Téléchargement de la playlist complété\n-# Vous pouvez démarrer le téléchargement d'une playlist")
                #     else:
                #         return await self.__yt_download_playlist_canceled()
                
                # else:
                #     await self.response_wrapper.whisper_to_author(f"{init_error_message}")



            case _:
                return await self.response_wrapper.whisper_to_author(f"Kaboom :boom:")




    #region Download

    async def __yt_download_video_final(self, entry: Entry, yt_video: youtube.YoutubeVideo) -> tuple[bool, str]:
        
            if await self.__yt_download_single_video(yt_video):
                queue: Queue = self.__get_queue_from_ctx()
                if queue is None:
                    print("[YOUTUBE.DOWNLOAD.REMOVED_QUEUE] Downloaded video but the queue has been removed while downloading")
                    return (False, f":warning: Téléchargement de {entry.title} mais entre temps la liste de lecture a été supprimée")
                
                filename = yt_video.get_filename()
                try:
                    file_size = os.path.getsize(config.downloadDirectory + filename)
                except:
                    print("[YOUTUBE.DOWNLOAD.FILE_SIZE.ERROR] trying to find a file that doesn't exist")
                    return (False, f":warning: Erreur lors du téléchargement de {entry.title}")
                entry.map_to_file(filename, yt_video.duration, file_size)
                position = await queue.add_entry(entry)
                print(f"[YOUTUBE.PROCESS.SUCCESS] title:{entry.title} | youtube.id:{yt_video.id} has been added to queue")
                return (True, f"[{position}] **{entry.title}** a été ajouté à la file d'attente")
                #return await self.response_wrapper.whisper_to_author(f"[{position}] **{yt_video.name}** a été ajouté à la file d'attente\n{self.__get_processing_time()}")
            else:
                return (False, f":warning: Erreur lors du téléchargement de {entry.title}")
                #return await self.response_wrapper.whisper_to_author(f":warning: Erreur lors du téléchargement de {yt_video.name}")
        


        

    async def __yt_download_playlist_final(self, queue_entries: list[Entry], yt_playlist: youtube.YoutubePlaylist) -> tuple[bool, dict]:
        queue: Queue = self.__get_queue_from_ctx()
        start_queue_position: int = queue.size
        number_of_entries: int = len(yt_playlist.entries)
        success: int = 0
        failed: int = 0

        for i in range(number_of_entries):
            
            #Check connection
            if not queue.is_connected():
                return False

            if success >= PLAYLIST_LIMIT_ENTRIES:
                break
            
            entry: Entry = queue_entries[i]
            pl_yt_video: youtube.YoutubeVideo = yt_playlist.entries[i]
            
            #video checks
            if pl_yt_video is None:
                print(f"[YOUTUBE.PLAYLIST.VIDEO.CONVERSION_ERROR] Converstion has returned None, ignoring")
                failed += 1
                continue
            
            if pl_yt_video.is_live:
                print(f"[YOUTUBE.PLAYLIST.VIDEO.CONVERSION_ERROR] video is live, ignoring")
                failed += 1
                continue

            await self.response_wrapper.append_to_last_whisper(f"Téléchargement de **{pl_yt_video.name}**\n[réussi: {success}/échec: {failed}/total: {number_of_entries}]", True, False)

            (result, result_message) = await self.__yt_download_video_final(entry, pl_yt_video)
            if result:
                print(f"[PLAY.TRANSACTION.SUCCESS] '{pl_yt_video.id}' has been added to queue")
                success += 1
                continue
            else:
                print(f"[YOUTUBE.PLAYLIST.VIDEO.DOWNLOAD.ERROR] unable to download {pl_yt_video.name} (GID:{self.response_wrapper.guild_id})")
                failed += 1
                continue
        
        results_dict = {'success': success, 'failed': failed}

        return (True, results_dict)

    async def __yt_download_playlist_canceled(self):
        MusicPlayCommandTransaction.playlist_in_process = False
        await self.response_wrapper.whisper_to_author(f":warning: Téléchargement annulé !")
        await self.response_wrapper.send_message_in_author_channel(f"Téléchargement annulé\n-# Vous pouvez démarrer le téléchargement d'une playlist")
        return
    






    async def __yt_download_single_video(self, yt_video: youtube.YoutubeVideo) -> bool:
        # await self.response_wrapper.append_to_last_whisper(f"- Informations reçues sur la video **{yt_video.name}**", True)

        if yt_video.is_live:
            print("[YOUTUBE.VIDEO.DOWNLOAD.ERROR] Attempting to download a live, aborted")
            return False
            #return await self.response_wrapper.whisper_to_author(f"Les vidéos live ne sont pas disponible pour le moment...")
        #Download attempt
        try:
            #await self.response_wrapper.append_to_last_whisper(f"- Téléchargement de la video **{yt_video.name}**...", True)
            await youtube.YoutubeAPI.download(yt_video)
            print(f"[YOUTUBE.VIDEO.DOWNLOAD] Download success")
            return True
        except Exception as ex:
            print(f"[YOUTUBE.VIDEO.DOWNLOAD.ERROR] unable to download {yt_video.name} | (GID:{self.response_wrapper.guild_id})\n\n{ex}")
            return False
    

    

    #endregion

    

    #region entry

    def __yt_prepare_video_entry(self, yt_video: youtube.YoutubeVideo) -> Entry:
        entry: Entry = Entry(yt_video.name, self.ctx.author, yt_video.web_url)
        entry.add_description(self.__yt_build_entry_description(yt_video))
        entry.add_image(yt_video.thumbnail)
        return entry


    def __yt_prepare_playlist_entries(self, yt_playlist: youtube.YoutubePlaylist) -> list[Entry]:
        playlist: EntryPlaylist = EntryPlaylist(yt_playlist.id, yt_playlist.name, yt_playlist.uploader, 'playlist', yt_playlist.web_url)
        entries: list[Entry] = []
        for video in yt_playlist.entries:
            new_entry: Entry = Entry(video.name, self.ctx.author, video.web_url)
            new_entry.add_description(self.__yt_build_entry_description(video))
            new_entry.add_image(video.thumbnail)
            new_entry.set_playlist(playlist)
            entries.append(new_entry)

        return entries
    

    def __yt_build_entry_description(self, yt_video: youtube.YoutubeVideo):
        description = f"- Chaîne : [{yt_video.channel}]({yt_video.channel_url}) | ({yt_video.channel_follower_count} abonnés)\n" \
        + f"- {(yt_video.view_count)} vues | {yt_video.like_count} likes\n" \
        + f"-# source: Youtube"
        return description

    #endregion




    #endregion









    #region Spotify Related
    async def __spt_process_link(self, spotify_link):
        await self.response_wrapper.whisper_to_author(f"- Investigation sur `{spotify_link}`...\n- Récupération des données auprès de Spotify...")
        spt_data: spotify.CommonResponseData = spotify.SpotifyAPI.sanitise_link_and_get_data(spotify_link)
        


        match spt_data.inferred_type:

            #region Track
            case 'track':
                spt_track: spotify.SpotifyTrack = spotify.SpotifyAPI.convert_to_track(spt_data)
                if spt_track is None:
                    print(f"[SPOTIFY.TRACK.CONVERSION_ERROR] Converstion has returned None ({spt_data})")
                    return await self.response_wrapper.whisper_to_author("Une erreure interne est survenue lors de l'analyse du titre :(")
                
                spt_entry = self.__spt_prepare_track_entry(spt_track)
                await self.response_wrapper.append_to_last_whisper(f"Morceau trouvé : {spt_track.get_title_response()}\n- Tentative de récupération du lien youtube...", True)

                song_link_failed_message = "" # Storing error message to skip one request to the discord API

                #retrieving the associated youtube video
                if not BYPASS_SONG_LINK:
                    (result, result_message, responseData) = await self.__spt_song_link_try_get_response_data(spt_track)
                    if result:
                        spt_yt_video: youtube.YoutubeVideo = youtube.YoutubeAPI.convert_to_youtube_video(responseData)
                        if spt_yt_video is None:
                            print(f"[SPT_YT.VIDEO.CONVERSION_ERROR] None response from youtube")
                            song_link_failed_message = "Tentative échouée !"
                        else:
                            await self.response_wrapper.append_to_last_whisper(f"Succès !\n- Téléchargement...", True)
                    
                            #All good, continue
                            (dl_result, dl_result_message) = await self.__yt_download_video_final(spt_entry, spt_yt_video)
                            if dl_result:
                                print(f"[PLAY.TRANSACTION.SUCCESS] '{spt_track.name}|{spt_track.id}' has been added to queue")
                                return await self.response_wrapper.whisper_to_author(f"{dl_result_message}\n{self.__get_processing_time()}")
                            else:
                                print(f"[SPT_YT.VIDEO.DOWNLOAD_ERROR] Conversion has returned None")
                                song_link_failed_message = f"Erreur lors du téléchargement via le lien !"
                    else:
                        song_link_failed_message = result_message
                        
                    
                
                # Fallback youtube search
                search_query = spt_track.get_yt_search_query()
                await self.response_wrapper.append_to_last_whisper(f"{song_link_failed_message}\n- Recherche youtube de `{search_query}`...", True)
                
                search_results: youtube.YoutubeSearch = youtube.YoutubeAPI.search_sync(search_query)
                if search_results is None:
                    return await self.response_wrapper.whisper_to_author(":warning: La recherche a echoué")
                
                spt_yt_video: youtube.YoutubeVideo = None
                for search_entry in search_results.entries:
                    if search_entry.type == 'video':
                        spt_yt_video = youtube.YoutubeVideo(search_entry._raw_data)
                        if spt_yt_video is not None:
                            break

                if spt_yt_video is None:
                    return await self.response_wrapper.whisper_to_author(f":warning: La recherche n'a pas permis de trouver une vidéo `{search_query}`")
                
                await self.response_wrapper.append_to_last_whisper(f"Succès !\n- Téléchargement...", True)

                (result, result_message) = await self.__yt_download_video_final(spt_entry, spt_yt_video)
                if result:
                    print(f"[PLAY.TRANSACTION.SUCCESS] '{spt_track.name}|{spt_track.id}' has been added to queue")
                    return await self.response_wrapper.whisper_to_author(f"{result_message}\n{self.__get_processing_time()}")
                else:
                    print(f"[SPT_YT.VIDEO.DOWNLOAD_ERROR] Converstion has returned None")
                    return await self.response_wrapper.whisper_to_author(f":warning: Erreur lors du téléchargement de la vidéo associée à la musique {spt_track.name}")


            #endregion





            #region Album
            case 'album':
                spt_album: spotify.SpotifyAlbum = spotify.SpotifyAPI.convert_to_album(spt_data)
                if spt_album is None:
                    print(f"[SPOTIFY.TRACK.CONVERSION_ERROR] Converstion has returned None ({spt_data})")
                    return await self.response_wrapper.whisper_to_author("Une erreure interne est survenue lors de l'analyse de l'album :(")

                if self.playlist_lock.locked() or self.playlist_in_process:
                    return await self.response_wrapper.whisper_to_author(f":warning: Une playlist (ou un album spotify) est en cours de téléchargement, veuillez réessayer après la fin de celle en cours")
                
                
                await self.response_wrapper.append_to_last_whisper(f"{spt_album.album_type.capitalize()} trouvé : {spt_album.name}\n- Tentative de récupération du lien youtube...", True)
                
                spt_ab_entries: list[Entry] = self.__spt_prepare_album_entries(spt_album)

                if not BYPASS_SONG_LINK:
                    (result, result_message, responseData) = await self.__spt_song_link_try_get_response_data(spt_album)
                    if result:
                        yt_playlist: youtube.YoutubePlaylist = youtube.YoutubeAPI.convert_to_youtube_playlist(responseData)
                        if yt_playlist is None:
                            print(f"[SPT_YT.VIDEO.CONVERSION_ERROR] None response from youtube")
                            song_link_failed_message = "Tentative échouée !"
                        else:
                            # playlist found
                            if len(spt_ab_entries) != len(spt_album.tracks) != len(yt_playlist.entries):
                                return await self.response_wrapper.whisper_to_author(f":warning: Une erreur interne est survenue lors de l'analyse de la playlist associée")

                            await self.response_wrapper.append_to_last_whisper(f"Succès !\n- Informations reçues sur la playlist **{yt_playlist.name}**", True)

                            (init_success, init_error_message) = await self.__playlist_lock_mutex()
                            if init_success:
                                # actual download
                                if len(spt_ab_entries) > PLAYLIST_LIMIT_ENTRIES:
                                    await self.response_wrapper.append_to_last_whisper(f"- Téléchargement de l'album...\n-# (Le téléchargement est limité à {PLAYLIST_LIMIT_ENTRIES} entrées réussies)", True)
                                else:
                                    await self.response_wrapper.append_to_last_whisper(f"- Téléchargement de l'album...", True)



                                (download_success, result_dict) = await self.__yt_download_playlist_final(spt_ab_entries, yt_playlist)
                    
                                if download_success:
                                    # await self.response_wrapper.whisper_to_author(f"Téléchargement effectué !\n{self.__get_processing_time()}")
                                    if result_dict['success'] <= 0:
                                        await self.response_wrapper.whisper_to_author(f"Je n'ai pas réussi à télécharger une seule musique de la playlist :(\n{self.__get_processing_time()}")
                                    if result_dict['failed'] > 0:
                                        await self.response_wrapper.whisper_to_author(f"Playlist téléchargée avec quelques échecs...\n{self.__get_processing_time()}")
                                    await self.response_wrapper.whisper_to_author(f"Playlist téléchargée avec succès !\n{self.__get_processing_time()}")
                                    self.__unlock_playlist_download()
                                    return await self.response_wrapper.send_message_in_author_channel("Téléchargement de la playlist complété\n-# Vous pouvez démarrer le téléchargement d'une playlist")
                                else:
                                    return await self.__yt_download_playlist_canceled()
                            else:
                                # return await self.response_wrapper.whisper_to_author(f"{init_error_message}")
                                pass
                
                # bruteforce
                number_of_entries = len(spt_ab_entries)
                queue: Queue = self.__get_queue_from_ctx()
                number_of_entries: int = len(spt_album.tracks)
                success: int = 0
                failed: int = 0

                for i in range(number_of_entries):
                    
                    #Check connection
                    if not queue.is_connected():
                        return False

                    if success >= PLAYLIST_LIMIT_ENTRIES:
                        break
                    

                    spt_entry: Entry = spt_ab_entries[i]
                    spt_track: spotify.SpotifyTrack = spt_album.tracks[i]
                    if await self.__spt_playlist_download_track(spt_entry, spt_track, success, failed, number_of_entries):
                        success += 1
                        continue
                    else:
                        failed += 1
                        continue

                    
            

            #endregion





            #region Playlist
            case 'playlist':
                spt_playlist: spotify.SpotifyPlaylist = spotify.SpotifyAPI.convert_to_playlist(spt_data)
                if spt_playlist is None:
                    print(f"[SPOTIFY.TRACK.CONVERSION_ERROR] Converstion has returned None ({spt_data})")
                    return await self.response_wrapper.whisper_to_author("Une erreure interne est survenue lors de l'analyse de l'album :(")
                
                spt_pl_entries: list[Entry] = self.__spt_prepare_playlist_entries(spt_playlist)



                (init_success, init_error_message) = await self.__playlist_lock_mutex()


                if init_success:
                    # await self.response_wrapper.append_to_last_whisper(f"Playlist trouvée : {spt_playlist.name}", True)
                    # actual download
                    await self.response_wrapper.append_to_last_whisper(f"Playlist trouvée : {spt_playlist.name}\n- Téléchargement de la playlist (nombre total d'entrées : {len(spt_pl_entries)}): \n-# (Le téléchargement est limité à {PLAYLIST_LIMIT_ENTRIES} entrées réussies)", True)
                    (download_success, resutl_dict) = await self.__yt_download_playlist_final(spt_pl_entries, yt_playlist)
                    if download_success:
                        # await self.response_wrapper.whisper_to_author(f"Téléchargement effectué !\n{self.__get_processing_time()}")
                        if result_dict['success'] <= 0:
                            await self.response_wrapper.whisper_to_author(f"Je n'ai pas réussi à télécharger une seule musique de la playlist :(\n{self.__get_processing_time()}")
                        if result_dict['failed'] > 0:
                            await self.response_wrapper.whisper_to_author(f"Playlist téléchargée avec quelques échecs...\n{self.__get_processing_time()}")
                        await self.response_wrapper.whisper_to_author(f"Playlist téléchargée avec succès !\n{self.__get_processing_time()}")
                        self.__unlock_playlist_download()
                        return await self.response_wrapper.send_message_in_author_channel("Téléchargement de la playlist complété\n-# Vous pouvez démarrer le téléchargement d'une playlist")
                    else:
                        return await self.__yt_download_playlist_canceled()
                else:
                    await self.response_wrapper.whisper_to_author(f"{init_error_message}")
                
                


                

                # number_of_entries = len(spt_ab_entries)
                # queue: Queue = self.__get_queue_from_ctx()
                # number_of_entries: int = len(spt_playlist.tracks)
                # success: int = 0
                # failed: int = 0

                # for i in range(number_of_entries):
                    
                #     #Check connection
                #     if not queue.is_connected():
                #         return False

                #     if success >= PLAYLIST_LIMIT_ENTRIES:
                #         break
                    

                #     spt_entry: Entry = spt_ab_entries[i]
                #     spt_track: spotify.SpotifyTrack = spt_playlist.tracks[i]
                #     if await self.__spt_playlist_download_track(spt_entry, spt_track, success, failed, number_of_entries):
                #         success += 1
                #         continue
                #     else:
                #         failed += 1
                #         continue
            
                

            #endregion
            


            # Will not be implemented in the forseeable future
            case 'artist':
                print(f"[SPOTIFY.ARTIST_NOT_HANDLED] Spotify artists are not processed by this application\tspotify_link : ({spotify_link})")
                return await self.response_wrapper.whisper_to_author(':warning: Je ne prends pas en charge les pages artistes')
            

            case _:
                print(f"[SPOTIFY.UNHANDLED] type \"{spt_data.inferred_type}\" is not handled by this application\tspotify_link : ({spotify_link})")
                return await self.response_wrapper.whisper_to_author(':warning: Une erreur est survenue, vérifier bien que le lien spotify dirige vers une musique')







    async def __spt_playlist_download_track(self, entry: Entry, track: spotify.SpotifyTrack, success_status: int, failed_status: int, number_of_entries:int):
        await self.response_wrapper.append_to_last_whisper(f"Recherche de `{track.get_yt_search_query()}`\n[réussi: {success_status}/échec: {failed_status}/total: {number_of_entries}]", True, False)
        spt_search: youtube.YoutubeSearch = await youtube.YoutubeAPI.search_async(track.get_yt_search_query())
        if spt_search is None:
            print(f"[SPOTIFY.ALBUM.TRACK.SEARCH.ERROR] API returned None")
            return False
            
        spt_pl_yt_video: youtube.YoutubeVideo = None
        for search_entry in spt_search.entries:
            print(f"type:{search_entry.type}")
            if search_entry.type == 'video':
                yt_video = youtube.YoutubeVideo(search_entry._raw_data)
                if yt_video is not None:
                    break
        
        #video checks
        if spt_pl_yt_video is None:
            print(f"[YOUTUBE.PLAYLIST.VIDEO.CONVERSION_ERROR] Converstion has returned None, ignoring")
            return False

        if spt_pl_yt_video.is_live:
            print(f"[YOUTUBE.PLAYLIST.VIDEO.CONVERSION_ERROR] video is live, ignoring")
            return False

        await self.response_wrapper.append_to_last_whisper(f"Téléchargement de '{spt_pl_yt_video.name}'\n[réussi: {success_status}/échec: {failed_status}/total: {number_of_entries}]", True, False)

        (result, result_message) = await self.__yt_download_video_final(entry, spt_pl_yt_video)
        if result:
            print(f"[PLAY.TRANSACTION.SUCCESS] '{spt_pl_yt_video.id}' has been added to queue")
            return True
        else:
            print(f"[YOUTUBE.PLAYLIST.VIDEO.DOWNLOAD.ERROR] unable to download {spt_pl_yt_video.name} (GID:{self.response_wrapper.guild_id})")
            return False




    #region song.link
    def __spt_song_link_try_convert(self, spt_item: spotify.SpotifyBaseObject) -> str:
        try:
            print(f"[SPOTIFY.CONVERT_YT] attempting song.link conversion\nspotify_url : ({spt_item.web_url})")
            songLinkResp: requests.Response = requests.get(f"https://api.song.link/v1-alpha.1/links?url=spotify%3A{spt_item.type}%3A{spt_item.id}&userCountry=FR")
            songLinkData = songLinkResp.json()
            return songLinkData['linksByPlatform']['youtube']['url']
        except Exception as ex:
            print(f"[SPOTIFY.CONVERT_YT.ERROR] an error occured while converting with song.link..."
                + f"falling back to lazy youtube search\nspotify_url : ({spt_item.web_url})\n"
                + f"{ex}")
            return None



    async def __spt_song_link_try_get_response_data(self, spt_item: spotify.SpotifyBaseObject) -> tuple[bool, str, youtube.CommonResponseData]:
        yt_link = self.__spt_song_link_try_convert(spt_item)
        if yt_link is None:
            print(f"[SPT_YT.VIDEO.CONVERSION_ERROR] Conversion has failed None")
            return (False, "Tentative échouée !", None)
        
        yt_data: youtube.CommonResponseData = await youtube.YoutubeAPI.get_data_async(yt_link, self.__retrieve_data_feedback)
        if yt_data is None:
            print(f"[SPT_YT.VIDEO.CONVERSION_ERROR] Converted link has returned None")
            return (False, "Tentative échouée !", None)

        return (True, "Succès !", yt_data)
    

    #endregion




        
    #region Spotify Entry
    def __spt_prepare_track_entry(self, spt_track: spotify.SpotifyTrack) -> Entry:
        new_entry: Entry = Entry(spt_track.name, self.ctx.author, spt_track.web_url)
        new_entry.add_image(spt_track.album.image)
        new_entry.add_description(self.__spt_build_entry_description_track(spt_track))

        return new_entry


    def __spt_prepare_album_entries(self, spt_album: spotify.SpotifyAlbum) -> list[Entry]:
        playlist: EntryPlaylist = EntryPlaylist(spt_album.id, spt_album.name, spt_album, 'album', spt_album.web_url)
        entries: list[Entry] = []

        for track in spt_album.tracks:
            new_entry: Entry = Entry(track.name, self.ctx.author, track.web_url)
            new_entry.add_image(spt_album.image)
            new_entry.set_playlist(playlist)
            new_entry.add_description(self.__spt_build_entry_description_album_track(track, spt_album))
            entries.append(new_entry)

        return entries
    

    def __spt_prepare_playlist_entries(self, spt_playlist: spotify.SpotifyPlaylist) -> list[Entry]:
        playlist: EntryPlaylist = EntryPlaylist(spt_playlist.id, spt_playlist.name, spt_playlist.owner, 'album', spt_playlist.web_url)
        entries: list[Entry] = []
        for track in spt_playlist.tracks:
            new_entry: Entry = Entry(track.name, self.ctx.author, track.web_url)
            new_entry.set_playlist(playlist)
            new_entry.add_image(spt_playlist.image)
            new_entry.add_description(self.__spt_build_entry_description_track(track))
            entries.append(new_entry)

        return entries


    def __spt_build_entry_description_track(self, spt_track: spotify.SpotifyTrack):
        description = f"{spt_track.album.album_type.capitalize()} : [{spt_track.album.name}]({spt_track.album.web_url})\n" # Album
        description += f"Artiste : [{spt_track.artists[0].name}]({spt_track.artists[0].web_url})\n" # Artiste
        description += f"-# source: Spotify"
        return description
    

    def __spt_build_entry_description_album_track(self, spt_track: spotify.SpotifyTrack, spt_album: spotify.SpotifyAlbum):
        description = f"{spt_album.album_type.capitalize()} : [{spt_album.name}]({spt_album.web_url})\n" # Album
        description += f"Artiste : [{spt_track.artists[0].name}]({spt_track.artists[0].web_url})\n" # Artiste
        description += f"-# source: Spotify"
        return description
    
    #endregion



    #endregion