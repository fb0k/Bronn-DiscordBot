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


# aioredis.util._converters[bool] = lambda x: b"1" if x else b"0"
# redis: aioredis.Redis


# async def connect_redis() -> None:
#     global redis

#     redis = aioredis.Redis(await aioredis.create_connection(constants.Redis.uri))


# asyncio.ensure_future(connect_redis())


# def from_redis_hash(cls, hashmap: dict) -> dict:
#     return {
#         k: v == "1" if isinstance(
#             cls._meta.fields_map[k], fields.BooleanField) else v
#         for k, v in hashmap.items()
#     }


# def redis_hashmap(instance) -> dict:
#     return {
#         k: getattr(instance, k)
#         for k in instance._meta.db_fields
#         if getattr(instance, k) is not None
#     }


# async def c_save(obj, update_fields=[]) -> None:
#     redis_hashmap(obj)
#     await asyncio.wait([c(obj) for c in obj.__cache_updaters])
#     await obj.save(update_fields=update_fields)


# def cached_model(*, key: str):
#     def predicate(cls: type) -> type:
#         nonlocal key

#         if not hasattr(cls, "__cache_updaters"):
#             cls.__cache_updaters = []

#         async def c_get_or_create(cls=cls, cached_key=None, **kwargs):
#             cached = await c_get_from_cache(cached_key)
#             if cached:
#                 return cls(**from_redis_hash(cls, cached)), False

#             obj, created = await cls.get_or_create(**{key: cached_key}, **kwargs)
#             await c_update_cache(obj)
#             return obj, created

#         async def c_get_or_none(cls=cls, cached_key=None, **kwargs):
#             cached = await c_get_from_cache(cached_key)
#             if cached:
#                 return cls(**from_redis_hash(cls, cached))

#             obj = await cls.get_or_none(**{key: cached_key}, **kwargs)
#             if obj is not None:
#                 await c_update_cache(obj)
#             return obj

#         async def c_get(cls=cls, cached_key=None, **kwargs):
#             cached = await c_get_from_cache(cached_key)
#             if cached:
#                 return cls(**from_redis_hash(cls, cached))

#             obj = await cls.get(**{key: cached_key}, **kwargs)
#             await c_update_cache(obj)
#             return obj

#         async def c_get_from_cache(value):
#             return await redis.hgetall(
#                 f"{cls.__name__};{key};{value}", encoding="utf-8"
#             )

#         async def c_update_cache(obj) -> None:
#             await redis.hmset_dict(
#                 f"{cls.__name__};{key};{getattr(obj, key)}", redis_hashmap(obj)
#             )

#         cls.__cache_updaters.append(c_update_cache)

#         cleankey: str = key.replace("__", "_")

#         # Internal methods added for possible use cases
#         setattr(cls, "c_update_cache_by_" + cleankey, c_update_cache)
#         setattr(cls, "c_get_from_cache_by_" + cleankey, c_get_from_cache)

#         # The save method
#         setattr(cls, "c_save", c_save)

#         # The classmethods
#         setattr(cls, "c_get_or_create_by_" + cleankey,
#                 classmethod(c_get_or_create))
#         setattr(cls, "c_get_or_none_by_" + cleankey,
#                 classmethod(c_get_or_none))
#         setattr(cls, "c_get_by_" + cleankey, classmethod(c_get))
#         return cls

#     return predicate


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
    async def update_by_guild(cls, field_name: str, value: Any, guild_id: int) -> bool:
        """Updates a database field with the given value. Returns True if the value is not 0."""
        await cls.update_or_create({field_name: value}, guild_id=guild_id)
        return value != 0

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
    
    @classmethod
    async def append_by_guild(cls, field: str, value: Any, guild_id: int):
        obj = await cls.get(guild_id=guild_id)
        await cls.update_or_create({field: obj.ArrayAppend(F(field), value)}, guild_id=guild_id)
        await obj.refresh_from_db(fields=[field])
        return obj
    
    @classmethod
    async def remove_by_guild(cls, field: str, value: Any, guild_id: int):
        obj = (await cls.get_or_create(guild_id=guild_id))[0]
        await cls.update_or_create({field: obj.ArrayRemove(F(field), value)}, guild_id=guild_id)
        await obj.refresh_from_db(fields=[field])
        return obj

    async def remove(self, field: str, value: Any):
        self.__dict__[field] = self.ArrayRemove(F("whitelist"), value)
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


class Roles(BaseModel):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=30)
    role_id = fields.BigIntField()
    is_mod = fields.BooleanField(default=False)
    comment = fields.TextField(default=None, unique=False, null=True)
    guild = fields.ForeignKeyField("B0F.Guild", related_name="Roles")


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


# class OSU(Model):
#     id = fields.BigIntField(pk=True)
#     username = fields.TextField(default=None, unique=False)
#     skin = fields.TextField(default="Default Skin", unique=False)
#     passive = fields.BooleanField(default=True)
#     discord_id = fields.BigIntField()
#     guild = fields.ForeignKeyField("B0F.Guild", related_name="OSU")


class AFKModel(BaseModel):
    id = fields.BigIntField(pk=True)
    afk_user_id = fields.BigIntField()
    start_time = fields.DatetimeField(auto_now_add=True)
    enabled = fields.BooleanField(default=True)
    nickname = fields.TextField(default=None, null=True)
    message = fields.TextField(default=None, null=True)
    guild = fields.ForeignKeyField("B0F.Guild", related_name="AFK")


# class Snipe(Model):
#     id = fields.BigIntField(pk=True)
#     enabled = fields.BooleanField(default=True)
#     guild = fields.ForeignKeyField("B0F.Guild", related_name="Snipe")


# class Captcha(Model):
#     id = fields.BigIntField(pk=True)
#     enabled = fields.BooleanField(default=False)
#     guild = fields.ForeignKeyField("B0F.Guild", related_name="Captcha")
#     # Types: Audio, Text, Picture, Arithmetic
#     type = fields.TextField(default="text")


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
    api_key = fields.ForeignKeyField("B0F.Keys", related_name="Users", null=True)
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
    guild = fields.ForeignKeyField("B0F.Guild", related_name="filterlist", pk=True)
    whitelist = ArrayField(str, null=True)

    def __str__(self):
        return self.whitelist


class Filters_test(BaseModel):
    whitelist = ArrayField(str, null=True)
    guild_id = fields.BigIntField()


class Keys(BaseModel):
    key_id = fields.UUIDField(pk=True)
    enabled = fields.BooleanField(default=False)
    # 0 = Normal | 1 = Premium | 2 = Bot Owner
    level = fields.TextField(default="0")


class Sometests(BaseModel):
    id = fields.IntField(pk=True)
    type = fields.CharField(max_length=20)
    allowed = fields.BooleanField(default=False)
    guild_id = fields.BigIntField()

    class Meta:
        unique_together = ("guild_id", "type")


class Filters_test2(BaseModel):
    whitelist = ArrayField(str, null=True)
    # guild = fields.OneToOneField(
    #     "B0F.Guild", on_delete=fields.CASCADE, related_name="whitelist", pk=True)
    guild = fields.ForeignKeyField("B0F.Guild", related_name="whitelist", pk=True)

    def __str__(self):
        return self.whitelist
