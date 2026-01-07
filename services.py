import asyncio
import requests
from bs4 import BeautifulSoup
from sqlalchemy import select
from datetime import datetime

from logger import log
from db import WeatherRecord, DBSession
from config import DEFAULT_CITY, PARSER_INTERVAL


class WeatherParser:
    def __init__(self, city_slug: str):
        self.city_slug = city_slug
        self.city_name = city_slug.capitalize()
        self.url = f"https://pogoda.mail.ru/prognoz/{city_slug}/extended/"
        self.headers = {'User-Agent': 'Mozilla/5.0'}

    def get_weather(self):
        try:
            response = requests.get(self.url, headers=self.headers, timeout=10)
            response.encoding = 'utf-8'
            soup = BeautifulSoup(response.text, 'html.parser')

            weather_data = []
            date_elements = soup.find_all('span', class_='hdr__inner')

            for i, date_elem in enumerate(date_elements):
                date_text = date_elem.get_text(strip=True)
                if i == 0 and date_text.startswith("Сегодня - "):
                    date_text = date_text.replace("Сегодня - ", "")

                date_div = date_elem.find_parent('div', class_='hdr')
                weather_block = date_div.find_next_sibling('div', class_='p-flex')
                if not weather_block:
                    continue

                for block in weather_block.find_all('div', class_='p-flex__column_percent-16'):
                    time_of_day = block.find('span', class_='text_bold_normal')
                    temperature = block.find('span', class_='text_bold_medium')
                    condition = block.find('span', class_='text_light_normal', title=True)

                    if time_of_day and temperature:
                        weather_data.append({
                            "date": date_text,
                            "time_of_day": time_of_day.get_text(strip=True),
                            "temperature": temperature.get_text(strip=True),
                            "condition": condition.get_text(strip=True) if condition else "",
                            "city": self.city_name
                        })

            log("parser", f"Спаршено {len(weather_data)} записей для {self.city_name}")
            return weather_data
        except Exception as e:
            log("error", f"Ошибка при парсинге: {e}")
            return []


async def background_weather_parser(db_session, city_slug=DEFAULT_CITY):
    """Парсинг погоды с сохранением в БД"""
    city_name = city_slug.capitalize()
    log("parser", f"Парсинг погоды для {city_name}")

    parser = WeatherParser(city_slug)
    weather_data = parser.get_weather()

    if not weather_data:
        log("parser", f"Нет данных для {city_name}")
        return

    saved, updated = 0, 0

    try:
        for item in weather_data:
            try:
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
                        updated += 1
                        log("db", f"Обновлено: {item['date']} {item['time_of_day']} {item['temperature']}")
                else:
                    # Создаем новую запись с явным указанием created_at БЕЗ часового пояса
                    new_record = WeatherRecord(
                        date=item["date"],
                        time_of_day=item["time_of_day"],
                        temperature=item["temperature"],
                        condition=item["condition"],
                        city=item["city"],
                        created_at=datetime.utcnow().replace(tzinfo=None)  # Важно: без tzinfo!
                    )
                    db_session.add(new_record)
                    saved += 1
                    log("db", f"Сохранено: {item['date']} {item['time_of_day']} {item['temperature']}")

                await db_session.commit()

            except Exception as e:
                await db_session.rollback()
                log("error", f"Ошибка при сохранении записи: {str(e)[:100]}...")
                continue

        log("parser", f"{city_name}: успешно добавлено {saved}, обновлено {updated}")

    except Exception as e:
        log("error", f"Общая ошибка при сохранении в БД: {e}")


async def start_background_tasks():
    """Фоновая задача, которая запускается автоматически"""
    while True:
        await asyncio.sleep(PARSER_INTERVAL)

        # Создаем новую сессию для каждой задачи
        async with DBSession() as db:
            try:
                await background_weather_parser(db)
            except Exception as e:
                log("error", f"Ошибка в фоновой задаче: {e}")
            finally:
                await db.close()