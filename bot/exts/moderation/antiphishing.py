from discord.ext import commands
import discord
from database.models import Guild
from discord.ext.commands import Bot, BucketType, Cooldown, CooldownMapping
import re
from converters import is_scam_link, is_valid_url
import constants

DELETION_MESSAGE = "{user}, looks like you posted a blocked url. Therefore, your " "message has been removed."


class Antiphishing(discord.Cog):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # guild: Guild = message.guild.id

        # if guild.is_bot_blacklisted:
        #     return

        if not message.guild:
            return

        if message.author.bot:
            return

        link = message.content
        if await is_valid_url(link):
            if await is_scam_link(link):
                await message.delete()
                await message.channel.send(DELETION_MESSAGE.format(user=message.author.mention))
            else:
                pass


def setup(bot) -> None:
    bot.add_cog(Antiphishing(bot))
