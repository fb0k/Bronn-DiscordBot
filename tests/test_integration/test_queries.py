from tests.models import Sometests
import pytest

"""Tests to assert async methods to create, fetch and list objects from a database(postgres) work"""

# Tortoise already ensures that passed attributes are of the field type, no need to test that


@pytest.mark.asyncio
async def test_list_objects():
    """
    GIVEN N unique objects
    WHEN the, query methods are called
    THEN a list and or dict must be returned with N 
    """
    obj1 = await Sometests.create(
        type=".cya",
        allowed=True,
        guild_id=123456,
    )
    obj2 = await Sometests.create(
        type=".hello",
        allowed=False,
        guild_id=123456,
    )

    obj3 = await Sometests.create(
        type=".yell",
        allowed=True,
        guild_id=123456,
    )

    query_to_list = await Sometests.all().values_list()
    query_to_dict = await Sometests.all().values()

    assert len(query_to_list) == 3
    assert query_to_dict[0] == dict(obj1)



@pytest.mark.asyncio
async def test_get_object_by_id():
    """
    GIVEN new object inserted in the database
    WHEN the get() method is called on object.id
    THEN it should return the inserted object
    """
    object = await Sometests.create(type=".jane", allowed=False, guild_id=654321)

    query = await Sometests.get(id=object.id)

    assert query.id == object.id


