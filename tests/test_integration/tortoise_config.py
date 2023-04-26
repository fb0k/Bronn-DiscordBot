from typing import Any
import os


ROOT_DIR = os.path.abspath(os.curdir)


TORTOISE_TO_PG_CONFIG_TESTS: dict[str, Any] = {
    "connections": {"default": "asyncpg://postgres@localhost:5432/testingubot"},
    "apps": {
        "B0F": {
            "models": ["tests.models", "aerich.models"],
            "default_connection": "default",
        }
    },
    "use_tz": False,
}
