from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder

from pprint import pprint

from REST_API_requests import get_all_available_projects

from decouple import config

BASE_URL_VIKUNJA = config('BASE_URL_VIKUNJA')

main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Взять", callback_data='take')],
    [InlineKeyboardButton(text="Выполнено", callback_data='ready')]
])


cansel = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="Отмена", callback_data='cansel')]
])




async def inline_projects():
    projects = await get_all_available_projects()
    print(projects)

    # keyboard = InlineKeyboardBuilder()
    # for car in cars:
    #     keyboard.add(InlineKeyboardButton(text=car, url="https://google.com"))
    # return keyboard.adjust(2).as_markup()