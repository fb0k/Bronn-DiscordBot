from discord.ext import commands
import discord
from database.models import Guild
from discord.ext.commands import Bot, Cog
from converters import is_scam_link, is_valid_url
import constants
from log import get_logger
import typing as t

log = get_logger(__name__)

DELETION_MESSAGE = "{user}, looks like you posted a blocked url. Therefore, your message has been removed."


class Antiphishing(discord.Cog):
    """Message listener, check and removes malicious links in real-time"""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @Cog.listener()
    async def on_message(self, message: t.Union[discord.Message, discord.Embed]) -> None:
        if message.author.bot:
            return

        guild: Guild = await Guild.from_id(message.guild.id)

        if guild.is_bot_blacklisted:
            return

        if not message.guild:
            return

        link = message.content
        if await is_valid_url(link):
            if await is_scam_link(link):
                await message.delete()
                await message.channel.send(DELETION_MESSAGE.format(user=message.author.mention))
            else:
                return


def setup(bot) -> None:
    bot.add_cog(Antiphishing(bot))
