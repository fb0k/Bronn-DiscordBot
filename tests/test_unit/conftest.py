import pytest
from tortoise import Tortoise
import asyncio
from tortoise.exceptions import DBConnectionError, OperationalError
from bot.database import tortoise_config
from _pytest.fixtures import SubRequest




@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    policy = asyncio.WindowsSelectorEventLoopPolicy()
    res = policy.new_event_loop()
    asyncio.set_event_loop(res)
    res._close = res.close
    res.close = lambda: None

    yield res

    res._close()


@pytest.fixture(scope="function", autouse=True)
def db(request: SubRequest) -> None:
    async def _init_db() -> None:
        await Tortoise.init(tortoise_config.DBTEST_CONFIG)
        try:
            await Tortoise._drop_databases()
        except (DBConnectionError, OperationalError):  # pragma: nocoverage
            pass

        await Tortoise.init(tortoise_config.DBTEST_CONFIG, _create_db=True)
        await Tortoise.generate_schemas(safe=False)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(_init_db())
    yield

    request.addfinalizer(lambda: loop.run_until_complete(Tortoise._drop_databases()))

