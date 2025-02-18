from aiogram import F, Router
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram import Bot
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from app.REST_API_requests import get_all_available_projects, get_buckets, task_changing, get_task, get_project
from pprint import pprint

import asyncio
from datetime import datetime
from decouple import config
# from dotenv import load_dotenv
# load_dotenv()

from app.states import Login
from app.database.requests import (set_user, get_token, delete_user, get_name_vikunja, get_user_by_name_vikunja, get_user,
                                   add_project_to_user, get_projects_by_user, check_project_exist)

from bs4 import BeautifulSoup

BASE_URL_VIKUNJA = config('BASE_URL_VIKUNJA')

user = Router()

assignees = ''
sent_tasks = []

# 5490098347,

ALLOWED_CHAT_IDS = [5490098347, 6135458595, 7369803652, 218985148, 5418562140, 254138581]

@user.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.set_state(Login.name_vikunja)
    await msg.answer("Добавьте name в Vikunja желательно такое же которое было при регистрации в Vikunja")
    await msg.reply(f"Привет! Введи свой name от Vikunja")


@user.message(Login.name_vikunja)
async def login_first(message: Message, state: FSMContext):
    await state.update_data(name_vikunja=message.text.strip())
    await state.set_state(Login.token)
    await message.answer("Введите Ваш токен")


@user.message(Login.token)
async def login_second(message: Message, state: FSMContext):
    await state.update_data(token=message.text.strip())
    data = await state.get_data()
    try:
        await set_user(chat_id=message.from_user.id, token=data['token'], username_tg=message.from_user.username,
                       name_vikunja=data['name_vikunja'])
        await message.answer(f"Вход завершен\nВаш токен {data['token']}\nВаш name Vikunja: {data['name_vikunja']}")
    except Exception as e:
        print(e)
        await message.answer("Вы ввели неправильный логин или пароль, нажмите комманду /start для того чтобы залогинится")

    await state.clear()


@user.message(Command("help"))
async def get_help(msg: Message):
    await msg.answer("Комманды которые присутствуют:\n/help\n/start для регистрации\n")
    await msg.answer("Комманада /get_project_tasks поможет вам выбрать проект и подписаться на него")
    await msg.answer("Комманада /get_tasks покажет вам таски на подписанные проекты, для фронтов и админов все проекты")
    await msg.answer("Если не удается зайти нажмите эту комманду и попробуйте перерегистрироваться /delete_user")
    await msg.answer("Токен можно найти в настройках профиля в Vikunja")
    await msg.answer("Добавьте имя в Vikunja желательно такое же которое было при регистрации в Vikunja")


@user.message(Command("delete_user"))
async def delete_from_database(message: Message):
    await delete_user(chat_id=message.from_user.id)
    await message.answer("Удалено из базы данных успешно, можете пересоздать профиль нажав на кнопку /start")


@user.message(Command('get_project_tasks'))
async def cmd_get_projects(message: Message):
    #projects_ids = []
    result = await get_token(message.from_user.id)
    user_token = result.scalar()
    # res = await get_name_vikunja(message.from_user.id)
    # Vikunja_username = res.scalar()
    headers = {
        "Authorization": f"Bearer {user_token}"
    }
    projects = await get_all_available_projects(BASE_URL_VIKUNJA, headers)

    # Создаем инлайн-клавиатуру для проектов
    builder = InlineKeyboardBuilder()

    # Добавляем кнопки с проектами по 2 в ряд
    for project in projects:
        builder.button(text=project['title'], callback_data=f"select_project_{project['id']}")

    # Расставляем кнопки по 2 в ряд
    builder.adjust(2)

    # Отправляем сообщение с инлайн-клавиатурой
    await message.answer("Вот доступные вам проекты:", reply_markup=builder.as_markup())


@user.callback_query(lambda c: c.data and c.data.startswith('select_project_'))
async def handle_project_selection(callback: CallbackQuery, bot: Bot):
    global assignees
    project_id = callback.data.split('_')[2]  # Получаем project_id из callback_data

    result = await get_token(callback.from_user.id)
    user_token = result.scalar()
    headers = {
        "Authorization": f"Bearer {user_token}"
    }
    project = await get_project(BASE_URL_VIKUNJA, project_id, headers)
    res_exist = await check_project_exist(project_id)
    if res_exist:
        await add_project_to_user(project_id, project['title'], callback.from_user.id)
    await callback.answer(f"Вы выбрали проект {project['title']}", show_alert=False)
    res = await get_name_vikunja(callback.from_user.id)
    Vikunja_name = res.scalar()
    buckets = await get_buckets(BASE_URL_VIKUNJA, project_id, headers)
    # print(buckets)
    buckets_and_tasks = {}
    count = 0
    bucket_name = ''
    for bucket in buckets:
        count += 1
        if count <= 2:
            bucket_name = bucket['title']
            buckets_and_tasks[project_id] = {bucket['id']: bucket['tasks']}
            try:
                # print(buckets_and_tasks[project_id][bucket['id']])
                for task in buckets_and_tasks[project_id][bucket['id']]:

                    string = ''
                    soup = BeautifulSoup(task['description'], 'html.parser')
                    description = soup.get_text()
                    if task["assignees"]:
                        string = (
                                f" 🆘TASK {task['identifier']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
                                f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}👨‍👧‍👦\n\n Исполнители: {task['assignees'][0]['name']}\n\n" +
                                f"🙈 Время создания: {task['created']}\n\n💻 Статус: {'Проверка' if task['done'] else bucket_name}\n\n🙈Время завершения: {task['done_at']}")
                    else:
                        string = (
                                f"🆘TASK {task['identifier']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
                                f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}👨‍👧‍👦\n\n Исполнители: \n\n" +
                                f"🙈 Время создания: {task['created']}\n\n💻 Статус: {'Проверка' if task['done'] else bucket_name}\n\n🙈Время завершения: {task['done_at']}")

                    main = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Взять", callback_data=f"take_{task['id']}_{project_id}")],
                        [InlineKeyboardButton(text="Выполнено", callback_data=f"complete_{task['id']}_{project_id}")]
                    ])
                    await callback.message.answer(string, reply_markup=main)
                    # await callback.answer(string, reply_markup=main)
            except TypeError:
                exit_response = "Task is empty"

        else:
            break

    buckets = await get_buckets(BASE_URL_VIKUNJA, project_id, headers)
    count = 0
    for bucket in buckets:
        try:
            for task in bucket['tasks']:
                if task['assignees']:
                    if task['assignees'][0]['name'] == Vikunja_name:
                        assignees = task['assignees']
                        break

        except TypeError:
            exit_response = "Empty assignees"


async def poll_vikunja_for_tasks(bot, user_id, message):
    global sent_tasks
    global assignees
    if message.from_user.id in ALLOWED_CHAT_IDS:
        while True:  # Опрос каждые 60 секунд
            try:
                result = await get_token(user_id)
                user_token = result.scalar()
                res = await get_name_vikunja(user_id)
                Vikunja_name = res.scalar()
                headers = {
                    "Authorization": f"Bearer {user_token}"
                }


                projects = await get_all_available_projects(BASE_URL_VIKUNJA, headers)
                print(f"📢 Проекты получены")
                if not projects:
                    print("⚠️ Ошибка: нет доступных проектов!")
                    return
                for project in projects:
                    project_id = project['id']
                    buckets = await get_buckets(BASE_URL_VIKUNJA, project_id, headers)
                    count = 0
                    bucket_name = ''
                    print(f"📌 Проект: {project['title']}, ID: {project_id}")
                    if not buckets:
                        print(f"⚠️ Ошибка: нет бакетов в проекте {project['title']}")
                        continue
                    for bucket in buckets:
                        count += 1
                        if count <= 2:
                            bucket_name = bucket['title']
                            try:
                                if 'tasks' not in bucket or not bucket['tasks']:
                                    print(f"⚠️ Ошибка: В bucket '{bucket['title']}' (ID: {bucket['id']}) нет задач!")
                                    continue
                                for task in bucket['tasks']:
                                    # Проверяем, была ли задача уже отправлена
                                    print(f"📋 Уже отправленные задачи: {sent_tasks}")
                                    if task['id'] in sent_tasks:
                                        continue  # Пропускаем уже отправленные задачи

                                    string = ''
                                    soup = BeautifulSoup(task['description'], 'html.parser')
                                    description = soup.get_text()

                                    if task["assignees"]:
                                        string = (
                                                f"📬Project {project['title']}\n\n 🆘TASK {task['identifier']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
                                                f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}\n\n Исполнители: {task['assignees'][0]['name']}\n\n" +
                                                f"🙈 Время создания: {task['created']}\n\n💻 Статус: {'Проверка' if task['done'] else bucket_name}\n\n🙈Время завершения: {task['done_at']}")
                                    else:
                                        string = (
                                                f"📬Project {project['title']}\n\n🆘TASK {task['identifier']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
                                                f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}\n\n Исполнители: \n\n" +
                                                f"🙈 Время создания: {task['created']}\n\n💻 Статус: {'Проверка' if task['done'] else bucket_name}\n\n🙈Время завершения: {task['done_at']}")

                                    main = InlineKeyboardMarkup(inline_keyboard=[
                                        [InlineKeyboardButton(text="Взять",
                                                              callback_data=f"take_{task['id']}_{project_id}")],
                                        [InlineKeyboardButton(text="Выполнено",
                                                              callback_data=f"complete_{task['id']}_{project_id}")]
                                    ])

                                    print(f"📩 Отправка таски: {task['title']} (ID: {task['id']})")

                                    # Отправляем задачу
                                    await message.answer(string, reply_markup=main)

                                    # Добавляем task_id в список отправленных задач
                                    sent_tasks.append(task['id'])

                            except TypeError:
                                exit_response = "Task is empty"

                        else:
                            break

                    # Обновляем информацию об исполнителях
                    for bucket in buckets:
                        try:
                            for task in bucket['tasks']:
                                if task['assignees']:
                                    if task['assignees'][0]['name'] == Vikunja_name:
                                        assignees = task['assignees']
                                        break
                        except TypeError:
                            exit_response = "Empty assignees"

                # Ждем 60 секунд перед следующим опросом
                await asyncio.sleep(60)
            except Exception as e:
                print(e)
    else:
        while True:  # Опрос каждые 60 секунд
            try:
                projects_list = await get_projects_by_user(user_id)

                if projects_list:
                    for project in projects_list:
                        result = await get_token(user_id)
                        user_token = result.scalar()

                        headers = {
                            "Authorization": f"Bearer {user_token}"
                        }
                        currentProject = await get_project(BASE_URL_VIKUNJA, project.project_id, headers)
                        # await message.answer(f"Вот задания из проекта {project.name}")
                        res = await get_name_vikunja(user_id)
                        Vikunja_name = res.scalar()

                        buckets = await get_buckets(BASE_URL_VIKUNJA, project.project_id, headers)

                        buckets_and_tasks = {}
                        count = 0
                        bucket_name = ''
                        for bucket in buckets:
                            count += 1
                            if count <= 2:
                                bucket_name = bucket['title']
                                buckets_and_tasks[project.project_id] = {bucket['id']: bucket['tasks']}
                                try:
                                    for task in buckets_and_tasks[project.project_id][bucket['id']]:
                                        # Проверяем, была ли задача уже отправлена
                                        if task['id'] in sent_tasks:
                                            continue  # Пропускаем уже отправленные задачи

                                        string = ''
                                        soup = BeautifulSoup(task['description'], 'html.parser')
                                        description = soup.get_text()

                                        if task["assignees"]:
                                            string = (
                                                    f" 🆘TASK {task['identifier']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
                                                    f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}\n\n Исполнители: {task['assignees'][0]['name']}\n\n" +
                                                    f"🙈 Время создания: {task['created']}\n\n💻 Статус: {'Проверка' if task['done'] else bucket_name}\n\n🙈Время завершения: {task['done_at']}")
                                        else:
                                            string = (
                                                    f"🆘TASK {task['identifier']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
                                                    f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}\n\n Исполнители: \n\n" +
                                                    f"🙈 Время создания: {task['created']}\n\n💻 Статус: {'Проверка' if task['done'] else bucket_name}\n\n🙈Время завершения: {task['done_at']}")

                                        main = InlineKeyboardMarkup(inline_keyboard=[
                                            [InlineKeyboardButton(text="Взять",
                                                                  callback_data=f"take_{task['id']}_{project.project_id}")],
                                            [InlineKeyboardButton(text="Выполнено",
                                                                  callback_data=f"complete_{task['id']}_{project.project_id}")]
                                        ])

                                        # Отправляем задачу
                                        await message.answer(string, reply_markup=main)

                                        # Добавляем task_id в список отправленных задач
                                        sent_tasks.append(task['id'])

                                except TypeError:
                                    exit_response = "Task is empty"
                                    # print(exit_response)

                            else:
                                break

                    # Обновляем информацию об исполнителях
                    count = 0
                    for bucket in buckets:
                        try:
                            for task in bucket['tasks']:
                                if task['assignees']:
                                    if task['assignees'][0]['name'] == Vikunja_name:
                                        assignees = task['assignees']
                                        break
                        except TypeError:
                            exit_response = "Empty assignees"
                            # print(exit_response)

                # Ждем 60 секунд перед следующим опросом
                await asyncio.sleep(60)
            except Exception as e:
                print(e)

@user.message(Command('get_tasks'))
async def cmd_get_tasks(message: Message):
    # Запускаем задачу для опроса в фоновом режиме
    asyncio.create_task(poll_vikunja_for_tasks(message.bot, message.from_user.id, message))
    # await message.answer("Начат опрос задач из Vikunja каждые 60 секунд.")




# @user.message(Command('get_tasks'))
# async def cmd_get_tasks(message: Message):
#     global assignees
#     projects_list = await get_projects_by_user(message.from_user.id)
#
#     if projects_list:
#         for project in projects_list:
#             result = await get_token(message.from_user.id)
#             user_token = result.scalar()
#
#             headers = {
#                 "Authorization": f"Bearer {user_token}"
#             }
#             currentProject = await get_project(BASE_URL_VIKUNJA, project.project_id, headers)
#             await message.answer(f"Вот задания из проекта {project.name}")
#             res = await get_name_vikunja(message.from_user.id)
#             Vikunja_name = res.scalar()
#
#             buckets = await get_buckets(BASE_URL_VIKUNJA, project.project_id, headers)
#
#
#             buckets_and_tasks = {}
#             count = 0
#             bucket_name = ''
#             for bucket in buckets:
#
#                 count += 1
#                 if count <= 2:
#                     bucket_name = bucket['title']
#                     buckets_and_tasks[project.project_id] = {bucket['id']: bucket['tasks']}
#                     try:
#                         # print(buckets_and_tasks[project_id][bucket['id']])
#                         for task in buckets_and_tasks[project.project_id][bucket['id']]:
#
#                             string = ''
#                             soup = BeautifulSoup(task['description'], 'html.parser')
#                             description = soup.get_text()
#                             if task["assignees"]:
#                                 string = (
#                                         f" 🆘TASK {task['identifier']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
#                                         f"👨‍👧‍👦 Заказчик: {task["created_by"]["username"]}👨‍👧‍👦\n\n Исполнители: {task["assignees"][0]["name"]}\n\n" +
#                                         f"🙈 Время создания: {task["created"]}\n\n💻 Статус: {'Проверка' if task["done"] else bucket_name}\n\n🙈Время завершения: {task["done_at"]}")
#                             else:
#                                 string = (
#                                         f"🆘TASK {task['identifier']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
#                                         f"👨‍👧‍👦 Заказчик: {task["created_by"]["username"]}👨‍👧‍👦\n\n Исполнители: \n\n" +
#                                         f"🙈 Время создания: {task["created"]}\n\n💻 Статус: {'Проверка' if task["done"] else bucket_name}\n\n🙈Время завершения: {task["done_at"]}")
#
#
#                             main = InlineKeyboardMarkup(inline_keyboard=[
#                                 [InlineKeyboardButton(text="Взять", callback_data=f"take_{task['id']}_{project.project_id}")],
#                                 [InlineKeyboardButton(text="Выполнено",
#                                                       callback_data=f"complete_{task['id']}_{project.project_id}")]
#                             ])
#                             await message.answer(string, reply_markup=main)
#                             # await callback.answer(string, reply_markup=main)
#                     except TypeError:
#                         exit_response = "Task is empty"
#                         # print(exit_response)
#
#                 else:
#                     break
#
#             buckets = await get_buckets(BASE_URL_VIKUNJA, project.project_id, headers)
#             count = 0
#             for bucket in buckets:
#                 try:
#                     for task in bucket['tasks']:
#                         if task['assignees']:
#                             if task['assignees'][0]['name'] == Vikunja_name:
#                                 assignees = task['assignees']
#                                 break
#
#                 except TypeError:
#                     exit_response = "Empty assignees"
#                     # print(exit_response)
#
#
#
#     else:
#         await message.answer(f"Вы не выбрали проект - нажмите на кнопку /get_project_tasks")



# @user.message(Command('get_tasks_admin'))
# async def cmd_get_tasks_admin(message: Message):
#     if message.from_user.id not in ALLOWED_CHAT_IDS:
#         await message.answer("У вас нет доступа к этой команде.")
#         return
#     global assignees
#     #projects_ids = []
#     result = await get_token(message.from_user.id)
#     user_token = result.scalar()
#     res = await get_name_vikunja(message.from_user.id)
#     Vikunja_name = res.scalar()
#     headers = {
#         "Authorization": f"Bearer {user_token}"
#     }
#     # Всё-таки нужно в 2 цикла + ещё projects надо закрепить ещё учитывать что оно проходит по нескольким проектам
#     # Нужен словарь
#     buckets_and_tasks = {}
#     assignees = ''
#     projects = await get_all_available_projects(BASE_URL_VIKUNJA, headers)
#     for project in projects:
#         project_id = project['id']
#         buckets = await get_buckets(BASE_URL_VIKUNJA, project_id, headers)
#         count = 0
#         bucket_name = ''
#         for bucket in buckets:
#             count += 1
#             if count <= 2:
#                 bucket_name = bucket['title']
#                 buckets_and_tasks[project_id] = {bucket['id']: bucket['tasks']}
#                 try:
#                     #print(buckets_and_tasks[project_id][bucket['id']])
#                     for task in buckets_and_tasks[project_id][bucket['id']]:
#
#                         string = ''
#                         soup = BeautifulSoup(task['description'], 'html.parser')
#                         description = soup.get_text()
#                         if task["assignees"]:
#                             string = (
#                                     f"📬Project {project['title']}\n\n 🆘TASK {task['identifier']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
#                                     f"👨‍👧‍👦 Заказчик: {task["created_by"]["username"]}👨‍👧‍👦\n\n Исполнители: {task["assignees"][0]["name"]}\n\n" +
#                                     f"🙈 Время создания: {task["created"]}\n\n💻 Статус: {'Проверка' if task["done"] else bucket_name}\n\n🙈Время завершения: {task["done_at"]}")
#                         else:
#                             string = (
#                                     f"📬Project {project['title']}\n\n🆘TASK {task['identifier']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
#                                     f"👨‍👧‍👦 Заказчик: {task["created_by"]["username"]}👨‍👧‍👦\n\n Исполнители: \n\n" +
#                                     f"🙈 Время создания: {task["created"]}\n\n💻 Статус: {'Проверка' if task["done"] else bucket_name}\n\n🙈Время завершения: {task["done_at"]}")
#
#
#                         main = InlineKeyboardMarkup(inline_keyboard=[
#                             [InlineKeyboardButton(text="Взять", callback_data=f"take_{task['id']}_{project_id}")],
#                             [InlineKeyboardButton(text="Выполнено", callback_data=f"complete_{task['id']}_{project_id}")]
#                         ])
#
#                         await message.answer(string, reply_markup=main)
#                 except TypeError:
#                     exit_response = "Task is empty"
#
#             else:
#                 break
#
#     for project in projects:
#         project_id = project['id']
#         buckets = await get_buckets(BASE_URL_VIKUNJA, project_id, headers)
#         count = 0
#         for bucket in buckets:
#             try:
#                 for task in bucket['tasks']:
#                     if task['assignees']:
#                         if task['assignees'][0]['name'] == Vikunja_name:
#                             assignees = task['assignees']
#                             break
#
#             except TypeError:
#                 exit_response = "Empty assignees"

active_tasks = set()  # Множество для отслеживания активных задач в bucket «В Работе»
checked_tasks = set()  # Множество для задач, находящихся в bucket «Проверка»


@user.callback_query(lambda c: c.data and (c.data.startswith('take_') or c.data.startswith('complete_')))
async def task_take_or_complete(callback: CallbackQuery, bot: Bot):
    global assignees, active_tasks, checked_tasks
    action, task_id, project_id = callback.data.split('_', 2)

    # Проверка на доступность задачи
    if task_id in active_tasks or task_id in checked_tasks:
        await callback.answer("Эта задача уже занята или в проверке.", show_alert=True)
        return


    if assignees:
        payload = {
            "done": False,
            "bucket_id": None,
            "assignees": assignees,
            "description": None
        }
    else:
        payload = {
            "done": False,
            "bucket_id": None,
            "description": None
        }

    result = await get_token(callback.from_user.id)
    user_token = result.scalar()
    headers = {
        "Authorization": f"Bearer {user_token}"
    }

    bucket_ids = []
    buckets = await get_buckets(BASE_URL_VIKUNJA, project_id, headers)
    for bucket in buckets:
        bucket_ids.append(bucket["id"])
    bucket_ids.sort()


    project = await get_project(BASE_URL_VIKUNJA, project_id, headers)
    member = await get_user(callback.from_user.id)

    if action == "take":
        # Получаем текущую задачу, чтобы извлечь описание
        task = await get_task(BASE_URL_VIKUNJA, task_id, headers)
        current_description = task.get('description', '')  # Получаем текущее описание задачи

        payload["bucket_id"] = bucket_ids[2]  # Колонка "В Работе"
        payload["description"] = current_description  # Сохраняем описание задачи

        await task_changing(BASE_URL_VIKUNJA, payload, task_id, headers)
        task = await get_task(BASE_URL_VIKUNJA, task_id, headers)

        description = BeautifulSoup(task['description'], 'html.parser').get_text()
        assignee_info = f"{task['assignees'][0]['name']} {'@' + member.username_tg if member else ''}" if task.get(
            "assignees") else f"{'@' + member.username_tg if member else ''}"

        task_info = (
            f"📬Project {project['title']}\n\n 🆘TASK {task['id']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n"
            f"👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n"
            f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}👨‍👧‍👦\n\n Исполнители: {assignee_info}\n\n"
            f"🙈 Время создания: {task['created']}\n\n💻 Статус: В работе\n\n🙈Время завершения: {task['done_at']}"
        )

        await callback.message.edit_text(task_info)

        active_tasks.add(task_id)
        main_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="Готово", callback_data=f"finish_{task['id']}_{project_id}")]])

        try:
            task_creator = await get_user_by_name_vikunja(task['created_by']['name'])
            await bot.send_message(chat_id=task_creator.chat_id, text=task_info, reply_markup=main_markup)
        except Exception as e:
            print(e)

    elif action == "complete":
        # Получаем текущую задачу, чтобы извлечь описание
        task = await get_task(BASE_URL_VIKUNJA, task_id, headers)
        current_description = task.get('description', '')  # Получаем текущее описание задачи

        payload["bucket_id"] = bucket_ids[3]  # Колонка "Проверка"
        payload["done"] = True
        payload["description"] = current_description  # Сохраняем описание задачи

        await task_changing(BASE_URL_VIKUNJA, payload, task_id, headers)
        await task_changing(BASE_URL_VIKUNJA, payload, task_id, headers)
        task = await get_task(BASE_URL_VIKUNJA, task_id, headers)

        description = BeautifulSoup(task['description'], 'html.parser').get_text()
        assignee_info = f"{task['assignees'][0]['name']} {'@' + member.username_tg if member else ''}" if task.get(
            "assignees") else f"{'@' + member.username_tg if member else ''}"

        task_info = (
            f"📬Project {project['title']}\n\n 🆘TASK {task['id']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n"
            f"👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n"
            f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}👨‍👧‍👦\n\n Исполнители: {assignee_info}\n\n"
            f"🙈 Время создания: {task['created']}\n\n💻 Статус: Проверка\n\n🙈Время завершения: {task['done_at']}"
        )

        await callback.message.edit_text(task_info)

        active_tasks.discard(task_id)
        checked_tasks.add(task_id)

        main_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Готово", callback_data=f"finish_{task['id']}_{project_id}")],
        ])
        try:
            task_creator = await get_user_by_name_vikunja(task['created_by']['name'])
            await bot.send_message(chat_id=task_creator.chat_id, text=task_info, reply_markup=main_markup)
        except Exception as e:
            print(e)

    # Обработка действий
    # if action == "take":
    #     payload["bucket_id"] = bucket_ids[2]  # Колонка "В Работе"
    #     await task_changing(BASE_URL_VIKUNJA, payload, task_id, headers)
    #     task = await get_task(BASE_URL_VIKUNJA, task_id, headers)
    #
    #     # Обновляем описание задачи
    #     description = BeautifulSoup(task['description'], 'html.parser').get_text()
    #     assignee_info = f"{task['assignees'][0]['name']} {'@' + member.username_tg if member else ''}" if task[
    #         "assignees"] else f"{'@' + member.username_tg if member else ''}"
    #
    #     task_info = (
    #         f"📬Project {project['title']}\n\n 🆘TASK {task['id']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n"
    #         f"👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n"
    #         f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}👨‍👧‍👦\n\n Исполнители: {assignee_info}\n\n"
    #         f"🙈 Время создания: {task['created']}\n\n💻 Статус: В работе\n\n🙈Время завершения: {task['done_at']}"
    #     )
    #
    #     await callback.message.edit_text(task_info)
    #
    #     # Отправляем уведомление о взятии задачи и обновляем активные задачи
    #     active_tasks.add(task_id)
    #     main_markup = InlineKeyboardMarkup(
    #         inline_keyboard=[[InlineKeyboardButton(text="Готово", callback_data=f"finish_{task['id']}_{project_id}")]])
    #
    #     try:
    #         task_creator = await get_user_by_name_vikunja(task['created_by']['name'])
    #         await bot.send_message(chat_id=task_creator.chat_id, text=task_info, reply_markup=main_markup)
    #     except Exception as e:
    #         print(e)
    #
    # elif action == "complete":
    #     payload["bucket_id"] = bucket_ids[3]  # Колонка "Проверка"
    #     payload["done"] = True
    #     await task_changing(BASE_URL_VIKUNJA, payload, task_id, headers)
    #     await task_changing(BASE_URL_VIKUNJA, payload, task_id, headers)
    #     task = await get_task(BASE_URL_VIKUNJA, task_id, headers)
    #
    #     description = BeautifulSoup(task['description'], 'html.parser').get_text()
    #     assignee_info = f"{task['assignees'][0]['name']} {'@' + member.username_tg if member else ''}" if task[
    #         "assignees"] else f"{'@' + member.username_tg if member else ''}"
    #
    #     task_info = (
    #         f"📬Project {project['title']}\n\n 🆘TASK {task['id']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n"
    #         f"👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n"
    #         f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}👨‍👧‍👦\n\n Исполнители: {assignee_info}\n\n"
    #         f"🙈 Время создания: {task['created']}\n\n💻 Статус: Проверка\n\n🙈Время завершения: {task['done_at']}"
    #     )
    #
    #     await callback.message.edit_text(task_info)
    #
    #     # Обновляем состояния активных и проверяемых задач
    #     active_tasks.discard(task_id)
    #     checked_tasks.add(task_id)
    #
    #     main_markup = InlineKeyboardMarkup(inline_keyboard=[
    #         [InlineKeyboardButton(text="Готово", callback_data=f"finish_{task['id']}_{project_id}")],
    #     ])
    #     try:
    #         task_creator = await get_user_by_name_vikunja(task['created_by']['name'])
    #         await bot.send_message(chat_id=task_creator.chat_id, text=task_info, reply_markup=main_markup)
    #     except Exception as e:
    #         print(e)


@user.callback_query(lambda c: c.data and (c.data.startswith('finish_')))
async def task_finish(callback: CallbackQuery):
    # Вот этот блок исправить
    global assignees
    # вот тут исправить и затестировать
    action, task_id, project_id = callback.data.split('_', 2)
    if assignees:
        payload = {
            "done": False,
            "bucket_id": None,
            "assignees": assignees,
            "description": None
        }
    else:
        payload = {
            "done": False,
            "bucket_id": None,
            "description": None
        }

    result = await get_token(callback.from_user.id)
    user_token = result.scalar()
    headers = {
        "Authorization": f"Bearer {user_token}"
    }
    bucket_ids = []
    buckets = await get_buckets(BASE_URL_VIKUNJA, project_id, headers)
    for bucket in buckets:
        bucket_ids.append(bucket["id"])

    project = await get_project(BASE_URL_VIKUNJA, project_id, headers)
    member = await get_user(callback.from_user.id)
    bucket_ids.sort()

    if action == "finish":
        task = await get_task(BASE_URL_VIKUNJA, task_id, headers)
        current_description = task.get('description', '')
        await callback.answer(f'Вы выбрали завершить задачу {task_id} и перенесли в колонку Готово', show_alert=False)
        payload["bucket_id"] = bucket_ids[4]
        payload["done"] = True
        payload["description"] = current_description
        await task_changing(BASE_URL_VIKUNJA, payload, task_id, headers)

        soup = BeautifulSoup(task['description'], 'html.parser')
        description = soup.get_text()
        if task["assignees"]:
            string = (
                    f"📬Project {project['title']}\n\n 🆘TASK {task['id']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
                    f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}👨‍👧‍👦\n\n Исполнители: {task['assignees'][0]['name']} {'@' + member.username_tg if member else ''}\n\n" +
                    f"🙈 Время создания: {task['created']}\n\n💻 Статус: Готово\n\n🙈Время завершения: {task['done_at']}")
        else:
            string = (
                    f"📬Project {project['title']}\n\n🆘TASK {task['id']}\n\n🕔 Время: {datetime.now().replace(microsecond=0)}\n\n👓 Заголовок: {task['title']}\n\n👀 Описание: {description}\n\n" +
                    f"👨‍👧‍👦 Заказчик: {task['created_by']['username']}👨‍👧‍👦\n\n Исполнители: {'@' + member.username_tg if member else ''}\n\n" +
                    f"🙈 Время создания: {task['created']}\n\n💻 Статус: Готово\n\n🙈Время завершения: {task['done_at']}")
        await callback.message.edit_text(string)