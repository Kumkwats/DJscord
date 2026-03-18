from dataclasses import dataclass
from typing import Self

from DJscordBot.utils.discord import InteractionWrapper

from ..Types.entry import Entry


from ..logging.utils import get_logger
_logger = get_logger('djscord.media_provider')


_PLAYLIST_ENTRIES_LIMIT = 50


@dataclass(frozen=True)
class MediaBaseIdentifier:
    provider: str
    provider_identifiers: list[str]

    def __repr__(self):
        return f"{self.provider}:{self._identifiers_as_str()}"

    def _identifiers_as_str(self):
        return ":".join(self.provider_identifiers)

    @classmethod
    def parse(cls, uri: str) -> Self:
        uri = "".join(uri.split()) #remove whitespaces
        splitted_uri = uri.split(':')
        if len(splitted_uri) < 2:
            raise ValueError("The provided uri is not in the correct format")
        return MediaBaseIdentifier(splitted_uri[0], [identifier for identifier in splitted_uri[1:]])



@dataclass
class MediaEntry:
    entry_data: Entry # used for DJscord interface
    download_web_url: str # used for download
    file_path: str # used for audio playback

    @property
    def data_processed(self):
        return self.entry_data is not None

    @property
    def downloadable(self):
        return self.download_web_url is not None

    @property
    def downloaded(self):
        return self.file_path is not None



class MediaProcessInteraction:
    def __init__(self, wrapper: InteractionWrapper):
        self.wrapper: InteractionWrapper = wrapper
        self.fixed_content: str = self.wrapper._last_message_content
        self.temp_content: str = ""

    @property
    def complete_message(self):
        return self._strip_trailing_line_break(self.fixed_content + self.temp_content)

    async def update_message(self, add: str):
        await self.wrapper.whisper_to_author(self._strip_trailing_line_break(self.complete_message + add))

    def add_title(self, title: str):
        formatted_title = f"**{title.capitalize()}**"
        self.fixed_content += formatted_title + "\n"

    def add_line(self, line:str):
        self.fixed_content += line + "\n"

    def add_temp_line(self, line: str):
        self.temp_content += line + "\n"

    def add_temp_to_fixed_content(self):
        self.fixed_content += self.temp_content

    def clear_temp(self):
        self.temp_content = ""

    def add_fixed_time_elapsed_stamp(self, title: str, time_elapsed: float):
        self.fixed_content += f"{self.format_time_elapsed(title, time_elapsed)}"

    def format_time_elapsed(self, description: str, time_elapsed: float=None):
        if time_elapsed is None:
            time_elapsed = time.time() - self.wrapper.interaction.created_at.timestamp()
        return f"-# {description} {{{int(time_elapsed)} secondes}}"

    def _strip_trailing_line_break(self, content: str):
        if self.content.endswith("\n"):
            self.content = self.temp_content[:len("\n")]





class CommonResponseData():
    def __init__(self, provider: str, provider_api_id: str, request_data, inferred_type: str = None):
        self.provider = provider
        self.provider_api_id = provider_api_id
        self.data = request_data
        self.inferred_type = inferred_type
    
    @staticmethod
    def create_empty():
        return CommonResponseData(None, None, {})
    
    @property
    def is_empty_or_incomplete(self):
        return self.provider is None or self.provider_api_id is None or len(self.data) <= 0


    def apply_values(self, other_response_data: Self):
        self.provider = other_response_data.provider
        self.provider_api_id = other_response_data.provider_api_id
        self.data = other_response_data.data
        self.inferred_type = other_response_data.inferred_type


    def __str__(self):
        return f"RequestData from [{self.provider}] API of element with provider ID of '{self.provider_api_id}'"
