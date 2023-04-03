import asyncio
import difflib
import itertools
import typing as t
from datetime import datetime, timezone
from itertools import zip_longest
import converters
import discord
from dateutil.relativedelta import relativedelta
from deepdiff import DeepDiff
from discord import Colour, Message, Thread
from discord.abc import GuildChannel
from discord.ext.commands import Cog, Context, BucketType, Greedy, command  # Bot
from discord.utils import escape_markdown, format_dt, snowflake_time
from constants import Colours, Emojis, Event, Icons
from log import get_logger
from Bronn import Bot
from database.models import Guild, Roles
from discord import AuditLogAction, AuditLogEntry
from discord.ext import commands
from tortoise.exceptions import DoesNotExist, IntegrityError


log = get_logger(__name__)


GUILD_CHANNEL = t.Union[discord.CategoryChannel, discord.TextChannel, discord.VoiceChannel]

CHANNEL_CHANGES_UNSUPPORTED = ("permissions",)
CHANNEL_CHANGES_SUPPRESSED = ("_overwrites", "position")
ROLE_CHANGES_UNSUPPORTED = ("colour", "permissions")

Log_options = {
    "Moderation": "Logs of moderation related action, like user ban or channel creation",
    "AutoModeration": "Logs of automatic bot related moderation, example, message filtering and urls deletion",
    "Messages": "Logs users deleted and edited messages in the server",
}


def format_user(user: discord.abc.User) -> str:
    """Return a string for `user` which has their mention and ID."""
    return f"{user.mention} (`{user.id}`)"


class SetLogs(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=15)  # specify the timeout here

    choice_cache = None
    # def _expires_at(self) -> float | None:
    #     if self.timeout:
    #         return time.monotonic() + self.timeout

    async def on_timeout(self):
        await asyncio.sleep(2)
        for child in self.children:
            child.disabled = True
        await self.message.delete()

    @discord.ui.select(
        placeholder="Choose a Action to log ",
        options=[
            discord.SelectOption(
                label=log_name,
                description=log_desc,
            )
            for log_name, log_desc in Log_options.items()
        ],
        row=0,
    )
    async def action_callback(self, select1, interaction: discord.Interaction):
        choice = select1.values[0]
        logname = "mod_log" if choice == "Moderation" else "message_log" if choice == "Messages" else "automod_log"
        self.choice_cache = logname
        await interaction.response.defer(ephemeral=True, invisible=True)

    @discord.ui.select(
        select_type=discord.ComponentType.channel_select,
        placeholder="Choose a channel to log ",
        channel_types=[discord.ChannelType.text],
        row=1,
    )
    async def channel_callback(self, select2, interaction: discord.Interaction):
        channel: discord.TextChannel = select2.values[0]
        method: str = self.children[0].values[0]
        logname: str = "mod_log" if method == "Moderation" else "message_log" if method == "Messages" else "automod_log"
        await Guild.update_or_create(discord_id=interaction.guild.id, defaults={logname: channel.id})
        # guild = await Guild.filter(discord_id=interaction.guild.id)
        # await guild.update_from_dict({method: channel}).save()
        embed = discord.Embed(
            title=f"{method} logging channel updated to {channel.mention}.",
            color=0x0060FF,
            description=("Current logging channels:\n"),
            timestamp=discord.utils.utcnow(),
        )
        embed.add_field(name="Moderation", value=str(1))
        embed.add_field(name="Message", value=str(1))
        embed.add_field(name="Automoderation", value=str(1))

        await interaction.response.edit_message(embed=embed, view=SetLogs())


class SetLogsButton(discord.ui.View):
    @discord.ui.button(label="Manage", style=discord.ButtonStyle.primary, emoji="😎")
    async def button_callback(self, button, interaction):
        embed = discord.Embed(
            title="Set method and channel to receive logs", color=0x0060FF, description=("Current logging channels:\n")
        )
        embed.add_field(name="Moderation", value=str(1))
        embed.add_field(name="Message", value=str(1))
        embed.add_field(name="Automoderation", value=str(1))
        view = SetLogs()

        await interaction.response.send_message(embed=embed, ephemeral=True, view=view)


class ModLog(Cog, name="ModLog"):
    """Logging for server events and staff actions."""

    def __init__(self, bot: Bot):
        self.bot = bot
        self._ignored = {event: [] for event in Event}

        self._cached_edits = []

    async def upload_log(
        self, messages: t.Iterable[discord.Message], actor_id: int, attachments: t.Iterable[t.List[str]] = None
    ) -> str:
        """Upload message logs to the database and return a URL to a page for viewing the logs."""
        if attachments is None:
            attachments = []

        response = await self.bot.api_client.post(
            "bot/deleted-messages",
            json={
                "actor": actor_id,
                "creation": datetime.now(timezone.utc).isoformat(),
                "deletedmessage_set": [
                    {
                        "id": message.id,
                        "author": message.author.id,
                        "channel_id": message.channel.id,
                        "content": message.content.replace("\0", ""),  # Null chars cause 400.
                        "embeds": [embed.to_dict() for embed in message.embeds],
                        "attachments": attachment,
                    }
                    for message, attachment in zip_longest(messages, attachments, fillvalue=[])
                ],
            },
        )

        return  # f"{URLs.site_logs_view}/{response['id']}"

    async def send_log_message(
        self,
        icon_url: t.Optional[str],
        colour: t.Union[discord.Colour, int],
        title: t.Optional[str],
        text: str,
        thumbnail: t.Optional[t.Union[str, discord.Asset]] = None,
        channel_id: int = None,
        ping_everyone: bool = False,
        files: t.Optional[t.List[discord.File]] = None,
        content: t.Optional[str] = None,
        additional_embeds: t.Optional[t.List[discord.Embed]] = None,
        timestamp_override: t.Optional[datetime] = None,
        footer: t.Optional[str] = None,
    ) -> Context:
        """Generate log embed and send to logging channel."""
        await self.bot.wait_until_guild_available()
        # Truncate string directly here to avoid removing newlines
        embed = discord.Embed(description=text[:4093] + "..." if len(text) > 4096 else text)

        if title and icon_url:
            embed.set_author(name=title, icon_url=icon_url)

        embed.colour = colour
        embed.timestamp = timestamp_override or datetime.utcnow()

        if footer:
            embed.set_footer(text=footer)

        if thumbnail:
            embed.set_thumbnail(url=thumbnail)

        if ping_everyone:
            if content:
                content = f"<@&{Roles.moderators}> {content}"
            else:
                content = f"<@&{Roles.moderators}>"

        # Truncate content to 2000 characters and append an ellipsis.
        if content and len(content) > 2000:
            content = content[: 2000 - 3] + "..."

        channel = self.bot.get_channel(channel_id)
        log_message = await channel.send(content=content, embed=embed, files=files)

        if additional_embeds:
            for additional_embed in additional_embeds:
                await channel.send(embed=additional_embed)

        return await self.bot.get_context(log_message)  # Optionally return for use with antispam

    async def get_audit_log_entry(
        self,
        guild: discord.Guild,
        action: AuditLogAction,
        target: discord.abc.Snowflake,
    ) -> t.Optional[AuditLogEntry]:
        """Retrieves an audit log entry that affected a specified entity.
        Parameters
        ----------
        guild : discord.Guild
            The guild to search logs for
        action : AuditLogAction
            The type of action to look for
        target : discord.abc.Snowflake
            The entity that was affected by this action
        Returns
        -------
        Optional[AuditLogEntry]
            The entry that was found or None if there is no entry matching requested conditions
        """
        entry = await guild.audit_logs(action=action).find(lambda entry: entry.target.id == target.id)
        return entry

    async def get_logs_channel(self, guild: t.Union[discord.Guild, int]) -> discord.TextChannel:
        """Get The Logging Channel Of A Guild
        Parameters
        ----------
        guild : Union[discord.Guild, int]
            The Guild To Find The Channel For
        Returns
        -------
        [discord.TextChannel]
            The Logging Channel
        """
        guild_id = guild.id if isinstance(guild, discord.Guild) else int(guild)

        guild_model = (await Guild.get_or_create(discord_id=guild_id))[0]

        logging = await Guild.get(discord_id=guild_model)

        if logging.enabled:
            logging_channel_id = logging.channel_id

            text_channels = self.bot.get_guild(guild).text_channels if isinstance(guild, int) else guild.text_channels

            logging_channel = discord.utils.get(text_channels, id=logging_channel_id)
            if logging_channel is None:
                pass
            else:
                return logging_channel
        else:
            return

    @command(name="setlogs")
    async def logs_command(self, ctx: Context):
        """Get and set info about the logging method of the guild."""
        assert self.bot.user
        embed = discord.Embed(
            title=f"{ctx.guild}s Logging",
            description=("View and Manage the server logging channels.\n"),
            colour=0x0060FF,
        )
        embed.set_thumbnail(url=self.bot.user.display_avatar.url)
        embed.add_field(name="Server Count", value=str(len(self.bot.guilds)))
        embed.add_field(name="User Count", value=str(len(self.bot.users)))
        view = SetLogsButton()
        await ctx.send(embed=embed, view=view, delete_after=7)

    @commands.cooldown(1, 2, BucketType.user)
    @command(
        name="logging",
        description="Toggle Logging on/off",
        extras={"Examples": "logging toggle on\nlogging toggle off\nlogging toggle True\nlogging toggle False"},
    )
    async def logging_toggle(self, ctx: commands.Context, toggle: t.Union[str, bool]):

        guild = await Guild.from_context(ctx)

        logging = await Guild.get_or_none(guild=guild)

        if isinstance(toggle, str):
            if toggle == "on":
                toggle = True
            elif toggle == "off":
                toggle = False
            elif toggle != "on" or "off":
                embed = discord.Embed(
                    color=Colours.ERROR,
                    description=f"{Emojis.ERROR} `toggle` expects `on`/`off`, not `{str(toggle)}`",
                )
                await ctx.send(embed=embed)
                return

        logging.is_logging = toggle
        await logging.save(update_fields=["is_logging"])
        await logging.refresh_from_db(fields=["is_logging"])

        embed = discord.Embed(
            color=Colours.DEFAULT,
            description=f"**Logging Toggled To:** `{toggle}`,\n Remember to set modlogs channel, messagelogs channel and automods channel\nThey can be the same channel, but things can get messy!",
        )

        await ctx.send(embed=embed)

    @commands.cooldown(1, 2, BucketType.user)
    @command(
        name="modlogs",
        aliases=("ml", "mlchannel", "logmods", "modlogs channel"),
        description="Set the channel to log moderation",
        extras={"Examples": "modlogs 1234567\nmodlogs #channel(mention)"},
    )
    async def modlogs_channel(self, ctx: commands.Context, channel: t.Union[discord.TextChannel, int]):
        channel_id = channel.id if isinstance(channel, discord.TextChannel) else int(channel)

        guild = await Guild.from_context(ctx)

        logging = await Guild.get_or_none(guild=guild)

        logging.mod_log = channel_id

        await logging.save(update_fields=["mod_log"])
        await logging.refresh_from_db(fields=["mod_log"])

        channel = ctx.guild.get_channel(channel_id)

        embed = discord.Embed(
            color=Colours.DEFAULT,
            description=f"**Modlogs Channel Updated Too:** {channel.mention}\n Remember to set messagelogs channel and automods channel\nThey can be the same channel, but things can get messy",
        )

        await ctx.send(embed=embed)

    # @commands.cooldown(1, 2, BucketType.user)
    # @logging.command(
    #     name="view",
    #     description="View all logs channels",
    # )
    # async def logging_view(self, ctx: commands.Context):
    #     loading_embed = discord.Embed(
    #         color=Colors.DEFAULT,
    #         description=f"{Emoji.LOADING_CIRCLE} Fetching Stats...",
    #     )
    #     message = await ctx.send(embed=loading_embed)

    #     guild = (await Guild.get_or_create(discord_id=ctx.guild.id))[0]

    #     logging = await ServerLogging.get(guild=guild)
    #     await message.edit(content=None, embed=format_logging_model(logging))

    # @commands.cooldown(1, 2, BucketType.user)
    # @logging.command(
    #     name="ignore",
    #     description="Set Channels To Be Ignored From Logging",
    #     extras={"Examples": "`logging ignore #mychannel`\n`logging ignore #mychannel1 #mychannel2 #mychannel3`"},
    # )
    # async def logging_ignore(self, ctx: commands.Context, channels: Greedy[discord.TextChannel]):
    #     if not channels:
    #         embed = discord.Embed(
    #             color=Colors.ERROR,
    #             description=f"{Emoji.ERROR} No Valid Channels Were Provided",
    #         )
    #         await ctx.send(embed=embed)
    #         return

    #     guild = await Guild.from_context(ctx)

    #     already_ignored_channels = []

    #     new_ignored_channels = []

    #     for channel in channels:
    #         ignored, exists = await ServerLogging.get_or_create(  # FIXME
    #             guild=guild, ignored_logging_channels=channel.id
    #         )
    #         if not exists:
    #             already_ignored_channels.append(channel)
    #         else:
    #             new_ignored_channels.append(channel)

    #     if already_ignored_channels:
    #         embed = discord.Embed(
    #             color=Colors.ERROR,
    #             description=f"{', '.join([channel.mention for channel in already_ignored_channels])} Is Already Being Ignored.",
    #         )
    #         await ctx.send(embed=embed)
    #         return

    #     embed = discord.Embed(
    #         color=Colors.SUCCESS,
    #         description=f"{', '.join([channel.mention for channel in new_ignored_channels])} Are Now Being Ignored.",
    #     )
    #     await ctx.send(embed=embed)
    #     await ctx.message.add_reaction(Emoji.CHECKMARK)

    @Cog.listener()
    async def on_guild_channel_create(self, channel: GUILD_CHANNEL) -> None:
        """Log channel create event to mod log."""
        if not self.bot.guilds_info_cache[f"{channel.guild.id}"]:
            return

        # if channel.guild.id not in self.bot.guilds_info_cache.keys():
        #     return

        if isinstance(channel, discord.CategoryChannel):
            title = "Category created"
            message = f"{channel.name} (`{channel.id}`)"
        elif isinstance(channel, discord.VoiceChannel):
            title = "Voice channel created"

            if channel.category:
                message = f"{channel.category}/{channel.name} (`{channel.id}`)"
            else:
                message = f"{channel.name} (`{channel.id}`)"
        else:
            title = "Text channel created"

            if channel.category:
                message = f"{channel.category}/{channel.name} (`{channel.id}`)"
            else:
                message = f"{channel.name} (`{channel.id}`)"

        await self.send_log_message(Icons.hash_green, Colours.soft_green, title, message)

    @Cog.listener()
    async def on_guild_channel_delete(self, channel: GUILD_CHANNEL) -> None:
        """Log channel delete event to mod log."""
        if not self.bot.guilds_info_cache[f"{channel.guild.id}"]:
            return

        if isinstance(channel, discord.CategoryChannel):
            title = "Category deleted"
        elif isinstance(channel, discord.VoiceChannel):
            title = "Voice channel deleted"
        else:
            title = "Text channel deleted"

        if channel.category and not isinstance(channel, discord.CategoryChannel):
            message = f"{channel.category}/{channel.name} (`{channel.id}`)"
        else:
            message = f"{channel.name} (`{channel.id}`)"

        await self.send_log_message(
            Icons.hash_red,
            Colours.soft_red,
            title,
            message,
            channel_id=self.bot.guilds_info_cache[f"{channel.guild.id}"]["mod_log"],
        )

    @Cog.listener()
    async def on_guild_channel_update(self, before: GUILD_CHANNEL, after: GuildChannel) -> None:
        """Log channel update event to mod log."""
        if not self.bot.guilds_info_cache[f"{before.guild.id}"]:
            return

        if before.id in self._ignored[Event.guild_channel_update]:
            self._ignored[Event.guild_channel_update].remove(before.id)
            return

        diff = DeepDiff(before, after)
        changes = []
        done = []

        diff_values = diff.get("values_changed", {})
        diff_values.update(diff.get("type_changes", {}))

        for key, value in diff_values.items():
            if not key:  # Not sure why, but it happens
                continue

            key = key[5:]  # Remove "root." prefix

            if "[" in key:
                key = key.split("[", 1)[0]

            if "." in key:
                key = key.split(".", 1)[0]

            if key in done or key in CHANNEL_CHANGES_SUPPRESSED:
                continue

            if key in CHANNEL_CHANGES_UNSUPPORTED:
                changes.append(f"**{key.title()}** updated")
            else:
                new = value["new_value"]
                old = value["old_value"]

                # Discord does not treat consecutive backticks ("``") as an empty inline code block, so the markdown
                # formatting is broken when `new` and/or `old` are empty values. "None" is used for these cases so
                # formatting is preserved.
                changes.append(f"**{key.title()}:** `{old or 'None'}` **→** `{new or 'None'}`")

            done.append(key)

        if not changes:
            return

        message = ""

        for item in sorted(changes):
            message += f"{Emojis.bullet} {item}\n"

        if after.category:
            message = f"**{after.category}/#{after.name} (`{after.id}`)**\n{message}"
        else:
            message = f"**#{after.name}** (`{after.id}`)\n{message}"

        await self.send_log_message(
            Icons.hash_blurple,
            Colour.og_blurple(),
            "Channel updated",
            message,
            channel_id=self.bot.guilds_info_cache[f"{before.guild.id}"]["mod_log"],
        )

    @Cog.listener()
    async def on_guild_role_create(self, role: discord.Role) -> None:
        """Log role create event to mod log."""
        if not self.bot.guilds_info_cache[f"{role.guild.id}"]:
            return

        await self.send_log_message(
            Icons.crown_green,
            Colours.soft_green,
            "Role created",
            f"`{role.id}`",
            channel_id=self.bot.guilds_info_cache[f"{role.guild.id}"]["mod_log"],
        )

    @Cog.listener()
    async def on_guild_role_delete(self, role: discord.Role) -> None:
        """Log role delete event to mod log."""
        if not self.bot.guilds_info_cache[f"{role.guild.id}"]:
            return

        await self.send_log_message(
            Icons.crown_red,
            Colours.soft_red,
            "Role removed",
            f"{role.name} (`{role.id}`)",
            channel_id=self.bot.guilds_info_cache[f"{role.guild.id}"]["mod_log"],
        )

    @Cog.listener()
    async def on_guild_role_update(self, before: discord.Role, after: discord.Role) -> None:
        """Log role update event to mod log."""
        if not self.bot.guilds_info_cache[f"{before.guild.id}"]:
            return

        diff = DeepDiff(before, after)
        changes = []
        done = []

        diff_values = diff.get("values_changed", {})
        diff_values.update(diff.get("type_changes", {}))

        for key, value in diff_values.items():
            if not key:  # Not sure why, but it happens
                continue

            key = key[5:]  # Remove "root." prefix

            if "[" in key:
                key = key.split("[", 1)[0]

            if "." in key:
                key = key.split(".", 1)[0]

            if key in done or key == "color":
                continue

            if key in ROLE_CHANGES_UNSUPPORTED:
                changes.append(f"**{key.title()}** updated")
            else:
                new = value["new_value"]
                old = value["old_value"]

                changes.append(f"**{key.title()}:** `{old}` **→** `{new}`")

            done.append(key)

        if not changes:
            return

        message = ""

        for item in sorted(changes):
            message += f"{Emojis.bullet} {item}\n"

        message = f"**{after.name}** (`{after.id}`)\n{message}"

        await self.send_log_message(
            Icons.crown_blurple,
            Colour.og_blurple(),
            "Role updated",
            message,
            channel_id=self.bot.guilds_info_cache[f"{before.guild.id}"]["mod_log"],
        )

    @Cog.listener()
    async def on_guild_update(self, before: discord.Guild, after: discord.Guild) -> None:
        """Log guild update event to mod log."""
        if not self.bot.guilds_info_cache[f"{before.guild.id}"]:
            return

        diff = DeepDiff(before, after)
        changes = []
        done = []

        diff_values = diff.get("values_changed", {})
        diff_values.update(diff.get("type_changes", {}))

        for key, value in diff_values.items():
            if not key:  # Not sure why, but it happens
                continue

            key = key[5:]  # Remove "root." prefix

            if "[" in key:
                key = key.split("[", 1)[0]

            if "." in key:
                key = key.split(".", 1)[0]

            if key in done:
                continue

            new = value["new_value"]
            old = value["old_value"]

            changes.append(f"**{key.title()}:** `{old}` **→** `{new}`")

            done.append(key)

        if not changes:
            return

        message = ""

        for item in sorted(changes):
            message += f"{Emojis.bullet} {item}\n"

        message = f"**{after.name}** (`{after.id}`)\n{message}"

        await self.send_log_message(
            Icons.guild_update,
            Colour.og_blurple(),
            "Guild updated",
            message,
            thumbnail=after.icon.with_static_format("png"),
            channel_id=self.bot.guilds_info_cache[f"{before.id}"]["mod_log"],
        )

    @Cog.listener()
    async def on_member_ban(self, guild: discord.Guild, member: discord.Member) -> None:
        """Log ban event to user log."""
        if not self.bot.guilds_info_cache[f"{guild.id}"]:
            return

        if member.id in self._ignored[Event.member_ban]:
            self._ignored[Event.member_ban].remove(member.id)
            return

        await self.send_log_message(
            Icons.user_ban,
            Colours.soft_red,
            "User banned",
            format_user(member),
            thumbnail=member.display_avatar.url,
            channel_id=self.bot.guilds_info_cache[f"{guild.id}"]["mod_log"],
        )

    @Cog.listener()
    async def on_member_join(self, member: discord.Member) -> None:
        """Log member join event to user log."""
        if not self.bot.guilds_info_cache[f"{member.guild.id}"]:
            return

        now = datetime.now(timezone.utc)
        difference = abs(relativedelta(now, member.created_at))

        message = format_user(member) + "\n\n**Account age:** " + converters.humanize_delta(difference)

        if difference.days < 1 and difference.months < 1 and difference.years < 1:  # New user account!
            message = f"{Emojis.new} {message}"

        await self.send_log_message(
            Icons.sign_in,
            Colours.soft_green,
            "User joined",
            message,
            thumbnail=member.display_avatar.url,
            channel_id=self.bot.guilds_info_cache[f"{member.guild.id}"]["automod_log"],
        )

    @Cog.listener()
    async def on_member_remove(self, member: discord.Member) -> None:
        """Log member leave event to user log."""
        if not self.bot.guilds_info_cache[f"{member.guild.id}"]:
            return

        if member.id in self._ignored[Event.member_remove]:
            self._ignored[Event.member_remove].remove(member.id)
            return

        await self.send_log_message(
            Icons.sign_out,
            Colours.soft_red,
            "User left",
            format_user(member),
            thumbnail=member.display_avatar.url,
            channel_id=self.bot.guilds_info_cache[f"{member.guild.id}"]["mod_log"],
        )

    @Cog.listener()
    async def on_member_unban(self, guild: discord.Guild, member: discord.User) -> None:
        """Log member unban event to mod log."""
        if not self.bot.guilds_info_cache[f"{guild.id}"]:
            return

        if member.id in self._ignored[Event.member_unban]:
            self._ignored[Event.member_unban].remove(member.id)
            return

        await self.send_log_message(
            Icons.user_unban,
            Colour.og_blurple(),
            "User unbanned",
            format_user(member),
            thumbnail=member.display_avatar.url,
            channel_id=self.bot.guilds_info_cache[f"{guild.id}"]["mod_log"],
        )

    @staticmethod
    def get_role_diff(before: t.List[discord.Role], after: t.List[discord.Role]) -> t.List[str]:
        """Return a list of strings describing the roles added and removed."""
        changes = []
        before_roles = set(before)
        after_roles = set(after)

        for role in before_roles - after_roles:
            changes.append(f"**Role removed:** {role.name} (`{role.id}`)")

        for role in after_roles - before_roles:
            changes.append(f"**Role added:** {role.name} (`{role.id}`)")

        return changes

    @Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        """Log member update event to user log."""
        if not self.bot.guilds_info_cache[f"{before.guild.id}"]:
            return

        if before.id in self._ignored[Event.member_update]:
            self._ignored[Event.member_update].remove(before.id)
            return

        changes = self.get_role_diff(before.roles, after.roles)

        # The regex is a simple way to exclude all sequence and mapping types.
        diff = DeepDiff(before, after, exclude_regex_paths=r".*\[.*")

        # A type change seems to always take precedent over a value change. Furthermore, it will
        # include the value change along with the type change anyway. Therefore, it's OK to
        # "overwrite" values_changed; in practice there will never even be anything to overwrite.
        diff_values = {**diff.get("values_changed", {}), **diff.get("type_changes", {})}

        for attr, value in diff_values.items():
            if not attr:  # Not sure why, but it happens.
                continue

            attr = attr[5:]  # Remove "root." prefix.
            attr = attr.replace("_", " ").replace(".", " ").capitalize()

            new = value.get("new_value")
            old = value.get("old_value")

            changes.append(f"**{attr}:** `{old}` **→** `{new}`")

        if not changes:
            return

        message = ""

        for item in sorted(changes):
            message += f"{Emojis.bullet} {item}\n"

        message = f"{format_user(after)}\n{message}"

        await self.send_log_message(
            icon_url=Icons.user_update,
            colour=Colour.og_blurple(),
            title="Member updated",
            text=message,
            thumbnail=after.display_avatar.url,
            channel_id=self.bot.guilds_info_cache[f"{before.guild.id}"]["mod_log"],
        )

    def is_message_blacklisted(self, message: Message) -> bool:
        """Return true if the message is in a blacklisted thread or channel."""
        # Ignore bots or DMs
        if message.author.bot or not message.guild:
            return True

        return self.is_channel_ignored(message.channel.id)

    def is_channel_ignored(self, channel_id: int) -> bool:
        """
        Return true if the channel, or parent channel in the case of threads, passed should be ignored by modlog.
        Currently ignored channels are:
        1. Channels not in the guild we care about (constants.Guild.id).
        2. Channels that mods do not have view permissions to
        3. Channels in constants.Guild.modlog_blacklist
        """
        channel = self.bot.get_channel(channel_id)

        # Ignore not found channels, DMs, and messages outside of the main guild.
        if not channel or not hasattr(channel, "guild") or not self.bot.guilds_info_cache[f"{channel.guild.id}"]:
            return True

        # Look at the parent channel of a thread.
        if isinstance(channel, Thread):
            channel = channel.parent

        # Mod team doesn't have view permission to the channel.
        if not channel.permissions_for(channel.guild.get_role(Roles.moderation)).view_channel:
            return True

        return  # channel.id in GuildConstant.modlog_blacklist

    async def log_cached_deleted_message(self, message: discord.Message) -> None:
        """
        Log the message's details to message change log.
        This is called when a cached message is deleted.
        """
        channel = message.channel
        author = message.author

        if self.is_message_blacklisted(message):
            return

        if message.id in self._ignored[Event.message_delete]:
            self._ignored[Event.message_delete].remove(message.id)
            return

        if channel.category:
            response = (
                f"**Author:** {format_user(author)}\n"
                f"**Channel:** {channel.category}/#{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{message.id}`\n"
                f"**Sent at:** {format_dt(message.created_at)}\n"
                f"[Jump to message]({message.jump_url})\n"
                "\n"
            )
        else:
            response = (
                f"**Author:** {format_user(author)}\n"
                f"**Channel:** #{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{message.id}`\n"
                f"**Sent at:** {format_dt(message.created_at)}\n"
                f"[Jump to message]({message.jump_url})\n"
                "\n"
            )

        if message.attachments:
            # Prepend the message metadata with the number of attachments
            response = f"**Attachments:** {len(message.attachments)}\n" + response

        # Shorten the message content if necessary
        content = message.clean_content
        remaining_chars = 4090 - len(response)

        if len(content) > remaining_chars:
            botlog_url = await self.upload_log(messages=[message], actor_id=message.author.id)
            ending = f"\n\nMessage truncated, [full message here]({botlog_url})."
            truncation_point = remaining_chars - len(ending)
            content = f"{content[:truncation_point]}...{ending}"

        response += f"{content}"

        await self.send_log_message(
            Icons.message_delete,
            Colours.soft_red,
            "Message deleted",
            response,
            channel_id=self.bot.guilds_info_cache[f"{message.guild.id}"]["message_log"],
        )

    async def log_uncached_deleted_message(self, event: discord.RawMessageDeleteEvent) -> None:
        """
        Log the message's details to message change log.
        This is called when a message absent from the cache is deleted.
        Hence, the message contents aren't logged.
        """
        await self.bot.wait_until_guild_available()
        if self.is_channel_ignored(event.channel_id):
            return

        if event.message_id in self._ignored[Event.message_delete]:
            self._ignored[Event.message_delete].remove(event.message_id)
            return

        channel = self.bot.get_channel(event.channel_id)

        if channel.category:
            response = (
                f"**Channel:** {channel.category}/#{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{event.message_id}`\n"
                f"**Sent at:** {format_dt(snowflake_time(event.message_id))}\n"
                "\n"
                "This message was not cached, so the message content cannot be displayed."
            )
        else:
            response = (
                f"**Channel:** #{channel.name} (`{channel.id}`)\n"
                f"**Message ID:** `{event.message_id}`\n"
                f"**Sent at:** {format_dt(snowflake_time(event.message_id))}\n"
                "\n"
                "This message was not cached, so the message content cannot be displayed."
            )

        await self.send_log_message(
            Icons.message_delete,
            Colours.soft_red,
            "Message deleted",
            response,
            channel_id=self.bot.guilds_info_cache[f"{event.guild_id}"]["message_log"],
        )

    @Cog.listener()
    async def on_raw_message_delete(self, event: discord.RawMessageDeleteEvent) -> None:
        """Log message deletions to message change log."""
        if event.cached_message is not None:
            await self.log_cached_deleted_message(event.cached_message)
        else:
            await self.log_uncached_deleted_message(event)

    @Cog.listener()
    async def on_message_edit(self, msg_before: discord.Message, msg_after: discord.Message) -> None:
        """Log message edit event to message change log."""
        if self.is_message_blacklisted(msg_before):
            return

        self._cached_edits.append(msg_before.id)

        if msg_before.content == msg_after.content:
            return

        channel = msg_before.channel
        channel_name = f"{channel.category}/#{channel.name}" if channel.category else f"#{channel.name}"

        cleaned_contents = (escape_markdown(msg.clean_content).split() for msg in (msg_before, msg_after))
        # Getting the difference per words and group them by type - add, remove, same
        # Note that this is intended grouping without sorting
        diff = difflib.ndiff(*cleaned_contents)
        diff_groups = tuple(
            (diff_type, tuple(s[2:] for s in diff_words))
            for diff_type, diff_words in itertools.groupby(diff, key=lambda s: s[0])
        )

        content_before: t.List[str] = []
        content_after: t.List[str] = []

        for index, (diff_type, words) in enumerate(diff_groups):
            sub = " ".join(words)
            if diff_type == "-":
                content_before.append(f"[{sub}](http://o.hi)")
            elif diff_type == "+":
                content_after.append(f"[{sub}](http://o.hi)")
            elif diff_type == " ":
                if len(words) > 2:
                    sub = (
                        f"{words[0] if index > 0 else ''}"
                        " ... "
                        f"{words[-1] if index < len(diff_groups) - 1 else ''}"
                    )
                content_before.append(sub)
                content_after.append(sub)

        response = (
            f"**Author:** {format_user(msg_before.author)}\n"
            f"**Channel:** {channel_name} (`{channel.id}`)\n"
            f"**Message ID:** `{msg_before.id}`\n"
            "\n"
            f"**Before**:\n{' '.join(content_before)}\n"
            f"**After**:\n{' '.join(content_after)}\n"
            "\n"
            f"[Jump to message]({msg_after.jump_url})"
        )

        if msg_before.edited_at:
            # Message was previously edited, to assist with self-bot detection, use the edited_at
            # datetime as the baseline and create a human-readable delta between this edit event
            # and the last time the message was edited
            timestamp = msg_before.edited_at
            delta = converters.humanize_delta(msg_after.edited_at, msg_before.edited_at)
            footer = f"Last edited {delta} ago"
        else:
            # Message was not previously edited, use the created_at datetime as the baseline, no
            # delta calculation needed
            timestamp = msg_before.created_at
            footer = None

        await self.send_log_message(
            Icons.message_edit,
            Colour.og_blurple(),
            "Message edited",
            response,
            channel_id=self.bot.guilds_info_cache[f"{msg_before.guild.id}"]["message_log"],
            timestamp_override=timestamp,
            footer=footer,
        )

    @Cog.listener()
    async def on_raw_message_edit(self, event: discord.RawMessageUpdateEvent) -> None:
        """Log raw message edit event to message change log."""
        if event.guild_id is None:
            return  # ignore DM edits

        await self.bot.wait_until_guild_available()
        try:
            channel = self.bot.get_channel(int(event.data["channel_id"]))
            message = await channel.fetch_message(event.message_id)
        except discord.NotFound:  # Was deleted before we got the event
            return

        if self.is_message_blacklisted(message):
            return

        await asyncio.sleep(1)  # Wait here in case the normal event was fired

        if event.message_id in self._cached_edits:
            # It was in the cache and the normal event was fired, so we can just ignore it
            self._cached_edits.remove(event.message_id)
            return

        channel = message.channel
        channel_name = f"{channel.category}/#{channel.name}" if channel.category else f"#{channel.name}"

        before_response = (
            f"**Author:** {format_user(message.author)}\n"
            f"**Channel:** {channel_name} (`{channel.id}`)\n"
            f"**Message ID:** `{message.id}`\n"
            "\n"
            "This message was not cached, so the message content cannot be displayed."
        )

        after_response = (
            f"**Author:** {format_user(message.author)}\n"
            f"**Channel:** {channel_name} (`{channel.id}`)\n"
            f"**Message ID:** `{message.id}`\n"
            "\n"
            f"{message.clean_content}"
        )

        await self.send_log_message(
            Icons.message_edit,
            Colour.og_blurple(),
            "Message edited (Before)",
            before_response,
            channel_id=self.bot.guilds_info_cache[f"{event.guild_id}"]["message_log"],
        )

        await self.send_log_message(
            Icons.message_edit,
            Colour.og_blurple(),
            "Message edited (After)",
            after_response,
            channel_id=self.bot.guilds_info_cache[f"{event.guild_id}"]["message_log"],
        )

    @Cog.listener()
    async def on_thread_update(self, before: Thread, after: Thread) -> None:
        """Log thread archiving, un-archiving and name edits."""
        if self.is_channel_ignored(after.id):
            log.trace("Ignoring update of thread %s (%d)", after.mention, after.id)
            return

        if before.name != after.name:
            await self.send_log_message(
                Icons.hash_blurple,
                Colour.og_blurple(),
                "Thread name edited",
                (
                    f"Thread {after.mention} (`{after.id}`) from {after.parent.mention} (`{after.parent.id}`): "
                    f"`{before.name}` -> `{after.name}`"
                ),
            )
            return

        if not before.archived and after.archived:
            colour = Colours.soft_red
            action = "archived"
            icon = Icons.hash_red
        elif before.archived and not after.archived:
            colour = Colours.soft_green
            action = "un-archived"
            icon = Icons.hash_green
        else:
            return

        await self.send_log_message(
            icon,
            colour,
            f"Thread {action}",
            (
                f"Thread {after.mention} ({after.name}, `{after.id}`) from {after.parent.mention} "
                f"(`{after.parent.id}`) was {action}",
            ),
            channel_id=self.bot.guilds_info_cache[f"{before.guild.id}"]["mod_log"],
        )

    @Cog.listener()
    async def on_thread_delete(self, thread: Thread) -> None:
        """Log thread deletion."""
        if self.is_channel_ignored(thread.id):
            log.trace("Ignoring deletion of thread %s (%d)", thread.mention, thread.id)
            return

        await self.send_log_message(
            Icons.hash_red,
            Colours.soft_red,
            "Thread deleted",
            (
                f"Thread {thread.mention} ({thread.name}, `{thread.id}`) from {thread.parent.mention} "
                f"(`{thread.parent.id}`) deleted"
            ),
            channel_id=self.bot.guilds_info_cache[f"{thread.guild.id}"]["mod_log"],
        )

    @Cog.listener()
    async def on_thread_create(self, thread: Thread) -> None:
        """Log thread creation."""
        if self.is_channel_ignored(thread.id):
            log.trace("Ignoring creation of thread %s (%d)", thread.mention, thread.id)
            return

        await self.send_log_message(
            Icons.hash_green,
            Colours.soft_green,
            "Thread created",
            (
                f"Thread {thread.mention} ({thread.name}, `{thread.id}`) from {thread.parent.mention} "
                f"(`{thread.parent.id}`) created"
            ),
            channel_id=self.bot.guilds_info_cache[f"{thread.guild.id}"]["mod_log"],
        )


def setup(bot: Bot) -> None:
    """Load the ModLog cog."""
    bot.add_cog(ModLog(bot))
