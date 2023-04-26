"""Tests to assert async methods to create, list, get, append and remove items from array field in a DB(postgres)."""


import pytest
from tests.models import Roles, Guild, Roles_NOFK


@pytest.mark.asyncio
async def test_append_to_int_array_field_with_givenobject() -> None:
    """Create object, append to array field, assert updated values, same object.

    GIVEN DB Object with 'staff_roles' as a array field
    WHEN the append(custom) method is called
    THEN the new item is appened to array, lenght increments by 1, same object

    """

    old = await Roles_NOFK.create(guild_id=12345, staff_roles=[1234577, 1234588])
    old.staff_roles = await old.append("staff_roles", 1234599)

    new = await Roles_NOFK.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.staff_roles == old.staff_roles == [1234577, 1234588, 1234599]
    assert new.staff_roles[2] == 1234599 == old.staff_roles[2]
    assert len(new.staff_roles) == len(old.staff_roles) == 3
    assert len(await Roles_NOFK.all().values_list()) == 1


@pytest.mark.asyncio
async def test_remove_from_int_array_field_with_givenobject() -> None:
    """Create object, remove from array field, assert updated values, same object.

    GIVEN DB Object with 'staff_roles' as a array field
    WHEN the remove(custom) method is called
    THEN the item is removed from array, lenght decrements by 1, same object

    """

    old = await Roles_NOFK.create(guild_id=12345, staff_roles=[1234577, 1234588])
    old.staff_roles = await old.remove("staff_roles", 1234588)

    new = await Roles_NOFK.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.staff_roles == old.staff_roles == [1234577]
    assert new.staff_roles[0] == 1234577 == old.staff_roles[0]
    assert len(new.staff_roles) == len(old.staff_roles) == 1
    assert len(await Roles_NOFK.all().values_list()) == 1


@pytest.mark.asyncio
async def test_replace_from_array_field_with_givenobject() -> None:
    """Create object, replace from array field, assert updated values, same object.

    GIVEN DB Object with 'staff_roles' as a array field
    WHEN the replace(custom) method is called
    THEN the item is replaced from array, lenght unchanged, same object

    """

    old = await Roles_NOFK.create(guild_id=12345, staff_roles=[1234577, 1234588])
    old.staff_roles = await old.replaceitem("staff_roles", 1234577, 1234599)

    new = await Roles_NOFK.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.staff_roles == old.staff_roles == [1234599, 1234588]
    assert new.staff_roles[0] == 1234599 == old.staff_roles[0]
    assert len(new.staff_roles) == len(old.staff_roles) == 2
    assert len(await Roles_NOFK.all().values_list()) == 1


@pytest.mark.asyncio
async def test_iterate_from_array_field_with_givenobject() -> None:
    """Create object, iterate from array field, assert items are distinguishable.

    GIVEN DB Object with 'staff_roles' as a array field
    WHEN iterating through the array
    THEN array items are identifiable and distinguishable.

    """

    old = await Roles_NOFK.create(guild_id=12345, staff_roles=[1234577, 1234588])
    iterable = []

    for item in old.staff_roles:
        if item == 1234588:
            iterable.append(item)

    assert type(old.staff_roles) == list
    assert len(iterable) == 1
    assert iterable == [1234588]


@pytest.mark.asyncio
async def test_concatenate_to_array_field_with_givenobject() -> None:
    """Create object, concatenate to array field, assert updated values, same object.

    GIVEN DB Object with 'staff_roles' as a array field
    WHEN the concat(custom) method is called
    THEN the new items are concatenated to array, lenght increments by X, same object

    """

    old = await Roles_NOFK.create(guild_id=12345, staff_roles=[1234577, 1234588])
    otherarray = [333, 444, 555]
    old.staff_roles = await old.concat("staff_roles", otherarray)

    new = await Roles_NOFK.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.staff_roles == old.staff_roles == [1234577, 1234588, 333, 444, 555]
    assert new.staff_roles[2] == 333 == old.staff_roles[2]
    assert len(new.staff_roles) == len(old.staff_roles) == 5
    assert len(await Roles_NOFK.all().values_list()) == 1


@pytest.mark.asyncio
async def test_prepend_to_array_field_with_givenobject() -> None:
    """Create object, prepend to array field, assert updated values, same object.

    GIVEN DB Object with 'staff_roles' as a array field
    WHEN the prepend(custom) method is called
    THEN the new item is prepended to array, lenght increments by 1, same object

    """

    old = await Roles_NOFK.create(guild_id=12345, staff_roles=[1234577, 1234588])
    old.staff_roles = await old.prepend("staff_roles", 1234599)

    new = await Roles_NOFK.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.staff_roles == old.staff_roles == [1234599, 1234577, 1234588]
    assert new.staff_roles[0] == 1234599 == old.staff_roles[0]
    assert len(new.staff_roles) == len(old.staff_roles) == 3
    assert len(await Roles_NOFK.all().values_list()) == 1


@pytest.mark.asyncio
async def test_append_to_array_field_using_unique_attribute() -> None:
    """Create object, append to array field, assert updated values, same object.

    GIVEN DB Object with 'staff_roles' as a array field
    WHEN the append(custom) method is called
    THEN the new item is appened to array, lenght increments by 1, same object

    """
    await Guild.create(discord_id=12345)
    old = await Roles.create(guild_id=12345, staff_roles=[1234577, 1234588])
    old = await Roles.append_by_guild("staff_roles", 1234599, 12345)

    new = await Roles.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.staff_roles == old.staff_roles == [1234577, 1234588, 1234599]
    assert new.staff_roles[2] == 1234599 == old.staff_roles[2]
    assert len(new.staff_roles) == len(old.staff_roles) == 3
    assert len(await Roles.all().values_list()) == 1


@pytest.mark.asyncio
async def test_remove_from_array_field_using_unique_attribute() -> None:
    """Create object, append to array field, assert updated values, same object.

    GIVEN DB Object with 'staff_roles' as a array field
    WHEN the append(custom) method is called
    THEN the new item is appened to array, lenght increments by 1, same object

    """
    await Guild.create(discord_id=12345)
    old = await Roles.create(guild_id=12345, staff_roles=[1234577])
    old = await Roles.remove_by_guild(field="staff_roles", value=1234577, guild_id=12345)

    new = await Roles.get(guild_id=12345)

    assert new.guild_id == old.guild_id == 12345
    assert new.staff_roles == old.staff_roles
    assert len(new.staff_roles) == len(old.staff_roles) == 0
    assert len(await Roles.all().values_list()) == 1
