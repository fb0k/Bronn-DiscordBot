import traceback
import typing
import discord
import humanize
from discord.ext import commands
from discord.ext.commands import Bot, BucketType
from log import get_logger
from utils.custommetacog import CustomCog as Cog
import constants

log = get_logger(__name__)


class ErrorHandler(Cog, command_attrs=dict(hidden=True), emoji=constants.Emojis.pycord):
    def __init__(self, bot: Bot) -> None:
        self.bot: Bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandOnCooldown):
            retry_after: float = error.retry_after

            precise: str = humanize.precisedelta(retry_after, minimum_unit="seconds", format="%0.2f")

            embed = discord.Embed(
                title="Active Cooldown",
                color=constants.Colours.default,
                description=f"Please wait `{precise}` before reusing `{ctx.command}`",
            )
            embed.set_thumbnail(url=ctx.author.avatar.url)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
            embed.set_footer(text=f"ID: {ctx.author.id}", icon_url=ctx.author.avatar.url)

            await ctx.send(embed=embed)
        if isinstance(error, commands.CommandNotFound):
            embed = discord.Embed(
                color=constants.Colours.error,
                description=f"{constants.Emojis.failed_file} The command `{ctx.prefix}{ctx.command}` was not found!",
            )
            embed.set_thumbnail(url=ctx.author.avatar.url)
            embed.set_author(
                name=ctx.author.name,
                url=constants.URLs.github,
                icon_url=ctx.author.avatar.url,
            )
            embed.set_footer(text=f"ID: {ctx.author.id}", icon_url=ctx.author.avatar.url)
            await ctx.send(embed=embed)
        else:
            traceback.print_exception(type(error), error, error.__traceback__)


async def handle_role_change(
    member: discord.Member, coro: typing.Callable[..., typing.Coroutine], role: discord.Role
) -> None:
    """
    Change `member`'s cooldown role via awaiting `coro` and handle errors.
    `coro` is intended to be `discord.Member.add_roles` or `discord.Member.remove_roles`.
    """
    try:
        await coro(role)
    except discord.NotFound:
        log.debug(f"Failed to change role for {member} ({member.id}): member not found")
    except discord.Forbidden:
        log.debug(f"Forbidden to change role for {member} ({member.id}); " f"possibly due to role hierarchy")
    except discord.HTTPException as e:
        log.error(f"Failed to change role for {member} ({member.id}): {e.status} {e.code}")


def setup(bot) -> None:
    bot.add_cog(ErrorHandler(bot))
