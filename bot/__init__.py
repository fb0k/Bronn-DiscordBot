import log
from discord.ext import commands
from .Bronn import Bot


log.setup()


class Cog(commands.Cog):
    """Base class for all cogs"""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
