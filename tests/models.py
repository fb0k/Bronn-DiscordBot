# import aioredis
from discord import Guild as GuildModel
from discord.ext.commands import Context
from tortoise import fields
from tortoise.expressions import F
from tortoise.models import Model
from pypika.terms import Function
from enum import Enum
from typing import Any, List, Type, Union
from tortoise.exceptions import ConfigurationError
from tortoise.fields.base import Field


class ArrayField(Field):  # type: ignore
    """
    Array field.

    This field can store array of integer or string or Enums of these.
    Only postgres db supported.
    """

    indexable = False

    def __init__(self, elem_type: Type, **kwargs: Any) -> None:
        if not issubclass(elem_type, (int, str)):
            raise ConfigurationError("ArrayField only supports integer or string or Enums of these!")
        super().__init__(**kwargs)
        self.elem_type = elem_type

    def to_db_value(self, value: List[Union[int, str, Enum]], instance) -> List[Union[int, str]]:
        if value and issubclass(self.elem_type, Enum):
            return [v.value for v in value]
        return value

    def to_python_value(self, value: List[Union[int, str]]) -> List[Union[int, str, Enum]]:
        if value and issubclass(self.elem_type, Enum):
            return [self.elem_type(v) for v in value]
        return value

    @property
    def SQL_TYPE(self) -> str:  # type: ignore
        if issubclass(self.elem_type, int):
            return "INTEGER ARRAY"
        if issubclass(self.elem_type, str):
            return "TEXT ARRAY"


class BaseModel(Model):
    @classmethod
    async def update_by_guild(cls, field_name: str, value: Any, guild_id: int) -> Any:
        """Updates a database field with the given value. Returns True if the value is not 0."""
        obj = (await cls.update_or_create({field_name: value}, guild_id=guild_id))[0]
        return obj

    class ArrayAppend(Function):
        def __init__(self, field: str, value: Any) -> None:
            super().__init__("ARRAY_APPEND", field, value)

    class ArrayRemove(Function):
        def __init__(self, field: str, value: Any) -> None:
            super().__init__("ARRAY_REMOVE", field, value)

    class ArrayReplace(Function):
        def __init__(self, field: str, value: Any, newvalue: Any) -> None:
            super().__init__("ARRAY_REPLACE", field, value, newvalue)

    class ArrayConcatenate(Function):
        def __init__(self, field: str, array: Any) -> None:
            super().__init__("ARRAY_CAT", field, array)

    class ArrayPrepend(Function):
        def __init__(self, field: str, value: Any) -> None:
            super().__init__("ARRAY_PREPEND", value, field)

    async def append(self, field: str, value: Any):
        self.__dict__[field] = self.ArrayAppend(F(field), value)
        await self.save(update_fields=[field])
        await self.refresh_from_db(fields=[field])
        return self.__getattribute__(field)

    # @classmethod
    # async def append_by_guild(cls, field: str, value: Any, guild_id: int):
    #     obj = await cls.get(guild_id=guild_id)
    #     await cls.update_or_create({field: obj.ArrayAppend(F(field), value)}, guild_id=guild_id)
    #     await obj.refresh_from_db(fields=[field])
    #     return obj

    # async def remove_by_guild(self, field: str, value: str, guild_id: int):
    #     obj = await self.get(guild_id=guild_id)
    #     obj.ArrayRemove(F(field), value)
    #     await obj.save(update_fields=[field])
    #     await obj.refresh_from_db(fields=[field])
    #     return obj

    async def remove(self, field: str, value: Any):
        self.__dict__[field] = self.ArrayRemove(F(field), value)
        await self.save(update_fields=[field])
        await self.refresh_from_db(fields=[field])
        return self.__getattribute__(field)

    async def replaceitem(self, field: str, value: Any, newvalue: Any):
        self.__dict__[field] = self.ArrayReplace(F(field), value, newvalue)
        await self.save(update_fields=[field])
        await self.refresh_from_db(fields=[field])
        return self.__getattribute__(field)

    async def concat(self, field: str, array: Any):
        self.__dict__[field] = self.ArrayConcatenate(F(field), array)
        await self.save(update_fields=[field])
        await self.refresh_from_db(fields=[field])
        return self.__getattribute__(field)

    async def prepend(self, field: str, value: Any):
        self.__dict__[field] = self.ArrayPrepend(F(field), value)
        await self.save(update_fields=[field])
        await self.refresh_from_db(fields=[field])
        return self.__getattribute__(field)

    class Meta:
        abstract = True


# @cached_model(key="discord_id")
class Guild(BaseModel):
    # Core Components Of The Model
    discord_id = fields.BigIntField(pk=True)
    language = fields.TextField(default="en")
    prefix = fields.TextField(default=".")
    # timezone = fields.TextField(default="UTC")
    is_logging = fields.BooleanField(default=False)
    is_automod = fields.BooleanField(default=False)
    automod_log = fields.BigIntField(default=0)
    message_log = fields.BigIntField(default=0)
    mod_log = fields.BigIntField(default=0)
    suggestions = fields.BigIntField(default=0)

    changelog_enabled = fields.BooleanField(default=False)
    changelog_channel = fields.BigIntField(default=None, null=True)

    trusted_bot_owners = fields.BigIntField(null=True)

    # Some Checks (soon™)
    is_bot_blacklisted = fields.BooleanField(default=False)
    is_nsfw_disabled = fields.BooleanField(default=True)
    blacklisted_reason = fields.TextField(default="Violating TOS", unique=False)

    # Premium
    is_premium = fields.BooleanField(default=False)

    @classmethod
    async def from_id(cls, guild_id):
        # TODO: Implement caching in here or override get method
        return (await cls.get_or_create(discord_id=guild_id))[0]

    @classmethod
    async def from_guild_object(cls, guild: GuildModel):
        return await cls.from_id(guild.id)

    @classmethod
    async def from_context(cls, ctx: Context):
        return await cls.from_id(ctx.guild.id)

    @classmethod
    async def fetch_to_dict(self):
        d = {}
        objs = await Guild.all().values(
            "discord_id", "is_bot_blacklisted", "is_automod", "automod_log", "message_log", "mod_log", "is_logging"
        )
        for obj in objs:
            d[obj["discord_id"]] = obj

        return d


class GuildEvent(BaseModel):
    id = fields.BigIntField(pk=True)
    description = fields.TextField(default=None, unique=False)
    old = fields.TextField(default=None, unique=False)
    new = fields.TextField(default=None, unique=False)
    timestamp = fields.DatetimeField(auto_now_add=True)
    guild = fields.ForeignKeyField("B0F.Guild", related_name="GuildEvent")


class Invite(BaseModel):
    id = fields.BigIntField(pk=True)
    inviter_id = fields.BigIntField()
    invite_count_total = fields.IntField(default=0)
    invite_count_bonus = fields.IntField(default=0)
    invite_count_left = fields.IntField(default=0)
    max_account_age = fields.IntField(default=3)  # 3 = 3 days
    channel_id = fields.BigIntField(default=None, null=True)
    enabled = fields.BooleanField(default=True)
    guild = fields.ForeignKeyField("B0F.Guild", related_name="Invites")


class AFKModel(BaseModel):
    id = fields.BigIntField(pk=True)
    afk_user_id = fields.BigIntField()
    start_time = fields.DatetimeField(auto_now_add=True)
    enabled = fields.BooleanField(default=True)
    nickname = fields.TextField(default=None, null=True)
    message = fields.TextField(default=None, null=True)
    guild = fields.ForeignKeyField("B0F.Guild", related_name="AFK")


class Warns(BaseModel):
    id = fields.BigIntField(pk=True)
    warn_id = fields.TextField()
    target_id = fields.BigIntField()
    mod_id = fields.BigIntField()
    guild = fields.ForeignKeyField("B0F.Guild", related_name="Warns")
    reason = fields.TextField(null=True)
    created_at = fields.DatetimeField(null=True, auto_now_add=True)


class Users(BaseModel):
    user_id = fields.BigIntField(pk=True)
    commands_run = fields.BigIntField(default=0, null=True)
    tracking_enabled = fields.BooleanField(default=True)
    # api_key = fields.ForeignKeyField("B0F.Keys", related_name="Users", null=True)
    # numwarns = commands_run = fields.BigIntField(default=0, null=True)

    async def increment(self, increase_no: int = 1):
        self.commands_run = F("commands_run") + increase_no
        await self.save(update_fields=["commands_run"])
        await self.refresh_from_db(fields=["commands_run"])
        return self.commands_run

    # async def incwarns(self, increase_no: int = 1):
    #     self.numwarns = F("numwarns") + increase_no
    #     await self.save(update_fields=["numwarns"])
    #     await self.refresh_from_db(fields=["numwarns"])
    #     return self.numwarns

    # async def decwarns(self, increase_no: int = 1):
    #     self.numwarns = F("numwarns") - increase_no
    #     await self.save(update_fields=["numwarns"])
    #     await self.refresh_from_db(fields=["numwarns"])
    #     return self.numwarns


class Tags(BaseModel):
    tag_id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(null=True, auto_now_add=True)
    author_id = fields.BigIntField()
    guild = fields.ForeignKeyField("B0F.Guild", related_name="Tags")
    content = fields.TextField()
    uses = fields.BigIntField()

    def __str__(self):
        return self.content


class Filterlist(BaseModel):
    id = fields.BigIntField(pk=True)
    guild = fields.ForeignKeyField("B0F.Guild", related_name="filterlist", unique=True)
    whitelist = ArrayField(str, null=True)

    @classmethod
    async def append_by_guild(cls, field: str, value: Any, guild_id: int):
        obj = (await cls.get_or_create(guild_id=guild_id))[0]
        await cls.update_or_create({field: obj.ArrayAppend(F(field), value)}, guild_id=guild_id)
        await obj.refresh_from_db(fields=[field])
        return obj

    @classmethod
    async def remove_by_guild(cls, field: str, value: Any, guild_id: int):
        obj = await cls.get(guild_id=guild_id)
        await cls.update_or_create({field: obj.ArrayRemove(F(field), value)}, guild_id=guild_id)
        await obj.refresh_from_db(fields=[field])
        return obj

    def __str__(self):
        return self.whitelist


class Filterlist_NOFK(BaseModel):
    id = fields.BigIntField(pk=True)
    whitelist = ArrayField(str, null=True)
    guild_id = fields.BigIntField()


class Sometests(BaseModel):
    id = fields.IntField(pk=True)
    type = fields.CharField(max_length=20)
    allowed = fields.BooleanField(default=False)
    guild_id = fields.BigIntField()

    class Meta:
        unique_together = ("guild_id", "type")


class Roles(BaseModel):
    id = fields.BigIntField(pk=True)
    guild = fields.ForeignKeyField("B0F.Guild", related_name="roleslist", unique=True)
    mod_roles = ArrayField(int, null=True)
    staff_roles = ArrayField(int, null=True)

    @classmethod
    async def append_by_guild(cls, field: str, value: Any, guild_id: int):
        obj = (await cls.get_or_create(guild_id=guild_id))[0]
        await cls.update_or_create({field: obj.ArrayAppend(F(field), value)}, guild_id=guild_id)
        await obj.refresh_from_db(fields=[field])
        return obj

    @classmethod
    async def remove_by_guild(cls, field: str, value: Any, guild_id: int):
        obj = await cls.get(guild_id=guild_id)
        await cls.update_or_create({field: obj.ArrayRemove(F(field), value)}, guild_id=guild_id)
        await obj.refresh_from_db(fields=[field])
        return obj


class Roles_NOFK(BaseModel):
    id = fields.BigIntField(pk=True)
    guild_id = fields.BigIntField()
    mod_roles = ArrayField(int, null=True)
    staff_roles = ArrayField(int, null=True)
