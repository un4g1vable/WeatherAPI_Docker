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

# Настройки приложения
DEFAULT_CITY = os.getenv("DEFAULT_CITY", "ekaterinburg")
PARSER_INTERVAL = int(os.getenv("PARSER_INTERVAL", "600"))
