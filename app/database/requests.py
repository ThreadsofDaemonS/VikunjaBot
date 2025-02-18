from app.database.models import async_session
from app.database.models import User, Project
from sqlalchemy import select, update, delete, desc


def connection(func):
    async def inner(*args, **kwargs):
        async with async_session() as session:
            return await func(session, *args, **kwargs)

    return inner


@connection
async def set_user(session, token, username_tg, name_vikunja, chat_id):
    user = await session.scalar(select(User).where(User.chat_id == chat_id))

    if not user:
        session.add(User(chat_id=chat_id, token=token, username_tg=username_tg, name_vikunja=name_vikunja))
        await session.commit()

@connection
async def check_project_exist(session, new_project_id):
    existing_project = await session.scalar(select(Project).where(Project.project_id == new_project_id))
    if existing_project:
        return False
    else:
        return True



@connection
async def add_project_to_user(session, project_id, project_name, chat_id):
    # Ищем пользователя по chat_id
    user = await session.scalar(select(User).where(User.chat_id == chat_id))

    # Если пользователь найден, добавляем проект
    if user:
        # Создаём новый проект
        new_project = Project(project_id=project_id, name=project_name, user_id=user.id)  # Привязываем к пользователю
        session.add(new_project)

        # Привязываем проект к пользователю
        user.projects.append(new_project)  # Убедитесь, что это делается внутри сессии

        # Сохраняем изменения
        await session.commit()

        # print(f"Проект {project_name} успешно привязан к пользователю {user.username_tg}.")
    else:
        print(f"Пользователь с chat_id = {chat_id} не найден.")



@connection
async def get_projects_by_user(session, chat_id):
    # Ищем пользователя по chat_id
    user = await session.scalar(select(User).where(User.chat_id == chat_id))

    # Если пользователь найден, возвращаем его проекты
    if user:
        return user.projects  # Все проекты пользователя загружаются здесь
    else:
        print(f"Пользователь с chat_id = {chat_id} не найден.")
        return None



@connection
async def get_token(session, chat_id):
    return await session.execute(select(User.token).filter_by(chat_id=chat_id))
    # return await session.scalar(select(User).where(User.token == token))

@connection
async def get_name_vikunja(session, chat_id):
    return await session.execute(select(User.name_vikunja).filter_by(chat_id=chat_id))
    # return await session.scalar(select(User).where(User.token == token))


@connection
async def get_user_by_name_vikunja(session, name_vikunja):
    result = await session.execute(select(User).where(User.name_vikunja == name_vikunja))
    user = result.scalars().first()
    return user

@connection
async def get_users(session, chat_id):
    return await session.scalars(select(User))

@connection
async def get_user(session, chat_id):
    result = await session.execute(select(User).where(User.chat_id == chat_id))
    user = result.scalars().first()
    return user


@connection
async def delete_user(session, chat_id):
    try:
        # Выполняем запрос на выборку уникального пользователя
        result = await session.execute(
            select(User).filter(User.chat_id == chat_id).execution_options(populate_existing=True)
        )
        user_to_delete = result.scalars().unique().first()

        if user_to_delete:
            await session.delete(user_to_delete)
            await session.commit()
            print(f"Пользователь с chat_id={chat_id} успешно удалён.")
        else:
            print(f"Пользователь с chat_id={chat_id} не найден.")
    except Exception as e:
        await session.rollback()
        print(f"Ошибка: {e}")
