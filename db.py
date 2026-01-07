from datetime import datetime
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Field
from config import DB_URL

engine = create_async_engine(
    DB_URL,
    echo=False,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)

DBSession = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    class_=AsyncSession,
    expire_on_commit=False
)

class WeatherRecord(SQLModel, table=True):
    __tablename__ = "weather_records"

    id: int | None = Field(primary_key=True, index=True)
    date: str = Field(index=True)
    time_of_day: str
    temperature: str
    condition: str
    city: str = Field(index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(tzinfo=None),  # Без часового пояса!
        nullable=False
    )

async def get_db():
    db = DBSession()
    try:
        yield db
    finally:
        await db.close()