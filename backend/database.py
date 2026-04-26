import os
from pathlib import Path
from sqlmodel import SQLModel, Session, create_engine


class DatabaseManager:
    def __init__(self, file_name: str):
        base_dir = Path(__file__).resolve().parent
        data_dir = base_dir / "Data"
        data_dir.mkdir(parents=True, exist_ok=True)

        db_path = Path(file_name)
        if not db_path.is_absolute() and db_path.parent == Path("."):
            db_path = data_dir / file_name

        self.file_name = str(db_path)
        sqlite_url = f"sqlite:///{self.file_name}"

        connect_args = {"check_same_thread": False}
        self.engine = create_engine(sqlite_url, connect_args=connect_args)

    def create_db_and_tables(self):
        SQLModel.metadata.create_all(self.engine)

    def get_session(self):
        with Session(self.engine) as session:
            yield session


DB_FILENAME = os.getenv("C2_DB_FILE", "c2_database.db")
db = DatabaseManager(DB_FILENAME)
