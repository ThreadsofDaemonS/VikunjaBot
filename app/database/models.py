from sqlalchemy import String, BigInteger, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine

engine = create_async_engine(url='sqlite+aiosqlite:///db.sqlite3', echo=False)
async_session = async_sessionmaker(engine)


class Base(AsyncAttrs, DeclarativeBase):
    pass


class User(Base):
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(primary_key=True)
    token: Mapped[str] = mapped_column(String(100), unique=True, index=True)
    username_tg: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    name_vikunja: Mapped[str] = mapped_column(String(15), unique=True, index=True)
    chat_id = mapped_column(BigInteger, unique=True, index=True)

    # Связь с проектами
    projects = relationship("Project", back_populates="user", lazy='joined')


class Project(Base):
    __tablename__ = 'projects'

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(Integer, unique=True)
    name: Mapped[str] = mapped_column(String(100), unique=True)

    # Связь с пользователем
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    user = relationship("User", back_populates="projects")


async def async_main():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)