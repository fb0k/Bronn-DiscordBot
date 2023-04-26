"""Tests to assert async methods to create, set unique attributes and get objects from a DB(postgres)."""

# Tortoise already ensures that passed attributes are of the field type, no need to test that.

import pytest
from tests.models import Sometests, Guild, Filterlist
from tortoise.exceptions import IntegrityError


@pytest.mark.asyncio
async def test_create_object() -> None:
    """Set object, insert(DB) if not duplicate, assert inserted.

    GIVEN CreateFilterCommand with valid type, allowed, and guild_id properties
    WHEN the execute method is called
    THEN a new Filter must exist in the database with the same attributes

    * CreateFilterCommand is a Model with the same properties as the model being tested,
    but with a custom method called 'execute'.
    ** Due to tortoise fieldtypes and python reasoning:
    type: text, will accept int, bools
    allowed: bool, will accept any input, empyt str,lists is False, int > 0 is true
    guild_id: int, will accept str if the content is a int eg. '123'
    """
    obj = await Sometests.create(
        type=".test",
        allowed=False,
        guild_id=12345,
    )

    db_obj = await Sometests.get(id=obj.id)

    assert db_obj.type == obj.type
    assert db_obj.allowed == obj.allowed
    assert db_obj.guild_id == obj.guild_id


@pytest.mark.asyncio
async def test_create_object_already_exists() -> None:
    """Create object, assert no other object can have same attrb.

    GIVEN CreateFilterCommand with 'type' and 'guild_id' of a existing entry in the DB
    WHEN the execute method is called
    THEN the IntegrityError exception must be raised, meaning duplicate value in unique field

    * Model parameter, unique_together=[field x, field y], was used to ensure
    each guild_id has no duplicate type attribute.
    """
    await Sometests.create(
        type=".best",
        allowed=True,
        guild_id=123456,
    )

    obj = Sometests(
        type=".best",
        allowed=False,
        guild_id=123456,
    )

    with pytest.raises(IntegrityError):
        await obj.save()


@pytest.mark.asyncio
async def test_modify_object() -> None:
    """Create object, Modify it, assert updated values, same object.

    GIVEN CreateFilterCommand with 'type' and 'guild_id' of a existing entry in the DB
    WHEN the update method is called
    THEN existing object is modified, with no new entries

     * Model parameter, unique_together=[field x, field y], was used to ensure
    each guild_id has no duplicate type attribute.
    """
    old = await Sometests.create(
        type=".best",
        allowed=True,
        guild_id=123456,
    )

    updated = await old.update_by_guild("allowed", False, old.guild_id)

    assert updated.id == old.id
    assert updated.type == old.type
    assert updated.allowed == False != old.allowed
    assert updated.guild_id == old.guild_id
    assert len(await Sometests.all().values_list()) == 1


@pytest.mark.asyncio
async def test_delete_object() -> None:
    """Create object, delete it, assert updated table, remaing objects unnafected.

    GIVEN CreateFilterCommand with 'type' and 'guild_id' of a existing entry in the DB
    WHEN the update method is called
    THEN existing object is modified, with no new entries

     * Model parameter, unique_together=[field x, field y], was used to ensure
    each guild_id has no duplicate type attribute.
    """
    obj = await Sometests.create(
        type=".best",
        allowed=True,
        guild_id=123456,
    )

    other = await Sometests.create(
        type=".test",
        allowed=False,
        guild_id=654321,
    )

    await obj.delete()

    assert len(await Sometests.all().values_list()) == 1


@pytest.mark.asyncio
async def test_create_object_FKrelation() -> None:
    """Create relation, assert ForeignKeyField has the same value.

    GIVEN CreateFilterCommand with valid type, allowed, and guild_id properties
    WHEN the execute method is called
    THEN a new Filter must exist in the database with the same attributes

    * CreateFilterCommand is a Model with the same properties as the model being tested,
    but with a custom method called 'execute'.
    ** Due to tortoise fieldtypes and python reasoning:
    type: text, will accept int, bools
    allowed: bool, will accept any input, empyt str,lists is False, int > 0 is true
    guild_id: int, will accept str if the content is a int eg. '123'
    """
    prt = await Guild.create(discord_id=12345)
    chd = await Filterlist.create(guild_id=12345, whitelist=[".test", ".best"])

    assert chd.whitelist == [".test", ".best"]
    assert prt.discord_id == 12345 == chd.guild_id


@pytest.mark.asyncio
async def test_delete_parent_object_FKrelation() -> None:
    """Create relation, delete parent, assert deleted parent and child.

    GIVEN a child model object(contains ForeignKeyField)
    WHEN the delete(parent object) method is called
    THEN child object must be deleted aswell


    ** Due to tortoise fieldtypes and python reasoning:
    type: text, will accept int, bools
    allowed: bool, will accept any input, empyt str,lists is False, int > 0 is true
    guild_id: int, will accept str if the content is a int eg. '123'
    """
    prt = await Guild.create(discord_id=12345)
    chd = await Filterlist.create(guild_id=12345, whitelist=[".test", ".best"])

    await prt.delete()

    assert len(await Filterlist.all().values_list()) == 0
    assert len(await Guild.all().values_list()) == 0


@pytest.mark.asyncio
async def test_delete_child_object_FKrelation() -> None:
    """Create relation, delete child, assert deleted child with unchanged parent.

    GIVEN a child model object(contains ForeignKeyField)
    WHEN the delete(child object) method is called
    THEN parent object must remain unchanged within its class


    ** Due to tortoise fieldtypes and python reasoning:
    type: text, will accept int, bools
    allowed: bool, will accept any input, empyt str,lists is False, int > 0 is true
    guild_id: int, will accept str if the content is a int eg. '123'
    """
    prt = await Guild.create(discord_id=12345)
    chd = await Filterlist.create(guild_id=12345, whitelist=[".test", ".best"])

    await chd.delete()

    assert len(await Filterlist.all().values_list()) == 0
    assert len(await Guild.all().values_list()) == 1
