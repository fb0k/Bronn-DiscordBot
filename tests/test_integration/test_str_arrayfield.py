"""Tests to assert async methods to create, list, get, append and remove items from array field in a DB(postgres)."""


import pytest
from tests.models import Filterlist, Guild, Filterlist_NOFK


@pytest.mark.asyncio
async def test_append_to_array_field_with_givenobject() -> None:
    """Create object, append to array field, assert updated values, same object.

    GIVEN DB Object with 'whitelist' as a array field
    WHEN the append(custom) method is called
    THEN the new item is appened to array, lenght increments by 1, same object

    """

    old = await Filterlist_NOFK.create(guild_id=12345, whitelist=[".test", ".best"])
    old.whitelist = await old.append("whitelist", ".fast")

    new = await Filterlist_NOFK.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.whitelist == old.whitelist == [".test", ".best", ".fast"]
    assert new.whitelist[2] == ".fast" == old.whitelist[2]
    assert len(new.whitelist) == len(old.whitelist) == 3
    assert len(await Filterlist_NOFK.all().values_list()) == 1


@pytest.mark.asyncio
async def test_remove_from_array_field_with_givenobject() -> None:
    """Create object, remove from array field, assert updated values, same object.

    GIVEN DB Object with 'whitelist' as a array field
    WHEN the remove(custom) method is called
    THEN the item is removed from array, lenght decrements by 1, same object

    """

    old = await Filterlist_NOFK.create(guild_id=12345, whitelist=[".test", ".best"])
    old.whitelist = await old.remove("whitelist", ".test")

    new = await Filterlist_NOFK.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.whitelist == old.whitelist == [".best"]
    assert new.whitelist[0] == ".best" == old.whitelist[0]
    assert len(new.whitelist) == len(old.whitelist) == 1
    assert len(await Filterlist_NOFK.all().values_list()) == 1


@pytest.mark.asyncio
async def test_replace_from_array_field_with_givenobject() -> None:
    """Create object, replace from array field, assert updated values, same object.

    GIVEN DB Object with 'whitelist' as a array field
    WHEN the replace(custom) method is called
    THEN the item is replaced from array, lenght unchanged, same object

    """

    old = await Filterlist_NOFK.create(guild_id=12345, whitelist=[".test", ".best"])
    old.whitelist = await old.replaceitem("whitelist", ".test", ".fast")

    new = await Filterlist_NOFK.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.whitelist == old.whitelist == [".fast", ".best"]
    assert new.whitelist[0] == ".fast" == old.whitelist[0]
    assert len(new.whitelist) == len(old.whitelist) == 2
    assert len(await Filterlist_NOFK.all().values_list()) == 1


@pytest.mark.asyncio
async def test_iterate_from_array_field_with_givenobject() -> None:
    """Create object, iterate from array field, assert items are distinguishable.

    GIVEN DB Object with 'whitelist' as a array field
    WHEN iterating through the array
    THEN array items are identifiable and distinguishable.

    """

    old = await Filterlist_NOFK.create(guild_id=12345, whitelist=[".test", ".best"])
    iterable = []

    for item in old.whitelist:
        if item == ".best":
            iterable.append(item)

    assert type(old.whitelist) == list
    assert len(iterable) == 1
    assert iterable == [".best"]


@pytest.mark.asyncio
async def test_concatenate_to_array_field_with_givenobject() -> None:
    """Create object, concatenate to array field, assert updated values, same object.

    GIVEN DB Object with 'whitelist' as a array field
    WHEN the concat(custom) method is called
    THEN the new items are concatenated to array, lenght increments by X, same object

    """

    old = await Filterlist_NOFK.create(guild_id=12345, whitelist=[".test", ".best"])
    otherarray = [".xxx", ".hhh", ".abc"]
    old.whitelist = await old.concat("whitelist", otherarray)

    new = await Filterlist_NOFK.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.whitelist == old.whitelist == [".test", ".best", ".xxx", ".hhh", ".abc"]
    assert new.whitelist[2] == ".xxx" == old.whitelist[2]
    assert len(new.whitelist) == len(old.whitelist) == 5
    assert len(await Filterlist_NOFK.all().values_list()) == 1


@pytest.mark.asyncio
async def test_prepend_to_array_field_with_givenobject() -> None:
    """Create object, prepend to array field, assert updated values, same object.

    GIVEN DB Object with 'whitelist' as a array field
    WHEN the prepend(custom) method is called
    THEN the new item is prepended to array, lenght increments by 1, same object

    """

    old = await Filterlist_NOFK.create(guild_id=12345, whitelist=[".test", ".best"])
    old.whitelist = await old.prepend("whitelist", ".fast")

    new = await Filterlist_NOFK.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.whitelist == old.whitelist == [".fast", ".test", ".best"]
    assert new.whitelist[0] == ".fast" == old.whitelist[0]
    assert len(new.whitelist) == len(old.whitelist) == 3
    assert len(await Filterlist_NOFK.all().values_list()) == 1


@pytest.mark.asyncio
async def test_append_to_array_field_using_unique_attribute() -> None:
    """Create object, append to array field, assert updated values, same object.

    GIVEN DB Object with 'whitelist' as a array field
    WHEN the append(custom) method is called
    THEN the new item is appened to array, lenght increments by 1, same object

    """
    await Guild.create(discord_id=12345)
    old = await Filterlist.create(guild_id=12345, whitelist=[".test", ".best"])
    old = await Filterlist.append_by_guild("whitelist", ".fast", 12345)

    new = await Filterlist.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.whitelist == old.whitelist == [".test", ".best", ".fast"]
    assert new.whitelist[2] == ".fast" == old.whitelist[2]
    assert len(new.whitelist) == len(old.whitelist) == 3
    assert len(await Filterlist.all().values_list()) == 1


@pytest.mark.asyncio
async def test_remove_from_array_field_using_unique_attribute() -> None:
    """Create object, append to array field, assert updated values, same object.

    GIVEN DB Object with 'whitelist' as a array field
    WHEN the append(custom) method is called
    THEN the new item is appened to array, lenght increments by 1, same object

    """
    await Guild.create(discord_id=12345)
    old = await Filterlist.create(guild_id=12345, whitelist=[".test"])
    old = await Filterlist.remove_by_guild(field="whitelist", value=".test", guild_id=12345)

    new = await Filterlist.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.whitelist == old.whitelist
    assert len(new.whitelist) == len(old.whitelist) == 0
    assert len(await Filterlist.all().values_list()) == 1
