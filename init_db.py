import asyncio
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlmodel import SQLModel
from config import DB_URL
from logger import log


async def init_database():
    try:
        engine = create_async_engine(DB_URL, echo=False)

        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        await engine.dispose()
        log("system", "База данных успешно инициализирована")
        return True
    except Exception as e:
        log("error", f"Ошибка при инициализации БД: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(init_database())
    sys.exit(0 if success else 1)