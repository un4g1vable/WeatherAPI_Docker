from sqlmodel import select
from db import engine, SQLModel, City
from config import CITIES
from logger import log


async def init_database():
    try:
        # Создаем таблицы
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        log("system", "✅ Таблицы созданы или уже существуют")

        # Проверяем и добавляем города из конфига
        async with engine.begin() as conn:
            for slug, name in CITIES.items():
                # Проверяем, существует ли город с таким slug
                result = await conn.execute(select(City).where(City.slug == slug))
                existing_city = result.first()

                if not existing_city:
                    # Город не существует, добавляем его
                    city = City(slug=slug, name=name, is_active=True)
                    await conn.merge(city)
                    log("db", f"✅ Добавлен город: {name} ({slug})")
                else:
                    log("db", f"ℹ️ Город уже существует: {name} ({slug})")

            await conn.commit()

        log("system", "✅ База данных инициализирована")
        log("system",
            "📊 Созданы таблицы: cities, weather_records_current, weather_records_archive, backup_records, database_stats")

        return True
    except Exception as e:
        log("error", f"❌ Ошибка инициализации базы данных: {e}")
        return False