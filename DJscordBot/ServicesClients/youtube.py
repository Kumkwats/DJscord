from youtubesearchpython.__future__ import VideosSearch
import yt_dlp
import asyncio
import time
import requests
import os

from DJscordBot.config import config

# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda: ''

ydl_opts = {
    'format': 'bestaudio/best',
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


class Youtube():
    def downloadProgress(d, message, text, loop):
        global oldTime
        if d['status'] == 'downloading':
            currentSize = d['downloaded_bytes']/1000000
            downloadSize = d['total_bytes']/1000000
            if time.time() - oldTime > 2:
                oldTime = time.time()
                asyncio.run_coroutine_threadsafe
                loop.create_task(message.edit(content="%s [%.2f/%.2f Mo]" % (text, currentSize, downloadSize)))


    async def searchVideos_YSP(query, nbEntries=1):
        videosSearch = VideosSearch(query, limit=nbEntries)
        videosResult = await videosSearch.next()
        
        video = videosResult["result"][0]

        if config.debug:
            if not os.path.isdir("./._debug"):
                os.mkdir("._debug")
            f = open(f"._debug/YT_DLP_{video['id']}-keys", "w")
            f_all = open(f"._debug/YT_DLP_{video['id']}", "w")
            for s in video.keys():
                f.write(f"{s}\n")
                f_all.write(f"{s} | {video[s]}\n")
            f.close()
            f_all.close()
            print("[DEBUG] written search data keys: " + f".debug/YT_DLP_{video['id']}-keys")
            print("[DEBUG] written search data: " + f".debug/YT_DLP_{video['id']}")

        return video
    

    async def searchVideosYT_DLP(query, nbEntries=1):
        try:
            requests.get(query)
        except:
            video = ydl.extract_info(f"ytsearch:{query}", download=False)['entries'][0]
        else:
            video = ydl.extract_info(query, download=False)

        if config.debug:
            if not os.path.isdir("./._debug"):
                os.mkdir("._debug")
            f = open(f"._debug/YT_DLP_{video['id']}-keys", "w")
            f_all = open(f"._debug/YT_DLP_{video['id']}", "w")
            for s in video.keys():
                f.write(f"{s}\n")
                f_all.write(f"{s} | {video[s]}\n")
            f.close()
            f_all.close()
            print("[DEBUG] written search data keys: " + f".debug/YT_DLP_{video['id']}-keys")
            print("[DEBUG] written search data: " + f".debug/YT_DLP_{video['id']}")


        return video

    async def fetchData(url, loop):
        data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
        return data

    def getFilename(data):
        filename = ydl.prepare_filename(data)[len(config.downloadDirectory):]
        print(filename)
        return filename

    @classmethod #TODO try update hook
    async def downloadAudio(self, url, message, text, loop):
        # ydl.add_progress_hook(lambda d: self.downloadProgress(d, message, text, loop))
        await loop.run_in_executor(None, lambda: ydl.download(url))
