"""
Intercept Cog Class creation, modify it, return the modified Cog Class
Adds a new attribute(emoji) to be passed on Cog creation
returns super().__new__ to override CogMeta __new__ constructor,
appending the new attr(emoji) to it.
CustomCog then will be used to create future Cogs
with the EmojiCogMeta __new__ constructor
"""


import discord
from discord.cog import CogMeta
from discord.ext import commands


# Create a new CogMeta, to be used as Cogs constructors
# appending new attrs added to existing discord.cog.CogMeta
# __new__ constructor
class EmojiCogMeta(discord.cog.CogMeta):
    def __new__(cls, *args, **kwargs) -> CogMeta:
        name, bases, attrs = args
        attrs["emoji"] = kwargs.pop("emoji", [])

        return super().__new__(cls, name, bases, attrs, **kwargs)


# Create a new Cog Class, with EmojiCogMeta __new__ constructor
class CustomCog(commands.Cog, metaclass=EmojiCogMeta):
    pass
