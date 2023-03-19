import inspect
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
from discord import Embed, Intents, Message
from discord.errors import (
    ExtensionAlreadyLoaded,
    ExtensionNotFound,
    ExtensionNotLoaded,
)
from discord.ext import commands, tasks
from discord.flags import MemberCacheFlags
from discord.mentions import AllowedMentions
from tortoise import Tortoise
from tortoise.exceptions import IntegrityError
from database.models import Guild
from collections import defaultdict
import constants
from log import get_logger
from database import tortoise_config


os.system("cls" if sys.platform == "win32" else "clear")
log = get_logger("bot")


class Bot(commands.Bot):
    on_ready_fired: bool = False
    cache: Dict[str, Dict] = {"afk": {}, "example_list": {}}

    def __init__(
        self,
        development_mode: str = None,
        extensions_dir: str = "exts",
        *args,
        **kwargs,
    ) -> None:
        self.extensions_dir: str = extensions_dir
        development_mode_passed: bool = development_mode is not None

        if not development_mode_passed:
            raise ValueError("__init__ expects development_mode to be provided, got None")
        self.filter_list_cache = defaultdict(dict)
        self.session: ClientSession = aiohttp.ClientSession()
        self.bot_owners = constants.Bot.owners_ids
        self.development_mode: str = development_mode
        self.github: str = constants.URLs.github
        self.support_server: str = constants.URLs.support_server
        self.documentation: str = constants.URLs.documentation
        self.invite_url: str = constants.URLs.invite_url
        self.redis_path = constants.Redis.uri
        self.guild_id = constants.Guild.id
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
        intents: Intents = discord.Intents.default()
        intents.members = True
        intents.typing = False
        intents.presences = True
        intents.message_content = True
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
        loaded_extensions = set()
        failed_extensions = set()
        for file in map(
            lambda file_path: file_path.replace(os.path.sep, ".")[:-3],
            glob(f"{self.extensions_dir}/**/*.py", recursive=True),
        ):
            try:
                self.load_extension(file)
                loaded_extensions.add(file)
                log.info(f"[bright_green][EXTENSION][/bright_green] [blue3]{file} LOADED[/blue3]")
            except Exception as e:
                failed_extensions.add(file)
                log.info(f"[bright red][EXTENSION ERROR][/bright red] [blue3]FAILED TO LOAD COG {file}[/blue3]")
                if not reraise_exceptions:
                    traceback.print_exception(type(e), e, e.__traceback__)
                else:
                    raise e
        result = (tuple(loaded_extensions), tuple(failed_extensions))
        return result

    @tasks.loop(seconds=10)
    async def status(self) -> None:
        """Cycles through all status every 10 seconds"""
        new_activity = next(self.activities)
        # The commands one is callable so the command counts actually change
        if callable(new_activity):
            await self.change_presence(status=discord.Status.online, activity=new_activity())
        else:
            await self.change_presence(status=discord.Status.online, activity=new_activity)

    @status.before_loop
    async def before_status(self) -> None:
        """Ensures the bot is fully ready before starting the task"""
        await self.wait_until_ready()

    async def on_ready(self) -> None:
        """Called when we have successfully connected to a gateway"""
        await Tortoise.init(tortoise_config.TORTOISE_CONFIG)
        # await Tortoise.generate_schemas()
        self.status.start()
        print(f"[blue3]Signed into Discord as {self.user} (ID: {self.user.id}[/blue3])\n")

    async def on_error(self, event: str, *args, **kwargs) -> None:
        """Log errors raised in event listeners rather than printing them to stderr."""

        with push_scope() as scope:
            scope.set_tag("event", event)
            scope.set_extra("args", args)
            scope.set_extra("kwargs", kwargs)

            log.exception(f"Unhandled exception in {event}.")

    def _start(self) -> None:
        self.run(constants.Bot.token, reconnect=True)


bot: Bot = Bot(development_mode="development")


@bot.command()
@commands.is_owner()
async def load(ctx: commands.Context, *, extentions: str) -> None:
    """Loads an extension, owners only"""

    if bot.development_mode != "development":
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} `bot.development_mode` set to `{bot.development_mode}`,"
            " commands such as `load`, `reload` and `unload` require `bot.development_mode` to be **development**",
        )
        await ctx.send(embed=embed)
        return

    if extentions is None:
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} `extention` argument missing",
        )
        await ctx.send(embed=embed)
        return

    loaded_extentions = []

    for extention in extentions.split():
        bot.load_extension(f"cogs.{extention}")
        loaded_extentions.append(extention)

    embed: Embed = discord.Embed(
        color=constants.Colours.bright_green,
        description=f"{', '.join(extention)} Are Now Loaded!",
    )

    message: Message = await ctx.send(embed=embed)

    await message.add_reaction(constants.Emojis.sucess)


@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    try:
        guild: Guild = await Guild.create(discord_id=guild.id, language="en", prefix="-")
        log.info(f"[blue3][GUILD] JOINED GUILD {guild.name}) (ID: {guild.id}) [/blue3]")
    except IntegrityError:
        log.info(f"[blue3]{guild.name} ({guild.id}) Has Reinvited {constants.Bot.name}.[/blue3]")


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


@bot.command(aliases=["where", "find"])
@commands.is_owner()
async def which(ctx: commands.Context, *, command_name: str) -> None:
    """Finds the cog a command is part of"""
    command = bot.get_command(command_name)
    if command is None:
        embed: Embed = discord.Embed(
            description=f"{constants.Emojis.error} `{command_name}` **does not exist.**",
            color=constants.Colours.soft_red,
        )
    else:
        inner_command = command.callback
        command_defined_on: int = inspect.getsourcelines(inner_command)[1]
        full_command_signature: str = f"`async def {inner_command.__name__}{inspect.signature(inner_command)}`"
        if type(command) is commands.Command and not command.parent:
            command_type: Literal["`Standalone command`"] = "`Standalone command`"
        elif type(command) is commands.Group:
            command_type: Literal["`Standalone command`"] = "`Command group`"
        else:
            command_type: Literal["`Standalone command`"] = f"Subcommand of `{command.parent.qualified_name}`"
        embed: Embed = discord.Embed(title="Target Acquired \U0001F3AF", color=constants.Colours.bright_green)
        embed.add_field(
            name="Part of Extension",
            value=f"`{command.cog.qualified_name}`" if command.cog is not None else "`Root Module`",
            inline=False,
        )
        embed.add_field(name="Type of command", value=command_type)
        embed.add_field(
            name="Defined on line",
            value=f"`{command_defined_on}`",
            inline=False,
        )
        embed.add_field(name="Signature", value=full_command_signature, inline=False)
    await ctx.send(embed=embed)


@load.error
async def load_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.NotOwner):
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} This Can Only Be Used By The Bot's Owners.",
        )
    elif isinstance(error, ExtensionAlreadyLoaded):
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} This Extension Is Already Loaded.",
        )
        await ctx.send(embed=embed)
    elif isinstance(error, ExtensionNotFound):
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} This Extension Does Not Exist.",
        )
        await ctx.send(embed=embed)
    else:
        traceback.print_exception(type(error), error, error.__traceback__)


@bot.command()
@commands.is_owner()
async def unload(ctx: commands.Context, *, extentions: str) -> None:
    """Unloads an extension, owners only"""
    if bot.development_mode != "development":
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} `bot.development_mode` set to `{bot.development_mode}`, "
            "commands such as `load`, `reload` and `unload` require `bot.development_mode` to be **development**",
        )
        await ctx.send(embed=embed)
        return

    if extentions is None:
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} `extention` argument missing",
        )
        await ctx.send(embed=embed)
        return

    loaded_extentions = []

    for extention in extentions.split():
        bot.unload_extension(f"cogs.{extention}")
        loaded_extentions.append(extention)

    embed: Embed = discord.Embed(
        color=constants.Colours.bright_green,
        description=f"{', '.join(loaded_extentions)} Are Now UnLoaded!",
    )

    message: Message = await ctx.send(embed=embed)

    await message.add_reaction(constants.Emojis.sucess)


@unload.error
async def unload_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.NotOwner):
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} This Can Only Be Used By The Bot's Owners.",
        )
        await ctx.send(embed=embed)
    elif isinstance(error, ExtensionNotLoaded):
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} This Extension Is Not Loaded.",
        )
        await ctx.send(embed=embed)
    elif isinstance(error, ExtensionNotFound):
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} This Extension Does Not Exist.",
        )
        await ctx.send(embed=embed)
    else:
        traceback.print_exception(type(error), error, error.__traceback__)


@bot.command()
@commands.is_owner()
async def reload(ctx: commands.Context, *, extension: str) -> None:
    bot.unload_extension(f"cogs.{extension}")
    bot.load_extension(f"cogs.{extension}")
    embed: Embed = discord.Embed(
        color=constants.Colours.bright_green,
        description=f"{constants.Emojis.sucess} Successfully Reloaded {extension}",
    )
    await ctx.send(embed=embed)


@reload.error
async def reload_error(ctx: commands.Context, error: commands.CommandError) -> None:
    if isinstance(error, commands.NotOwner):
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} This Can Only Be Used By The Bot's Owners.",
        )
    elif isinstance(error, ExtensionNotLoaded):
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} This Extension Is Not Loaded.",
        )
        await ctx.send(embed=embed)
    elif isinstance(error, ExtensionNotFound):
        embed: Embed = discord.Embed(
            color=constants.Colours.soft_red,
            description=f"{constants.Emojis.error} This Extension Does Not Exist.",
        )
        await ctx.send(embed=embed)
    else:
        traceback.print_exception(type(error), error, error.__traceback__)
