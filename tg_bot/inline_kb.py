from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

start_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="swagger чайника", url="http://192.168.1.71:8000/docs")],
        [InlineKeyboardButton(text="лс", url="https://t.me/Ntttnttn")]
        
    ]
)


cancel_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Выход", callback_data="cancel_fsm_boil")]
    ])

stop_boil_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить нагрев", callback_data="stop_boil")]
    ])

