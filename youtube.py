from youtubesearchpython.__future__ import VideosSearch
import yt_dlp
import asyncio
from config import DLDIR

# Suppress noise about console usage from errors
yt_dlp.utils.bug_reports_message = lambda: ''

ydl_opts = {
    'format': 'bestaudio/best',
    'outtmpl': DLDIR + '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'verbose': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    # bind to ipv4 since ipv6 addresses cause issues sometimes
    'source_address': '0.0.0.0'
}

ydl = yt_dlp.YoutubeDL(ydl_opts)


class Youtube():
    async def searchVideos(query, nbEntries=1):
        videosSearch = VideosSearch(query, limit=nbEntries)
        videosResult = await videosSearch.next()
        return videosResult["result"][0]

    async def fetchData(url, loop=None):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=False))
        return data

    def getFilename(data):
        filename = ydl.prepare_filename(data)[len(DLDIR):]
        print(filename)
        return filename

    async def downloadAudio(url, loop=None):
        loop = loop or asyncio.get_event_loop()
        await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))


if __name__ == "__main__":
    data = asyncio.run(Youtube.fetchData("https://www.youtube.com/playlist?list=PLI_rLWXMqpSkAYfar0HRA7lykydwmRY_2"))
    #data, filename = asyncio.run(Youtube.downloadAudio("https://www.youtube.com/watch?v=WnqOhgI_8wA?list="))
    f = open('ex.json', 'w')
    f.write(str(data))
    f.close()
