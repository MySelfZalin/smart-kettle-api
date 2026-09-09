import time

import aiohttp
from aiogram import Router, types
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext

from tg_bot.api_client import _get_state, _stop_boil
from tg_bot.inline_kb import start_kb

rout = Router()


@rout.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext):
    await state.clear()
    current_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    await message.answer(f"Время щас <code>{current_time}</code>", reply_markup=start_kb)


@rout.message(Command("status"))
async def get_state(message: types.Message, aio_session: aiohttp.ClientSession):
    processing_msg = await message.answer("Получаю данные с датчиков..")
    response_dict = await _get_state(session=aio_session)

    if response_dict is None:
        await processing_msg.edit_text("Не удалось получить данные. Попробуйте еще раз")
        return

    current_temp = response_dict["current_temp"]
    status_text = response_dict["status"]

    text = f"☕ <b>Статус чайника:</b>\n\n<b>Текущая температура:</b> {current_temp}°C\n<b>Состояние:</b> {status_text}"

    await processing_msg.edit_text(text)


@rout.message(Command("stop"))
async def stop_boil(message: types.Message, aio_session: aiohttp.ClientSession):
    processing_msg = await message.answer("Выключаю чайник..")
    response = await _stop_boil(session=aio_session)

    if response.get("success"):
        await processing_msg.edit_text("Нагрев отменен успешно")
    else:
        await processing_msg.edit_text("Нагрев не удалось отменить. Попробуйте еще раз")


@rout.message(Command("my_id"))
async def get_TGid(message: types.Message):
    id = message.from_user.id
    await message.answer(f"твой айди {id}")


@rout.message(Command("graphics"))
async def get_graphics(message: types.Message):
    from tg_bot.graphics import generate_graphics_image
    from aiogram.types import BufferedInputFile

    processing_msg = await message.answer("Рисую график и считаю статистику...")

    buf, stats = await generate_graphics_image()
    
    text = "⚡ <b>Статистика энергопотребления:</b>\n\n"
    for period, data in stats.items():
        text += f"<b>За {period}:</b> {data['kwh']} кВт*ч (≈ {data['cost']} руб.)\n"

    photo = BufferedInputFile(buf.read(), filename="chart.png")
    
    await message.answer_photo(photo=photo, caption=text)
    await processing_msg.delete()
