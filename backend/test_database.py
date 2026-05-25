from sqlmodel import Session, select

from backend.database import db
from backend.models import PoiTypeDefinition, User


def test_database_tables_created(client):
    with Session(db.engine) as session:
        users = session.exec(select(User)).all()
        types = session.exec(select(PoiTypeDefinition)).all()
    assert len(users) >= 1
    assert len(types) >= 3


def test_default_admin_seeded(client):
    with Session(db.engine) as session:
        admin = session.exec(select(User).where(User.username == "admin")).first()
    assert admin is not None
    assert admin.role.value == "admin"
    assert admin.requires_setup is True


def test_default_poi_types_seeded(client):
    with Session(db.engine) as session:
        labels = {row.label for row in session.exec(select(PoiTypeDefinition)).all()}
    assert "Unknowns" in labels
    assert "Infentry" in labels
    assert "Tank" in labels


def test_seed_is_idempotent(client):
    with Session(db.engine) as session:
        before_users = len(session.exec(select(User)).all())
        before_types = len(session.exec(select(PoiTypeDefinition)).all())

    from scripts.init.seed import seed_poi_types, seed_users

    with Session(db.engine) as session:
        seed_users(session)
        seed_poi_types(session)
        after_users = len(session.exec(select(User)).all())
        after_types = len(session.exec(select(PoiTypeDefinition)).all())

    assert after_users == before_users
    assert after_types == before_types
