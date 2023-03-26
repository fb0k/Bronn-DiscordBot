from collections import defaultdict
from typing import Optional
from tortoise.exceptions import OperationalError
from database.models import Filterlist
import discord
from discord.ext.commands import BadArgument, Cog, Context, command, group, has_any_role
import constants
from Bronn import Bot
from constants import Colours
from log import get_logger
from utils.paginator import LinePaginator


log = get_logger(__name__)


class Filters(Cog):
    """Commands for blacklisting and whitelisting things."""

    def __init__(self, bot: Bot) -> None:
        self.bot = bot

    @command(name="whitelist", aliases=("allowlist", "allow", "al", "wl"))
    async def whitelist(
        self,
        ctx: Context,
        file_type: str,
        comment: Optional[str] = None,
        allow: bool = True,
    ) -> None:

        # let's make sure it has a leading dot.
        if not file_type.startswith("."):
            file_type = f".{file_type}"

        # Try to add the item to the database
        log.trace(f"Trying to set {allow} to the {file_type} file")
        try:
            if await Filterlist.exists(type=file_type, guild=ctx.guild.id, allowed=allow):
                await ctx.message.add_reaction("✅")
                await ctx.reply("This extension is already whitelisted.")
            else:
                item = await Filterlist.update_or_create(
                    type=file_type,
                    guild_id=ctx.guild.id,
                    allowed=allow,
                    comment=comment,
                )
                # self.bot.insert_item_into_filter_list_cache(item)
                item.di
                await ctx.message.add_reaction("✅")
                await ctx.reply(f"File `{file_type}` added to the whitelist.")
        except OperationalError:
            await ctx.message.add_reaction("❌")
            log.debug(f"{ctx.author} tried to add filetype to whitelist, but tortoise returned a operational error. ")
            raise BadArgument(f"Unable to add the {file_type} to the whitelist. " "Check args and variables")

    @command(name="blacklist", aliases=("denylist", "deny", "bl", "dl"))
    async def blacklist(
        self,
        ctx: Context,
        file_type: str,
        comment: Optional[str] = None,
        allow: bool = False,
    ) -> None:
        """Remove an item from a filterlist."""

        # let's make sure it has a leading dot.
        if not file_type.startswith("."):
            file_type = f".{file_type}"

        # Find the content and delete it.
        log.trace(f"Trying to blacklist the {file_type} item in the filterlist")
        try:
            if await Filterlist.exists(type=file_type, guild=ctx.guild.id, allowed=allow):
                await ctx.message.add_reaction("✅")
                await ctx.reply("This extension is already blacklisted.")
            else:
                item = await Filterlist.update_or_create(
                    type=file_type,
                    guild_id=ctx.guild.id,
                    allowed=allow,
                    comment=comment,
                )
                # del self.bot.filter_list_cache[f"{file_type}.{allowed}"][id]
                self.bot.insert_item_into_filter_list_cache(item)
                await ctx.message.add_reaction("✅")
                await ctx.reply(f"File `{file_type}` blacklisted.")
        except OperationalError:
            await ctx.message.add_reaction("❌")
            log.debug(
                f"{ctx.author} tried to add filetype to a filterlist, but tortoise returned a operational error. "
            )
            raise BadArgument(f"Unable to add the {file_type} to the filterlist. Check args and variables")

    async def _list_all_data(self, ctx: Context, allow: bool, file_type: str) -> None:
        """Paginate and display all items in a filterlist."""
        # result = self.bot.filter_list_cache[f"{file_type}.{allowed}"]
        guild = ctx.guild.id
        result = await Filterlist.filter(guild_id=guild)
        # Build a list of lines we want to show in the paginator
        lines = []
        for item in result:
            line = f"• `{item.type}`"

            if comment := item.comment:
                line += f" - {comment}"

            lines.append(line)
        lines = sorted(lines)

        # Build the embed
        embed = discord.Embed(title=f"Current {ctx.guild} Filterlist", colour=Colours.blue)
        log.trace(f"Trying to list {len(result)} items from the {ctx.guild} Filterlist")

        if result:
            await LinePaginator.paginate(lines, ctx, embed, max_lines=15, empty=False)
        else:
            embed.description = "Hmmm, seems like there's nothing here yet."
            await ctx.send(embed=embed)
            await ctx.message.add_reaction("❌")

    async def _sync_data(self, ctx: Context) -> None:
        """Syncs the filterlists with the API."""
        try:
            log.trace("Attempting to sync FilterList cache with data from the API.")
            await self.bot.cache_filter_list_data()
            await ctx.message.add_reaction("✅")
        except OperationalError as e:
            log.debug(
                f"{ctx.author} tried to sync FilterList cache data but " f"the API raised an unexpected error: {e}"
            )
            await ctx.message.add_reaction("❌")

    @command(name="filterlist", aliases=("typelist", "fl", "fetch"))
    async def get_list(self, ctx: Context, file_type: str) -> None:
        """Get the contents of a specified allowlist."""
        await self._list_all_data(ctx, True, file_type)

    @command(name="synclist", aliases=("sl",))
    async def allow_sync(self, ctx: Context) -> None:
        """Syncs both allowlists and denylists with the API."""
        await self._sync_data(ctx)

    async def cog_check(self, ctx: Context) -> bool:
        """Only allow moderators to invoke the commands in this cog."""
        return await has_any_role(*constants.MODERATION_ROLES).predicate(ctx)


def setup(bot: Bot) -> None:
    """Load the FilterLists cog."""
    bot.add_cog(Filters(bot))