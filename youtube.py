from youtubesearchpython.__future__ import VideosSearch
import yt_dlp
import asyncio
import time
from config import DLDIR

# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda: ''

ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': DLDIR + '%(extractor)s-%(id)s-%(title)s.%(ext)s',
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

    async def searchVideos(query, nbEntries=1):
        videosSearch = VideosSearch(query, limit=nbEntries)
        videosResult = await videosSearch.next()
        return videosResult["result"][0]

    async def fetchData(url, loop):
        data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
        return data

    def getFilename(data):
        filename = ydl.prepare_filename(data)[len(DLDIR):]
        print(filename)
        return filename

    @classmethod
    async def downloadAudio(self, url, message, text, loop):
        ydl.add_progress_hook(lambda d: self.downloadProgress(d, message, text, loop))
        await loop.run_in_executor(None, lambda: ydl.download([url]))


if __name__ == "__main__":
    #data = asyncio.run(Youtube.fetchData("https://www.youtube.com/playlist?list=PLI_rLWXMqpSkAYfar0HRA7lykydwmRY_2"))
    asyncio.run(Youtube.downloadAudio("https://www.youtube.com/watch?v=jIQ6UV2onyI", "lol"))
    #f = open('ex.json', 'w')
    # f.write(str(data))
    # f.close()
