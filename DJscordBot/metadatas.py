
# pylint: disable=C0116,C0303

class YoutubeMetadata:
    def __init__(self, metadata):
        self.title = metadata["title"]

        self.view_count = metadata['view_count']
        self.like_count = metadata['like_count']

        self.channel = metadata['channel']
        self.channel_url = metadata['channel_url']
        self.channel_follower_count = metadata['channel_follower_count']
        self.channel_is_verified = metadata['channel_is_verified']

        self.album = metadata['album'] if 'album' in metadata else None
        self.release_date = metadata["release_date"]
        self.release_year = metadata["release_year"]

        self.filesize = metadata['filesize']
        self.duration = metadata['duration']
        
        self.id = metadata['id']
        self.url = metadata['webpage_url']
        self.thumbnail = metadata['thumbnail']
        
        self.upload_date = metadata["upload_date"]

class SpotifyMetadata:
    def __init__(self):
        self.title = ""