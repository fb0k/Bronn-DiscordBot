from typing import Optional, Union, Any
from tortoise.exceptions import OperationalError
from database.models import Filterlist, Guild
from tortoise.functions import Concat, Coalesce
from tortoise.expressions import F
import discord
from discord.ext.commands import BadArgument, Cog, Context, command, has_any_role
import constants
from Bronn import Bot
from constants import Colours
from log import get_logger
from utils.paginator import LinePaginator
from collections import defaultdict
import Bronn
import sys
import asyncio

log = get_logger(__name__)


class Filters(Cog):
    """Commands for blacklisting and whitelisting things."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.synced_guilds: list = []

    @command(name="whitelist", aliases=("allowlist", "wl"))
    async def whitelist(
        self,
        ctx: Context,
        file_type: str,
    ) -> None:
        """Add a file type to the Whitelist."""

        # assert it has a leading dot.
        if not file_type.startswith("."):
            file_type = f".{file_type}"

        # Try to add the item to the database
        log.trace(f"Trying to whitelist the {file_type} file")
        # item = self.bot.filter_list_cache[f"{ctx.guild.id}"]
        guild = ctx.guild.id
        try:
            cached_item = self.bot.filter_list_cache[f"{ctx.guild.id}"]
            if file_type in cached_item:
                item = False
            else:
                item = await Filterlist.append_by_guild("whitelist", file_type, guild)

        except KeyError:
            item = await Filterlist.create(guild_id=guild, whitelist=[file_type])
            log.error(f"{ctx.author} tried whitelist {file_type}, but tortoise returned a key error. ")
            # raise BadArgument(f"Unable to add the {file_type} to the whitelist. " "Check args and variables")

        whitelist = item.whitelist if item else cached_item
        log.info(whitelist)
        log.trace(f"Updating {guild} filterlist cache...")
        self.bot.insert_item_into_filter_list_cache(guild, whitelist)
        await ctx.message.add_reaction("✅")
        await ctx.reply(f"File `{file_type}` whitelisted.")

    @command(name="blacklist", aliases=("denylist", "deny", "bl", "dl"))
    async def blacklist(
        self,
        ctx: Context,
        file_type: str,
    ) -> None:
        """Blacklist a file extension, removing it from whitelist."""

        # assert it has a leading dot.
        if not file_type.startswith("."):
            file_type = f".{file_type}"

        # Find the file in the cache
        guild = ctx.guild.id
        try:
            log.trace(f"Checking for {file_type} in the filterlist chache")
            cached_item = self.bot.filter_list_cache[f"{ctx.guild.id}"]

            if file_type in cached_item:
                item = await Filterlist.remove_by_guild("whitelist", file_type, guild)
            else:  # if already blacklisted, pass
                pass
        except KeyError:
            item = await Filterlist.create(guild_id=guild, whitelist=[])
        except Exception as e:
            log.error(e)

        whitelist = item.whitelist
        log.info(whitelist)
        log.trace(f"Updating {guild} filterlist cache...")
        self.bot.insert_item_into_filter_list_cache(guild_id=guild, whitelist=whitelist)
        await ctx.message.add_reaction("✅")
        await ctx.reply(f"File `{file_type}` blacklisted.")

    @command(name="filterlist")
    async def _list_all_data(self, ctx: Context) -> None:
        """Paginate and display all items in the filterlist."""

        # Return only files that match the passed 'allowed: bool'
        # .items() to get 'allow' values , since results is a dict
        result = [v for v in self.bot.filter_list_cache[f"{ctx.guild.id}"]]

        # Build a list of lines we want to show in the paginator
        lines = []
        for file in result:
            line = f"• `{file}`"

            lines.append(line)
        lines = sorted(lines)

        embed = discord.Embed(title=f"{ctx.guild}'s latest whitelist", colour=Colours.blue)

        log.trace(f"Trying to list {len(result)} items from the {ctx.guild} Filterlist")

        if result:
            await LinePaginator.paginate(lines, ctx, embed, max_lines=15, empty=False)
        else:
            embed.description = "Hmmm, seems like there's nothing here yet."
            await ctx.send(embed=embed)
            await ctx.message.add_reaction("❌")

    async def cog_check(self, ctx: Context) -> bool:
        """Only allow moderators to invoke the commands in this cog."""
        return await has_any_role(*constants.MODERATION_ROLES).predicate(ctx)


def setup(bot: Bot) -> None:
    """Load the FilterLists cog."""
    bot.add_cog(Filters(bot))
