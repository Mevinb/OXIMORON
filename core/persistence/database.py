import os
import shutil
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from sqlalchemy import event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from core.persistence.models import Base

DEFAULT_DB_PATH = Path.home() / ".oximoron" / "oximoron.db"

class DatabaseManager:
    def __init__(self, db_path: Path | None = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self._engine: AsyncEngine | None = None
        self._session_factory: async_sessionmaker[AsyncSession] | None = None

    async def initialize(self) -> None:
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create database backup before initialization if db already exists
        if self.db_path.exists() and self.db_path.stat().st_size > 0:
            backup_path = self.db_path.with_suffix(f".backup_{int(os.path.getmtime(self.db_path))}.db")
            try:
                shutil.copy2(self.db_path, backup_path)
            except Exception:
                pass

        db_url = f"sqlite+aiosqlite:///{self.db_path}"
        self._engine = create_async_engine(
            db_url,
            echo=False,
            future=True,
        )

        # Enforce WAL mode and foreign keys on SQLite
        @event.listens_for(self._engine.sync_engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        self._session_factory = async_sessionmaker(
            self._engine,
            expire_on_commit=False,
            class_=AsyncSession,
        )

        # Create tables
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    async def close(self) -> None:
        if self._engine:
            await self._engine.dispose()
            self._engine = None

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        if not self._session_factory:
            raise RuntimeError("DatabaseManager not initialized. Call initialize() first.")
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
