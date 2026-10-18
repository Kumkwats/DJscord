from dataclasses import dataclass
from typing import Sequence

from discord import *
from discord.ui import LayoutView, View



class InteractionMessageContent():
    __slots__ = [
        'message',
        '_frozen_message',
        'embeds',
        'attachments',
        'view',
        'allowed_mentions',
        'poll']

    def __init__(self):
        self.message: str = ""
        self._frozen_message: list[str] = ""
        self.embeds: Sequence[Embed] = None
        self.attachments: Sequence[Attachment | File] = None
        self.view: View | LayoutView | None
        self.allowed_mentions: AllowedMentions = None
        self.poll : Poll = None

    def freeze_content(self):
        self._frozen_message.append(self.message)
