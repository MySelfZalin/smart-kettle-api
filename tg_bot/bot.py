import asyncio
import logging
import aiohttp
import sys
from loguru import logger
from aiogram import Bot, Dispatcher, types
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import settings
from .routers import rout
from .boil_FSM import boil_router
from .constants import commands_list


class InterceptHandler(logging.Handler):
    def emit(self, record):
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        frame, depth = logging.currentframe(), 2
        while frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())



default_settings = DefaultBotProperties(
    parse_mode=ParseMode.HTML,
    protect_content=False,
    link_preview_prefer_small_media=True
)

session = AiohttpSession(proxy="http://127.0.0.1:10809") #обход блокировки при помощи xray vpn
bot = Bot(token=settings.BOT_TOKEN, session=session, default=default_settings) #с vpn

# bot = Bot(token=settings.BOT_TOKEN, default=default_settings) #без впн-а

dp = Dispatcher()
dp.include_routers(rout, boil_router)
   
#====================================================================

async def on_startup(dispatcher: Dispatcher):
    timeout = aiohttp.ClientTimeout(total=5)
    
    dispatcher["aio_session"] = aiohttp.ClientSession(timeout=timeout)
    logger.info("Сессия для FastAPI создана")   
    
    
async def on_shutdown(dispatcher: Dispatcher):
    session: aiohttp.ClientSession = dispatcher["aio_session"]
    await session.close()



async def main():
    logger.info("Запуск Telegram бота")
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_my_commands(commands=commands_list, scope=types.BotCommandScopeAllPrivateChats())
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())



if __name__ == "__main__":  
    logger.remove()
    logger.add(sys.stderr, format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>")
    logger.add("bot.log", rotation="5 MB", retention="10 days", encoding="utf-8", level="INFO")
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO, force=True)
    
    asyncio.run(main())   
