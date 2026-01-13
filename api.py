from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct, func
from typing import List, Optional
from datetime import datetime, timedelta

from db import WeatherRecord, City, get_db, engine, WeatherArchive, BackupRecord, DatabaseStats
from services import background_weather_parser, WeatherParser
from config import CITIES
from storage_service import storage_service

router = APIRouter()


# Модели для погоды
class WeatherCreate(BaseModel):
    date: str
    time_of_day: str
    temperature: str
    condition: str
    city: str


class WeatherUpdate(BaseModel):
    date: str | None = None
    time_of_day: str | None = None
    temperature: str | None = None
    condition: str | None = None
    city: str | None = None


# Модели для городов
class CityCreate(BaseModel):
    slug: str
    name: str
    is_active: bool = True


class CityUpdate(BaseModel):
    slug: str | None = None
    name: str | None = None
    is_active: bool | None = None


class ParseRequest(BaseModel):
    city_slug: str = "ekaterinburg"


# Модели для архивации и бэкапов
class ArchiveRequest(BaseModel):
    days_old: int = 30


class BackupRequest(BaseModel):
    backup_type: str = "incremental"  # full или incremental


class RestoreRequest(BaseModel):
    backup_id: int


# API для погоды (существующий функционал)
@router.get("/weather")
async def get_weather(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        include_archived: bool = Query(False),
        db: AsyncSession = Depends(get_db)
):
    query = select(WeatherRecord)

    if not include_archived:
        query = query.where(WeatherRecord.is_archived == False)

    query = query.order_by(WeatherRecord.created_at.desc()).offset(skip).limit(limit)

    result = await db.execute(query)
    records = result.scalars().all()

    # Получаем общее количество
    count_query = select(func.count(WeatherRecord.id))
    if not include_archived:
        count_query = count_query.where(WeatherRecord.is_archived == False)

    count_result = await db.execute(count_query)
    total = count_result.scalar() or 0

    return {
        "records": records,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(records)) < total
    }


@router.get("/weather/cities")
async def get_available_cities(db: AsyncSession = Depends(get_db)):
    """Получить список всех доступных городов"""
    result = await db.execute(select(City).where(City.is_active == True))
    cities = result.scalars().all()

    cities_dict = {city.slug: city.name for city in cities}
    return {
        "cities": cities_dict,
        "count": len(cities_dict),
        "default": "ekaterinburg"
    }


@router.get("/weather/cities/all")
async def get_all_cities(db: AsyncSession = Depends(get_db)):
    """Получить список всех городов (включая неактивные)"""
    result = await db.execute(select(City))
    cities = result.scalars().all()
    return [{"id": city.id, "slug": city.slug, "name": city.name, "is_active": city.is_active} for city in cities]


@router.get("/weather/cities/unique")
async def get_unique_cities_in_db(db: AsyncSession = Depends(get_db)):
    """Получить список городов, которые уже есть в базе данных"""
    result = await db.execute(select(distinct(WeatherRecord.city)))
    cities = result.scalars().all()
    return {"cities": cities, "count": len(cities)}


@router.get("/weather/{record_id}")
async def get_weather_record(record_id: int, db: AsyncSession = Depends(get_db)):
    record = await db.get(WeatherRecord, record_id)
    if not record:
        raise HTTPException(404)
    return record


@router.post("/weather", status_code=201)
async def create_weather(record: WeatherCreate, db: AsyncSession = Depends(get_db)):
    new = WeatherRecord(**record.dict())
    db.add(new)
    await db.commit()
    await db.refresh(new)
    return new


@router.patch("/weather/{record_id}")
async def update_weather(record_id: int, record_update: WeatherUpdate, db: AsyncSession = Depends(get_db)):
    record = await db.get(WeatherRecord, record_id)
    if not record:
        raise HTTPException(404)

    for k, v in record_update.dict(exclude_unset=True).items():
        setattr(record, k, v)

    record.updated_at = datetime.utcnow().replace(tzinfo=None)

    await db.commit()
    return record


@router.delete("/weather/{record_id}", status_code=204)
async def delete_weather(record_id: int, db: AsyncSession = Depends(get_db)):
    record = await db.get(WeatherRecord, record_id)
    if not record:
        raise HTTPException(404)

    await db.delete(record)
    await db.commit()


# API для городов
@router.get("/cities")
async def get_cities(db: AsyncSession = Depends(get_db)):
    """Получить все города"""
    result = await db.execute(select(City))
    cities = result.scalars().all()
    return cities


@router.get("/cities/{city_id}")
async def get_city(city_id: int, db: AsyncSession = Depends(get_db)):
    """Получить город по ID"""
    city = await db.get(City, city_id)
    if not city:
        raise HTTPException(404, detail="Город не найден")
    return city


@router.post("/cities", status_code=201)
async def create_city(city: CityCreate, db: AsyncSession = Depends(get_db)):
    """Создать новый город"""
    # Проверяем, существует ли уже город с таким slug
    existing = await db.execute(select(City).where(City.slug == city.slug))
    if existing.scalar_one_or_none():
        raise HTTPException(400, detail="Город с таким slug уже существует")

    new_city = City(**city.dict())
    db.add(new_city)
    await db.commit()
    await db.refresh(new_city)
    return new_city


@router.patch("/cities/{city_id}")
async def update_city(city_id: int, city_update: CityUpdate, db: AsyncSession = Depends(get_db)):
    """Обновить город"""
    city = await db.get(City, city_id)
    if not city:
        raise HTTPException(404, detail="Город не найден")

    update_data = city_update.dict(exclude_unset=True)
    for k, v in update_data.items():
        setattr(city, k, v)

    city.updated_at = datetime.utcnow().replace(tzinfo=None)

    await db.commit()
    await db.refresh(city)
    return city


@router.delete("/cities/{city_id}", status_code=204)
async def delete_city(city_id: int, db: AsyncSession = Depends(get_db)):
    """Удалить город"""
    city = await db.get(City, city_id)
    if not city:
        raise HTTPException(404, detail="Город не найден")

    await db.delete(city)
    await db.commit()


# API для парсинга
@router.post("/weather/parse")
async def run_parser(parse: ParseRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    """Запустить парсинг для конкретного города"""
    # Проверяем, существует ли город
    city_result = await db.execute(select(City).where(City.slug == parse.city_slug))
    city = city_result.scalar_one_or_none()

    if not city:
        raise HTTPException(status_code=404, detail=f"Город {parse.city_slug} не найден в базе")

    if not city.is_active:
        raise HTTPException(status_code=400, detail=f"Город {city.name} отключен для парсинга")

    background_tasks.add_task(background_weather_parser, db, parse.city_slug)
    return {
        "status": "started",
        "city": parse.city_slug,
        "city_name": city.name,
        "url": f"https://pogoda.mail.ru/prognoz/{parse.city_slug}/extended/",
        "message": f"Парсинг для города {city.name} запущен"
    }


@router.get("/weather/parser/test/{city_slug}")
async def test_parser(city_slug: str, db: AsyncSession = Depends(get_db)):
    """Тестирование парсера для конкретного города"""
    # Проверяем, существует ли город
    city_result = await db.execute(select(City).where(City.slug == city_slug))
    city = city_result.scalar_one_or_none()

    if not city:
        return {
            "success": False,
            "city": city_slug,
            "error": "Город не найден в базе",
            "message": f"Город {city_slug} не найден в базе данных"
        }

    try:
        parser = WeatherParser(city_slug, city.name)
        test_data = parser.get_weather()

        return {
            "success": True,
            "city": parser.city_name,
            "url": parser.url,
            "data_count": len(test_data),
            "data": test_data,
            "message": f"Парсер работает для города {parser.city_name}"
        }
    except Exception as e:
        return {
            "success": False,
            "city": city_slug,
            "error": str(e),
            "message": f"Ошибка парсера: {str(e)}"
        }


@router.get("/weather/parser/debug")
async def debug_parser(db: AsyncSession = Depends(get_db)):
    """Отладочная информация о парсере"""
    # Получаем первые 3 активных города
    result = await db.execute(select(City).where(City.is_active == True).limit(3))
    cities = result.scalars().all()

    results = {}
    for city in cities:
        try:
            parser = WeatherParser(city.slug, city.name)
            test_data = parser.get_weather()
            results[city.slug] = {
                "city": parser.city_name,
                "url": parser.url,
                "data_count": len(test_data),
                "sample": test_data[:2] if test_data else []
            }
        except Exception as e:
            results[city.slug] = {"error": str(e)}

    return {"debug": results}


# API для архивации и бэкапов (новый функционал S3)
@router.get("/storage/info")
async def get_storage_info(db: AsyncSession = Depends(get_db)):
    """Получить информацию о хранилище"""
    info = await storage_service.get_storage_info(db)
    if "error" in info:
        raise HTTPException(status_code=500, detail=info["error"])
    return info


@router.post("/storage/archive")
async def archive_weather(
        archive_request: ArchiveRequest = ArchiveRequest(),
        background_tasks: BackgroundTasks = None,
        db: AsyncSession = Depends(get_db)
):
    """Архивация старых записей"""
    if background_tasks:
        # Запускаем в фоне
        background_tasks.add_task(storage_service.archive_old_records, db, archive_request.days_old)
        return {
            "status": "started",
            "message": f"Архивация записей старше {archive_request.days_old} дней запущена в фоне"
        }
    else:
        # Выполняем синхронно
        result = await storage_service.archive_old_records(db, archive_request.days_old)
        return result


@router.get("/storage/archive/list")
async def get_archived_records(
        skip: int = Query(0, ge=0),
        limit: int = Query(100, ge=1, le=1000),
        db: AsyncSession = Depends(get_db)
):
    """Получить архивные записи"""
    query = select(WeatherArchive).order_by(WeatherArchive.archived_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    records = result.scalars().all()

    count_result = await db.execute(select(func.count(WeatherArchive.id)))
    total = count_result.scalar() or 0

    return {
        "records": records,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(records)) < total
    }


@router.post("/storage/backup")
async def create_backup(
        backup_request: BackupRequest = BackupRequest(),
        background_tasks: BackgroundTasks = None,
        db: AsyncSession = Depends(get_db)
):
    """Создание резервной копии"""
    if background_tasks:
        background_tasks.add_task(storage_service.create_backup, db, backup_request.backup_type)
        return {
            "status": "started",
            "message": f"Создание {backup_request.backup_type} бэкапа запущено в фоне"
        }
    else:
        result = await storage_service.create_backup(db, backup_request.backup_type)
        if result is None:
            raise HTTPException(status_code=500, detail="Ошибка создания бэкапа")
        return result


@router.get("/storage/backup/list")
async def get_backup_list(
        skip: int = Query(0, ge=0),
        limit: int = Query(50, ge=1, le=100),
        db: AsyncSession = Depends(get_db)
):
    """Получить список бэкапов"""
    query = select(BackupRecord).order_by(BackupRecord.created_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    backups = result.scalars().all()

    count_result = await db.execute(select(func.count(BackupRecord.id)))
    total = count_result.scalar() or 0

    return {
        "backups": backups,
        "total": total,
        "skip": skip,
        "limit": limit,
        "has_more": (skip + len(backups)) < total
    }


@router.post("/storage/restore")
async def restore_backup(
        restore_request: RestoreRequest,
        db: AsyncSession = Depends(get_db)
):
    """Восстановление из резервной копии"""
    result = await storage_service.restore_backup(db, restore_request.backup_id)

    if not result.get("success", False):
        raise HTTPException(status_code=500, detail=result.get("error", "Ошибка восстановления"))

    return result


@router.post("/storage/cleanup")
async def cleanup_backups(
        background_tasks: BackgroundTasks = None,
        db: AsyncSession = Depends(get_db)
):
    """Очистка старых бэкапов"""
    if background_tasks:
        background_tasks.add_task(storage_service.cleanup_old_backups, db)
        return {
            "status": "started",
            "message": "Очистка старых бэкапов запущена в фоне"
        }
    else:
        result = await storage_service.cleanup_old_backups(db)
        return result


@router.get("/storage/stats")
async def get_database_stats(
        days: int = Query(7, ge=1, le=365),
        db: AsyncSession = Depends(get_db)
):
    """Получить статистику базы данных"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)

    query = select(DatabaseStats).where(
        DatabaseStats.date >= cutoff_date
    ).order_by(DatabaseStats.date.desc())

    result = await db.execute(query)
    stats = result.scalars().all()

    # Вычисляем тренды
    if len(stats) >= 2:
        latest = stats[0]
        previous = stats[1]

        growth_rate = ((
                                   latest.total_records - previous.total_records) / previous.total_records * 100) if previous.total_records > 0 else 0

        trends = {
            "record_growth": latest.total_records - previous.total_records,
            "growth_rate_percent": round(growth_rate, 2),
            "archive_growth": latest.archived_records - previous.archived_records,
            "size_growth_mb": round(latest.total_size_mb - previous.total_size_mb, 2)
        }
    else:
        trends = {}

    return {
        "stats": stats,
        "trends": trends,
        "period_days": days
    }


@router.post("/storage/optimize")
async def optimize_database(
        background_tasks: BackgroundTasks = None,
        db: AsyncSession = Depends(get_db)
):
    """Оптимизация базы данных (VACUUM ANALYZE)"""
    if background_tasks:
        background_tasks.add_task(optimize_database_task, db)
        return {
            "status": "started",
            "message": "Оптимизация базы данных запущена в фоне"
        }
    else:
        await optimize_database_task(db)
        return {"status": "completed", "message": "Оптимизация завершена"}


async def optimize_database_task(db: AsyncSession):
    """Задача оптимизации базы данных"""
    from sqlalchemy import text

    try:
        log("storage", "Запуск оптимизации базы данных...")

        # Выполняем VACUUM ANALYZE для оптимизации
        await db.execute(text("VACUUM ANALYZE weather_records_current"))
        await db.execute(text("VACUUM ANALYZE weather_records_archive"))
        await db.execute(text("VACUUM ANALYZE backup_records"))

        await db.commit()

        log("storage", "✅ Оптимизация базы данных завершена")

    except Exception as e:
        log("error", f"Ошибка оптимизации базы данных: {str(e)}")
        await db.rollback()


# Эндпоинт для сброса базы данных (только для разработки)
@router.post("/admin/reset-db", include_in_schema=False)
async def reset_database_endpoint():
    """Сброс базы данных (только для разработки!)"""
    from sqlmodel import SQLModel

    # Удаляем все таблицы
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.drop_all)
        await conn.run_sync(SQLModel.metadata.create_all)

    # Добавляем города из конфига
    async with engine.begin() as conn:
        for slug, name in CITIES.items():
            city = City(slug=slug, name=name, is_active=True)
            await conn.merge(city)
        await conn.commit()

    return {"message": "База данных сброшена и инициализирована"}