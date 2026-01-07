![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?style=for-the-badge&logo=postgresql&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)

# 🌤️ Weather Monitoring API


Асинхронный сервис мониторинга погоды с REST API, WebSocket уведомлениями, фоновым парсингом и интеграцией с NATS.

## 🚀 Функциональность

### ✅ REST API
- `GET /` - информация о сервисе и навигация
- `GET /health` - проверка состояния сервиса и подключения к БД
- `GET /weather` - получить все записи о погоде
- `GET /weather/{id}` - получить запись по ID
- `POST /weather` - создать запись о погоде вручную
- `PATCH /weather/{id}` - обновить запись
- `DELETE /weather/{id}` - удалить запись
- `POST /weather/parse` - принудительно запустить парсинг погоды для города

### 🔄 Фоновая задача
- Автоматический парсинг погоды с сайта Mail.ru каждые 10 минут
- Сохранение данных в PostgreSQL базу данных
- Умное обновление: только новые или измененные записи


## 🛠 Технологии

- **FastAPI** - асинхронный веб-фреймворк
- **SQLModel** - ORM для работы с БД
- **PostgreSQL 15** - реляционная база данных в Docker
- **Docker & Docker Compose** - контейнеризация и оркестрация
- **BeautifulSoup4** - парсинг HTML страниц
- **Colorama** - цветное логирование


## 📦 Установка и запуск


```bash
# 1. Установка Docker
https://www.docker.com/products/docker-desktop/

# 2. Клонирование репозитория
git clone https://github.com/un4g1vable/WeatherAPI_Docker.git
cd WeatherAPI_Docker

# 3. Запуск
docker-compose up --build

# 4. Открыть в браузере
Документация: http://localhost:8000/docs
Проверка: http://localhost:8000/health
