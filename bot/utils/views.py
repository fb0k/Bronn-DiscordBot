import discord
from database.models import Guild
from Bronn import Bot


Log_options = {
    "Moderation": "Logs of moderation related action, like user ban or channel creation",
    "AutoModeration": "Logs of automatic bot related moderation, example, message filtering and urls deletion",
    "Messages": "Logs users deleted and edited messages in the server",
}


async def setlogsembed(choices: dict, view: discord.ui.View):
    guild = await Guild.get(discord_id=view.message.guild.id)
    # await Guild.filter()
    action = (
        "Moderation"
        if choices["action"] == "mod_log"
        else "Messages"
        if choices["action"] == "message_log"
        else "Automoderation"
    )
    embed = discord.Embed(
        title=f"```{action} logging channel updated to {choices['channel']}```",
        color=0x0060FF,
        description=("Current logging channels:\n"),
        timestamp=discord.utils.utcnow(),
    )
    embed.add_field(name="Moderation", value=guild.mod_log)
    embed.add_field(name="Message", value=guild.message_log)
    embed.add_field(name="Automoderation", value=guild.automod_log)

    return embed


class ActionSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            placeholder="Choose a Action to log ",
            options=[
                discord.SelectOption(
                    label=log_name,
                    description=log_desc,
                )
                for log_name, log_desc in Log_options.items()
            ],
        )

    async def callback(self, interaction: discord.Interaction):
        logname = (
            "mod_log"
            if self.values[0] == "Moderation"
            else "message_log"
            if self.values[0] == "Messages"
            else "automod_log"
        )
        self.view.choice_cache["action"] = logname
        self.view.action_check = True
        self.view.timeout += 20
        if self.view.action_check and self.view.channel_check:
            await Guild.update_or_create(
                discord_id=interaction.guild.id, defaults={logname: self.view.choice_cache["channel"].id}
            )
            embed = await setlogsembed(self.view.choice_cache, self.view)

            await interaction.response.edit_message(embed=embed, view=SetLogs())
        else:
            await interaction.response.defer(ephemeral=True, invisible=True)


class ChannelSelect(discord.ui.Select):
    def __init__(self) -> None:
        super().__init__(
            select_type=discord.ComponentType.channel_select,
            placeholder="Choose a channel to log ",
            channel_types=[discord.ChannelType.text],
        )

    async def callback(self, interaction: discord.Interaction):
        self.view.choice_cache["channel"] = self.values[0]
        self.view.channel_check = True
        self.view.timeout += 20
        if self.view.action_check and self.view.channel_check:
            await Guild.update_or_create(
                discord_id=interaction.guild.id,
                defaults={self.view.choice_cache["action"]: self.view.choice_cache["channel"].id},
            )
            embed = setlogsembed(self.view.choice_cache, self.view)
            await interaction.response.edit_message(embed=embed, view=SetLogs())
        else:
            await interaction.response.defer(ephemeral=True, invisible=True)


class SetLogs(discord.ui.View):
    def __init__(self, bot: Bot):
        super().__init__(timeout=20)
        self.bot = bot
        self.choice_cache = {}
        self.action_check = False
        self.channel_check = False

        self.add_item(ActionSelect())
        self.add_item(ChannelSelect())

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        await self.message.delete()


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
