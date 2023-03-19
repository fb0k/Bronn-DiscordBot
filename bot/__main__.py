import sys


# from bot import bot
# from bot import Bot
from bot import Bot
from log import get_logger, setup_sentry


setup_sentry()
bot: Bot = Bot(development_mode="development")


if __name__ == "__main__":
    try:
        bot._start()

    except Exception:
        message = "{}. {}, line: {}".format(
            sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2].tb_lineno
        )
        log = get_logger("bot")
        log.fatal("", exc_info=Exception)
        log.fatal(message)

        exit(69)
