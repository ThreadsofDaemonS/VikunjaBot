from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from decouple import config

from app.database.models import async_main

import logging
from aiogram.types import BotCommand, BotCommandScopeDefault, MenuButtonDefault
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

from app.user import user
from app.admin_panel import admin


# переменные для работы
ADMIN_ID = config('ADMIN_ID')
BOT_TOKEN = config("BOT_TOKEN")
HOST = config("HOST")
PORT = int(config("PORT"))
WEBHOOK_PATH = f'/{BOT_TOKEN}'
BASE_URL = config("BASE_URL")

# инициализируем бота и диспетчера для работы с ним
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()


# Функция для установки командного меню для бота
async def set_commands():
    # Создаем список команд, которые будут доступны пользователям
    commands = [
        BotCommand(command="start", description="Начать регистрацию"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="get_tasks", description="Получить таски по подписанным проектам, для фронтов - это все проекты"),
        BotCommand(command="get_project_tasks", description="Подписаться на таски по проекту"),
        BotCommand(command="delete_user", description="Удалить юзера в случае если регистрация прошла, а таски не идут")

    ]
    await bot.set_my_commands(commands)

    # Устанавливаем кнопку меню слева
    await bot.set_chat_menu_button(menu_button=MenuButtonDefault())


# Функция, которая будет вызвана при запуске бота
async def on_startup() -> None:
    await async_main()
    # Устанавливаем командное меню
    await set_commands()
    # Устанавливаем вебхук для приема сообщений через заданный URL
    await bot.set_webhook(f"{BASE_URL}{WEBHOOK_PATH}")
    # Отправляем сообщение администратору о том, что бот был запущен
    await bot.send_message(chat_id=ADMIN_ID, text='Бот запущен!')


# Функция, которая будет вызвана при остановке бота
async def on_shutdown() -> None:
    # Отправляем сообщение администратору о том, что бот был остановлен
    await bot.send_message(chat_id=ADMIN_ID, text='Бот остановлен!')
    # Удаляем вебхук и, при необходимости, очищаем ожидающие обновления
    await bot.delete_webhook(drop_pending_updates=True)
    # Закрываем сессию бота, освобождая ресурсы
    await bot.session.close()


# Основная функция, которая запускает приложение
def main() -> None:
    # Подключаем маршрутизаторы (роутер) для обработки сообщений
    dp.include_routers(user, admin)

    # Регистрируем функцию, которая будет вызвана при старте бота
    dp.startup.register(on_startup)

    # Регистрируем функцию, которая будет вызвана при остановке бота
    dp.shutdown.register(on_shutdown)

    # Создаем веб-приложение на базе aiohttp
    app = web.Application()

    # Настраиваем обработчик запросов для работы с вебхуком
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,  # Передаем диспетчер
        bot=bot  # Передаем объект бота
    )
    # Регистрируем обработчик запросов на определенном пути
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Настраиваем приложение и связываем его с диспетчером и ботом
    setup_application(app, dp, bot=bot)

    # Запускаем веб-сервер на указанном хосте и порте
    web.run_app(app, host=HOST, port=PORT)


# Точка входа в программу
if __name__ == "__main__":
    # Настраиваем логирование (информация, предупреждения, ошибки) и выводим их в консоль
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger = logging.getLogger(__name__)  # Создаем логгер для использования в других частях программы
    main()  # Запускаем основную функцию