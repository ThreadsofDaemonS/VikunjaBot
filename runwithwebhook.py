import logging
import ssl
import sys
from os import getenv
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import BotCommand, BotCommandScopeDefault, FSInputFile, MenuButtonDefault, Message
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from decouple import config

from app.database.models import async_main
from app.user import user
from app.admin_panel import admin

# Настройки SSL и переменные окружения
SELF_SSL = True
BOT_TOKEN = config('BOT_TOKEN')
ADMIN_ID = config('ADMIN_ID')
PROJECT_NAME = config('PROJECT_NAME')
DOMAIN = config('DOMAIN_IP') if SELF_SSL else config('DOMAIN_NAME')
WEBHOOK_PATH = f"/{PROJECT_NAME}"
EXTERNAL_PORT = 8443 if SELF_SSL else 8080
BASE_WEBHOOK_URL = f"https://{DOMAIN}:{EXTERNAL_PORT}"
#WEBHOOK_SECRET = config('WEBHOOK_SECRET')
WEBHOOK_SSL_CERT = config('WEBHOOK_SSL_CERT_PATH')
WEBHOOK_SSL_PRIV = config('WEBHOOK_SSL_PRIV_PATH')

# Хост и порт для веб-сервера
WEB_SERVER_HOST = DOMAIN if SELF_SSL else "127.0.0.1"
WEB_SERVER_PORT = EXTERNAL_PORT

# Инициализация бота и диспетчера
bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# Функция для установки команд бота
async def set_commands():
    commands = [
        BotCommand(command="start", description="Начать регистрацию"),
        BotCommand(command="help", description="Помощь"),
        BotCommand(command="get_tasks", description="Получить таски по проектам"),
        BotCommand(command="get_project_tasks", description="Подписаться на таски проекта"),
        BotCommand(command="delete_user", description="Удалить юзера")
    ]
    await bot.set_my_commands(commands)
    await bot.set_chat_menu_button(menu_button=MenuButtonDefault())

# Функция для старта
async def on_startup():
    await async_main()
    await set_commands()
    if SELF_SSL:
        await bot.set_webhook(
            f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}",
            certificate=FSInputFile(WEBHOOK_SSL_CERT)
            #secret_token=WEBHOOK_SECRET
        )
    else:
        await bot.set_webhook(f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}") #secret_token=WEBHOOK_SECRET
    await bot.send_message(ADMIN_ID, text="Бот запущен!")

# Функция для остановки
async def on_shutdown():
    await bot.send_message(ADMIN_ID, text="Бот остановлен!")
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.session.close()

# Основная функция для запуска бота и веб-сервера
def main():
    # Подключаем маршрутизаторы (роутеры)
    dp.include_routers(user, admin)

    # Регистрируем функции старта и остановки
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Создаем веб-приложение
    app = web.Application()

    # Настраиваем обработчик запросов
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot
        # secret_token=WEBHOOK_SECRET
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)

    # Связываем приложение и бот
    setup_application(app, dp, bot=bot)

    if SELF_SSL:
        # Настраиваем SSL для самоподписанного сертификата
        context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        context.load_cert_chain(WEBHOOK_SSL_CERT, WEBHOOK_SSL_PRIV)
        web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT, ssl_context=context)
    else:
        web.run_app(app, host=WEB_SERVER_HOST, port=WEB_SERVER_PORT)

if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    main()
