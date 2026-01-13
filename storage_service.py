"""
Storage Service - реализация критериев S3 для PostgreSQL
"""
import json
import gzip
import os
import shutil
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession

from logger import log
from db import (
    WeatherRecord, WeatherArchive, BackupRecord,
    DatabaseStats, engine, City
)
from config import (
    ARCHIVE_AFTER_DAYS, BACKUP_DIR, BACKUP_RETENTION_DAYS,
    STATS_UPDATE_INTERVAL, CLEANUP_INTERVAL
)


class StorageService:
    """Сервис для управления хранением данных с поддержкой S3-принципов"""

    def __init__(self):
        self.backup_dir = Path(BACKUP_DIR)
        self.backup_dir.mkdir(exist_ok=True, parents=True)

    async def archive_old_records(self, db: AsyncSession, days_old: int = None) -> Dict[str, Any]:
        """
        Архивация записей старше указанного количества дней
        Возвращает в архивную таблицу, помечая оригиналы как архивированные
        """
        if days_old is None:
            days_old = ARCHIVE_AFTER_DAYS

        cutoff_date = datetime.utcnow() - timedelta(days=days_old)
        cutoff_date_str = cutoff_date.strftime("%Y-%m-%d %H:%M:%S")

        log("storage", f"Начинаем архивацию записей старше {days_old} дней (до {cutoff_date_str})")

        try:
            # Находим записи для архивации
            stmt = select(WeatherRecord).where(
                WeatherRecord.created_at < cutoff_date,
                WeatherRecord.is_archived == False
            ).order_by(WeatherRecord.created_at)

            result = await db.execute(stmt)
            records_to_archive = result.scalars().all()

            if not records_to_archive:
                log("storage", "Нет записей для архивации")
                return {"archived": 0, "skipped": 0}

            archived_count = 0
            skipped_count = 0

            for record in records_to_archive:
                try:
                    # Создаем архивную запись
                    archive_record = WeatherArchive(
                        original_id=record.id,
                        date=record.date,
                        time_of_day=record.time_of_day,
                        temperature=record.temperature,
                        condition=record.condition,
                        city=record.city,
                        original_created_at=record.created_at,
                        archived_at=datetime.utcnow().replace(tzinfo=None)
                    )

                    db.add(archive_record)

                    # Помечаем оригинальную запись как архивированную
                    record.is_archived = True
                    record.updated_at = datetime.utcnow().replace(tzinfo=None)

                    archived_count += 1

                    if archived_count % 100 == 0:
                        log("storage", f"Архивировано {archived_count} записей...")

                except Exception as e:
                    log("error", f"Ошибка архивации записи {record.id}: {str(e)}")
                    skipped_count += 1
                    await db.rollback()
                    continue

            await db.commit()

            log("storage", f"✅ Архивация завершена: {archived_count} записей архивировано, {skipped_count} пропущено")

            return {
                "archived": archived_count,
                "skipped": skipped_count,
                "cutoff_date": cutoff_date_str
            }

        except Exception as e:
            await db.rollback()
            log("error", f"❌ Ошибка архивации: {str(e)}")
            return {"archived": 0, "skipped": 0, "error": str(e)}

    async def create_backup(self, db: AsyncSession, backup_type: str = "full") -> Optional[Dict[str, Any]]:
        """
        Создание резервной копии данных
        Типы: full (полная), incremental (инкрементальная)
        """
        log("storage", f"Создание {backup_type} бэкапа...")

        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"weather_backup_{backup_type}_{timestamp}"
            backup_filepath = self.backup_dir / f"{backup_filename}.json.gz"

            # Начинаем запись бэкапа
            backup_record = BackupRecord(
                filename=backup_filename,
                size_mb=0,
                record_count=0,
                backup_type=backup_type,
                status="in_progress",
                storage_path=str(backup_filepath)
            )

            db.add(backup_record)
            await db.commit()
            await db.refresh(backup_record)

            # Экспортируем данные в зависимости от типа бэкапа
            if backup_type == "full":
                # Полный бэкап всех данных
                result = await db.execute(select(WeatherRecord))
                records = result.scalars().all()

                result_archive = await db.execute(select(WeatherArchive))
                archive_records = result_archive.scalars().all()

                result_cities = await db.execute(select(City))
                cities = result_cities.scalars().all()

                backup_data = {
                    "metadata": {
                        "type": "full",
                        "created_at": datetime.now().isoformat(),
                        "version": "1.0"
                    },
                    "weather_records": [record.dict() for record in records],
                    "archive_records": [record.dict() for record in archive_records],
                    "cities": [city.dict() for city in cities]
                }

                record_count = len(records) + len(archive_records) + len(cities)

            else:  # incremental
                # Инкрементальный бэкап только новых данных
                last_backup = await db.execute(
                    select(BackupRecord)
                    .where(BackupRecord.status == "completed")
                    .order_by(BackupRecord.created_at.desc())
                    .limit(1)
                )

                last_backup_record = last_backup.scalar_one_or_none()

                if last_backup_record:
                    # Бэкап только записей, созданных после последнего бэкапа
                    result = await db.execute(
                        select(WeatherRecord)
                        .where(WeatherRecord.created_at > last_backup_record.created_at)
                    )
                    records = result.scalars().all()
                else:
                    # Если это первый инкрементальный бэкап
                    result = await db.execute(select(WeatherRecord))
                    records = result.scalars().all()

                backup_data = {
                    "metadata": {
                        "type": "incremental",
                        "created_at": datetime.now().isoformat(),
                        "version": "1.0"
                    },
                    "weather_records": [record.dict() for record in records]
                }

                record_count = len(records)

            # Сохраняем бэкап в сжатом JSON
            json_data = json.dumps(backup_data, ensure_ascii=False, default=str)

            with gzip.open(backup_filepath, 'wt', encoding='utf-8') as f:
                f.write(json_data)

            # Получаем размер файла
            file_size_mb = backup_filepath.stat().st_size / (1024 * 1024)

            # Обновляем запись о бэкапе
            backup_record.size_mb = round(file_size_mb, 2)
            backup_record.record_count = record_count
            backup_record.status = "completed"
            backup_record.created_at = datetime.utcnow().replace(tzinfo=None)

            await db.commit()

            log("storage", f"✅ Бэкап создан: {backup_filename} ({file_size_mb:.2f} MB, {record_count} записей)")

            return {
                "id": backup_record.id,
                "filename": backup_filename,
                "size_mb": file_size_mb,
                "record_count": record_count,
                "filepath": str(backup_filepath),
                "created_at": backup_record.created_at.isoformat()
            }

        except Exception as e:
            log("error", f"❌ Ошибка создания бэкапа: {str(e)}")

            # Помечаем бэкап как неудачный
            if 'backup_record' in locals():
                backup_record.status = "failed"
                await db.commit()

            return None

    async def restore_backup(self, db: AsyncSession, backup_id: int) -> Dict[str, Any]:
        """
        Восстановление данных из резервной копии
        """
        log("storage", f"Восстановление из бэкапа ID: {backup_id}")

        try:
            # Получаем информацию о бэкапе
            result = await db.execute(
                select(BackupRecord).where(BackupRecord.id == backup_id)
            )
            backup_record = result.scalar_one_or_none()

            if not backup_record:
                return {"success": False, "error": "Бэкап не найден"}

            if backup_record.status != "completed":
                return {"success": False, "error": "Бэкап не завершен или поврежден"}

            backup_filepath = Path(backup_record.storage_path)

            if not backup_filepath.exists():
                return {"success": False, "error": "Файл бэкапа не найден"}

            # Читаем данные из бэкапа
            with gzip.open(backup_filepath, 'rt', encoding='utf-8') as f:
                backup_data = json.load(f)

            restored_count = 0

            # Восстанавливаем данные в зависимости от типа бэкапа
            if backup_data["metadata"]["type"] == "full":
                # Полное восстановление
                # Очищаем существующие данные (осторожно!)
                await db.execute(text("TRUNCATE TABLE weather_records_current RESTART IDENTITY CASCADE"))
                await db.execute(text("TRUNCATE TABLE weather_records_archive RESTART IDENTITY CASCADE"))
                await db.execute(text("TRUNCATE TABLE cities RESTART IDENTITY CASCADE"))

                # Восстанавливаем города
                for city_data in backup_data.get("cities", []):
                    city = City(**city_data)
                    db.add(city)

                # Восстанавливаем текущие записи
                for record_data in backup_data.get("weather_records", []):
                    record = WeatherRecord(**record_data)
                    db.add(record)

                # Восстанавливаем архивные записи
                for archive_data in backup_data.get("archive_records", []):
                    archive = WeatherArchive(**archive_data)
                    db.add(archive)

                restored_count = (
                        len(backup_data.get("cities", [])) +
                        len(backup_data.get("weather_records", [])) +
                        len(backup_data.get("archive_records", []))
                )

            else:  # incremental
                # Инкрементальное восстановление (добавление данных)
                for record_data in backup_data.get("weather_records", []):
                    # Проверяем, существует ли уже запись
                    existing = await db.get(WeatherRecord, record_data.get("id"))
                    if not existing:
                        record = WeatherRecord(**record_data)
                        db.add(record)
                        restored_count += 1

            await db.commit()

            log("storage", f"✅ Восстановление завершено: {restored_count} записей восстановлено")

            return {
                "success": True,
                "restored_count": restored_count,
                "backup_type": backup_data["metadata"]["type"],
                "backup_date": backup_data["metadata"]["created_at"]
            }

        except Exception as e:
            await db.rollback()
            log("error", f"❌ Ошибка восстановления: {str(e)}")
            return {"success": False, "error": str(e)}

    async def cleanup_old_backups(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Очистка старых бэкапов по политике хранения
        """
        log("storage", "Очистка старых бэкапов...")

        try:
            cutoff_date = datetime.utcnow() - timedelta(days=BACKUP_RETENTION_DAYS)

            # Находим старые бэкапы
            result = await db.execute(
                select(BackupRecord)
                .where(BackupRecord.created_at < cutoff_date)
                .order_by(BackupRecord.created_at)
            )

            old_backups = result.scalars().all()

            deleted_count = 0
            deleted_size_mb = 0

            for backup in old_backups:
                try:
                    # Удаляем файл
                    if backup.storage_path:
                        backup_path = Path(backup.storage_path)
                        if backup_path.exists():
                            file_size = backup_path.stat().st_size / (1024 * 1024)
                            backup_path.unlink()
                            deleted_size_mb += file_size

                    # Удаляем запись из БД
                    await db.delete(backup)
                    deleted_count += 1

                except Exception as e:
                    log("error", f"Ошибка удаления бэкапа {backup.id}: {str(e)}")
                    continue

            await db.commit()

            log("storage", f"✅ Очистка завершена: {deleted_count} бэкапов удалено ({deleted_size_mb:.2f} MB)")

            return {
                "deleted_count": deleted_count,
                "deleted_size_mb": round(deleted_size_mb, 2),
                "cutoff_date": cutoff_date.isoformat()
            }

        except Exception as e:
            await db.rollback()
            log("error", f"❌ Ошибка очистки бэкапов: {str(e)}")
            return {"deleted_count": 0, "error": str(e)}

    async def update_database_stats(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Обновление статистики базы данных
        """
        try:
            # Считаем общее количество записей
            result = await db.execute(select(func.count(WeatherRecord.id)))
            total_records = result.scalar() or 0

            # Считаем активные записи (не архивированные)
            result = await db.execute(
                select(func.count(WeatherRecord.id))
                .where(WeatherRecord.is_archived == False)
            )
            active_records = result.scalar() or 0

            # Считаем архивные записи
            result = await db.execute(select(func.count(WeatherArchive.id)))
            archived_records = result.scalar() or 0

            # Считаем количество бэкапов
            result = await db.execute(select(func.count(BackupRecord.id)))
            backup_count = result.scalar() or 0

            # Вычисляем среднюю температуру
            try:
                result = await db.execute(
                    select(func.avg(func.cast(func.substring(WeatherRecord.temperature, 1, 3), Integer)))
                )
                avg_temp = result.scalar() or 0
            except:
                avg_temp = 0

            # Оцениваем размер базы данных
            # Это примерная оценка - в реальной системе нужно использовать pg_size_pretty
            estimated_size_mb = (total_records * 0.5) + (archived_records * 0.3) + (backup_count * 5)

            # Сохраняем статистику
            stats_record = DatabaseStats(
                date=datetime.utcnow().replace(tzinfo=None),
                total_records=total_records,
                active_records=active_records,
                archived_records=archived_records,
                backup_count=backup_count,
                total_size_mb=round(estimated_size_mb, 2),
                avg_temperature=round(avg_temp, 1)
            )

            db.add(stats_record)
            await db.commit()

            log("storage", f"📊 Статистика обновлена: {total_records} записей, {archived_records} в архиве")

            return {
                "total_records": total_records,
                "active_records": active_records,
                "archived_records": archived_records,
                "backup_count": backup_count,
                "total_size_mb": round(estimated_size_mb, 2),
                "avg_temperature": round(avg_temp, 1)
            }

        except Exception as e:
            await db.rollback()
            log("error", f"Ошибка обновления статистики: {str(e)}")
            return {"error": str(e)}

    async def get_storage_info(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Получение информации о хранилище
        """
        try:
            # Основная статистика
            stats_result = await self.update_database_stats(db)

            if "error" in stats_result:
                return stats_result

            # Информация о бэкапах
            result = await db.execute(
                select(BackupRecord)
                .order_by(BackupRecord.created_at.desc())
                .limit(5)
            )
            recent_backups = result.scalars().all()

            # Информация об архиве
            result = await db.execute(
                select(WeatherArchive)
                .order_by(WeatherArchive.archived_at.desc())
                .limit(1)
            )
            last_archived = result.scalar_one_or_none()

            # Сводная информация
            backup_files = list(self.backup_dir.glob("*.json.gz"))
            total_backup_size = sum(f.stat().st_size for f in backup_files) / (1024 * 1024)

            storage_info = {
                **stats_result,
                "backup_directory": str(self.backup_dir),
                "backup_files_count": len(backup_files),
                "total_backup_size_mb": round(total_backup_size, 2),
                "last_archive_date": last_archived.archived_at.isoformat() if last_archived else None,
                "recent_backups": [
                    {
                        "id": b.id,
                        "filename": b.filename,
                        "size_mb": b.size_mb,
                        "type": b.backup_type,
                        "created_at": b.created_at.isoformat(),
                        "status": b.status
                    }
                    for b in recent_backups
                ],
                "settings": {
                    "archive_after_days": ARCHIVE_AFTER_DAYS,
                    "backup_retention_days": BACKUP_RETENTION_DAYS,
                    "backup_dir": BACKUP_DIR
                }
            }

            return storage_info

        except Exception as e:
            log("error", f"Ошибка получения информации о хранилище: {str(e)}")
            return {"error": str(e)}


# Глобальный экземпляр сервиса
storage_service = StorageService()


async def start_storage_maintenance():
    """
    Фоновая задача для обслуживания хранилища
    """
    log("storage", "🚀 Запуск службы обслуживания хранилища")

    from db import DBSession

    while True:
        try:
            async with DBSession() as db:
                # 1. Обновляем статистику
                await storage_service.update_database_stats(db)

                # 2. Архивируем старые записи (раз в день)
                current_hour = datetime.now().hour
                if current_hour == 3:  # В 3 ночи
                    await storage_service.archive_old_records(db)

                # 3. Создаем бэкап (раз в день в 2 ночи)
                if current_hour == 2:
                    await storage_service.create_backup(db, backup_type="incremental")

                # 4. Очищаем старые бэкапы (раз в неделю в воскресенье)
                if datetime.now().weekday() == 6 and current_hour == 4:  # Воскресенье в 4 утра
                    await storage_service.cleanup_old_backups(db)

                await db.commit()

        except Exception as e:
            log("error", f"Ошибка в службе обслуживания хранилища: {str(e)}")

        # Ждем 1 час до следующей проверки
        await asyncio.sleep(3600)