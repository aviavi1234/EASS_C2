import os
from pathlib import Path

from sqlmodel import SQLModel, Session, create_engine

from backend.paths import DEFAULT_DB_FILE, ensure_data_dirs


class DatabaseManager:
    def __init__(self, file_name: str | Path):
        ensure_data_dirs()

        db_path = Path(file_name)
        if not db_path.is_absolute():
            db_path = DEFAULT_DB_FILE.parent / db_path

        self.file_name = str(db_path)
        sqlite_url = f"sqlite:///{self.file_name}"

        connect_args = {"check_same_thread": False}
        self.engine = create_engine(sqlite_url, connect_args=connect_args)

    def create_db_and_tables(self):
        SQLModel.metadata.create_all(self.engine)

    def get_session(self):
        with Session(self.engine) as session:
            yield session


DB_FILENAME = os.getenv("C2_DB_FILE", str(DEFAULT_DB_FILE))
db = DatabaseManager(DB_FILENAME)
