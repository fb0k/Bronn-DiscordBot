"""
Loads bot configuration from environment variables
and `.env` files. By default, this simply loads the
default configuration defined thanks to the `default`
keyword argument in each instance of the `Field` class
If two files called `.env` and `.env.server` are found
in the project directory, the values will be loaded
from both of them, thus overlooking the predefined defaults.
Any settings left out in the custom user configuration
will default to the values passed to the `default` kwarg.
"""
import os
from enum import Enum
from typing import Optional
from typing import Any
import database
from pydantic import BaseModel, BaseSettings, root_validator

# Load env files


class EnvConfig(BaseSettings):
    class Config:
        env_file = ".env", ".env.server",
        env_file_encoding = 'utf-8'
        env_nested_delimiter = '__'

# For setting debug or logs when starting program


class _Miscellaneous(EnvConfig):
    debug = True
    file_logs = False


Miscellaneous = _Miscellaneous()

# Read values from Miscellaneus, True or False
FILE_LOGS = Miscellaneous.file_logs
DEBUG_MODE = Miscellaneous.debug


class _Bot(EnvConfig):
    # Bot related constants, to override use bot_xxx = y, (bot_prefirx = '.')
    # Bot.name, to get a specific value

    EnvConfig.Config.env_prefix = "bot_"

    name = "B0F"
    discord_id = "bot_id"
    prefix = "!"
    sentry_dsn = "https://5a6c0fa78ab745b6b6166ff6ec413e22@o4504850831114240.ingest.sentry.io/4504850837536768"
    token = "bot_token"
    trace_loggers = "*"
    owners_ids = ["my_id", ]


Bot = _Bot()


class _Database(EnvConfig):

    EnvConfig.Config.env_prefix = "database_"

    uri = "db_url2"
    model_path = database.models
    # timezone = "UTC"
    use_tz = False


Database = _Database()


# class _TortoiseConfig(EnvConfig):

#     EnvConfig.Config.env_prefix = "tortoiseconfig_"

#     connections = {"default": Database.uri}
#     apps = {Bot.name: {
#             "models": [Database.model_path, "aerich.models"],
#             "default_connection": "default",
#             }
#             }
#     use_tz = Database.use_tz
#     timezone = Database.timezone


# TortoiseConfig = _TortoiseConfig()

TORTOISE_CONFIG: dict[str, Any] = {
    "connections": {"default": "db_url2"},
    "apps": {
        f'{Bot.name}': {
            "models": [f'{Database.model_path}', "aerich.models"],
            "default_connection": "default",
        }
    },
    "use_tz": Database.use_tz,
    # "timezone": f'{Database.timezone},
}


class _Channels(EnvConfig):
    # Channels ID's, 'channels_name = newid' to override
    # Channels.name, to get a specific ID

    EnvConfig.Config.env_prefix = "channels_"

    announcements = 354619224620138496
    serverlog = 748238795236704388
    modlog = 41424214214121
    automodlog = 729674110270963822
    messagelog = 704372456592506880
    chat = 458224812528238616
    admins = 458224812528238616
    admin_spam = 458224812528238616
    mods = 458224812528238616
    attachment_log = 458224812528238616
    staff_voice = 458224812528238616
    filter_log = 458224812528238616


# Object of _Channels, to receive attrs (Channels.name...)
Channels = _Channels()


class _Roles(EnvConfig):
    # Roles ID's, 'roles_name = newid' to override
    # Roles.name, to get a specific ID

    EnvConfig.Config.env_prefix = "roles_"

    # Self-assignable roles, see the Subscribe cog
    admins = 518565788744024082
    announcements = 463658397560995840
    moderators = 542431903886606399
    helpers = 897568414044938310
    staff = 988801794668908655
    mod_team = 988801794668908655
    owners = 988801794668908655
    muted = 277914926603829249


Roles = _Roles()


class _Categories(EnvConfig):
    # Categories ID's, 'Categories_name = newid' to override
    # Categories.name, to get a specific ID

    EnvConfig.Config.env_prefix = "categories_"

    logs = 468520609152892958
    moderators = 749736277464842262
    modmail = 714494672835444826
    appeals = 890331800025563216
    appeals_2 = 895417395261341766
    voice = 356013253765234688


Categories = _Categories()


class _Guild(EnvConfig):
    # Server Info, mod categories and channels etc
    # Guild.name to get a attr

    EnvConfig.Config.env_prefix = "guild_"

    id = 893622012717719634
    invite = ""

    moderation_categories = [
        Categories.moderators,
        Categories.modmail,

    ]
    moderation_channels = [Channels.admins, Channels.admin_spam, Channels.mods]
    modlog_blacklist = [
        Channels.attachment_log,
        Channels.messagelog,
        Channels.modlog,
        Channels.staff_voice,
        Channels.filter_log,
        Channels.automodlog,
        Channels.serverlog,

    ]
    moderation_roles = [Roles.admins, Roles.mod_team,
                        Roles.moderators, Roles.owners]
    staff_roles = [Roles.admins, Roles.helpers, Roles.mod_team, Roles.owners]


Guild = _Guild()


class Event(Enum):
    """
    Event names. This does not include every event (for example, raw
    events aren't here), but only events used in ModLog for now.
    """

    guild_channel_create = "guild_channel_create"
    guild_channel_delete = "guild_channel_delete"
    guild_channel_update = "guild_channel_update"
    guild_role_create = "guild_role_create"
    guild_role_delete = "guild_role_delete"
    guild_role_update = "guild_role_update"
    guild_update = "guild_update"

    member_join = "member_join"
    member_remove = "member_remove"
    member_ban = "member_ban"
    member_unban = "member_unban"
    member_update = "member_update"

    message_delete = "message_delete"
    message_edit = "message_edit"

    voice_state_update = "voice_state_update"


class ThreadArchiveTimes(Enum):
    HOUR = 60
    DAY = 1440
    THREE_DAY = 4320
    WEEK = 10080


class _Colours(EnvConfig):
    # Colours with Hexadecimal as values
    # Custom method to convert hex to int before passing

    EnvConfig.Config.env_prefix = "colours_"

    blue = 0x3775a8
    bright_green = 0x01d277
    orange = 0xe67e22
    pink = 0xcf84e0
    purple = 0xb734eb
    soft_green = 0x68c290
    soft_orange = 0xf9cb54
    soft_red = 0xcd6d6d
    white = 0xfffffe
    yellow = 0xffd241

    @root_validator(pre=True)
    def parse_hex_values(cls, values):
        for key, value in values.items():
            values[key] = int(value, 16)
        return values


Colours = _Colours()


class _Free(EnvConfig):
    EnvConfig.Config.env_prefix = "free_"

    activity_timeout = 600
    cooldown_per = 60.0
    cooldown_rate = 1


Free = _Free()


class Punishment(BaseModel):
    # Punishment time in seconds to a mute type punish

    remove_after = 600
    role_id: int = Roles.muted


class Rule(BaseModel):
    # Rule attrs for messages spam, will receive values
    # from Rules Class above, for each type of spam

    interval: int
    max: int


# Some help in choosing an appropriate name for this is appreciated
class ExtendedRule(Rule):
    # Attr used to check if messages were spam or not

    max_consecutive: int


# class Rules(BaseModel):
#     # Types of spams, each with specific Rule attribute(interval, max)

#     attachments: Rule = Rule(interval=10, max=6)
#     burst: Rule = Rule(interval=10, max=7)
#     chars: Rule = Rule(interval=5, max=4_200)
#     discord_emojis: Rule = Rule(interval=10, max=20)
#     duplicates: Rule = Rule(interval=10, max=3)
#     links: Rule = Rule(interval=10, max=10)
#     mentions: Rule = Rule(interval=10, max=5)
#     newlines: ExtendedRule = ExtendedRule(
#         interval=10, max=100, max_consecutive=10)
#     role_mentions: Rule = Rule(interval=10, max=3)


# class _AntiSpam(EnvConfig):
#     # Antispam config, with cache for the messages to be punished
#     # defaults of clean spam messages and ping are True
#     # Receive punishment and rules objects with attr values to be used
#     # in a method in the antispam cog

#     EnvConfig.Config.env_prefix = 'anti_spam_'

#     cache_size = 100

#     clean_offending = True
#     ping_everyone = True

#     punishment = Punishment()
#     rules = Rules()


# AntiSpam = _AntiSpam()


class _CleanMessages(EnvConfig):
    # N of messages allowed before cleaning the cache

    EnvConfig.Config.env_prefix = "clean_"

    message_limit = 10_000


CleanMessages = _CleanMessages()


class _Cooldowns(EnvConfig):
    EnvConfig.Config.env_prefix = "cooldowns_"

    tags = 60


Cooldowns = _Cooldowns()


class _Redis(EnvConfig):
    EnvConfig.Config.env_prefix = "redis_"

    host = ""  # "redis.default.svc.cluster.local"
    password = ""
    port = 6379
    use_fakeredis = False  # If this is True, Bot will use fakeredis.aioredis
    default_path = "C:/Redis"
    uri = "redis://localhost:6379"


Redis = _Redis()


class _BaseURLs(EnvConfig):
    EnvConfig.Config.env_prefix = "urls_"
    # CoinMarketCap API
    cmc_api = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    cmc_hearders = "application/json"

    # Discord API
    discord_api = "https://discordapp.com/api/v7/"


BaseURLs = _BaseURLs()


class _URLs(_BaseURLs):

    # Discord API endpoints
    discord_invite_api: str = "".join([BaseURLs.discord_api, "invites"])

    # Support links
    github = ""
    support_server = ""
    documentation = ""
    invite_url = ""


URLs = _URLs()


class _Emojis(EnvConfig):
    # Emojis abbreviations

    EnvConfig.Config.env_prefix = "emojis_"

    badge_bug_hunter = "<:bug_hunter_lvl1:743882896372269137>"
    error = ":x:"
    sucess = ":white_check_mark:"
    information = ":speech_balloon:"


Emojis = _Emojis()


class _Icons(EnvConfig):
    # Discord Icons jpg urls

    EnvConfig.Config.env_prefix = "icons_"

    crown_blurple = "https://cdn.discordapp.com/emojis/469964153289965568.png"
    crown_green = "https://cdn.discordapp.com/emojis/469964154719961088.png"
    crown_red = "https://cdn.discordapp.com/emojis/469964154879344640.png"

    defcon_denied = "https://cdn.discordapp.com/emojis/472475292078964738.png"    # noqa: E704
    defcon_shutdown = "https://cdn.discordapp.com/emojis/470326273952972810.png"  # noqa: E704
    defcon_unshutdown = "https://cdn.discordapp.com/emojis/470326274213150730.png"   # noqa: E704
    defcon_update = "https://cdn.discordapp.com/emojis/472472638342561793.png"   # noqa: E704

    filtering = "https://cdn.discordapp.com/emojis/472472638594482195.png"

    green_checkmark = "https://raw.githubusercontent.com/python-discord/branding/main/icons/checkmark/green-checkmark-dist.png"
    green_questionmark = "https://raw.githubusercontent.com/python-discord/branding/main/icons/checkmark/green-question-mark-dist.png"
    guild_update = "https://cdn.discordapp.com/emojis/469954765141442561.png"

    hash_blurple = "https://cdn.discordapp.com/emojis/469950142942806017.png"
    hash_green = "https://cdn.discordapp.com/emojis/469950144918585344.png"
    hash_red = "https://cdn.discordapp.com/emojis/469950145413251072.png"

    message_bulk_delete = "https://cdn.discordapp.com/emojis/469952898994929668.png"
    message_delete = "https://cdn.discordapp.com/emojis/472472641320648704.png"
    message_edit = "https://cdn.discordapp.com/emojis/472472638976163870.png"

    pencil = "https://cdn.discordapp.com/emojis/470326272401211415.png"

    questionmark = "https://cdn.discordapp.com/emojis/512367613339369475.png"

    remind_blurple = "https://cdn.discordapp.com/emojis/477907609215827968.png"
    remind_green = "https://cdn.discordapp.com/emojis/477907607785570310.png"
    remind_red = "https://cdn.discordapp.com/emojis/477907608057937930.png"

    sign_in = "https://cdn.discordapp.com/emojis/469952898181234698.png"
    sign_out = "https://cdn.discordapp.com/emojis/469952898089091082.png"

    superstarify = "https://cdn.discordapp.com/emojis/636288153044516874.png"
    unsuperstarify = "https://cdn.discordapp.com/emojis/636288201258172446.png"

    token_removed = "https://cdn.discordapp.com/emojis/470326273298792469.png"

    user_ban = "https://cdn.discordapp.com/emojis/469952898026045441.png"
    user_mute = "https://cdn.discordapp.com/emojis/472472640100106250.png"
    user_unban = "https://cdn.discordapp.com/emojis/469952898692808704.png"
    user_unmute = "https://cdn.discordapp.com/emojis/472472639206719508.png"
    user_update = "https://cdn.discordapp.com/emojis/469952898684551168.png"
    user_verified = "https://cdn.discordapp.com/emojis/470326274519334936.png"
    user_warn = "https://cdn.discordapp.com/emojis/470326274238447633.png"

    voice_state_blue = "https://cdn.discordapp.com/emojis/656899769662439456.png"
    voice_state_green = "https://cdn.discordapp.com/emojis/656899770094452754.png"
    voice_state_red = "https://cdn.discordapp.com/emojis/656899769905709076.png"


Icons = _Icons()


class _Keys(EnvConfig):
    # API keys

    EnvConfig.Config.env_prefix = "api_keys_"
    cmc = "cmc_key"

    youtube_api_key = ""

    spotify_client_id = ""
    spotify_client_secret = ""

    twitch_api_id = ""
    twitch_api_secret = ""

    praw_id = ""
    praw_secret = ""

    x_rapid_api_key = ""
    x_rapid_api_host = ""  # mashape-community-urban-dictionary.p.rapidapi.com

    some_random_api_key = ""

    statcord_api_key = ""

    dagpi_api_key = ""

    kawaii_red_api_token = ""

    genius_api_token = ""

    api_flash_token = ""

    azreal_api_token = ""

    random_stuff_api_key = ""


Keys = _Keys()


BOT_DIR = os.path.dirname(__file__)
PROJECT_ROOT = os.path.abspath(os.path.join(BOT_DIR, os.pardir))


# Default role combinations
MODERATION_ROLES = Guild.moderation_roles
STAFF_ROLES = Guild.staff_roles

# Channel combinations
MODERATION_CHANNELS = Guild.moderation_channels

# Category combinations
MODERATION_CATEGORIES = Guild.moderation_categories

# Git SHA for Sentry
GIT_SHA = os.environ.get("GIT_SHA", "development")


# Bot replies
NEGATIVE_REPLIES = [
    "Noooooo!!",
    "Nope.",
    "I'm sorry Dave, I'm afraid I can't do that.",
    "I don't think so.",
    "Not gonna happen.",
    "Out of the question.",
    "Huh? No.",
    "Nah.",
    "Naw.",
    "Not likely.",
    "No way, José.",
    "Not in a million years.",
    "Fat chance.",
    "Certainly not.",
    "NEGATORY.",
    "Nuh-uh.",
    "Not in my house!",
]

POSITIVE_REPLIES = [
    "Yep.",
    "Absolutely!",
    "Can do!",
    "Affirmative!",
    "Yeah okay.",
    "Sure.",
    "Sure thing!",
    "You're the boss!",
    "Okay.",
    "No problem.",
    "I got you.",
    "Alright.",
    "You got it!",
    "ROGER THAT",
    "Of course!",
    "Aye aye, cap'n!",
    "I'll allow it.",
]

ERROR_REPLIES = [
    "Please don't do that.",
    "You have to stop.",
    "Do you mind?",
    "In the future, don't do that.",
    "That was a mistake.",
    "You blew it.",
    "You're bad at computers.",
    "Are you trying to kill me?",
    "Noooooo!!",
    "I can't believe you've done this",
]
