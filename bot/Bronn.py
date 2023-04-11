"""
This is the bot subclass file.

It contains all the subclass specific methods and attributes.
such as cachelists, activities iterator and load_extensions().
"""

import itertools
import os
import sys
import traceback
from glob import glob
from typing import Literal, Tuple, Dict
from sentry_sdk import push_scope
import aiohttp
import discord
from aiohttp import ClientSession
from discord import Embed, Intents
from discord.ext import commands, tasks
from discord.flags import MemberCacheFlags
from discord.mentions import AllowedMentions
from tortoise import Tortoise
from tortoise.exceptions import IntegrityError
from database.models import Guild
from collections import defaultdict
import constants
from log import get_logger, return_error
from database import tortoise_config
from database.models import Filterlist


os.system("cls" if sys.platform == "win32" else "clear")
log = get_logger("bot")


class Bot(commands.Bot):
    """Subclass of Pycord commands.Bot with custom methods and attributes."""

    on_ready_fired: bool = False
    cache: Dict[str, Dict] = {"afk": {}, "example_list": {}}

    def __init__(
        self,
        extensions_dir: str = "exts",
        *args,
        **kwargs,
    ) -> None:
        self.extensions_dir: str = extensions_dir
        self.filter_list_cache: dict = defaultdict(dict)
        self.guilds_info_cache: dict = defaultdict(dict)
        self.session: ClientSession = aiohttp.ClientSession()
        self.bot_owners = constants.Bot.owners_ids
        self.redis_path = constants.Redis.uri
        self.command_prefix = commands.when_mentioned_or(constants.Bot.prefix)

        # -- Tuple of all activities the bot will display as a status
        self.activities = itertools.cycle(
            (
                discord.Activity(type=discord.ActivityType.playing, name="!help"),
                lambda: discord.Activity(
                    type=discord.ActivityType.watching,
                    name=f"{len(bot.users)} Users | {len(bot.guilds)} Servers",
                ),
            )
        )

        # -- Intents
        intents: Intents = discord.Intents.all()
        allowed_roles = list({discord.Object(id_) for id_ in constants.MODERATION_ROLES})
        chunk_guilds_at_startup: Literal[False] = False
        allowed_mentions: AllowedMentions = discord.mentions.AllowedMentions(everyone=False, roles=allowed_roles)
        stuff_to_cache: MemberCacheFlags = MemberCacheFlags.from_intents(intents)

        super().__init__(
            intents=intents,
            command_prefix=self.command_prefix,
            case_insensitive=True,
            help_command=None,
            allowed_mentions=allowed_mentions,
            member_cache_flags=stuff_to_cache,
            chunk_guilds_at_startup=chunk_guilds_at_startup,
            max_messages=1000,
            *args,
            **kwargs,
        )

        # -- Load Extensions
        self.load_extension("jishaku")
        self.load_extensions()

    def load_extensions(self, reraise_exceptions: bool = False) -> Tuple[Tuple[str], Tuple[str]]:
        bot_dir = os.path.dirname(__file__)
        loaded_extensions = set()
        failed_extensions = set()
        for file in map(
            lambda file_path: file_path.replace(os.path.sep, ".")[:-3],
            glob(f"{self.extensions_dir}/**/*.py", recursive=True, root_dir=bot_dir),
        ):
            try:
                if file.endswith("__init__"):
                    pass
                else:
                    self.load_extension(file)
                    loaded_extensions.add(file)
                    log.info(f"Loaded {file}")
            except Exception as e:
                failed_extensions.add(file)
                log.error(f"{file.upper()}")
                if not reraise_exceptions:
                    # traceback.print_exception(type(e), e, e.__traceback__)
                    log.error(return_error())

                else:
                    # raise e
                    log.error(return_error())
        result = (tuple(loaded_extensions), tuple(failed_extensions))
        return result

    @tasks.loop(seconds=10)
    async def status(self) -> None:
        """Cycles through all status every 10 seconds."""
        new_activity = next(self.activities)
        # The commands one is callable so the command counts actually change
        if callable(new_activity):
            await self.change_presence(status=discord.Status.online, activity=new_activity())
        else:
            await self.change_presence(status=discord.Status.online, activity=new_activity)

    @status.before_loop
    async def before_status(self) -> None:
        """Ensures the bot is fully ready before starting the task."""
        await self.wait_until_ready()

    async def on_ready(self) -> None:
        """Called when we have successfully connected to a gateway"""
        await Tortoise.init(tortoise_config.TORTOISE_CONFIG)
        await Tortoise.generate_schemas()
        self.status.start()
        log.info(f"Signed into Discord as {self.user} (ID: {self.user.id})\n")
        await self.cache_guilds_data()

    def _start(self) -> None:
        self.run(constants.Bot.token, reconnect=True)

    def insert_item_into_filter_list_cache(self, item: dict) -> None:
        """Add an item to the bots filter_list_cache."""
        file = item["type"]
        allow = item["allowed"]
        guild = item["guild_id"]

        self.filter_list_cache[f"{guild}"][file] = {
            "file": item["type"],
            "guild_id": guild,
            "allow": allow,
            "comment": item["comment"],
        }

    async def cache_filter_list_data(self, ctx: discord.ApplicationContext) -> None:
        """Cache all the data in the FilterList on the database."""
        result = await Filterlist.filter(guild_id=f"{ctx.guild.id}").values(
            "id", "allowed", "comment", "created_at", "type", "guild_id"
        )

        for item in result:
            self.insert_item_into_filter_list_cache(item)

    def append_to_guilds_cache(self, guild_id: int, item: dict) -> None:
        """Add an item to the bots guilds_cache."""

        self.guilds_info_cache[f"{guild_id}"] = {
            "id": item["discord_id"],
            "blacklisted": item["is_bot_blacklisted"],
            "automod": item["is_automod"],
            "automod_log": item["automod_log"],
            "message_log": item["message_log"],
            "mod_log": item["mod_log"],
            "logging": item["is_logging"],
        }

    async def cache_guilds_data(self) -> None:
        """Cache guild ids, logs channel and blacklisted guilds on the database."""
        fullcache = await Guild.fetch_to_dict()

        for id, item in fullcache.items():
            self.append_to_guilds_cache(id, item)


bot: Bot = Bot(development_mode="development")


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    try:
        await Guild.create(discord_id=guild.id, language="en", prefix=".")
        log.info(f"Joined Guild {guild.name} - ID: {guild.id}")
    except IntegrityError:
        log.info(f"{guild.name} ({guild.id}) Has Reinvited {constants.Bot.name}.")


# -- Bot Checks


@bot.check
async def is_bot_on_maintenance_mode(ctx: commands.Context) -> bool:
    maintenance_mode = False
    bot_name = constants.Bot.name

    if maintenance_mode and ctx.author.id not in bot.bot_owners:
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.information} {bot_name} Is Currently In Maintenance Mode, Try Again Later.",
        )
        await ctx.send(embed=embed)
        return False
    else:
        return True


@bot.check
async def is_guild_blacklisted(ctx: commands.Context) -> bool:
    guild = await Guild.get(discord_id=ctx.guild.id)
    blacklisted = guild.is_bot_blacklisted
    bot_name = constants.Bot.name

    if blacklisted and ctx.author.id not in bot.bot_owners:
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{ctx.author.mention}, {ctx.guild.name} Is blacklisted from using {bot_name}"
            " for breaking [{bot_name} TOS](https://soontobeourtoslink.com)",
        )
        await ctx.send(embed=embed)
        return False
    else:
        return True
