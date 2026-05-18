import aiohttp
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from .api_client import _boil, _stop_boil
from .inline_kb import cancel_kb, stop_boil_kb

class BoilKettleFSM(StatesGroup):
    waiting_for_temp = State()
    waiting_for_mode = State() #на будущее для поддержание температуры
    waiting_for_time_hitting = State() #тоже на будущее
    
    
boil_router = Router()


@boil_router.message(Command('boil')) 
async def cmd_start_boil(message: Message, state: FSMContext):
    await message.answer("Введите желаюмую температуру? (число от 40 до 99)", reply_markup=cancel_kb) 
    await state.set_state(BoilKettleFSM.waiting_for_temp) 
    
@logger.catch
@boil_router.message(BoilKettleFSM.waiting_for_temp)
async def process_temp(message: Message, state: FSMContext, aio_session: aiohttp.ClientSession):
    text = message.text.strip()
    if not text.isdigit():
        await message.reply("Введите температуру числом", reply_markup=cancel_kb)
        return
    
    input_num = int(text)
    if 40 <= input_num <= 99:
        processing_msg = await message.answer("Включаю чайник..")
        response = await _boil(session=aio_session, temp=input_num)
        if response.get('success') == True:
            await processing_msg.edit_text(f"Отлично, чайник включил нагрев до {input_num}",reply_markup=stop_boil_kb)
            await state.clear()
        else:
            await processing_msg.edit_text(f"Чайнику не удалось включить нагрев. Попробуйте еще раз")
            return  
    else:
        logger.warning(f"Пользователь вводит чтото странное, у него желаемая температуру {input_num}")
        await message.reply(f"Число желаемой температуры должно быть строго от 40 до 99", reply_markup=cancel_kb) #правда поставить на температуру от 90+ пока что не выйдет и будет 100С 
        
        
@boil_router.callback_query(F.data == "cancel_fsm_boil") 
async def cancel_boil_handler(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    
    await callback.answer()
    
    await callback.message.edit_text("<b>Действие отмененно</b>")
    


@boil_router.callback_query(F.data == "stop_boil")
async def stop_boil_callback_handler(callback: CallbackQuery, aio_session: aiohttp.ClientSession):
    await callback.answer("Останавливаем нагрев...")
    await callback.message.edit_text("Выключаю чайник")
    response = await _stop_boil(session=aio_session)
    if response.get('success'):
        await callback.message.edit_text(f"Нагрев отменен успешно")
    else:
        await callback.message.edit_text(f"Нагрев не удалось отменить. Попробуйте еще раз")      