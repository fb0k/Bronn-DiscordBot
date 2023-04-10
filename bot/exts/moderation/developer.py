import discord
import inspect
from discord.ext import commands
from discord import Embed, Message
from log import get_logger
import constants
from Bronn import Bot
from discord.errors import (
    ExtensionAlreadyLoaded,
    ExtensionNotFound,
    ExtensionNotLoaded,
)
from discord.ext.commands import command, Cog
from jishaku.codeblocks import codeblock_converter
from jishaku.cog import Jishaku
from jishaku.modules import ExtensionConverter


log = get_logger(__name__)


class Developer(Cog, command_attrs={"hidden": True}):
    def __init__(self, bot: Bot) -> None:
        self.bot = bot
        self.jishaku: Jishaku = bot.get_cog("Jishaku")

    @command(name="eval")
    @commands.is_owner()
    async def _eval(self, ctx, *, code: codeblock_converter):
        await self.jishaku.jsk_python(ctx, argument=code)

    @command(aliases=["reload"])
    @commands.is_owner()
    async def load(self, ctx, *files: ExtensionConverter):
        await self.jishaku.jsk_load(ctx, *files)

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
            log.error(error)

    @command()
    @commands.is_owner()
    async def unload(self, ctx, *files: ExtensionConverter):
        await self.jishaku.jsk_unload(ctx, *files)

        loaded_extentions = []

        for extention in files.split():
            loaded_extentions.append(extention)

        embed: Embed = discord.Embed(
            color=constants.Colours.bright_green,
            description=f"{', '.join(loaded_extentions)} Are Now Unloaded!",
        )

        message: Message = await ctx.send(embed=embed)

        await message.add_reaction(constants.Emojis.sucess)

    @unload.error
    async def unload_error(ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, ExtensionNotLoaded):
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
            log.error(error)

    @command(aliases=["where", "find"])
    @commands.is_owner()
    async def which(self, ctx: commands.Context, *, command_name: str) -> None:
        """Finds the cog a command is part of."""
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

    @command()
    async def shutdown(self, ctx):
        await ctx.send("Shutting down.")

        await self.bot.close()

    @command()
    async def pull(self, ctx, *to_load: ExtensionConverter):
        await self.jishaku.jsk_git(ctx, argument=codeblock_converter("pull"))
        await self.jishaku.jsk_load(ctx, *to_load)

    async def cog_check(self, ctx):
        return ctx.author.id in self.bot.owner_ids


def setup(bot: Bot) -> None:
    bot.add_cog(Developer(bot))
