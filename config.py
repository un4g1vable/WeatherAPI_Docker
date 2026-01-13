# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Настройки базы данных
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "weather_db")
DB_USER = os.getenv("DB_USER", "weather_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "weather_pass")

# Формируем URL для подключения
DB_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Настройки репликации (для масштабирования)
DB_REPLICA_HOST = os.getenv("DB_REPLICA_HOST", "localhost")
DB_REPLICA_PORT = os.getenv("DB_REPLICA_PORT", "5433")
DB_REPLICA_URL = f"postgresql+asyncpg://{DB_USER}:{DB_PASSWORD}@{DB_REPLICA_HOST}:{DB_REPLICA_PORT}/{DB_NAME}"

# Настройки приложения
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "ekaterinburg")
PARSER_INTERVAL = int(os.getenv("PARSER_INTERVAL", "600"))

# Настройки архивации и бэкапов
ARCHIVE_AFTER_DAYS = int(os.getenv("ARCHIVE_AFTER_DAYS", "30"))
BACKUP_INTERVAL_HOURS = int(os.getenv("BACKUP_INTERVAL_HOURS", "24"))
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "90"))
BACKUP_DIR = os.getenv("BACKUP_DIR", "./backups")

# Настройки мониторинга
STATS_UPDATE_INTERVAL = int(os.getenv("STATS_UPDATE_INTERVAL", "3600"))  # 1 час
CLEANUP_INTERVAL = int(os.getenv("CLEANUP_INTERVAL", "86400"))  # 24 часа

# Настройки шардирования (подготовка к масштабированию)
SHARD_COUNT = int(os.getenv("SHARD_COUNT", "1"))
SHARD_KEY = os.getenv("SHARD_KEY", "city")  # Поле для шардирования

# Список доступных городов для парсинга (с правильными slug)
CITIES = {
    "ekaterinburg": "Екатеринбург",
    "moskva": "Москва",
    "saint-petersburg": "Санкт-Петербург",
    "novosibirsk": "Новосибирск",
    "kazan": "Казань",
    "omsk": "Омск",
    "chelyabinsk": "Челябинск",
    "ufa": "Уфа",
    "krasnoyarsk": "Красноярск",
    "perm": "Пермь",
    "volgograd": "Волгоград",
    "voronezh": "Воронеж",
    "saratov": "Саратов",
    "tyumen": "Тюмень",
    "krasnodar": "Краснодар"
}