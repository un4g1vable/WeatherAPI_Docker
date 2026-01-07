import asyncio
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from datetime import datetime
import re

from logger import log
from db import WeatherRecord, DBSession, City
from config import DEFAULT_CITY
from storage_service import start_storage_maintenance


class WeatherParser:
    def __init__(self, city_slug: str, city_name: str = None):
        self.city_slug = city_slug
        self.city_name = city_name or city_slug.capitalize()
        self.url = f"https://pogoda.mail.ru/prognoz/{city_slug}/extended/"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def get_weather(self):
        try:
            log("parser", f"Начинаем парсинг для {self.city_name} ({self.url})...")
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.raise_for_status()
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            weather_data = []
            current_date = None

            # Проходим по всем div-элементам на странице
            for element in soup.find_all('div'):
                text = element.get_text(strip=True)
                if not text:
                    continue

                # 1. Ищем строку с датой
                date_match = re.search(r'(?:Сегодня\s*-\s*)?(\d{1,2}\s+[а-я]+,\s*[а-я]+)', text)
                if date_match:
                    current_date = date_match.group(1)
                    # Если есть "Сегодня - ", убираем это
                    if 'Сегодня' in date_match.group(0):
                        current_date = date_match.group(1)
                    continue

                # 2. Если у нас есть текущая дата, ищем температурные данные
                if current_date:
                    # Ищем время суток и температуру
                    time_temp_match = re.search(r'(ночь|утро|день|вечер)[^\d]*([+-]?\d{1,2})°', text)
                    if time_temp_match:
                        time_of_day = time_temp_match.group(1)
                        temperature = time_temp_match.group(2) + "°"

                        # Пытаемся найти условия погоды
                        condition_text = re.sub(r'.*?°', '', text, count=1)
                        condition_text = re.sub(r'ощущается.*', '', condition_text).strip()
                        condition_text = re.sub(r'\d+.*', '', condition_text).strip()

                        # Если текст короткий (1-3 слова), это, скорее всего, условие
                        if condition_text and len(condition_text.split()) <= 3:
                            condition = condition_text
                        else:
                            condition = "Неизвестно"

                        weather_data.append({
                            "date": current_date,
                            "time_of_day": time_of_day,
                            "temperature": temperature,
                            "condition": condition,
                            "city_slug": self.city_slug,
                            "city_name": self.city_name
                        })

            log("parser", f"Спаршено {len(weather_data)} записей для {self.city_name}")
            return weather_data

        except requests.RequestException as e:
            log("error", f"Ошибка сети при парсинге {self.city_name}: {e}")
            return []
        except Exception as e:
            log("error", f"Ошибка при парсинге {self.city_name}: {e}")
            return []


async def background_weather_parser(db_session, city_slug):
    """Парсинг погоды с сохранением в БД"""
    log("parser", f"🚀 Запуск парсера для города: {city_slug}")

    # Получаем город из базы для получения имени
    city_result = await db_session.execute(select(City).where(City.slug == city_slug))
    city = city_result.scalar_one_or_none()

    if not city:
        log("error", f"Город {city_slug} не найден в базе")
        return {"success": False, "message": "Город не найден", "city_slug": city_slug}

    if not city.is_active:
        log("error", f"Город {city.name} отключен для парсинга")
        return {"success": False, "message": "Город отключен", "city_slug": city_slug}

    parser = WeatherParser(city_slug, city.name)
    weather_data = parser.get_weather()

    if not weather_data:
        log("parser", f"⚠️ Нет данных для города {city.name}")
        return {"success": False, "message": "Нет данных", "city_name": city.name}

    saved, updated = 0, 0
    errors = 0

    try:
        for item in weather_data:
            try:
                # Используем русское имя города из парсера
                item["city"] = city.name

                # Проверяем, существует ли уже запись
                stmt = select(WeatherRecord).where(
                    WeatherRecord.date == item["date"],
                    WeatherRecord.time_of_day == item["time_of_day"],
                    WeatherRecord.city == item["city"]
                )
                result = await db_session.execute(stmt)
                existing = result.scalar_one_or_none()

                if existing:
                    # Обновляем если изменились температура или условия
                    if (existing.temperature != item["temperature"] or
                            existing.condition != item["condition"]):
                        existing.temperature = item["temperature"]
                        existing.condition = item["condition"]
                        existing.updated_at = datetime.utcnow().replace(tzinfo=None)
                        updated += 1
                        log("db",
                            f"📝 Обновлено: {item['city']} - {item['date']} {item['time_of_day']} {item['temperature']}")
                else:
                    # Создаем новую запись
                    new_record = WeatherRecord(
                        date=item["date"],
                        time_of_day=item["time_of_day"],
                        temperature=item["temperature"],
                        condition=item["condition"],
                        city=item["city"],
                        created_at=datetime.utcnow().replace(tzinfo=None),
                        updated_at=datetime.utcnow().replace(tzinfo=None)
                    )
                    db_session.add(new_record)
                    saved += 1
                    log("db",
                        f"💾 Сохранено: {item['city']} - {item['date']} {item['time_of_day']} {item['temperature']}")

                await db_session.commit()

            except Exception as e:
                await db_session.rollback()
                errors += 1
                log("error", f"Ошибка при сохранении записи: {str(e)[:100]}")
                continue

        log("parser", f"✅ {city.name}: добавлено {saved}, обновлено {updated}, ошибок {errors}")
        return {
            "success": True,
            "saved": saved,
            "updated": updated,
            "errors": errors,
            "city_name": city.name
        }

    except Exception as e:
        log("error", f"❌ Общая ошибка при сохранении в БД: {e}")
        return {"success": False, "message": str(e), "city_name": city.name}


async def start_background_tasks():
    """Запуск всех фоновых задач"""
    log("system", "🚀 Запуск фоновых задач...")

    # Запускаем задачу обслуживания хранилища
    asyncio.create_task(start_storage_maintenance())

    log("system", "🔄 Автоматический парсинг отключен - только по запросу пользователя")
    log("system", "🛡️  Служба архивации и бэкапов запущена")

    while True:
        await asyncio.sleep(600)  # Основной цикл