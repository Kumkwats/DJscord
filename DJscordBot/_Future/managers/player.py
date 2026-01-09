from DJscordBot._Future.guild_player import GuildPlayer

from ...logging.utils import get_logger
__logger = get_logger("djscordbot.player_manager")


class PlayerManager:
    __guild_players: list[GuildPlayer]

    @classmethod
    async def create_player(self, guild_id: int) -> GuildPlayer:
        __logger.debug(f"Created player for guild ({guild_id})")
        pass
    
    

