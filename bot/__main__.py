import logging

from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler

from .config import TELEGRAM_TOKEN
from .handlers import (
    callback_handler,
    cmd_add,
    cmd_list,
    cmd_pause,
    cmd_remove,
    cmd_resume,
    cmd_sdadd,
    cmd_sdlink,
    cmd_sdlist,
    cmd_start,
    cmd_status,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start",   cmd_start))
    app.add_handler(CommandHandler("list",    cmd_list))
    app.add_handler(CommandHandler("add",     cmd_add))
    app.add_handler(CommandHandler("remove",  cmd_remove))
    app.add_handler(CommandHandler("pause",   cmd_pause))
    app.add_handler(CommandHandler("resume",  cmd_resume))
    app.add_handler(CommandHandler("status",  cmd_status))
    app.add_handler(CommandHandler("sdlist",  cmd_sdlist))
    app.add_handler(CommandHandler("sdadd",   cmd_sdadd))
    app.add_handler(CommandHandler("sdlink",  cmd_sdlink))
    app.add_handler(CallbackQueryHandler(callback_handler))

    logger.info("Allowlist bot started.")
    app.run_polling()


if __name__ == "__main__":
    main()
