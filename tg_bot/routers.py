from aiogram import types, Router, F, html
from aiogram.filters import CommandStart, Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
import time
import aiohttp
from tg_bot.inline_kb import start_kb
from tg_bot.api_client import _boil, _stop_boil

rout = Router()
   


@rout.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    await message.answer(f"Время щас <code>{current_time}</code>", reply_markup=start_kb)
   

   
@rout.message(Command("stop"))
async def stop_boil(message: types.Message, aio_session: aiohttp.ClientSession):
    processing_msg = await message.answer("Выключаю чайник..")
    response = await _stop_boil(session=aio_session)
    
    if response.get('success'):
        await processing_msg.edit_text(f"Нагрев отменен успешно")
    else:
        await processing_msg.edit_text(f"Нагрев не удалось отменить. Попробуйте еще раз")

