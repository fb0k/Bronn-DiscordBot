# import aioredis
from discord import Guild as GuildModel
from discord.ext.commands import Context
from tortoise import fields
from tortoise.expressions import F
from tortoise.models import Model


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


# @cached_model(key="discord_id")
class Guild(Model):
    # Core Components Of The Model
    discord_id = fields.BigIntField(pk=True)
    language = fields.TextField(default="en")
    prefix = fields.TextField(default=".")
    timezone = fields.TextField(default="UTC")
    automod = fields.BooleanField(default=False)
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

    # Some Fields When Doing Global Checks (soon™)
    blacklisted_channels = fields.BigIntField(null=True)

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


class GuildEvent(Model):
    id = fields.BigIntField(pk=True)
    description = fields.TextField(default=None, unique=False)
    old = fields.TextField(default=None, unique=False)
    new = fields.TextField(default=None, unique=False)
    timestamp = fields.DatetimeField(auto_now_add=True)
    guild = fields.ForeignKeyField("B0F.Guild", related_name="GuildEvent")


class Invite(Model):
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


class AFKModel(Model):
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


class Warns(Model):
    key = fields.IntField(pk=True)
    warn_id = fields.TextField()
    target_id = fields.BigIntField()
    warner_id = fields.BigIntField()
    guild = fields.ForeignKeyField("B0F.Guild", related_name="Warns")
    reason = fields.TextField(null=True)
    created_at = fields.DatetimeField(null=True, auto_now_add=True)


class Users(Model):
    user_id = fields.BigIntField(pk=True)
    commands_run = fields.BigIntField(default=0, null=True)
    tracking_enabled = fields.BooleanField(default=True)
    api_key = fields.ForeignKeyField("B0F.Keys", related_name="Users", null=True)

    async def increment(self, increase_no: int = 1):
        self.commands_run = F("commands_run") + increase_no
        await self.save(update_fields=["commands_run"])
        await self.refresh_from_db(fields=["commands_run"])
        return self.commands_run


class TagModel(Model):
    tag_id = fields.IntField(pk=True)
    name = fields.TextField()
    created_at = fields.DatetimeField(null=True, auto_now_add=True)
    author_id = fields.BigIntField()
    guild = fields.ForeignKeyField("B0F.Guild", related_name="Tags")
    content = fields.TextField()
    uses = fields.BigIntField()

    def __str__(self):
        return self.content


class Keys(Model):
    key_id = fields.UUIDField(pk=True)
    enabled = fields.BooleanField(default=False)
    # 0 = Normal | 1 = Premium | 2 = Bot Owner
    level = fields.TextField(default="0")
