from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db import WeatherRecord, get_db
from services import background_weather_parser

router = APIRouter()

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

class ParseRequest(BaseModel):
    city_slug: str = "ekaterinburg"

@router.get("/weather")
async def get_weather(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(WeatherRecord))
    return result.scalars().all()

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

    await db.commit()
    return record

@router.delete("/weather/{record_id}", status_code=204)
async def delete_weather(record_id: int, db: AsyncSession = Depends(get_db)):
    record = await db.get(WeatherRecord, record_id)
    if not record:
        raise HTTPException(404)

    await db.delete(record)
    await db.commit()

@router.post("/weather/parse")
async def run_parser(parse: ParseRequest, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    background_tasks.add_task(background_weather_parser, db, parse.city_slug)
    return {"status": "started"}