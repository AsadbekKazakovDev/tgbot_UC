from aiogram import Bot, Dispatcher, types
from aiogram.types import Message
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command
import asyncio
import logging
import json
from config import BOT_TOKEN, ADMIN_ID

dp = Dispatcher(storage=MemoryStorage())

class OrderStates(StatesGroup):
    choosing_uc = State()
    entering_pubg_id = State()
    choosing_payment = State()
    sending_screenshot = State()

with open("locale/uz.json", "r", encoding="utf-8") as f:
    uz = json.load(f)
with open("locale/ru.json", "r", encoding="utf-8") as f:
    ru = json.load(f)

lang_data = {"uz": uz, "ru": ru}
user_lang = {}

@dp.message(Command("start"))
async def start_handler(message: Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    builder.button(text="🇺🇿 O'zbekcha", callback_data="lang_uz")
    builder.button(text="🇷🇺 Русский", callback_data="lang_ru")
    await message.answer("Tilni tanlang / Выберите язык:", reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data and c.data.startswith("lang_"))
async def language_selected(callback_query: types.CallbackQuery, state: FSMContext):
    lang = callback_query.data.split("_")[1]
    user_lang[callback_query.from_user.id] = lang
    await state.set_state(OrderStates.choosing_uc)
    builder = InlineKeyboardBuilder()
    uc_list = lang_data[lang]["uc_options"]
    for uc in uc_list:
        builder.button(text=f"{uc['label']} – {uc['price']}", callback_data=f"uc_{uc['label']}")
    await callback_query.message.edit_text(lang_data[lang]["choose_uc"], reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data and c.data.startswith("uc_"))
async def uc_chosen(callback_query: types.CallbackQuery, state: FSMContext):
    uc = callback_query.data.split("_")[1]
    await state.update_data(uc_amount=uc)
    await state.set_state(OrderStates.entering_pubg_id)
    lang = user_lang.get(callback_query.from_user.id, "uz")
    await callback_query.message.answer(lang_data[lang]["enter_pubg_id"])

@dp.message(OrderStates.entering_pubg_id)
async def pubg_id_entered(message: Message, state: FSMContext):
    await state.update_data(pubg_id=message.text)
    await state.set_state(OrderStates.choosing_payment)
    lang = user_lang.get(message.from_user.id, "uz")
    builder = InlineKeyboardBuilder()
    for method in lang_data[lang]["payment_methods"]:
        builder.button(text=method, callback_data=f"pay_{method}")
    await message.answer(lang_data[lang]["choose_payment"], reply_markup=builder.as_markup())

@dp.callback_query(lambda c: c.data and c.data.startswith("pay_"))
async def payment_chosen(callback_query: types.CallbackQuery, state: FSMContext):
    method = callback_query.data.split("_")[1]
    await state.update_data(payment_method=method)
    lang = user_lang.get(callback_query.from_user.id, "uz")
    await callback_query.message.answer(lang_data[lang]["send_screenshot"])
    await callback_query.message.answer(lang_data[lang]["cards"])
    await state.set_state(OrderStates.sending_screenshot)

@dp.message(OrderStates.sending_screenshot)
async def screenshot_received(message: Message, state: FSMContext):
    data = await state.get_data()
    lang = user_lang.get(message.from_user.id, "uz")
    caption = (
        f"📥 Yangi buyurtma:\n\n"
        f"UC: {data['uc_amount']}\n"
        f"PUBG ID: {data['pubg_id']}\n"
        f"To'lov turi: {data['payment_method']}\n\n"
        f"Foydalanuvchi: @{message.from_user.username or message.from_user.id}"
    )

    if message.photo:
        await message.bot.send_photo(chat_id=ADMIN_ID, photo=message.photo[-1].file_id, caption=caption)
    else:
        await message.bot.send_message(chat_id=ADMIN_ID, text=caption)
    await message.answer(lang_data[lang]["done"])
    await state.clear()

from aiogram.client.bot import DefaultBotProperties

async def main():
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
