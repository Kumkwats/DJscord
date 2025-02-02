
# pylint: disable=C0116,C0303

class YoutubeMetadata:
    def __init__(self, metadata):
        self.title = metadata["title"]

class SpotifyMetadata:
    def __init__(self):
        self.title = ""