import time
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from logger import log
from db import engine, SQLModel
from services import start_background_tasks
from api import router
from init_db import init_database

app = FastAPI(
    title="Weather Monitoring API",
    version="1.0",
    description="Weather Monitoring API — сервис для сбора, хранения и мониторинга погодных данных."
)


@app.on_event("startup")
async def startup():
    log("system", "Запуск Weather Monitoring API")

    # Инициализация базы данных
    if await init_database():
        log("system", "База данных готова к работе")
    else:
        log("error", "Не удалось инициализировать базу данных")

    # Запускаем фоновую задачу
    asyncio.create_task(start_background_tasks())
    log("system", "Фоновая задача запущена")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    log("http", f"{request.method} {request.url.path} {response.status_code} ({time.time() - start_time:.3f}s)")
    return response


app.include_router(router)


@app.get("/")
async def root():
    return {"message": "Weather Monitoring API", "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "weather-api",
        "timestamp": time.time(),
        "database": "connected"
    }