from typing import Any
import os
import yaml

ROOT_DIR = os.path.abspath(os.curdir)

CONFIG_PATH = "config.yaml"

with open(CONFIG_PATH) as f:
    config = yaml.load(f, yaml.Loader)

TORTOISE_CONFIG: dict[str, Any] = {
    "connections": {"default": config["DATABASE_URI"]},
    "apps": {
        config["TORTOISE_APP_NAME"]: {
            "models": [config["DATABASE_MODEL_PATH"], "aerich.models"],
            "default_connection": "default",
        }
    },
    "use_tz": config["DATABASE_USE_TZ"],
    
}
