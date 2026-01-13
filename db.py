from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlmodel import SQLModel, Field
from config import DB_URL
from typing import Optional

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

class City(SQLModel, table=True):
    __tablename__ = "cities"

    id: int | None = Field(primary_key=True, index=True)
    slug: str = Field(unique=True, index=True)
    name: str = Field(index=True)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(tzinfo=None),
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(tzinfo=None),
        nullable=False
    )

class WeatherRecord(SQLModel, table=True):
    __tablename__ = "weather_records_current"

    id: int | None = Field(primary_key=True, index=True)
    date: str = Field(index=True)
    time_of_day: str
    temperature: str
    condition: str
    city: str = Field(index=True)
    created_at: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(tzinfo=None),
        nullable=False
    )
    updated_at: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(tzinfo=None),
        nullable=False
    )
    is_archived: bool = Field(default=False)
    last_backup_date: Optional[datetime] = Field(default=None)

class WeatherArchive(SQLModel, table=True):
    __tablename__ = "weather_records_archive"

    id: int | None = Field(primary_key=True, index=True)
    original_id: int = Field(index=True)
    date: str = Field(index=True)
    time_of_day: str
    temperature: str
    condition: str
    city: str = Field(index=True)
    original_created_at: datetime
    archived_at: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(tzinfo=None),
        nullable=False
    )

class BackupRecord(SQLModel, table=True):
    __tablename__ = "backup_records"

    id: int | None = Field(primary_key=True, index=True)
    filename: str = Field(index=True)
    size_mb: float
    record_count: int
    backup_type: str = Field(default="full")  # full, incremental
    created_at: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(tzinfo=None),
        nullable=False
    )
    status: str = Field(default="completed")  # completed, failed, in_progress
    storage_path: Optional[str] = Field(default=None)

class DatabaseStats(SQLModel, table=True):
    __tablename__ = "database_stats"

    id: int | None = Field(primary_key=True, index=True)
    date: datetime = Field(
        default_factory=lambda: datetime.utcnow().replace(tzinfo=None),
        nullable=False,
        index=True
    )
    total_records: int
    active_records: int
    archived_records: int
    backup_count: int
    total_size_mb: float
    avg_temperature: float

async def get_db():
    db = DBSession()
    try:
        yield db
    finally:
        await db.close()