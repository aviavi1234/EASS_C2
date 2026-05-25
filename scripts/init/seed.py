"""Database seeding for first-time setup."""

from sqlmodel import Session, select

from backend.auth import hash_password
from backend.database import db
from backend.models import PoiTypeDefinition, User, UserRole

DEFAULT_USERS = [
    ("admin", "admin1234", UserRole.ADMIN, None),
]

DEFAULT_POI_TYPES: list[str] = [
    "Unknowns",
    "Infentry",
    "Tank",
]


def seed_users(session: Session) -> None:
    for username, password, role, permission in DEFAULT_USERS:
        existing = session.exec(select(User).where(User.username == username)).first()
        if existing:
            continue
        requires_setup = username == "admin"
        session.add(
            User(
                username=username,
                hashed_password=hash_password(password),
                role=role,
                permission=permission if role == UserRole.USER else None,
                requires_setup=requires_setup,
            )
        )
    session.commit()


def seed_poi_types(session: Session) -> None:
    if session.exec(select(PoiTypeDefinition)).first():
        return
    for label in DEFAULT_POI_TYPES:
        existing = session.exec(
            select(PoiTypeDefinition).where(PoiTypeDefinition.label == label)
        ).first()
        if existing:
            continue
        session.add(PoiTypeDefinition(label=label))
    session.commit()


def run_seed() -> None:
    db.create_db_and_tables()
    with Session(db.engine) as session:
        seed_users(session)
        seed_poi_types(session)


if __name__ == "__main__":
    run_seed()
