from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery
import asyncio
import sqlite3
from adds import *

TOKEN = '7964962560:AAGF2LldCw0dZfqcqY0IAokhEbgvN9kIfkM'
conn = sqlite3.connect('main.db', check_same_thread=False)
conn.isolation_level = None
cursor = sqlite3.Cursor(conn)
users = {}

bot = Bot(token=TOKEN)
dp = Dispatcher()


async def check_user(tg_id):

    if tg_id in users.keys():
        return True
    else:
        user_id = cursor.execute(SELECT_USER_BY_TG, (tg_id, )).fetchone()[0]
        if user_id is not None:
            users[tg_id] = True
            return True
    return False


@dp.message(lambda x: x.chat.id in users.keys() and users[x.chat.id] is False)
async def input_token(message: Message):
    token = message.text
    tg_id = message.chat.id
    user_id = cursor.execute(TOKEN_CHECK, (token,)).fetchone()
    if user_id:
        cursor.execute(SET_TG_ID, (tg_id, user_id[0]))
        await message.answer('Вы успешно привязали ваш аккаунт')
    else:
        await message.answer("Неверный токен, вы можете получить его в личном кабинете")
    await message.delete()


@dp.message(F.text.in_({'/start'}))
async def start_menu(message: Message):
    tg_id = message.chat.id
    if not await check_user(tg_id):
        users[tg_id] = False
        await message.answer("Введите токен с сайта для подключения уведомлений")
    else:
        await message.answer("Вы уже подтвердили свой аккаунт")
    await message.delete()


async def startup():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(startup())